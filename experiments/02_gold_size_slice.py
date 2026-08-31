"""Does retrieval behaviour change with the size of the gold set?

The benchmark queries occupations, which carry a mean of 22 essential skills.
The target application queries learning outcomes, which carry 1 to 3. If method
rankings shift as gold sets shrink, the benchmark is a poor proxy for the
application. This slices the recorded per-query results into gold-size
quartiles to find out.

Reads results/bm25_per_query.csv rather than re-running retrieval, so the
numbers here are the same ones already committed. Writes:

    results/gold_size_slice.csv   per bucket per language per metric
    results/gold_size_slice.md    summary with bootstrap intervals

Usage:
    python -m experiments.02_gold_size_slice
    python -m experiments.02_gold_size_slice --variant description --stemming raw
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
PROCESSED = REPO_ROOT / "data" / "processed"
RESULTS = REPO_ROOT / "results"

METRICS = ["ndcg@10", "recall@10", "precision@10", "mrr"]
BUCKET_NAMES = ["Q1 smallest", "Q2", "Q3", "Q4 largest"]
LANGUAGES = ["pt", "en"]


def bootstrap_ci(values: np.ndarray, n_resamples: int = 2000,
                 confidence: float = 0.95, seed: int = 42) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(values), size=(n_resamples, len(values)))
    means = values[idx].mean(axis=1)
    lo = (1.0 - confidence) / 2.0
    return float(np.quantile(means, lo)), float(np.quantile(means, 1.0 - lo))


def gold_sizes() -> pd.Series:
    rel = pd.read_parquet(PROCESSED / "occupation_skill_relations.parquet")
    ess = rel[rel["relationType"] == "essential"]
    return ess.groupby("occupationUri").size().rename("n_gold")


def recall_ceiling(n_gold: pd.Series, k: int = 10) -> float:
    """Highest recall@k reachable given these gold set sizes."""
    return float((n_gold.clip(upper=k) / n_gold).mean())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", default="labels_desc")
    ap.add_argument("--stemming", default="stemmed", choices=["stemmed", "raw"])
    ap.add_argument("--quantiles", type=int, default=4)
    args = ap.parse_args()

    per_query = pd.read_csv(RESULTS / "bm25_per_query.csv")
    sel = per_query[(per_query["variant"] == args.variant)
                    & (per_query["stemming"] == args.stemming)].copy()
    if sel.empty:
        raise SystemExit(
            f"No rows for variant={args.variant} stemming={args.stemming}. "
            f"Run experiments/01_bm25.py first."
        )

    sel = sel.merge(gold_sizes(), left_on="occupationUri", right_index=True)

    # Bucket on the query set, not on the joined frame, so every language sees
    # the same occupations in the same bucket.
    queries = sel[["occupationUri", "n_gold"]].drop_duplicates()
    queries["bucket"] = pd.qcut(queries["n_gold"], args.quantiles,
                                labels=BUCKET_NAMES[:args.quantiles])
    sel = sel.merge(queries[["occupationUri", "bucket"]], on="occupationUri")

    rows = []
    for bucket in BUCKET_NAMES[:args.quantiles]:
        b = sel[sel["bucket"] == bucket]
        n_gold = b.drop_duplicates("occupationUri")["n_gold"]
        for lang in LANGUAGES:
            sub = b[b["language"] == lang]
            row = {
                "bucket": bucket,
                "language": lang,
                "queries": sub["occupationUri"].nunique(),
                "gold_min": int(n_gold.min()),
                "gold_max": int(n_gold.max()),
                "gold_median": int(n_gold.median()),
                "recall@10_ceiling": round(recall_ceiling(n_gold), 4),
            }
            for m in METRICS:
                v = sub[m].to_numpy(dtype=float)
                lo, hi = bootstrap_ci(v)
                row[m] = float(v.mean())
                row[f"{m}_lo"], row[f"{m}_hi"] = lo, hi
            rows.append(row)

    df = pd.DataFrame(rows)
    df.to_csv(RESULTS / "gold_size_slice.csv", index=False)
    (RESULTS / "gold_size_slice.md").write_text(
        render(df, args.variant, args.stemming), encoding="utf-8")

    print(render(df, args.variant, args.stemming))
    print(f"wrote results/gold_size_slice.csv")
    print(f"wrote results/gold_size_slice.md")


def render(df: pd.DataFrame, variant: str, stemming: str) -> str:
    out: list[str] = []
    w = out.append

    w("# Retrieval quality by gold set size\n")
    w(f"BM25, `{variant}`, {stemming}, test split. Occupations are split into "
      f"quartiles by number of essential skills. Computed from the per-query "
      f"results recorded by `experiments/01_bm25.py`; no retrieval is re-run.")
    w("Intervals are 95% percentile bootstrap over queries within each bucket.\n")

    w("## Buckets\n")
    w("| bucket | queries | essential skills | median | max recall@10 |")
    w("|---|---:|---|---:|---:|")
    for bucket in df["bucket"].unique():
        r = df[df["bucket"] == bucket].iloc[0]
        w(f"| {bucket} | {r['queries']} | {r['gold_min']}–{r['gold_max']} | "
          f"{r['gold_median']} | {r['recall@10_ceiling']:.3f} |")
    w("")
    w("Recall ceilings differ sharply between buckets, so recall is not "
      "comparable across them. nDCG normalises by the ideal ranking and is.\n")

    for m in METRICS:
        w(f"## {m}\n")
        w("| bucket | pt | en | en advantage |")
        w("|---|---|---|---:|")
        for bucket in df["bucket"].unique():
            b = df[df["bucket"] == bucket].set_index("language")
            pt, en = b.loc["pt"], b.loc["en"]
            adv = (en[m] / pt[m] - 1.0) if pt[m] else float("nan")
            w(f"| {bucket} | {pt[m]:.3f} [{pt[f'{m}_lo']:.3f}, {pt[f'{m}_hi']:.3f}] "
              f"| {en[m]:.3f} [{en[f'{m}_lo']:.3f}, {en[f'{m}_hi']:.3f}] "
              f"| {adv:+.1%} |")
        w("")

    # Per-bucket samples are roughly a quarter of the split, so intervals are
    # wide. Report separability rather than implying a bucket where intervals
    # touch is a bucket where the effect reverses.
    w("## Separability within buckets\n")
    w(f"Each bucket holds roughly a quarter of the split, so intervals are "
      f"wider than the pooled comparison and individual buckets may not "
      f"separate. What matters is whether the direction and magnitude are "
      f"consistent across buckets.\n")
    w("| bucket | queries | pt nDCG@10 | en nDCG@10 | separable at this n |")
    w("|---|---:|---|---|---|")
    advantages = []
    for bucket in df["bucket"].unique():
        b = df[df["bucket"] == bucket].set_index("language")
        pt, en = b.loc["pt"], b.loc["en"]
        overlap = pt["ndcg@10_hi"] >= en["ndcg@10_lo"]
        advantages.append(en["ndcg@10"] / pt["ndcg@10"] - 1.0)
        w(f"| {bucket} | {int(pt['queries'])} "
          f"| {pt['ndcg@10']:.3f} [{pt['ndcg@10_lo']:.3f}, {pt['ndcg@10_hi']:.3f}] "
          f"| {en['ndcg@10']:.3f} [{en['ndcg@10_lo']:.3f}, {en['ndcg@10_hi']:.3f}] "
          f"| {'no' if overlap else 'yes'} |")
    w("")
    w(f"English leads in {sum(a > 0 for a in advantages)} of {len(advantages)} "
      f"buckets, by {min(advantages):+.1%} to {max(advantages):+.1%}. "
      f"Consistent direction across independent buckets is the evidence here; "
      f"no single bucket is individually decisive.\n")

    return "\n".join(out)


if __name__ == "__main__":
    main()