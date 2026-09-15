"""What is left of the language gap once dense retrieval has closed most of it?

Experiments 07 to 09 characterised the lexical gap: identical medians, a doubled
mean, and the whole difference produced by a tail of queries where the two
records use different words for the same concept. Experiment 11 showed dense
retrieval compresses that tail, cutting the gap from 22.3% to 8.9%.

An 8.9% residual survives, with disjoint intervals, and nothing measured so far
explains it. This asks whether it has the same shape as its predecessor.

Two questions, one experiment.

**Is the residual a tail or is it uniform?** If Portuguese still fails badly on
a minority of queries while matching English elsewhere, the residual is the
lexical story again in weaker form. If Portuguese is slightly worse across the
whole distribution, it is something else: a model that represents one language
better than the other rather than a data problem concentrated in specific
records.

**Do the two languages still fail on different queries?** Experiment 07 reported
a per-query correlation of 0.321 between the languages, but that was measured on
the count of non-gold skills outranking the best gold skill, a heavily skewed
statistic ranging to 1,162. Correlating nDCG@10 on the same queries gives 0.737,
so the languages fail together far more than that figure suggested. What matters
for bilingual fusion, which the deployment setting makes available since both
texts exist for every course unit, is the share of occupations where one
language fails and the other does not. That share is measured here directly
rather than inferred from a correlation.

Paired on occupation, which is valid because ESCO assigns one URI per concept
and the gold set for an occupation is identical in both languages.

Note on method: experiment 11 split queries into quartiles by the baseline
method's score. That is not repeated here. Splitting on the English score to
compare Portuguese would select groups on English noise with nothing to offset
the regression, so the comparison is made on distributions and on the paired
correlation instead.

Writes:
    results/residual_gap.csv
    results/residual_gap.md

Usage:
    python -m experiments.12_residual_gap
    python -m experiments.12_residual_gap --model qwen3-4b
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS = REPO_ROOT / "results"

METRIC = "ndcg@10"
PERCENTILES = [10, 25, 50, 75, 90]
FAILURE_THRESHOLD = 0.10


def bootstrap_ci(values: np.ndarray, n_resamples: int = 2000,
                 confidence: float = 0.95, seed: int = 42) -> tuple[float, float]:
    if len(values) == 0:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(values), size=(n_resamples, len(values)))
    means = values[idx].mean(axis=1)
    lo = (1.0 - confidence) / 2.0
    return float(np.quantile(means, lo)), float(np.quantile(means, 1.0 - lo))


def paired(df: pd.DataFrame, metric: str) -> pd.DataFrame:
    """One row per occupation with both languages' scores side by side."""
    p = df.pivot(index="occupationUri", columns="language", values=metric)
    return p.dropna()


def lexical_per_query() -> pd.DataFrame:
    """BM25 at its best configuration, for the shape comparison."""
    df = pd.read_csv(RESULTS / "bm25_stopwords_per_query.csv")
    df = df[(df["variant"] == "labels_desc") & (df["stemming"] == "stemmed")
            & (df["stopwords"] == "removed")]
    out = df[["language", "occupationUri", METRIC]].copy()
    out["model"] = "bm25"
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=None,
                    help="restrict to one bi-encoder; default is all")
    args = ap.parse_args()

    dense = pd.read_csv(RESULTS / "bi_encoder_per_query.csv")
    frames = [lexical_per_query()]
    models = [args.model] if args.model else sorted(dense["model"].unique())
    for m in models:
        sub = dense[dense["model"] == m][["language", "occupationUri", METRIC]].copy()
        sub["model"] = m
        frames.append(sub)
    allq = pd.concat(frames, ignore_index=True)

    rows = []
    for model in ["bm25"] + models:
        sub = allq[allq["model"] == model]
        p = paired(sub, METRIC)
        if not {"pt", "en"} <= set(p.columns):
            continue

        delta = p["en"] - p["pt"]
        lo, hi = bootstrap_ci(delta.to_numpy())
        row = {
            "model": model,
            "queries": len(p),
            "pt_mean": float(p["pt"].mean()),
            "en_mean": float(p["en"].mean()),
            "gap_relative": float(p["en"].mean() / p["pt"].mean() - 1),
            "mean_delta": float(delta.mean()),
            "delta_lo": lo, "delta_hi": hi,
            "correlation": float(p["pt"].corr(p["en"])),
            "spearman": float(p["pt"].corr(p["en"], method="spearman")),
            "pt_fails": float((p["pt"] < FAILURE_THRESHOLD).mean()),
            "en_fails": float((p["en"] < FAILURE_THRESHOLD).mean()),
            "both_fail": float(((p["pt"] < FAILURE_THRESHOLD)
                                & (p["en"] < FAILURE_THRESHOLD)).mean()),
            "pt_only_fails": float(((p["pt"] < FAILURE_THRESHOLD)
                                    & (p["en"] >= FAILURE_THRESHOLD)).mean()),
            "en_only_fails": float(((p["en"] < FAILURE_THRESHOLD)
                                    & (p["pt"] >= FAILURE_THRESHOLD)).mean()),
        }
        for q in PERCENTILES:
            row[f"pt_p{q}"] = float(np.percentile(p["pt"], q))
            row[f"en_p{q}"] = float(np.percentile(p["en"], q))
            # Gap at each percentile: if the residual is uniform this is flat,
            # if it is a tail it is large at the bottom and small at the top.
            row[f"gap_p{q}"] = float(
                np.percentile(p["en"], q) - np.percentile(p["pt"], q))
        rows.append(row)

        print(f"  {model:<16} gap {row['gap_relative']:+.1%}  "
              f"r={row['correlation']:.3f}  "
              f"pt-only failures {row['pt_only_fails']:.1%}")

    df = pd.DataFrame(rows)
    RESULTS.mkdir(exist_ok=True)
    df.to_csv(RESULTS / "residual_gap.csv", index=False)
    (RESULTS / "residual_gap.md").write_text(render(df), encoding="utf-8")
    print("\nwrote results/residual_gap.csv")
    print("wrote results/residual_gap.md")


def render(df: pd.DataFrame) -> str:
    out: list[str] = []
    w = out.append
    g = df.set_index("model")

    w("# The residual language gap under dense retrieval\n")
    w(f"Per-query `{METRIC}` on the test split, paired on occupation. The gold "
      f"set for an occupation is identical in both languages, since ESCO "
      f"assigns one URI per concept, so the pairing is exact.")
    w("No retrieval is re-run.\n")

    w("## Is the residual a tail or is it uniform?\n")
    w("Absolute gap between English and Portuguese at each percentile of the "
      "per-query score distribution. A tail effect shows a large gap at the "
      "bottom and a small one at the top. A uniform effect is flat.\n")
    w("| model | p10 | p25 | p50 | p75 | p90 | relative gap |")
    w("|---|---:|---:|---:|---:|---:|---:|")
    for model in g.index:
        r = g.loc[model]
        w(f"| {model} | " + " | ".join(f"{r[f'gap_p{q}']:+.4f}"
                                       for q in PERCENTILES)
          + f" | {r['gap_relative']:+.1%} |")
    w("")

    w("Portuguese and English distributions separately:\n")
    w("| model | lang | p10 | p25 | p50 | p75 | p90 |")
    w("|---|---|---:|---:|---:|---:|---:|")
    for model in g.index:
        r = g.loc[model]
        for lang in ("pt", "en"):
            w(f"| {model} | {lang} | "
              + " | ".join(f"{r[f'{lang}_p{q}']:.4f}" for q in PERCENTILES)
              + " |")
    w("")

    w("## Do the languages still fail on the same queries?\n")
    w("| model | Pearson r | Spearman | pt fails | en fails | both | pt only | en only |")
    w("|---|---:|---:|---:|---:|---:|---:|---:|")
    for model in g.index:
        r = g.loc[model]
        w(f"| {model} | {r['correlation']:.3f} | {r['spearman']:.3f} "
          f"| {r['pt_fails']:.1%} | {r['en_fails']:.1%} | {r['both_fail']:.1%} "
          f"| {r['pt_only_fails']:.1%} | {r['en_only_fails']:.1%} |")
    w("")
    w(f"A query counts as failed below {FAILURE_THRESHOLD:.2f}. The **pt only** "
      f"column is the share of occupations where Portuguese fails and English "
      f"does not, which is exactly what bilingual fusion could recover, since "
      f"the deployment setting supplies both texts for every course unit.\n")

    w("## Mean paired difference\n")
    w("| model | pt | en | difference | 95% CI |")
    w("|---|---:|---:|---:|---|")
    for model in g.index:
        r = g.loc[model]
        w(f"| {model} | {r['pt_mean']:.4f} | {r['en_mean']:.4f} "
          f"| {r['mean_delta']:+.4f} | [{r['delta_lo']:+.4f}, "
          f"{r['delta_hi']:+.4f}] |")
    w("")

    w("## Reading this\n")
    w("If the percentile gaps under the dense models are flat, the residual is "
      "a uniform representation difference rather than the tail phenomenon that "
      "produced the lexical gap, and the explanation for one does not carry to "
      "the other.\n")
    w("A low correlation means the two languages still fail on different "
      "occupations, which is the precondition for bilingual fusion. A "
      "correlation that rises sharply under a dense model would mean the model "
      "has normalised the language-specific failures away, leaving shared task "
      "difficulty, and fusion would have less to recover.\n")

    return "\n".join(out)


if __name__ == "__main__":
    main()