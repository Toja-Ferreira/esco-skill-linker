"""Cross-encoder reranking over the hybrid first stage.

The first method that reads query and document together. A bi-encoder
compresses each side into one fixed vector independently, so a rare technical
term contributes a small share of it. A cross-encoder attends across both texts
at once, which is what could let it recognise that *puncionadora* and *prensa
biela-manivela* name the same machine. Experiments 07 to 09 identified that as
the failure mode behind the Portuguese gap, so this is a targeted test as well
as a standard second stage.

Nothing can be precomputed, so a cross-encoder reranks a shortlist instead of
retrieving. That makes the first stage's recall at the shortlist depth a hard
ceiling, and it is reported here regardless of how the reranker performs: a
reranker cannot promote what was never retrieved.

**Scoring happens once at the maximum depth.** A pair's score does not depend
on how many other pairs were scored, so every shallower depth comes free by
truncation. The depth sweep therefore costs one pass, not one pass per depth.

**Checkpoint:** `BAAI/bge-reranker-v2-m3`, Apache 2.0, the standard open
multilingual cross-encoder. Jina's v3.5 is smaller and stronger on BEIR but its
weights are CC-BY-NC-4.0, which rules it out for a public institution.
Qwen3-Reranker scores higher on MMTEB-R but uses a generative yes/no
formulation rather than a regression head, so it needs a separate scoring path
and is left for a follow-up.

**Selection on dev, on a subsample.** Reranking 100 candidates for all 2,431
dev queries is 243,100 forward passes per language. Depth is selected on a
random subsample, stated in the output, then the choice is applied once to the
full test split.

Writes:
    results/rerank_dev.csv
    results/rerank_test.csv
    results/rerank_per_query.csv
    results/rerank.md

Usage:
    python -m experiments.14_rerank
    python -m experiments.14_rerank --dev-sample 300
    python -m experiments.14_rerank --render-only
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
from src.retrieval.rerank import (RERANKERS, build_reranker,
                                  recall_at_depths, rerank_at_depth,
                                  resolve_device)

REPO_ROOT = Path(__file__).resolve().parents[1]
PROCESSED = REPO_ROOT / "data" / "processed"
BENCHMARK = REPO_ROOT / "data" / "benchmark"
RUNS = REPO_ROOT / "data" / "runs"
RESULTS = REPO_ROOT / "results"

LANGUAGES = ("pt", "en")
GRADES = {"essential": 2, "optional": 1}
SELECT_ON = "ndcg@10"
DENSE = "embeddinggemma"

# Shortlist depths. The deepest is what gets scored; the rest are truncations.
DEPTHS = (10, 20, 50, 100)
CEILING_DEPTHS = (10, 20, 50, 100, 200)

HEADLINE = ["precision@10", "recall@10", "mrr", "ndcg@10", "micro_recall@10"]

# Random shuffles of the shortlist, averaged, as a sanity floor.
RANDOM_REPEATS = 20


def load():
    splits = pd.read_csv(BENCHMARK / "splits.csv")
    texts = pd.read_parquet(PROCESSED / "texts.parquet")
    labels = pd.read_parquet(PROCESSED / "labels.parquet")
    rel = pd.read_parquet(PROCESSED / "occupation_skill_relations.parquet")

    gold: dict[str, dict[str, int]] = {}
    for occ, skill, rtype in zip(rel["occupationUri"], rel["skillUri"],
                                 rel["relationType"]):
        gold.setdefault(occ, {})[skill] = GRADES[rtype]
    return splits, texts, labels, gold


def load_run(path: Path, only: set[str] | None = None
             ) -> dict[str, list[tuple[str, float]]]:
    df = pd.read_parquet(path)
    if only is not None:
        df = df[df["query"].isin(only)]
    df = df.sort_values(["query", "rank"])
    run: dict[str, list[tuple[str, float]]] = {}
    for q, skill, score in zip(df["query"], df["skillUri"], df["score"]):
        run.setdefault(q, []).append((skill, float(score)))
    return run


def fusion_weight(lang: str) -> float:
    """Dev-selected hybrid weight from experiment 13, read from its records.

    Read rather than hardcoded so the first stage here is provably the same
    configuration experiment 13 reported, and so a re-run of that sweep
    propagates instead of silently diverging.
    """
    dev = pd.read_csv(RESULTS / "fusion_dev.csv")
    sub = dev[dev["combination"] == f"hybrid {lang}"]
    if "beta" in sub.columns:
        sub = sub[sub["beta"].isna()]
    if sub.empty:
        raise SystemExit(
            f"No dev sweep for 'hybrid {lang}' in results/fusion_dev.csv. "
            f"Run experiments/13_fusion.py first."
        )
    return float(sub.loc[sub[SELECT_ON].idxmax(), "weight"])


def first_stage(lang: str, split: str,
                only: Sequence[str] | None = None
                ) -> dict[str, list[tuple[str, float]]]:
    """Hybrid weighted score fusion, the best system from experiment 13.

    `only` restricts fusion to the queries actually needed. Fusing all 2,431
    dev queries when the depth sweep uses a subsample is pure waste, and it is
    the slowest step that runs before the reranker is even loaded.
    """
    keep = set(only) if only is not None else None
    bm25 = load_run(RUNS / f"bm25_{lang}_{split}.parquet", keep)
    dense = load_run(RUNS / f"{DENSE}_{lang}_{split}.parquet", keep)
    w = fusion_weight(lang)
    return weighted_score_fusion([bm25, dense], [w, 1.0 - w])


def skill_text(texts, labels, lang: str) -> dict[str, str]:
    """Document text for the reranker: label plus description.

    Matches the `labels_desc` variant the first stage uses, minus alternative
    labels, which would pad the pair text without adding discriminative
    content for a model that reads both sides together.
    """
    t = texts[(texts["language"] == lang) & (texts["conceptKind"] == "skill")]
    return {u: f"{p}. {d}" if d else p
            for u, p, d in zip(t["conceptUri"], t["preferredLabel"],
                               t["description"])}


def oracle_rerank(fused, query_uris, gold, depth):
    """Upper bound: sort the shortlist by true relevance.

    This is what a flawless reranker would achieve over the same candidates,
    so it separates two very different failures. If the oracle is close to the
    first stage, the shortlist has nothing left to gain and the retrieval
    stage is the thing to improve. If the oracle is far above it, the ordering
    problem is real and a reranker that captures none of it is simply the
    wrong instrument.

    No model is involved, so this costs a sort over the recorded runs.
    """
    per_query = {}
    for q in query_uris:
        candidates = [d for d, _ in fused.get(q, [])]
        if not candidates:
            continue
        head = sorted(candidates[:depth],
                      key=lambda d: -gold[q].get(d, 0))
        ranked = head + candidates[depth:]
        per_query[q] = evaluate_query(ranked[:max(DEFAULT_KS)], gold[q])
    return per_query


def run_split(reranker, fused, query_uris, occ_desc, docs, gold, max_depth,
              depths):
    """Score every (query, candidate) pair once, then evaluate each depth."""
    pairs, index = [], []
    for q in query_uris:
        for doc, _ in fused.get(q, [])[:max_depth]:
            pairs.append((occ_desc[q], docs.get(doc, "")))
            index.append((q, doc))

    t0 = time.perf_counter()
    scores = reranker.score_pairs(pairs)
    seconds = time.perf_counter() - t0

    by_query: dict[str, dict[str, float]] = {}
    for (q, doc), s in zip(index, scores):
        by_query.setdefault(q, {})[doc] = s

    out = {}
    for depth in depths:
        per_query = {}
        for q in query_uris:
            ranked = rerank_at_depth([d for d, _ in fused.get(q, [])],
                                     by_query.get(q, {}), depth)
            if ranked:
                per_query[q] = evaluate_query(ranked[:max(DEFAULT_KS)], gold[q])
        out[depth] = per_query
    return out, len(pairs), seconds, by_query


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="bge-m3", choices=list(RERANKERS))
    ap.add_argument("--tag", default=None,
                    help="suffix for the output files, so checkpoints do not "
                         "overwrite one another")
    ap.add_argument("--dev-sample", type=int, default=200,
                    help="dev queries used to select the shortlist depth")
    ap.add_argument("--batch-size", type=int, default=64)
    ap.add_argument("--device", default=None)
    ap.add_argument("--allow-cpu", action="store_true",
                    help="run on CPU rather than stopping; expect hours")
    ap.add_argument("--no-fp16", action="store_true")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--render-only", action="store_true")
    args = ap.parse_args()

    tag = args.tag or ("" if args.model == "bge-m3" else f"_{args.model}")

    if args.render_only:
        dev = pd.read_csv(RESULTS / f"rerank_dev{tag}.csv")
        test = pd.read_csv(RESULTS / f"rerank_test{tag}.csv")
        ceil = pd.read_csv(RESULTS / f"rerank_ceiling{tag}.csv")
        dp = RESULTS / f"rerank_diagnostics{tag}.csv"
        diag = pd.read_csv(dp) if dp.exists() else pd.DataFrame()
        (RESULTS / f"rerank{tag}.md").write_text(
            render(dev, test, ceil, args.model, args.dev_sample, diag),
            encoding="utf-8")
        print(f"rewrote results/rerank{tag}.md from saved CSVs")
        return

    splits, texts, labels, gold = load()
    rng = np.random.default_rng(args.seed)
    dev_all = splits[splits["split"] == "dev"]["conceptUri"].tolist()
    dev_uris = sorted(rng.choice(dev_all, size=min(args.dev_sample,
                                                   len(dev_all)),
                                 replace=False).tolist())
    test_uris = splits[splits["split"] == "test"]["conceptUri"].tolist()
    max_depth = max(DEPTHS)

    spec = RERANKERS[args.model]
    device = resolve_device(args.device, allow_cpu=args.allow_cpu)
    reranker = build_reranker(spec, device=device,
                              batch_size=args.batch_size,
                              fp16=not args.no_fp16)

    print(f"reranker: {spec.hf_name} ({spec.licence})")
    print(f"first stage: hybrid weighted score fusion, bm25 + {DENSE}")
    print(f"dev sample {len(dev_uris)} of {len(dev_all)} | test {len(test_uris)}")
    print(f"depths {DEPTHS}, scored once at {max_depth}")
    print(f"device: {device}  |  scoring: {spec.kind}  |  pairs: "
          f"{len(dev_uris) * max_depth * 2:,} dev, "
          f"up to {len(test_uris) * max_depth * 2:,} test")

    if hasattr(reranker, "sanity_check"):
        good, bad = reranker.sanity_check()
        print(f"sanity check: relevant {good:.4f} > irrelevant {bad:.4f}")
    print()
    dev_rows, test_rows, ceil_rows, pq_rows, diag_rows = [], [], [], [], []

    for lang in LANGUAGES:
        occ = texts[(texts["language"] == lang)
                    & (texts["conceptKind"] == "occupation")]
        occ_desc = dict(zip(occ["conceptUri"], occ["description"]))
        docs = skill_text(texts, labels, lang)

        # First-stage ceiling on the full test split, independent of reranking.
        t0 = time.perf_counter()
        fused_test = first_stage(lang, "test")
        print(f"  {lang}: fused test first stage "
              f"({time.perf_counter() - t0:.0f}s)", flush=True)
        for q in test_uris:
            essential = {u for u, g in gold[q].items() if g == 2}
            r = recall_at_depths([d for d, _ in fused_test.get(q, [])],
                                 essential, CEILING_DEPTHS)
            ceil_rows.append({"language": lang, "occupationUri": q, **r})

        # Depth selection on the dev subsample.
        t0 = time.perf_counter()
        fused_dev = first_stage(lang, "dev", only=dev_uris)
        print(f"  {lang}: fused dev first stage "
              f"({time.perf_counter() - t0:.0f}s)", flush=True)
        print(f"  {lang}: loading reranker and scoring "
              f"{len(dev_uris) * max_depth:,} dev pairs", flush=True)
        dev_out, n_pairs, secs, _ = run_split(
            reranker, fused_dev, dev_uris, occ_desc, docs, gold,
            max_depth, DEPTHS)
        print(f"  {lang} dev: {n_pairs:,} pairs in {secs:.0f}s "
              f"({n_pairs/secs:.0f} pairs/s) on {reranker.actual_device}")

        base_dev = {}
        for q in dev_uris:
            ranked = [d for d, _ in fused_dev.get(q, [])][:max(DEFAULT_KS)]
            if ranked:
                base_dev[q] = evaluate_query(ranked, gold[q])
        base_agg = aggregate(list(base_dev.values()))
        dev_rows.append({"language": lang, "depth": 0,
                         SELECT_ON: base_agg[SELECT_ON], "queries": len(base_dev)})
        print(f"    depth   0 (no rerank)  {SELECT_ON} {base_agg[SELECT_ON]:.4f}")

        for depth in DEPTHS:
            agg = aggregate(list(dev_out[depth].values()))
            dev_rows.append({"language": lang, "depth": depth,
                             SELECT_ON: agg[SELECT_ON],
                             "queries": len(dev_out[depth])})
            print(f"    depth {depth:>3}               "
                  f"{SELECT_ON} {agg[SELECT_ON]:.4f}")

        cand = [r for r in dev_rows if r["language"] == lang and r["depth"] > 0]
        best_depth = max(cand, key=lambda r: r[SELECT_ON])["depth"]

        # Test, scored once at the selected depth.
        test_out, n_pairs, secs, test_scores = run_split(
            reranker, fused_test, test_uris, occ_desc, docs, gold,
            best_depth, (best_depth,))
        per_query = test_out[best_depth]
        agg = aggregate(list(per_query.values()))
        lo, hi = bootstrap_ci(list(per_query.values()), SELECT_ON)

        base_test = {}
        for q in test_uris:
            ranked = [d for d, _ in fused_test.get(q, [])][:max(DEFAULT_KS)]
            if ranked:
                base_test[q] = evaluate_query(ranked, gold[q])
        b_agg = aggregate(list(base_test.values()))
        b_lo, b_hi = bootstrap_ci(list(base_test.values()), SELECT_ON)

        shared = sorted(set(per_query) & set(base_test))
        diffs = np.array([per_query[q][SELECT_ON] - base_test[q][SELECT_ON]
                          for q in shared])
        bidx = np.random.default_rng(args.seed).integers(
            0, len(diffs), size=(2000, len(diffs)))
        means = diffs[bidx].mean(axis=1)

        test_rows.append({
            "language": lang, "stage": "first stage", "depth": 0,
            **{m: b_agg[m] for m in HEADLINE},
            "ndcg@10_lo": b_lo, "ndcg@10_hi": b_hi,
            "pairs": 0, "seconds": 0.0, "ms_per_query": 0.0,
        })
        test_rows.append({
            "language": lang, "stage": "reranked", "depth": best_depth,
            **{m: agg[m] for m in HEADLINE},
            "ndcg@10_lo": lo, "ndcg@10_hi": hi,
            "pairs": n_pairs, "seconds": round(secs, 1),
            "ms_per_query": round(1000 * secs / len(test_uris), 1),
            "mean_delta": float(diffs.mean()),
            "delta_lo": float(np.quantile(means, 0.025)),
            "delta_hi": float(np.quantile(means, 0.975)),
            "won": float((diffs > 0).mean()),
        })
        for q, s in per_query.items():
            pq_rows.append({"language": lang, "depth": best_depth,
                            "occupationUri": q,
                            **{k: v for k, v in s.items()
                               if not k.startswith("_")}})

        # Random baseline. A reranker with weak but real signal should land
        # between random and the first stage. Landing at random means no
        # signal; landing below it means something is inverted or misaligned,
        # which would make the result a bug rather than a finding.
        rb = np.random.default_rng(args.seed)
        rand_runs = []
        for _ in range(RANDOM_REPEATS):
            pq = {}
            for q in test_uris:
                cands = [d for d, _ in fused_test.get(q, [])]
                if not cands:
                    continue
                head = cands[:best_depth]
                rb.shuffle(head)
                pq[q] = evaluate_query((head + cands[best_depth:])
                                       [:max(DEFAULT_KS)], gold[q])
            rand_runs.append(aggregate(list(pq.values()))[SELECT_ON])
        rand_mean = float(np.mean(rand_runs))
        test_rows.append({
            "language": lang, "stage": "random", "depth": best_depth,
            "ndcg@10": rand_mean,
            "ndcg@10_lo": float(np.min(rand_runs)),
            "ndcg@10_hi": float(np.max(rand_runs)),
            "pairs": 0, "seconds": 0.0, "ms_per_query": 0.0,
        })

        # Can the reranker tell gold from non-gold at all? Reported as the
        # probability that a randomly chosen gold candidate outscores a
        # randomly chosen non-gold one from the same shortlist, which is the
        # AUC. 0.5 is chance.
        aucs, gold_means, other_means = [], [], []
        for q, scored in test_scores.items():
            g = [s for d, s in scored.items() if gold[q].get(d, 0) == 2]
            o = [s for d, s in scored.items() if gold[q].get(d, 0) != 2]
            if not g or not o:
                continue
            ga, oa = np.array(g), np.array(o)
            wins = (ga[:, None] > oa[None, :]).sum()
            ties = (ga[:, None] == oa[None, :]).sum()
            aucs.append((wins + 0.5 * ties) / (len(ga) * len(oa)))
            gold_means.append(ga.mean())
            other_means.append(oa.mean())
        diag_rows.append({
            "language": lang, "model": args.model, "depth": best_depth,
            "queries": len(aucs),
            "auc": float(np.mean(aucs)),
            "auc_lo": float(np.quantile(aucs, 0.025)),
            "auc_hi": float(np.quantile(aucs, 0.975)),
            "mean_gold_score": float(np.mean(gold_means)),
            "mean_other_score": float(np.mean(other_means)),
            "random_ndcg": rand_mean,
            "first_stage_ndcg": b_agg[SELECT_ON],
            "reranked_ndcg": agg[SELECT_ON],
        })
        print(f"    random baseline: {SELECT_ON} {rand_mean:.4f}  |  "
              f"gold-vs-rest AUC {np.mean(aucs):.3f} "
              f"(0.5 = chance)")

        # Oracle at every depth: the headroom a perfect reranker would have.
        for depth in DEPTHS:
            o_pq = oracle_rerank(fused_test, test_uris, gold, depth)
            o_agg = aggregate(list(o_pq.values()))
            o_lo, o_hi = bootstrap_ci(list(o_pq.values()), SELECT_ON)
            test_rows.append({
                "language": lang, "stage": "oracle", "depth": depth,
                **{m: o_agg[m] for m in HEADLINE},
                "ndcg@10_lo": o_lo, "ndcg@10_hi": o_hi,
                "pairs": 0, "seconds": 0.0, "ms_per_query": 0.0,
            })
            if depth == best_depth:
                print(f"    oracle depth {depth}: {SELECT_ON} "
                      f"{o_agg[SELECT_ON]:.4f}  R@10 {o_agg['recall@10']:.4f}")

        print(f"    TEST depth {best_depth}: {SELECT_ON} {agg[SELECT_ON]:.4f} "
              f"[{lo:.4f}, {hi:.4f}] against first stage "
              f"{b_agg[SELECT_ON]:.4f} ({agg[SELECT_ON]/b_agg[SELECT_ON]-1:+.1%})\n")

    reranker.unload()

    RESULTS.mkdir(exist_ok=True)
    dev = pd.DataFrame(dev_rows)
    test = pd.DataFrame(test_rows)
    ceil = pd.DataFrame(ceil_rows)
    dev.to_csv(RESULTS / f"rerank_dev{tag}.csv", index=False)
    test.to_csv(RESULTS / f"rerank_test{tag}.csv", index=False)
    ceil.to_csv(RESULTS / f"rerank_ceiling{tag}.csv", index=False)
    pd.DataFrame(pq_rows).to_csv(RESULTS / f"rerank_per_query{tag}.csv", index=False)
    diag = pd.DataFrame(diag_rows)
    diag.to_csv(RESULTS / f"rerank_diagnostics{tag}.csv", index=False)
    (RESULTS / f"rerank{tag}.md").write_text(
        render(dev, test, ceil, args.model, len(dev_uris), diag),
        encoding="utf-8")

    for name in ("rerank_dev.csv", "rerank_test.csv", "rerank_ceiling.csv",
                 "rerank_per_query.csv", "rerank_diagnostics.csv",
                 "rerank.md"):
        stem, ext = name.rsplit(".", 1)
        print(f"wrote results/{stem}{tag}.{ext}")


def render(dev: pd.DataFrame, test: pd.DataFrame, ceil: pd.DataFrame,
           model: str, dev_sample: int,
           diag: pd.DataFrame | None = None) -> str:
    out: list[str] = []
    w = out.append
    spec = RERANKERS[model]

    w("# Cross-encoder reranking\n")
    w(f"`{spec.hf_name}` ({spec.licence}) reranking the hybrid weighted score "
      f"fusion first stage from experiment 13.")
    w(f"Shortlist depth selected on a random subsample of {dev_sample} dev "
      f"queries, then applied once to the full test split. Scoring runs once at "
      f"the deepest shortlist; shallower depths are truncations of it.")
    w("Intervals are 95% percentile bootstrap over queries.\n")

    w("## First-stage ceiling\n")
    w("Mean recall of essential skills within the shortlist. A reranker cannot "
      "promote what the first stage never retrieved, so these bound everything "
      "below.\n")
    w("| language | " + " | ".join(f"depth {d}" for d in CEILING_DEPTHS) + " |")
    w("|---|" + "---:|" * len(CEILING_DEPTHS))
    for lang in LANGUAGES:
        sub = ceil[ceil["language"] == lang]
        w(f"| {lang} | " + " | ".join(f"{sub[str(d)].mean():.4f}"
                                      if str(d) in sub.columns
                                      else f"{sub[d].mean():.4f}"
                                      for d in CEILING_DEPTHS) + " |")
    w("")

    w("## Depth sweep on dev\n")
    w("Depth 0 is the first stage without reranking.\n")
    piv = dev.pivot(index="depth", columns="language", values=SELECT_ON)
    w("| depth | " + " | ".join(str(c) for c in piv.columns) + " |")
    w("|---|" + "---:|" * len(piv.columns))
    for depth, row in piv.iterrows():
        label = "0 (none)" if depth == 0 else str(depth)
        w(f"| {label} | " + " | ".join(f"{v:.4f}" for v in row) + " |")
    w("")

    w("## Test results\n")
    w("| language | stage | depth | nDCG@10 (95% CI) | P@10 | R@10 | MRR |")
    w("|---|---|---:|---:|---:|---:|---:|")
    for _, r in test.iterrows():
        d = "" if r["depth"] == 0 else f"{int(r['depth'])}"
        w(f"| {r['language']} | {r['stage']} | {d} "
          f"| {r['ndcg@10']:.4f} [{r['ndcg@10_lo']:.4f}, {r['ndcg@10_hi']:.4f}] "
          f"| {r['precision@10']:.3f} | {r['recall@10']:.3f} | {r['mrr']:.3f} |")
    w("")

    if diag is not None and len(diag):
        w("## Is the result real, or an implementation error?\n")
        w("A reranker with weak but genuine signal should land between a "
          "random shuffle of the shortlist and the first stage. Landing at "
          "random means no signal at all. Landing **below** random would mean "
          "the ordering is inverted or misaligned, which would make this a "
          "bug rather than a finding.\n")
        w("AUC is the probability that a randomly chosen gold candidate "
          "outscores a randomly chosen non-gold one from the same shortlist. "
          "0.5 is chance; it tests whether the model can separate them at all, "
          "independently of how the ranking is assembled. The bracketed range "
          "is the 2.5th to 97.5th percentile **across queries**, not "
          "uncertainty on the mean: a query with one or two gold items in its "
          "shortlist yields an AUC of 0 or 1 by construction, so the spread is "
          "wide even when the mean is well determined.\n")
        w("| language | random | reranked | first stage | recovered | gold-vs-rest AUC | per-query range | mean gold | mean other |")
        w("|---|---:|---:|---:|---:|---:|---|---:|---:|")
        for _, r in diag.iterrows():
            span = r["first_stage_ndcg"] - r["random_ndcg"]
            rec = (r["reranked_ndcg"] - r["random_ndcg"]) / span if span else float("nan")
            w(f"| {r['language']} | {r['random_ndcg']:.4f} "
              f"| {r['reranked_ndcg']:.4f} | {r['first_stage_ndcg']:.4f} "
              f"| {rec:.0%} | {r['auc']:.3f} "
              f"| [{r['auc_lo']:.2f}, {r['auc_hi']:.2f}] "
              f"| {r['mean_gold_score']:.4f} | {r['mean_other_score']:.4f} |")
        w("")
        w("**Recovered** is where the reranker sits between a random shuffle "
          "and the first stage. Near 100% means it reproduces the first "
          "stage's ordering quality without exceeding it. Above 0% rules out "
          "an inverted or misaligned implementation.\n")

    oracle = test[test["stage"] == "oracle"]
    base = test[test["stage"] == "first stage"].set_index("language")
    rr_only = test[test["stage"] == "reranked"].set_index("language")
    if len(oracle):
        w("## How much ordering headroom exists\n")
        w("The oracle sorts each shortlist by true relevance, so it is what a "
          "flawless reranker would reach over the same candidates. It involves "
          "no model and bounds every reranking attempt on this first stage.\n")
        w("The **reranked** column is filled only at the depth selected on "
          "dev, since that is the only depth scored on test. Blank cells are "
          "depths that were not run, not missing results.\n")
        w("| language | depth | first stage | reranked | oracle | headroom captured |")
        w("|---|---:|---:|---:|---:|---:|")
        for lang in LANGUAGES:
            if lang not in base.index:
                continue
            b = base.loc[lang, "ndcg@10"]
            for _, r in oracle[oracle["language"] == lang].iterrows():
                got = (rr_only.loc[lang, "ndcg@10"]
                       if lang in rr_only.index
                       and int(rr_only.loc[lang, "depth"]) == int(r["depth"])
                       else float("nan"))
                if pd.notna(got) and r["ndcg@10"] > b:
                    captured = f"{(got - b) / (r['ndcg@10'] - b):.0%}"
                    got_s = f"{got:.4f}"
                else:
                    captured, got_s = "", "" if pd.isna(got) else f"{got:.4f}"
                w(f"| {lang} | {int(r['depth'])} | {b:.4f} | {got_s} "
                  f"| {r['ndcg@10']:.4f} | {captured} |")
        w("")
        w("A large gap between the first stage and the oracle means the "
          "ordering problem is real and unsolved, not that the shortlist is "
          "exhausted. Those are different conclusions and they point at "
          "different work.\n")

    rr = test[test["stage"] == "reranked"]
    if len(rr) and "mean_delta" in rr.columns:
        w("## Paired change against the first stage\n")
        w("Both stages are scored on the identical queries, so the comparison "
          "is paired. **Won** is the share of queries where reranking "
          "improved the result.\n")
        w("| language | first stage | reranked | gain | paired difference (95% CI) | won |")
        w("|---|---:|---:|---:|---|---:|")
        for _, r in rr.iterrows():
            b = base.loc[r["language"], "ndcg@10"]
            w(f"| {r['language']} | {b:.4f} | {r['ndcg@10']:.4f} "
              f"| {r['ndcg@10']/b - 1:+.1%} "
              f"| {r['mean_delta']:+.4f} [{r['delta_lo']:+.4f}, "
              f"{r['delta_hi']:+.4f}] | {r['won']:.0%} |")
        w("")

        w("## Cost\n")
        w("A cross-encoder scores every pair individually, so nothing is "
          "precomputed and cost scales with shortlist depth. It comes on top of "
          "the first stage: the bi-encoder answers in well under a millisecond "
          "per query once indexed, and BM25 over the full index takes tens of "
          "milliseconds (experiment 01).\n")
        w("| language | pairs scored | total s | ms/query |")
        w("|---|---:|---:|---:|")
        for _, r in rr.iterrows():
            w(f"| {r['language']} | {int(r['pairs']):,} | {r['seconds']} "
              f"| {r['ms_per_query']} |")
        w("")

    return "\n".join(out)


if __name__ == "__main__":
    main()