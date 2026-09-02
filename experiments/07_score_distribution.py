"""Do Portuguese gold skills separate from the field as well as English ones?

Experiments 03 and 04 measured how much vocabulary a query shares with its gold
skills. Neither measured what it shares with the roughly 13,000 non-gold skills.
Ranking is a contest: a gold skill scoring well still ranks poorly if many
distractors score similarly. Only the numerator has been examined.

The hypothesis: Portuguese gold skills score as well as English ones in absolute
terms, but Portuguese distractors also score well, so gold does not stand out.
Every remaining lexical explanation reduces to this, because a retrieval metric
is a function of ordering alone.

Four measures per query, over the full score vector across all skills:

    gold_percentile     where the best gold skill sits in the score
                        distribution, as a percentile of all candidates
    n_outranking        how many non-gold skills outscore the best gold skill
    separation          (mean gold score - mean non-gold score) divided by the
                        standard deviation of non-gold scores. A signal to noise
                        ratio: how many standard deviations gold sits above the
                        field
    top_flatness        (score at rank 10 - score at rank 100) divided by the
                        score at rank 1. A flat top means many candidates are
                        nearly tied and small differences decide the ordering

Configuration is fixed to the current best: labels_desc, stemmed, stopwords
removed, BM25 defaults. Writes:

    results/score_distribution.csv    per language per measure
    results/score_distribution.md

Usage:
    python -m experiments.07_score_distribution
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from src.retrieval.bm25 import (BM25Index, build_documents, get_stemmer,
                                get_stopwords)

REPO_ROOT = Path(__file__).resolve().parents[1]
PROCESSED = REPO_ROOT / "data" / "processed"
BENCHMARK = REPO_ROOT / "data" / "benchmark"
RESULTS = REPO_ROOT / "results"

LANGUAGES = ("pt", "en")
VARIANT = "labels_desc"


def bootstrap_ci(values: np.ndarray, n_resamples: int = 2000,
                 confidence: float = 0.95, seed: int = 42) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(values), size=(n_resamples, len(values)))
    means = values[idx].mean(axis=1)
    lo = (1.0 - confidence) / 2.0
    return float(np.quantile(means, lo)), float(np.quantile(means, 1.0 - lo))


def language_data(texts, labels, skills, lang: str):
    skill_uris = sorted(skills["conceptUri"])
    t = texts[texts["language"] == lang]
    preferred = dict(zip(t["conceptUri"], t["preferredLabel"]))
    description = dict(zip(t["conceptUri"], t["description"]))
    a = labels[(labels["language"] == lang) & (labels["labelType"] == "alt")]
    alt: dict[str, list[str]] = {}
    for uri, label in zip(a["conceptUri"], a["label"]):
        alt.setdefault(uri, []).append(label)
    return skill_uris, preferred, alt, description


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="test", choices=["test", "dev"])
    args = ap.parse_args()

    splits = pd.read_csv(BENCHMARK / "splits.csv")
    splits = splits[splits["split"] == args.split]
    texts = pd.read_parquet(PROCESSED / "texts.parquet")
    labels = pd.read_parquet(PROCESSED / "labels.parquet")
    skills = pd.read_parquet(PROCESSED / "skills.parquet")
    rel = pd.read_parquet(PROCESSED / "occupation_skill_relations.parquet")

    ess = rel[(rel["relationType"] == "essential")
              & rel["occupationUri"].isin(splits["conceptUri"])]
    gold: dict[str, set[str]] = {}
    for occ, skill in zip(ess["occupationUri"], ess["skillUri"]):
        gold.setdefault(occ, set()).add(skill)

    print(f"{args.split} split: {len(splits):,} queries | "
          f"{len(skills):,} skills | {VARIANT}, stemmed, stopwords removed\n")

    rows, per_query_rows = [], []

    for lang in LANGUAGES:
        skill_uris, preferred, alt, description = language_data(
            texts, labels, skills, lang)
        docs = build_documents(skill_uris, preferred, alt, description, VARIANT)
        index = BM25Index(skill_uris, docs, get_stemmer(lang), get_stopwords(lang))

        uri_to_pos = {u: i for i, u in enumerate(skill_uris)}
        occ = texts[(texts["language"] == lang)
                    & (texts["conceptKind"] == "occupation")]
        occ_desc = dict(zip(occ["conceptUri"], occ["description"]))

        measures: dict[str, list[float]] = {
            "gold_percentile": [], "n_outranking": [], "separation": [],
            "top_flatness": [], "top1_score": [], "mean_gold_score": [],
            "mean_nongold_score": [], "nongold_sd": [],
        }

        for occ_uri in splits["conceptUri"]:
            from src.retrieval.bm25 import tokenize
            q = tokenize(occ_desc[occ_uri], index.stemmer, index.stopwords)
            if not q:
                continue
            scores = index.bm25.get_scores(q)

            gold_pos = np.array([uri_to_pos[u] for u in gold[occ_uri]
                                 if u in uri_to_pos])
            mask = np.zeros(len(scores), dtype=bool)
            mask[gold_pos] = True
            gold_scores, nongold = scores[mask], scores[~mask]

            best_gold = gold_scores.max()
            measures["n_outranking"].append(float((nongold > best_gold).sum()))
            measures["gold_percentile"].append(
                float((scores < best_gold).mean() * 100))

            sd = nongold.std()
            measures["separation"].append(
                float((gold_scores.mean() - nongold.mean()) / sd) if sd > 0 else 0.0)

            ordered = np.sort(scores)[::-1]
            top1 = ordered[0]
            measures["top_flatness"].append(
                float((ordered[9] - ordered[99]) / top1) if top1 > 0 else 0.0)

            measures["top1_score"].append(float(top1))
            measures["mean_gold_score"].append(float(gold_scores.mean()))
            measures["mean_nongold_score"].append(float(nongold.mean()))
            measures["nongold_sd"].append(float(sd))

            per_query_rows.append({
                "language": lang, "occupationUri": occ_uri,
                **{k: v[-1] for k, v in measures.items()},
            })

        row = {"language": lang, "queries": len(measures["separation"])}
        for name, vals in measures.items():
            v = np.array(vals)
            row[name] = float(v.mean())
            row[f"{name}_median"] = float(np.median(v))
            if name in ("separation", "n_outranking", "top_flatness",
                        "gold_percentile"):
                lo, hi = bootstrap_ci(v)
                row[f"{name}_lo"], row[f"{name}_hi"] = lo, hi
        rows.append(row)

        print(f"  {lang}  separation {row['separation']:.3f} sd  |  "
              f"non-gold outranking best gold: {row['n_outranking']:.0f} "
              f"(median {row['n_outranking_median']:.0f})  |  "
              f"top flatness {row['top_flatness']:.3f}")

    df = pd.DataFrame(rows)
    RESULTS.mkdir(exist_ok=True)
    df.to_csv(RESULTS / "score_distribution.csv", index=False)
    pd.DataFrame(per_query_rows).to_csv(
        RESULTS / "score_distribution_per_query.csv", index=False)
    (RESULTS / "score_distribution.md").write_text(
        render(df, args.split, len(skills)), encoding="utf-8")

    print(f"\nwrote results/score_distribution.csv")
    print(f"wrote results/score_distribution_per_query.csv")
    print(f"wrote results/score_distribution.md")


def render(df: pd.DataFrame, split: str, n_skills: int) -> str:
    out: list[str] = []
    w = out.append
    g = df.set_index("language")

    w("# Score distribution: does gold separate from the field?\n")
    w(f"Split `{split}`, {VARIANT}, stemmed, stopwords removed, BM25 defaults. "
      f"Each query produces a score over all {n_skills:,} skills; these measure "
      f"where the gold skills sit within it.")
    w("Intervals are 95% percentile bootstrap over queries.\n")

    w("## Separation\n")
    w("Mean gold score minus mean non-gold score, in units of the non-gold "
      "standard deviation. Higher means gold stands further above the field, "
      "which is what a ranking metric rewards.\n")
    w("| language | separation | 95% CI |")
    w("|---|---:|---|")
    for lang in LANGUAGES:
        r = g.loc[lang]
        w(f"| {lang} | {r['separation']:.4f} | "
          f"[{r['separation_lo']:.4f}, {r['separation_hi']:.4f}] |")
    adv = g.loc["en", "separation"] / g.loc["pt", "separation"] - 1
    w(f"\nEnglish separation is {adv:+.1%} relative to Portuguese.\n")

    w("## How much competition sits above the best gold skill\n")
    w("| language | non-gold outranking best gold | median | best gold percentile |")
    w("|---|---:|---:|---:|")
    for lang in LANGUAGES:
        r = g.loc[lang]
        w(f"| {lang} | {r['n_outranking']:.1f} | "
          f"{r['n_outranking_median']:.0f} | {r['gold_percentile']:.3f} |")
    w("")

    w("## Flatness at the top\n")
    w("Score at rank 10 minus score at rank 100, divided by the score at rank "
      "1. A flatter top means many candidates are nearly tied, so small "
      "differences decide the ordering.\n")
    w("| language | flatness | 95% CI |")
    w("|---|---:|---|")
    for lang in LANGUAGES:
        r = g.loc[lang]
        w(f"| {lang} | {r['top_flatness']:.4f} | "
          f"[{r['top_flatness_lo']:.4f}, {r['top_flatness_hi']:.4f}] |")
    w("")

    w("## Raw score levels\n")
    w("Included so the normalised measures above can be checked. Absolute BM25 "
      "scores are not comparable across corpora; the ratios are what matter.\n")
    w("| language | rank-1 score | mean gold | mean non-gold | non-gold sd |")
    w("|---|---:|---:|---:|---:|")
    for lang in LANGUAGES:
        r = g.loc[lang]
        w(f"| {lang} | {r['top1_score']:.2f} | {r['mean_gold_score']:.2f} "
          f"| {r['mean_nongold_score']:.2f} | {r['nongold_sd']:.2f} |")
    w("")

    w("## Reading this\n")
    w("If Portuguese separation is materially lower, the residual gap is a "
      "signal to noise problem: gold scores as well as it does in English but "
      "the field scores well too, so ordering degrades. That would be the "
      "mechanism the earlier overlap experiments could not see, since they "
      "measured only the query to gold relationship.\n")
    w("If separation is comparable while the retrieval metrics still differ, "
      "the cause is not capturable by any aggregate of the score distribution, "
      "and lexical analysis has been exhausted.\n")

    return "\n".join(out)


if __name__ == "__main__":
    main()