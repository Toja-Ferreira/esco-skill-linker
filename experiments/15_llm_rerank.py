"""Listwise LLM reranking, local against API.

The last method, and the first with the capability the oracle's headroom
requires. Experiment 14's cross-encoders scored candidates independently and
reproduced the first stage's ordering without exceeding it. A listwise model
sees the whole shortlist at once and can compare candidates against each other,
which is exactly what the oracle does.

Two backends behind one interface, so the comparison answers a question the
project has not been able to ask: **does paying buy quality, or only speed?**
A local model costs nothing per query and runs on the GPU; an API model costs
money and latency. If they score the same, the cheap one wins and that is worth
knowing. DeepSeek is the API choice because the 2024 thesis used it for exactly
this stage, making this the closest available comparison against the original
system.

Malformed output is counted, never silently repaired. A model that mangles a
tenth of its queries is not usable however good its mean looks, so the rate of
invalid indices, duplicates, omissions and unparsable responses is reported
alongside the metrics.

Writes, one set per model:
    results/llm_rerank_dev_<model>.csv
    results/llm_rerank_test_<model>.csv
    results/llm_rerank_per_query_<model>.csv
    results/llm_rerank_<model>.md

Usage:
    python -m experiments.15_llm_rerank --model qwen3-4b-local --dev-sample 200
    python -m experiments.15_llm_rerank --model deepseek --dev-sample 200
    python -m experiments.15_llm_rerank --model deepseek --render-only
"""

from __future__ import annotations

import argparse
import time
from collections.abc import Sequence
from pathlib import Path

import numpy as np
import pandas as pd

from src.eval.metrics import DEFAULT_KS, aggregate, bootstrap_ci, evaluate_query
from src.retrieval.fusion import weighted_score_fusion
from src.retrieval.llm_rerank import LLMS, apply_ranking, build_llm_reranker

REPO_ROOT = Path(__file__).resolve().parents[1]
PROCESSED = REPO_ROOT / "data" / "processed"
BENCHMARK = REPO_ROOT / "data" / "benchmark"
RUNS = REPO_ROOT / "data" / "runs"
RESULTS = REPO_ROOT / "results"

LANGUAGES = ("pt", "en")
GRADES = {"essential": 2, "optional": 1}
SELECT_ON = "ndcg@10"
DENSE = "embeddinggemma"

# Shallower than the cross-encoder sweep: every candidate goes in one prompt,
# so depth drives prompt length, cost and the chance of a malformed response.
# Depth 50 puts roughly 2,900 tokens per prompt into the KV cache, which was
# enough to destabilise a 12GB card even at batch 2, so the default stops at
# 20 and deeper shortlists are opt-in.
DEPTHS = (10, 20)

# The model is asked for the best TOP_K of the shortlist rather than a full
# ordering. Only the top 10 affects nDCG@10, generating 10 numbers instead of
# 50 cuts decode time several-fold, and picking a few winners is an easier
# task than totally ordering 50 near-duplicates. Everything not named keeps
# its first-stage order below.
TOP_K = 10
HEADLINE = ["precision@10", "recall@10", "mrr", "ndcg@10", "micro_recall@10"]


def load():
    splits = pd.read_csv(BENCHMARK / "splits.csv")
    texts = pd.read_parquet(PROCESSED / "texts.parquet")
    rel = pd.read_parquet(PROCESSED / "occupation_skill_relations.parquet")
    gold: dict[str, dict[str, int]] = {}
    for occ, skill, rtype in zip(rel["occupationUri"], rel["skillUri"],
                                 rel["relationType"]):
        gold.setdefault(occ, {})[skill] = GRADES[rtype]
    return splits, texts, gold


def load_run(path: Path, only: set[str] | None = None) -> dict:
    df = pd.read_parquet(path)
    if only is not None:
        df = df[df["query"].isin(only)]
    df = df.sort_values(["query", "rank"])
    run: dict[str, list[tuple[str, float]]] = {}
    for q, skill, score in zip(df["query"], df["skillUri"], df["score"]):
        run.setdefault(q, []).append((skill, float(score)))
    return run


def fusion_weight(lang: str) -> float:
    """Dev-selected hybrid weight from experiment 13, read from its records."""
    dev = pd.read_csv(RESULTS / "fusion_dev.csv")
    sub = dev[dev["combination"] == f"hybrid {lang}"]
    if "beta" in sub.columns:
        sub = sub[sub["beta"].isna()]
    if sub.empty:
        raise SystemExit("Run experiments/13_fusion.py first.")
    return float(sub.loc[sub[SELECT_ON].idxmax(), "weight"])


def first_stage(lang: str, split: str, only: Sequence[str] | None = None):
    keep = set(only) if only is not None else None
    bm25 = load_run(RUNS / f"bm25_{lang}_{split}.parquet", keep)
    dense = load_run(RUNS / f"{DENSE}_{lang}_{split}.parquet", keep)
    w = fusion_weight(lang)
    return weighted_score_fusion([bm25, dense], [w, 1.0 - w])


def candidate_text(texts, lang: str) -> dict[str, str]:
    t = texts[(texts["language"] == lang) & (texts["conceptKind"] == "skill")]
    return {u: f"{p}. {d}" if d else p
            for u, p, d in zip(t["conceptUri"], t["preferredLabel"],
                               t["description"])}


def truncate(text: str, words: int = 40) -> str:
    """Keep candidate entries short so a 50-way prompt stays manageable."""
    parts = text.split()
    return " ".join(parts[:words]) + ("..." if len(parts) > words else "")


def run_depth(reranker, fused, query_uris, occ_desc, docs, gold, depth):
    queries, cand_lists, uris = [], [], []
    for q in query_uris:
        cands = [d for d, _ in fused.get(q, [])][:depth]
        if not cands:
            continue
        queries.append(occ_desc[q])
        cand_lists.append([truncate(docs.get(c, "")) for c in cands])
        uris.append((q, cands))

    t0 = time.perf_counter()
    results = reranker.rank(queries, cand_lists, top_k=TOP_K)
    wall = time.perf_counter() - t0

    per_query, repairs = {}, []
    for (q, cands), res in zip(uris, results):
        order = apply_ranking(cands, res)
        ranked = [cands[i] for i in order]
        tail = [d for d, _ in fused.get(q, [])][depth:]
        per_query[q] = evaluate_query((ranked + tail)[:max(DEFAULT_KS)], gold[q])
        repairs.append({
            "invalid": res.invalid, "duplicates": res.duplicates,
            "missing": res.missing, "unparsable": int(res.unparsable),
            "raw": res.raw,
            "prompt_tokens": res.prompt_tokens,
            "completion_tokens": res.completion_tokens,
        })
    return per_query, pd.DataFrame(repairs), wall


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="qwen3-4b-local", choices=list(LLMS))
    ap.add_argument("--dev-sample", type=int, default=200)
    ap.add_argument("--depths", type=int, nargs="+", default=list(DEPTHS),
                    help="shortlist depths to sweep on dev")
    # 8 fits at depth 10 but not at 20 on a 12GB card, and under WSL the
    # driver spills to system RAM instead of raising, which is a silent 10x
    # slowdown. Batch size also changes padding and therefore fp16 rounding,
    # so keep it fixed across runs that should reproduce each other.
    ap.add_argument("--batch-size", type=int, default=4)
    ap.add_argument("--max-workers", type=int, default=8)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--render-only", action="store_true")
    args = ap.parse_args()

    tag = f"_{args.model}"
    if args.render_only:
        dev = pd.read_csv(RESULTS / f"llm_rerank_dev{tag}.csv")
        test = pd.read_csv(RESULTS / f"llm_rerank_test{tag}.csv")
        (RESULTS / f"llm_rerank{tag}.md").write_text(
            render(dev, test, args.model), encoding="utf-8")
        print(f"rewrote results/llm_rerank{tag}.md")
        return

    spec = LLMS[args.model]
    splits, texts, gold = load()
    rng = np.random.default_rng(args.seed)
    dev_all = splits[splits["split"] == "dev"]["conceptUri"].tolist()
    dev_uris = sorted(rng.choice(dev_all,
                                 size=min(args.dev_sample, len(dev_all)),
                                 replace=False).tolist())
    test_uris = splits[splits["split"] == "test"]["conceptUri"].tolist()

    kwargs = ({"device": args.device, "batch_size": args.batch_size}
              if spec.backend == "local" else {"max_workers": args.max_workers})
    reranker = build_llm_reranker(spec, **kwargs)
    if hasattr(reranker, "preflight"):
        reranker.preflight()

    print(f"model: {spec.name} ({spec.backend})")
    print(f"first stage: hybrid weighted score fusion, bm25 + {DENSE}")
    print(f"dev sample {len(dev_uris)} of {len(dev_all)} | test {len(test_uris)}")
    print(f"depths {tuple(args.depths)}, one prompt per query, asking for "
          f"the top {TOP_K}\n")
    print("note: the first depth's timing includes model load\n")

    dev_rows, test_rows, pq_rows = [], [], []

    for lang in LANGUAGES:
        occ = texts[(texts["language"] == lang)
                    & (texts["conceptKind"] == "occupation")]
        occ_desc = dict(zip(occ["conceptUri"], occ["description"]))
        docs = candidate_text(texts, lang)

        fused_dev = first_stage(lang, "dev", only=dev_uris)
        fused_test = first_stage(lang, "test")

        base_dev = {q: evaluate_query(
            [d for d, _ in fused_dev.get(q, [])][:max(DEFAULT_KS)], gold[q])
            for q in dev_uris if fused_dev.get(q)}
        b_dev = aggregate(list(base_dev.values()))
        dev_rows.append({"language": lang, "depth": 0,
                         SELECT_ON: b_dev[SELECT_ON]})
        print(f"  {lang} dev  depth  0 (none)  {SELECT_ON} "
              f"{b_dev[SELECT_ON]:.4f}")

        for depth in args.depths:
            pq, rep, wall = run_depth(reranker, fused_dev, dev_uris, occ_desc,
                                      docs, gold, depth)
            if rep["unparsable"].mean() > 0.5:
                sample = rep.loc[rep["unparsable"] == 1, "raw"].iloc[0]
                raise SystemExit(
                    f"{rep['unparsable'].mean():.0%} of {lang} responses at "
                    f"depth {depth} were unusable, so nothing was written. "
                    f"First one: {sample[:300]!r}")
            agg = aggregate(list(pq.values()))
            dev_rows.append({"language": lang, "depth": depth,
                             SELECT_ON: agg[SELECT_ON],
                             "unparsable_rate": float(rep["unparsable"].mean()),
                             "s_per_query": round(wall / max(len(pq), 1), 2)})
            print(f"  {lang} dev  depth {depth:>2}        {SELECT_ON} "
                  f"{agg[SELECT_ON]:.4f}  "
                  f"({wall / max(len(pq), 1):.2f} s/query, "
                  f"{rep['unparsable'].mean():.1%} unparsable)")

        cand = [r for r in dev_rows
                if r["language"] == lang and r["depth"] > 0]
        best_depth = max(cand, key=lambda r: r[SELECT_ON])["depth"]

        base_test = {q: evaluate_query(
            [d for d, _ in fused_test.get(q, [])][:max(DEFAULT_KS)], gold[q])
            for q in test_uris if fused_test.get(q)}
        b_agg = aggregate(list(base_test.values()))
        b_lo, b_hi = bootstrap_ci(list(base_test.values()), SELECT_ON)

        pq, rep, wall = run_depth(reranker, fused_test, test_uris, occ_desc,
                                  docs, gold, best_depth)
        agg = aggregate(list(pq.values()))
        lo, hi = bootstrap_ci(list(pq.values()), SELECT_ON)

        shared = sorted(set(pq) & set(base_test))
        diffs = np.array([pq[q][SELECT_ON] - base_test[q][SELECT_ON]
                          for q in shared])
        idx = np.random.default_rng(args.seed).integers(
            0, len(diffs), size=(2000, len(diffs)))
        means = diffs[idx].mean(axis=1)

        test_rows.append({"language": lang, "stage": "first stage", "depth": 0,
                          **{m: b_agg[m] for m in HEADLINE},
                          "ndcg@10_lo": b_lo, "ndcg@10_hi": b_hi})
        test_rows.append({
            "language": lang, "stage": "llm reranked", "depth": best_depth,
            **{m: agg[m] for m in HEADLINE},
            "ndcg@10_lo": lo, "ndcg@10_hi": hi,
            "mean_delta": float(diffs.mean()),
            "delta_lo": float(np.quantile(means, 0.025)),
            "delta_hi": float(np.quantile(means, 0.975)),
            "won": float((diffs > 0).mean()),
            "s_per_query": round(wall / max(len(pq), 1), 2),
            "unparsable_rate": float(rep["unparsable"].mean()),
            "invalid_per_query": float(rep["invalid"].mean()),
            "duplicates_per_query": float(rep["duplicates"].mean()),
            "missing_per_query": float(rep["missing"].mean()),
            "prompt_tokens": int(rep["prompt_tokens"].sum()),
            "completion_tokens": int(rep["completion_tokens"].sum()),
            "served_model": getattr(reranker, "served_model", None)
                            or spec.name,
            "run_date": time.strftime("%Y-%m-%d"),
        })
        for q, s in pq.items():
            pq_rows.append({"language": lang, "model": args.model,
                            "depth": best_depth, "occupationUri": q,
                            **{k: v for k, v in s.items()
                               if not k.startswith("_")}})

        print(f"    TEST depth {best_depth}: {SELECT_ON} {agg[SELECT_ON]:.4f} "
              f"[{lo:.4f}, {hi:.4f}] against first stage "
              f"{b_agg[SELECT_ON]:.4f} "
              f"({agg[SELECT_ON] / b_agg[SELECT_ON] - 1:+.1%})\n")

    reranker.unload()
    RESULTS.mkdir(exist_ok=True)
    dev = pd.DataFrame(dev_rows)
    test = pd.DataFrame(test_rows)
    dev.to_csv(RESULTS / f"llm_rerank_dev{tag}.csv", index=False)
    test.to_csv(RESULTS / f"llm_rerank_test{tag}.csv", index=False)
    pd.DataFrame(pq_rows).to_csv(
        RESULTS / f"llm_rerank_per_query{tag}.csv", index=False)
    (RESULTS / f"llm_rerank{tag}.md").write_text(
        render(dev, test, args.model), encoding="utf-8")
    for n in ("llm_rerank_dev", "llm_rerank_test", "llm_rerank_per_query"):
        print(f"wrote results/{n}{tag}.csv")
    print(f"wrote results/llm_rerank{tag}.md")


# Oracle and cross-encoder references, read from their own recorded runs.
def references() -> dict:
    out = {}
    p = RESULTS / "rerank_test.csv"
    if p.exists():
        d = pd.read_csv(p)
        for lang in LANGUAGES:
            sub = d[(d["language"] == lang) & (d["stage"] == "oracle")]
            # Keyed by depth: a reranker that sees the top 20 can only be
            # judged against perfect ordering of those same 20.
            for _, r in sub.iterrows():
                out[f"oracle_{lang}_{int(r['depth'])}"] = float(r["ndcg@10"])
            ce = d[(d["language"] == lang) & (d["stage"] == "reranked")]
            if len(ce):
                out[f"bge_{lang}"] = float(ce.iloc[0]["ndcg@10"])
    return out


def render(dev: pd.DataFrame, test: pd.DataFrame, model: str) -> str:
    out: list[str] = []
    w = out.append
    spec = LLMS[model]
    ref = references()

    w("# Listwise LLM reranking\n")
    w(f"`{spec.name}` ({spec.backend}) reranking the hybrid weighted fusion "
      f"first stage. The whole shortlist goes into one prompt, so the model "
      f"can compare candidates against each other, which a pointwise "
      f"cross-encoder cannot.")
    w("Depth selected on a dev subsample, applied once to test. Intervals are "
      "95% percentile bootstrap over queries.\n")

    w("## Test results\n")
    w("| language | stage | depth | nDCG@10 (95% CI) | P@10 | R@10 | MRR |")
    w("|---|---|---:|---:|---:|---:|---:|")
    for _, r in test.iterrows():
        d = "" if r["depth"] == 0 else str(int(r["depth"]))
        w(f"| {r['language']} | {r['stage']} | {d} "
          f"| {r['ndcg@10']:.4f} [{r['ndcg@10_lo']:.4f}, {r['ndcg@10_hi']:.4f}] "
          f"| {r['precision@10']:.3f} | {r['recall@10']:.3f} | {r['mrr']:.3f} |")
    w("")

    rr = test[test["stage"] == "llm reranked"]
    base = test[test["stage"] == "first stage"].set_index("language")
    if len(rr) and "mean_delta" in rr.columns:
        w("## Paired change against the first stage\n")
        w("| language | first stage | llm | gain | paired difference (95% CI) | won |")
        w("|---|---:|---:|---:|---|---:|")
        for _, r in rr.iterrows():
            b = base.loc[r["language"], "ndcg@10"]
            w(f"| {r['language']} | {b:.4f} | {r['ndcg@10']:.4f} "
              f"| {r['ndcg@10'] / b - 1:+.1%} "
              f"| {r['mean_delta']:+.4f} [{r['delta_lo']:+.4f}, "
              f"{r['delta_hi']:+.4f}] | {r['won']:.0%} |")
        w("")

        if ref:
            w("## Against the other rerankers and the ceiling\n")
            w("The oracle is taken at the same depth as the LLM, since a "
              "reranker cannot recover a skill it was never shown.\n")
            w("| language | depth | first stage | bge cross-encoder | this LLM | oracle | headroom captured |")
            w("|---|---:|---:|---:|---:|---:|---:|")
            for _, r in rr.iterrows():
                lang = r["language"]
                dep = int(r["depth"])
                b = base.loc[lang, "ndcg@10"]
                o = ref.get(f"oracle_{lang}_{dep}")
                ce = ref.get(f"bge_{lang}")
                cap = (f"{(r['ndcg@10'] - b) / (o - b):.0%}"
                       if o and o > b else "")
                w(f"| {lang} | {dep} | {b:.4f} "
                  f"| {ce:.4f} | {r['ndcg@10']:.4f} "
                  f"| {o:.4f} | {cap} |" if o and ce else
                  f"| {lang} | {dep} | {b:.4f} | | {r['ndcg@10']:.4f} | | |")
            w("")

        w("## Output reliability\n")
        w("Listwise output is a list of candidate numbers, so a malformed "
          "response is an out-of-range index, a repeat, or an omission. Each "
          "is counted rather than quietly repaired: a method that mangles a "
          "tenth of its queries is not usable whatever its mean looks like. "
          "Omitted candidates keep their first-stage order beneath the ranked "
          "block, and an unparsable response leaves the query untouched.\n")
        w("| language | unparsable | invalid/query | duplicates/query | omitted/query |")
        w("|---|---:|---:|---:|---:|")
        for _, r in rr.iterrows():
            w(f"| {r['language']} | {r['unparsable_rate']:.1%} "
              f"| {r['invalid_per_query']:.2f} "
              f"| {r['duplicates_per_query']:.2f} "
              f"| {r['missing_per_query']:.2f} |")
        w("")

        w("## Cost\n")
        w("| language | depth | s/query | prompt tokens | completion tokens |")
        w("|---|---:|---:|---:|---:|")
        for _, r in rr.iterrows():
            w(f"| {r['language']} | {int(r['depth'])} | {r['s_per_query']} "
              f"| {int(r['prompt_tokens']):,} "
              f"| {int(r['completion_tokens']):,} |")
        w("")

    w("## Depth sweep on dev\n")
    w("| depth | " + " | ".join(sorted(dev["language"].unique())) + " |")
    w("|---|" + "---:|" * dev["language"].nunique())
    piv = dev.pivot_table(index="depth", columns="language", values=SELECT_ON)
    for depth, row in piv.iterrows():
        label = "0 (none)" if depth == 0 else str(int(depth))
        w(f"| {label} | " + " | ".join(f"{v:.4f}" for v in row) + " |")
    w("")

    return "\n".join(out)


if __name__ == "__main__":
    main()