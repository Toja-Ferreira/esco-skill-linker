"""How much vocabulary do occupation descriptions share with their gold skills?

BM25 can only score a match on tokens that appear on both sides. If Portuguese
occupation descriptions share fewer tokens with their gold skills than English
ones do, that is the mechanism behind the retrieval gap, and it points at the
source text rather than at the retrieval method.

Two splits make the result interpretable:

**Raw against stemmed.** A gap on raw tokens that closes under stemming is
morphological: the same word in different forms. A gap that persists under
stemming is vocabulary choice, which is what the translation-drift explanation
predicts. The size of the raw-to-stemmed jump within one language also measures
how much that language's stemmer actually conflates, which is the competing
explanation.

**Labels against descriptions.** Scored separately, because English carries
roughly 24 times more alternative labels while descriptions are complete in both
languages. Mixing them would blur the field where the puzzle lives.

Measures no retrieval, so nothing here depends on BM25 parameters. Writes:

    results/lexical_overlap.csv
    results/lexical_overlap.md

Usage:
    python -m experiments.03_lexical_overlap
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from src.retrieval.bm25 import get_stemmer, tokenize

REPO_ROOT = Path(__file__).resolve().parents[1]
PROCESSED = REPO_ROOT / "data" / "processed"
BENCHMARK = REPO_ROOT / "data" / "benchmark"
RESULTS = REPO_ROOT / "results"

LANGUAGES = ["pt", "en"]
FIELDS = ["labels", "description"]


def bootstrap_ci(values: np.ndarray, n_resamples: int = 2000,
                 confidence: float = 0.95, seed: int = 42) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(values), size=(n_resamples, len(values)))
    means = values[idx].mean(axis=1)
    lo = (1.0 - confidence) / 2.0
    return float(np.quantile(means, lo)), float(np.quantile(means, 1.0 - lo))


def skill_texts(texts: pd.DataFrame, labels: pd.DataFrame,
                lang: str) -> dict[str, dict[str, str]]:
    """Per skill, the two text fields kept apart."""
    t = texts[(texts["language"] == lang) & (texts["conceptKind"] == "skill")]
    out = {u: {"labels": p, "description": d}
           for u, p, d in zip(t["conceptUri"], t["preferredLabel"], t["description"])}

    a = labels[(labels["language"] == lang) & (labels["labelType"] == "alt")]
    for uri, label in zip(a["conceptUri"], a["label"]):
        if uri in out:
            out[uri]["labels"] += " " + label
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="test", choices=["test", "dev"])
    args = ap.parse_args()

    splits = pd.read_csv(BENCHMARK / "splits.csv")
    splits = splits[splits["split"] == args.split]
    texts = pd.read_parquet(PROCESSED / "texts.parquet")
    labels = pd.read_parquet(PROCESSED / "labels.parquet")
    rel = pd.read_parquet(PROCESSED / "occupation_skill_relations.parquet")

    ess = rel[(rel["relationType"] == "essential")
              & rel["occupationUri"].isin(splits["conceptUri"])]
    gold: dict[str, list[str]] = {}
    for occ, skill in zip(ess["occupationUri"], ess["skillUri"]):
        gold.setdefault(occ, []).append(skill)

    rows = []
    per_query: dict[tuple, np.ndarray] = {}

    for lang in LANGUAGES:
        skills = skill_texts(texts, labels, lang)
        occ = texts[(texts["language"] == lang) & (texts["conceptKind"] == "occupation")]
        occ_desc = dict(zip(occ["conceptUri"], occ["description"]))

        for stemming in ("raw", "stemmed"):
            stemmer = get_stemmer(lang) if stemming == "stemmed" else None

            for field in FIELDS:
                covered, jaccard, gold_sizes = [], [], []

                for occ_uri in splits["conceptUri"]:
                    q = set(tokenize(occ_desc[occ_uri], stemmer))
                    if not q:
                        continue

                    # Union of the gold skills' tokens for this field.
                    g: set[str] = set()
                    for skill_uri in gold.get(occ_uri, []):
                        g |= set(tokenize(skills[skill_uri][field], stemmer))
                    if not g:
                        continue

                    shared = q & g
                    # Share of the gold vocabulary the query can reach. This is
                    # the quantity BM25 depends on: a gold token absent from the
                    # query contributes nothing to that skill's score.
                    covered.append(len(shared) / len(g))
                    jaccard.append(len(shared) / len(q | g))
                    gold_sizes.append(len(g))

                cov = np.array(covered)
                jac = np.array(jaccard)
                lo, hi = bootstrap_ci(cov)
                per_query[(lang, stemming, field)] = cov

                rows.append({
                    "language": lang, "stemming": stemming, "field": field,
                    "queries": len(cov),
                    "gold_coverage": float(cov.mean()),
                    "gold_coverage_lo": lo, "gold_coverage_hi": hi,
                    "jaccard": float(jac.mean()),
                    "mean_gold_vocab": float(np.mean(gold_sizes)),
                })
                print(f"  {lang} / {stemming:<8} / {field:<12} "
                      f"coverage {cov.mean():.4f} [{lo:.4f}, {hi:.4f}]  "
                      f"jaccard {jac.mean():.4f}  "
                      f"({np.mean(gold_sizes):.0f} gold tokens)")

    df = pd.DataFrame(rows)
    RESULTS.mkdir(exist_ok=True)
    df.to_csv(RESULTS / "lexical_overlap.csv", index=False)
    (RESULTS / "lexical_overlap.md").write_text(
        render(df, args.split), encoding="utf-8")
    print(f"\nwrote results/lexical_overlap.csv")
    print(f"wrote results/lexical_overlap.md")


def render(df: pd.DataFrame, split: str) -> str:
    out: list[str] = []
    w = out.append
    g = df.set_index(["language", "stemming", "field"])

    w("# Lexical overlap between queries and their gold skills\n")
    w(f"Split `{split}`. For each occupation, the share of its gold skills' "
      f"vocabulary that also appears in the occupation description. This is the "
      f"quantity BM25 depends on: a token present in a gold skill but absent "
      f"from the query contributes nothing to that skill's score.")
    w("No retrieval is run, so nothing here depends on BM25 parameters.")
    w("Intervals are 95% percentile bootstrap over queries.\n")

    w("## Gold vocabulary covered by the query\n")
    w("| field | stemming | pt | en | en advantage |")
    w("|---|---|---|---|---:|")
    for field in FIELDS:
        for stemming in ("raw", "stemmed"):
            pt, en = g.loc[("pt", stemming, field)], g.loc[("en", stemming, field)]
            adv = en["gold_coverage"] / pt["gold_coverage"] - 1.0
            w(f"| {field} | {stemming} "
              f"| {pt['gold_coverage']:.4f} [{pt['gold_coverage_lo']:.4f}, "
              f"{pt['gold_coverage_hi']:.4f}] "
              f"| {en['gold_coverage']:.4f} [{en['gold_coverage_lo']:.4f}, "
              f"{en['gold_coverage_hi']:.4f}] | {adv:+.1%} |")
    w("")

    w("## What stemming recovers\n")
    w("Relative gain in coverage from stemming, within each language. A "
      "language whose stemmer conflates more aggressively gains more.\n")
    w("| field | pt | en |")
    w("|---|---:|---:|")
    for field in FIELDS:
        vals = []
        for lang in LANGUAGES:
            raw = g.loc[(lang, "raw", field), "gold_coverage"]
            stem = g.loc[(lang, "stemmed", field), "gold_coverage"]
            vals.append(stem / raw - 1.0)
        w(f"| {field} | {vals[0]:+.1%} | {vals[1]:+.1%} |")
    w("")

    w("## Gold vocabulary size\n")
    w("Mean distinct tokens across an occupation's gold skills. Sets the "
      "denominator above, and shows how much larger the English label "
      "vocabulary is.\n")
    w("| field | stemming | pt | en |")
    w("|---|---|---:|---:|")
    for field in FIELDS:
        for stemming in ("raw", "stemmed"):
            w(f"| {field} | {stemming} "
              f"| {g.loc[('pt', stemming, field), 'mean_gold_vocab']:.0f} "
              f"| {g.loc[('en', stemming, field), 'mean_gold_vocab']:.0f} |")
    w("")

    w("## Reading this\n")
    w("On `description`, both languages have complete coverage of the field, so "
      "a gap there is about word choice rather than about how much text exists. "
      "If the gap persists under stemming, it is vocabulary drift between "
      "independently translated records. If stemming closes it, the gap was "
      "morphological and the retrieval difference is a stemmer question.\n")
    w("On `labels`, the English vocabulary is far larger because of alternative "
      "label coverage, so coverage figures there are not directly comparable "
      "between languages: the denominators differ.\n")

    return "\n".join(out)


if __name__ == "__main__":
    main()