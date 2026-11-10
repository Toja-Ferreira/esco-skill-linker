"""Fusion: combining lexical with dense, and Portuguese with English.

Two combinations, each justified by a measurement rather than by the general
observation that fusion tends to help.

**Hybrid, lexical plus dense.** Experiment 11 showed the two families fail on
structurally different queries: EmbeddingGemma wins 80% of BM25's worst
Portuguese quartile and loses 56% of its best. That complementarity is the
precondition for fusion.

**Bilingual, Portuguese plus English.** Course documentation at the target
institution is authored in both languages, including learning outcomes, so a
deployed system has both texts for every course unit. Experiment 12 measured the
headroom: under the best bi-encoder, 6.2% of occupations fail in Portuguese
while succeeding in English, and 3.3% the reverse. An oracle picking the better
language per query would recover about 6% of Portuguese failures; fusion
recovers less.

Reciprocal rank fusion is reported first because it has no weight to tune, so it
can be scored on test without touching dev. Weighted score fusion follows, with
its weight selected on dev and applied once to test.

Fusion needs ranked lists, which the per-query metric files do not hold, so runs
are produced here and cached under `data/runs/`. Dense embeddings are cached
from experiment 10, so re-running is cheap.

Writes:
    results/fusion_dev.csv
    results/fusion_test.csv
    results/fusion.md

Usage:
    python -m experiments.13_fusion
    python -m experiments.13_fusion --dense-model qwen3-4b
    python -m experiments.13_fusion --render-only
    python -m experiments.13_fusion --rrf-tuned   tune RRF on dev, own files
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from src.eval.metrics import DEFAULT_KS, aggregate, bootstrap_ci, evaluate_query
from src.retrieval.bm25 import (BM25Index, build_documents, get_stemmer,
                                get_stopwords, tokenize)
from src.retrieval.dense import MODELS, DenseIndex
from src.retrieval.fusion import (reciprocal_rank_fusion, to_ranked_uris,
                                  weighted_score_fusion)

REPO_ROOT = Path(__file__).resolve().parents[1]
PROCESSED = REPO_ROOT / "data" / "processed"
BENCHMARK = REPO_ROOT / "data" / "benchmark"
RUNS = REPO_ROOT / "data" / "runs"
RESULTS = REPO_ROOT / "results"

LANGUAGES = ("pt", "en")
GRADES = {"essential": 2, "optional": 1}
SELECT_ON = "ndcg@10"

# Best configuration for each family, from experiments 05 and 10.
BM25_VARIANT = "labels_desc"
DENSE_DEFAULT = "embeddinggemma"
DENSE_VARIANT = {"embeddinggemma": "labels_desc", "e5-base": "labels_desc",
                 "qwen3-4b": "preferred"}

# Fusion input depth. Deeper than the deepest metric (50) so that fusion has
# room to promote a document that one run ranked poorly.
RUN_DEPTH = 200

WEIGHT_GRID = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
# The four-way sweep is over two parameters, so it uses a coarser grid to keep
# the dev pass to a few minutes.
WEIGHT_GRID_4WAY = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
HEADLINE = ["precision@10", "recall@10", "mrr", "ndcg@10", "micro_recall@10"]

# How many of the strongest configurations to compare against one another.
TOP_N_HEAD_TO_HEAD = 4


def load():
    splits = pd.read_csv(BENCHMARK / "splits.csv")
    texts = pd.read_parquet(PROCESSED / "texts.parquet")
    labels = pd.read_parquet(PROCESSED / "labels.parquet")
    skills = pd.read_parquet(PROCESSED / "skills.parquet")
    rel = pd.read_parquet(PROCESSED / "occupation_skill_relations.parquet")
    gold: dict[str, dict[str, int]] = {}
    for occ, skill, rtype in zip(rel["occupationUri"], rel["skillUri"],
                                 rel["relationType"]):
        gold.setdefault(occ, {})[skill] = GRADES[rtype]
    return splits, texts, labels, skills, gold


def language_data(texts, labels, skills, lang: str):
    skill_uris = sorted(skills["conceptUri"])
    t = texts[texts["language"] == lang]
    preferred = dict(zip(t["conceptUri"], t["preferredLabel"]))
    description = dict(zip(t["conceptUri"], t["description"]))
    a = labels[(labels["language"] == lang) & (labels["labelType"] == "alt")]
    alt: dict[str, list[str]] = {}
    for uri, label in zip(a["conceptUri"], a["label"]):
        alt.setdefault(uri, []).append(label)
    occ = texts[(texts["language"] == lang) & (texts["conceptKind"] == "occupation")]
    occ_desc = dict(zip(occ["conceptUri"], occ["description"]))
    return skill_uris, preferred, alt, description, occ_desc


def top_n(scores: np.ndarray, uris: np.ndarray, n: int) -> list[tuple[str, float]]:
    n = min(n, len(scores))
    idx = np.argpartition(-scores, n - 1)[:n]
    idx = idx[np.argsort(-scores[idx], kind="stable")]
    return [(uris[i], float(scores[i])) for i in idx]


def run_path(method: str, lang: str, split: str) -> Path:
    return RUNS / f"{method}_{lang}_{split}.parquet"


def save_run(run: dict, path: Path) -> None:
    rows = [{"query": q, "rank": r, "skillUri": d, "score": s}
            for q, items in run.items()
            for r, (d, s) in enumerate(items, start=1)]
    RUNS.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(path, index=False)


def load_run(path: Path) -> dict:
    df = pd.read_parquet(path).sort_values(["query", "rank"])
    run: dict[str, list[tuple[str, float]]] = {}
    for q, skill, score in zip(df["query"], df["skillUri"], df["score"]):
        run.setdefault(q, []).append((skill, float(score)))
    return run


def build_runs(args, splits, texts, labels, skills) -> dict:
    """Produce or load a ranked run for each method, language and split."""
    runs: dict[tuple[str, str, str], dict] = {}
    query_uris = {s: splits[splits["split"] == s]["conceptUri"].tolist()
                  for s in ("dev", "test")}

    for lang in LANGUAGES:
        skill_uris, preferred, alt, description, occ_desc = language_data(
            texts, labels, skills, lang)
        uri_arr = np.asarray(skill_uris)

        # BM25
        needed = [s for s in ("dev", "test")
                  if not run_path("bm25", lang, s).exists() or args.no_cache]
        if needed:
            docs = build_documents(skill_uris, preferred, alt, description,
                                   BM25_VARIANT)
            index = BM25Index(skill_uris, docs, get_stemmer(lang),
                              get_stopwords(lang))
            for split in needed:
                run = {}
                for q in query_uris[split]:
                    toks = tokenize(occ_desc[q], index.stemmer, index.stopwords)
                    run[q] = top_n(index.bm25.get_scores(toks), uri_arr, RUN_DEPTH)
                save_run(run, run_path("bm25", lang, split))
                print(f"  built bm25 / {lang} / {split}")
        for split in ("dev", "test"):
            runs[("bm25", lang, split)] = load_run(run_path("bm25", lang, split))

        # Dense
        model = args.dense_model
        needed = [s for s in ("dev", "test")
                  if not run_path(model, lang, s).exists() or args.no_cache]
        if needed:
            spec = MODELS[model]
            index = DenseIndex(spec, device=args.device,
                               batch_size=args.batch_size)
            variant = DENSE_VARIANT.get(model, "labels_desc")
            docs = build_documents(skill_uris, preferred, alt, description,
                                   variant)
            index.build(skill_uris, docs, lang, variant)
            for split in needed:
                qvecs = index.encode_queries([occ_desc[q] for q in query_uris[split]])
                all_scores = qvecs @ index.embeddings.T
                run = {q: top_n(all_scores[i], uri_arr, RUN_DEPTH)
                       for i, q in enumerate(query_uris[split])}
                save_run(run, run_path(model, lang, split))
                print(f"  built {model} / {lang} / {split}")
            index.unload()
        for split in ("dev", "test"):
            runs[(model, lang, split)] = load_run(run_path(model, lang, split))

    return runs, query_uris


def score(fused, query_order, gold) -> tuple[dict, dict]:
    """Aggregate metrics, plus per-query metrics keyed by occupation.

    Keying by query rather than returning a list is what allows two
    combinations to be compared on the same queries afterwards.
    """
    ranked = to_ranked_uris(fused, query_order, max(DEFAULT_KS))
    per_query = {q: evaluate_query(r, gold[q])
                 for r, q in zip(ranked, query_order) if r}
    return aggregate(list(per_query.values())), per_query


def paired_delta(a: dict, b: dict, metric: str = SELECT_ON,
                 n_resamples: int = 2000, seed: int = 42) -> dict:
    """Bootstrap the per-query difference between two combinations.

    Every combination is scored on the identical query set, so comparing
    marginal confidence intervals is a weak test: two overlapping intervals can
    still correspond to a difference that holds on almost every query. The
    paired difference is the right quantity.
    """
    shared = sorted(set(a) & set(b))
    diffs = np.array([a[q][metric] - b[q][metric] for q in shared])
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(diffs), size=(n_resamples, len(diffs)))
    means = diffs[idx].mean(axis=1)
    return {
        "queries": len(diffs),
        "mean_delta": float(diffs.mean()),
        "delta_lo": float(np.quantile(means, 0.025)),
        "delta_hi": float(np.quantile(means, 0.975)),
        "share_positive": float((diffs > 0).mean()),
        "resamples_positive": float((means > 0).mean()),
    }


# RRF's constant, swept on dev in --rrf-tuned mode. 60 is the conventional
# default the main run uses.
RRF_K_GRID = [1, 5, 10, 20, 40, 60, 100, 200]


def rrf_tuned(runs, query_uris, gold, combos, inputs) -> None:
    """Tune RRF's k and run weights on dev, the same way weighted score fusion
    is tuned, then score the selected setting once on test against the
    stronger of its inputs. Answers whether RRF failed only for want of the
    tuning weighted fusion was given. Writes its own files, so the main run's
    results are untouched."""
    test_q, dev_q = query_uris["test"], query_uris["dev"]
    singles = {}
    for name in {n for ns in inputs.values() for n in ns}:
        method, lang = name.rsplit(" ", 1)
        singles[name] = score(runs[(method, lang, "test")], test_q, gold)[1]

    def weight_grid(n):
        if n == 2:
            return [(w, None, [w, 1.0 - w]) for w in WEIGHT_GRID]
        return [(a, b, [a * b, a * (1 - b), (1 - a) * b, (1 - a) * (1 - b)])
                for a in WEIGHT_GRID_4WAY for b in WEIGHT_GRID_4WAY]

    # Weighted score fusion at its committed dev-selected weights, rebuilt on
    # test for the paired comparison, and checked against the committed score.
    wsf_dev = pd.read_csv(RESULTS / "fusion_dev.csv")
    wsf_test = pd.read_csv(RESULTS / "fusion_test.csv").query("fusion == 'wsf'")

    def wsf_per_query(name, keys):
        r = wsf_dev[wsf_dev["combination"] == name]
        r = r.loc[r[SELECT_ON].idxmax()]
        a = r["weight"]
        wts = ([a, 1.0 - a] if len(keys) == 2 else
               [a * r["beta"], a * (1 - r["beta"]),
                (1 - a) * r["beta"], (1 - a) * (1 - r["beta"])])
        agg, pq = score(weighted_score_fusion(
            [runs[(m, l, "test")] for m, l in keys], wts), test_q, gold)
        committed = wsf_test.loc[wsf_test["combination"] == name, SELECT_ON].item()
        if abs(agg[SELECT_ON] - committed) > 1e-12:
            raise SystemExit(f"{name}: rebuilt wsf {agg[SELECT_ON]} != committed {committed}")
        return agg[SELECT_ON], pq

    dev_rows, test_rows = [], []
    for name, keys in combos.items():
        wsf_score, wsf_pq = wsf_per_query(name, keys)
        best = None
        for k in RRF_K_GRID:
            for w, beta, wts in weight_grid(len(keys)):
                fused = reciprocal_rank_fusion(
                    [runs[(m, l, "dev")] for m, l in keys], k=k, weights=wts)
                s = score(fused, dev_q, gold)[0][SELECT_ON]
                dev_rows.append({"combination": name, "k": k, "weight": w,
                                 "beta": beta, SELECT_ON: s})
                if best is None or s > best[0]:
                    best = (s, k, w, beta, wts)
        _, k, w, beta, wts = best
        base_name = max(inputs[name], key=lambda n: aggregate(
            list(singles[n].values()))[SELECT_ON])
        for label, kk, ww in (("rrf", 60, None), ("rrf tuned", k, wts)):
            fused = reciprocal_rank_fusion(
                [runs[(m, l, "test")] for m, l in keys], k=kk, weights=ww)
            agg, pq = score(fused, test_q, gold)
            lo, hi = bootstrap_ci(list(pq.values()), SELECT_ON)
            test_rows.append({
                "combination": name, "fusion": label, "k": kk,
                "weight": w if ww is not None else np.nan,
                "beta": beta if ww is not None else np.nan,
                SELECT_ON: agg[SELECT_ON], "ndcg@10_lo": lo, "ndcg@10_hi": hi,
                "baseline": base_name,
                **paired_delta(pq, singles[base_name]),
                "wsf_ndcg@10": wsf_score,
                **{f"vs_wsf_{k}": v for k, v in paired_delta(pq, wsf_pq).items()
                   if k != "queries"}})
        r = test_rows[-1]
        print(f"  {name:<24} k={k:<3} weight={w} beta={beta}  test {SELECT_ON} "
              f"{r[SELECT_ON]:.4f}, over {base_name} {r['mean_delta']:+.4f} "
              f"[{r['delta_lo']:+.4f}, {r['delta_hi']:+.4f}]")

    dev, test = pd.DataFrame(dev_rows), pd.DataFrame(test_rows)
    dev.to_csv(RESULTS / "fusion_rrf_tuned_dev.csv", index=False)
    test.to_csv(RESULTS / "fusion_rrf_tuned.csv", index=False)
    lines = ["# Reciprocal rank fusion, tuned on dev\n",
             f"k swept over {RRF_K_GRID} and run weights over the same grids as "
             f"weighted score fusion, selected on {len(dev_q):,} dev queries by "
             f"{SELECT_ON}, then scored once on {len(test_q)} test queries. "
             "`rrf` is the untuned default (k = 60, equal weights) for "
             "reference. Paired differences are against the stronger single "
             "input and against weighted score fusion at its dev-selected "
             "weights, 95% percentile bootstrap over queries.\n",
             "| combination | fusion | k | weight | pt weight | nDCG@10 | "
             "over better input (95% CI) | wins | minus weighted score fusion (95% CI) |",
             "|---|---|---:|---:|---:|---:|---|---:|---|"]
    for _, r in test.iterrows():
        opt = lambda v: "" if pd.isna(v) else f"{v:.1f}"
        lines.append(
            f"| {r['combination']} | {r['fusion']} | {r['k']} | {opt(r['weight'])} "
            f"| {opt(r['beta'])} | {r[SELECT_ON]:.4f} | {r['mean_delta']:+.4f} "
            f"[{r['delta_lo']:+.4f}, {r['delta_hi']:+.4f}] | {r['share_positive']:.0%} "
            f"| {r['vs_wsf_mean_delta']:+.4f} [{r['vs_wsf_delta_lo']:+.4f}, "
            f"{r['vs_wsf_delta_hi']:+.4f}] |")
    (RESULTS / "fusion_rrf_tuned.md").write_text("\n".join(lines) + "\n",
                                                encoding="utf-8")
    print("\nwrote results/fusion_rrf_tuned_dev.csv")
    print("wrote results/fusion_rrf_tuned.csv")
    print("wrote results/fusion_rrf_tuned.md")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dense-model", default=DENSE_DEFAULT, choices=list(MODELS))
    ap.add_argument("--batch-size", type=int, default=64)
    ap.add_argument("--device", default=None)
    ap.add_argument("--no-cache", action="store_true")
    ap.add_argument("--render-only", action="store_true")
    ap.add_argument("--rrf-tuned", action="store_true",
                    help="tune RRF's k and weights on dev, score once on test, "
                         "write fusion_rrf_tuned*; the main results are untouched")
    args = ap.parse_args()

    if args.render_only:
        dev = pd.read_csv(RESULTS / "fusion_dev.csv")
        test = pd.read_csv(RESULTS / "fusion_test.csv")
        pp = RESULTS / "fusion_paired.csv"
        hp = RESULTS / "fusion_head_to_head.csv"
        paired = pd.read_csv(pp) if pp.exists() else pd.DataFrame()
        head = pd.read_csv(hp) if hp.exists() else pd.DataFrame()
        (RESULTS / "fusion.md").write_text(
            render(dev, test, args.dense_model, paired, head),
            encoding="utf-8")
        print("rewrote results/fusion.md from saved CSVs")
        return

    splits, texts, labels, skills, gold = load()
    runs, query_uris = build_runs(args, splits, texts, labels, skills)
    dense = args.dense_model
    print()

    # Combinations to evaluate. Each is a list of (method, language) keys.
    combos = {
        "hybrid pt": [("bm25", "pt"), (dense, "pt")],
        "hybrid en": [("bm25", "en"), (dense, "en")],
        f"bilingual {dense}": [(dense, "pt"), (dense, "en")],
        "bilingual bm25": [("bm25", "pt"), ("bm25", "en")],
        "all four": [("bm25", "pt"), ("bm25", "en"),
                     (dense, "pt"), (dense, "en")],
    }
    # The single runs each combination fuses, for paired comparisons.
    inputs = {name: [f"{m} {l}" for m, l in keys] for name, keys in combos.items()}
    if args.rrf_tuned:
        rrf_tuned(runs, query_uris, gold, combos, inputs)
        return

    test_rows, dev_rows = [], []
    per_query_store: dict[str, dict] = {}

    # Single-method references, scored the same way for comparability.
    for method in ("bm25", dense):
        for lang in LANGUAGES:
            name = f"{method} {lang}"
            agg, pq = score(runs[(method, lang, "test")],
                            query_uris["test"], gold)
            per_query_store[f"{name}|single"] = pq
            lo, hi = bootstrap_ci(list(pq.values()), SELECT_ON)
            test_rows.append({
                "combination": name, "fusion": "single",
                "weight": np.nan, **{m: agg[m] for m in HEADLINE},
                "ndcg@10_lo": lo, "ndcg@10_hi": hi,
            })

    # Reciprocal rank fusion. No weight, so test can be scored directly.
    for name, keys in combos.items():
        fused = reciprocal_rank_fusion(
            [runs[(m, l, "test")] for m, l in keys])
        agg, pq = score(fused, query_uris["test"], gold)
        per_query_store[f"{name}|rrf"] = pq
        lo, hi = bootstrap_ci(list(pq.values()), SELECT_ON)
        test_rows.append({
            "combination": name, "fusion": "rrf", "weight": np.nan,
            **{m: agg[m] for m in HEADLINE},
            "ndcg@10_lo": lo, "ndcg@10_hi": hi,
        })
        print(f"  RRF  {name:<24} {SELECT_ON} {agg[SELECT_ON]:.4f}")

    print()

    # Weighted score fusion over pairs only, weight swept on dev.
    for name, keys in combos.items():
        if len(keys) != 2:
            continue
        best = None
        for w in WEIGHT_GRID:
            fused = weighted_score_fusion(
                [runs[(m, l, "dev")] for m, l in keys], [w, 1.0 - w])
            agg, _ = score(fused, query_uris["dev"], gold)
            dev_rows.append({"combination": name, "weight": w,
                             SELECT_ON: agg[SELECT_ON]})
            if best is None or agg[SELECT_ON] > best[1]:
                best = (w, agg[SELECT_ON])

        w_star = best[0]
        fused = weighted_score_fusion(
            [runs[(m, l, "test")] for m, l in keys], [w_star, 1.0 - w_star])
        agg, pq = score(fused, query_uris["test"], gold)
        per_query_store[f"{name}|wsf"] = pq
        lo, hi = bootstrap_ci(list(pq.values()), SELECT_ON)
        test_rows.append({
            "combination": name, "fusion": "wsf", "weight": w_star,
            **{m: agg[m] for m in HEADLINE},
            "ndcg@10_lo": lo, "ndcg@10_hi": hi,
        })
        print(f"  WSF  {name:<24} {SELECT_ON} {agg[SELECT_ON]:.4f} "
              f"(dev-selected weight {w_star:.1f} on {keys[0][0]} {keys[0][1]})")

    # Four-way weighted fusion, parameterised over two axes rather than four
    # free weights: alpha splits lexical against dense, beta splits Portuguese
    # against English. Weights are the product, so they sum to one by
    # construction.
    print()
    order = [("bm25", "pt"), ("bm25", "en"), (dense, "pt"), (dense, "en")]
    best4 = None
    for alpha in WEIGHT_GRID_4WAY:
        for beta in WEIGHT_GRID_4WAY:
            wts = [alpha * beta, alpha * (1 - beta),
                   (1 - alpha) * beta, (1 - alpha) * (1 - beta)]
            fused = weighted_score_fusion(
                [runs[(m, l, "dev")] for m, l in order], wts)
            agg, _ = score(fused, query_uris["dev"], gold)
            dev_rows.append({"combination": "all four", "weight": alpha,
                             "beta": beta, SELECT_ON: agg[SELECT_ON]})
            if best4 is None or agg[SELECT_ON] > best4[2]:
                best4 = (alpha, beta, agg[SELECT_ON])

    alpha, beta, _ = best4
    wts = [alpha * beta, alpha * (1 - beta),
           (1 - alpha) * beta, (1 - alpha) * (1 - beta)]
    fused = weighted_score_fusion(
        [runs[(m, l, "test")] for m, l in order], wts)
    agg, pq = score(fused, query_uris["test"], gold)
    per_query_store["all four|wsf"] = pq
    lo, hi = bootstrap_ci(list(pq.values()), SELECT_ON)
    test_rows.append({
        "combination": "all four", "fusion": "wsf", "weight": alpha,
        "beta": beta, **{m: agg[m] for m in HEADLINE},
        "ndcg@10_lo": lo, "ndcg@10_hi": hi,
    })
    print(f"  WSF  {'all four':<24} {SELECT_ON} {agg[SELECT_ON]:.4f} "
          f"(dev-selected lexical weight {alpha:.1f}, pt weight {beta:.1f})")

    # Paired comparisons against the stronger of each combination's inputs.
    singles = {r["combination"]: r["ndcg@10"]
               for r in test_rows if r["fusion"] == "single"}
    paired_rows = []
    for row in test_rows:
        if row["fusion"] == "single":
            continue
        names = [n for n in inputs.get(row["combination"], []) if n in singles]
        if not names:
            continue
        base_name = max(names, key=lambda n: singles[n])
        stats = paired_delta(per_query_store[f"{row['combination']}|{row['fusion']}"],
                             per_query_store[f"{base_name}|single"])
        paired_rows.append({"combination": row["combination"],
                            "fusion": row["fusion"], "baseline": base_name,
                            "baseline_score": singles[base_name],
                            "fused_score": row["ndcg@10"], **stats})

    # Head to head between the strongest configurations. Comparing each of
    # them against a shared baseline leaves their difference from one another
    # undetermined, since those two comparisons are themselves correlated.
    ranked_rows = sorted(
        (r for r in test_rows if r["fusion"] != "single"),
        key=lambda r: -r["ndcg@10"])[:TOP_N_HEAD_TO_HEAD]
    head_rows = []
    for i, a in enumerate(ranked_rows):
        for b in ranked_rows[i + 1:]:
            ka = f"{a['combination']}|{a['fusion']}"
            kb = f"{b['combination']}|{b['fusion']}"
            stats = paired_delta(per_query_store[ka], per_query_store[kb])
            head_rows.append({
                "a": f"{a['combination']} ({a['fusion']})",
                "b": f"{b['combination']} ({b['fusion']})",
                "a_score": a["ndcg@10"], "b_score": b["ndcg@10"], **stats,
            })

    RESULTS.mkdir(exist_ok=True)
    dev = pd.DataFrame(dev_rows)
    test = pd.DataFrame(test_rows)
    pd.DataFrame(paired_rows).to_csv(RESULTS / "fusion_paired.csv", index=False)
    pd.DataFrame(head_rows).to_csv(RESULTS / "fusion_head_to_head.csv",
                                   index=False)
    dev.to_csv(RESULTS / "fusion_dev.csv", index=False)
    test.to_csv(RESULTS / "fusion_test.csv", index=False)
    (RESULTS / "fusion.md").write_text(
        render(dev, test, dense, pd.DataFrame(paired_rows),
               pd.DataFrame(head_rows)), encoding="utf-8")
    print("\nwrote results/fusion_dev.csv")
    print("wrote results/fusion_test.csv")
    print("wrote results/fusion_paired.csv")
    print("wrote results/fusion_head_to_head.csv")
    print("wrote results/fusion.md")


def render(dev: pd.DataFrame, test: pd.DataFrame, dense: str,
           paired: pd.DataFrame, head: pd.DataFrame) -> str:
    out: list[str] = []
    w = out.append

    w("# Fusion\n")
    w(f"BM25 and `{dense}` combined two ways: lexical with dense within a "
      f"language, and Portuguese with English for the same occupation. Runs are "
      f"produced at depth {RUN_DEPTH} and fused, then scored at the usual "
      f"cutoffs.")
    w("Reciprocal rank fusion has no weight, so it is scored on test directly. "
      "Weighted score fusion has its weight selected on dev and applied once to "
      "test.")
    w("Intervals are 95% percentile bootstrap over queries.\n")

    singles = test[test["fusion"] == "single"].set_index("combination")

    w("## Test results\n")
    w("| combination | fusion | weight | nDCG@10 (95% CI) | P@10 | R@10 | MRR |")
    w("|---|---|---:|---:|---:|---:|---:|")
    for _, r in test.iterrows():
        wt = "" if pd.isna(r["weight"]) else f"{r['weight']:.1f}"
        w(f"| {r['combination']} | {r['fusion']} | {wt} "
          f"| {r['ndcg@10']:.4f} [{r['ndcg@10_lo']:.4f}, {r['ndcg@10_hi']:.4f}] "
          f"| {r['precision@10']:.3f} | {r['recall@10']:.3f} | {r['mrr']:.3f} |")
    w("")

    w("## Gain over the better input\n")
    w("Fusion is only worth its cost if it beats the stronger of the two runs "
      "it combines, not merely the weaker one.\n")
    w("Every combination is scored on the identical 608 queries, so the "
      "comparison is paired. Marginal confidence intervals are a weak test "
      "here: two overlapping intervals can still correspond to a difference "
      "that holds on most queries. The interval below is on the per-query "
      "difference, and **won** is the share of queries where fusion beat the "
      "baseline.\n")
    if len(paired):
        w("| combination | fusion | baseline | baseline | fused | gain | "
          "paired difference (95% CI) | won |")
        w("|---|---|---|---:|---:|---:|---|---:|")
        for _, r in paired.iterrows():
            sig = "" if (r["delta_lo"] <= 0 <= r["delta_hi"]) else ""
            w(f"| {r['combination']} | {r['fusion']} | {r['baseline']} "
              f"| {r['baseline_score']:.4f} | {r['fused_score']:.4f} "
              f"| {r['fused_score'] / r['baseline_score'] - 1:+.1%} "
              f"| {r['mean_delta']:+.4f} [{r['delta_lo']:+.4f}, "
              f"{r['delta_hi']:+.4f}]{sig} | {r['share_positive']:.0%} |")
        w("")
        w("An interval that spans zero means the improvement is not "
          "distinguishable from none on this split, whatever the point "
          "estimate.\n")

    if len(head):
        w("## Head to head\n")
        w("The table above compares each configuration against a shared "
          "baseline, which leaves their difference from one another "
          "undetermined: two comparisons against the same baseline are "
          "correlated. These are direct paired comparisons between the "
          "strongest configurations.\n")
        w("| a | b | a | b | difference (95% CI) | a wins |")
        w("|---|---|---:|---:|---|---:|")
        for _, r in head.iterrows():
            sep = "" if (r["delta_lo"] <= 0 <= r["delta_hi"]) else " **"
            w(f"| {r['a']} | {r['b']} | {r['a_score']:.4f} | {r['b_score']:.4f} "
              f"| {r['mean_delta']:+.4f} [{r['delta_lo']:+.4f}, "
              f"{r['delta_hi']:+.4f}]{sep.strip()} | "
              f"{r['share_positive']:.0%} |")
        w("")
        w("Bold marks a difference whose interval excludes zero. Where the "
          "interval spans zero the two configurations are not separable on "
          "this split, whatever their point estimates.\n")

    pairs = dev[dev["combination"] != "all four"] if "beta" in dev.columns else dev
    if len(pairs):
        w("## Weight sweep on dev, pairs\n")
        w("Weight applies to the first run in each pair; the second takes one "
          "minus it. A selected weight at 0.0 or 1.0 would mean fusion did not "
          "beat using one run alone.\n")
        piv = pairs.pivot(index="weight", columns="combination", values=SELECT_ON)
        w("| weight | " + " | ".join(str(c) for c in piv.columns) + " |")
        w("|---|" + "---:|" * len(piv.columns))
        for weight, row in piv.iterrows():
            w(f"| {weight:.1f} | " + " | ".join(f"{v:.4f}" for v in row) + " |")
        w("")

    if "beta" in dev.columns:
        four = dev[dev["combination"] == "all four"]
        if len(four):
            w("## Weight sweep on dev, four-way\n")
            w("Rows are the weight on lexical against dense, columns the weight "
              "on Portuguese against English. Each cell's four weights are the "
              "product of the two, so they sum to one.\n")
            piv = four.pivot(index="weight", columns="beta", values=SELECT_ON)
            w("| lexical \\ pt | " + " | ".join(f"{c:.1f}" for c in piv.columns)
              + " |")
            w("|---|" + "---:|" * len(piv.columns))
            for a, row in piv.iterrows():
                w(f"| **{a:.1f}** | " + " | ".join(f"{v:.4f}" for v in row) + " |")
            w("")

    return "\n".join(out)


if __name__ == "__main__":
    main()