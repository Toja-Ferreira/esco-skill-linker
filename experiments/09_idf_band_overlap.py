"""Does Portuguese lose overlap specifically on the terms that decide ranking?

Experiment 03 measured how much of a query's gold vocabulary the query reaches,
counting every token type once, and found Portuguese equal to English or
slightly ahead. Experiment 08 raises a possible objection to that measurement.
Among the worst Portuguese failures, a recurring pattern is that a query and its
gold skills use different renderings of the same rare technical term:

    cabedal / couro                      (leather)
    puncionadora / prensa biela-manivela (punch press)
    mudanca / movimentacao, deslocacao   (moving)
    estradas / rodoviaria, transito      (roads)

In each of those cases English uses one string on both sides and matches
exactly. They are the worst failures rather than a sample, so they establish
that the pattern occurs, not how often.

A count of token types might not see this even if it were widespread. Such a
count is dominated by ordinary mid-frequency vocabulary, which translates
consistently because there is one obvious rendering of words like `sistema` or
`efetuar`. The terms that decide a BM25 score are rare and high-IDF, and those
are where a translator has a real choice. Portuguese could match English on
total overlap while failing on the handful of terms that carry the score.

**Hypothesis:** Portuguese coverage is comparable to English in the low-IDF
bands and materially lower in the highest band. If Portuguese is lower in every
band, the effect is not specific to rare terms. If it is lower in none,
experiment 03's conclusion stands and the divergence is too infrequent to
register in aggregate.

**On banding.** IDF quantiles do not work here: terms appearing in exactly one
document all share the maximum IDF, and that tie covers about a quarter of the
vocabulary, so `np.quantile` splits it arbitrarily and the two rarest bands are
not distinguishable. `--by-df` bins on document frequency with explicit
boundaries instead, giving single-document terms their own band. The quantile
path is kept as the default so the original run remains reproducible.

Writes:
    results/idf_band_overlap.csv
    results/idf_band_overlap.md

Usage:
    python -m experiments.09_idf_band_overlap
    python -m experiments.09_idf_band_overlap --by-df
    python -m experiments.09_idf_band_overlap --bands 5
"""

from __future__ import annotations

import argparse
import math
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from src.retrieval.bm25 import (build_documents, get_stemmer, get_stopwords,
                                tokenize)

REPO_ROOT = Path(__file__).resolve().parents[1]
PROCESSED = REPO_ROOT / "data" / "processed"
BENCHMARK = REPO_ROOT / "data" / "benchmark"
RESULTS = REPO_ROOT / "results"

LANGUAGES = ("pt", "en")
VARIANT = "labels_desc"


def bootstrap_ci(values: np.ndarray, n_resamples: int = 2000,
                 confidence: float = 0.95, seed: int = 42) -> tuple[float, float]:
    if len(values) == 0:
        return float("nan"), float("nan")
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
    ap.add_argument("--bands", type=int, default=4)
    ap.add_argument("--by-df", action="store_true",
                    help="band on document frequency with explicit boundaries "
                         "instead of IDF quantiles, which tie at the top")
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

    band_names = [f"Q{i+1}" for i in range(args.bands)]
    band_names[0] += " commonest"
    band_names[-1] += " rarest"

    # Document frequency boundaries, used when --by-df is set. Terms appearing
    # in exactly one document form their own band, which is the group IDF
    # quantiles cannot separate because they all share the maximum IDF.
    DF_EDGES = [1, 2, 6, 51]
    DF_NAMES = ["df 1", "df 2 to 5", "df 6 to 50", "df 51+"]
    if args.by_df:
        band_names = DF_NAMES
        n_bands = len(DF_NAMES)
    else:
        n_bands = args.bands

    print(f"{args.split} split: {len(splits):,} queries | {VARIANT}, stemmed, "
          f"stopwords removed | "
          f"{'document frequency bands' if args.by_df else f'{n_bands} IDF quantile bands'}\n")

    rows, examples = [], {}

    for lang in LANGUAGES:
        skill_uris, preferred, alt, description = language_data(
            texts, labels, skills, lang)
        stemmer, stops = get_stemmer(lang), get_stopwords(lang)
        docs = build_documents(skill_uris, preferred, alt, description, VARIANT)
        skill_tokens = {u: set(tokenize(d, stemmer, stops))
                        for u, d in zip(skill_uris, docs)}

        n = len(skill_tokens)
        df: Counter = Counter()
        for toks in skill_tokens.values():
            df.update(toks)
        idf = {t: math.log(1 + (n - d + 0.5) / (d + 0.5)) for t, d in df.items()}

        # Bands are defined on the corpus, so a term always falls in the same
        # band regardless of which query it appears in.
        vocab = sorted(idf, key=lambda t: idf[t])
        if args.by_df:
            edges = [float(e) for e in DF_EDGES] + [float("inf")]

            def band_of(t: str) -> int:
                d = df.get(t, 1)
                for i in range(len(DF_EDGES) - 1, -1, -1):
                    if d >= DF_EDGES[i]:
                        return i
                return 0
        else:
            edges = np.quantile([idf[t] for t in vocab],
                                np.linspace(0, 1, n_bands + 1))

            def band_of(t: str) -> int:
                v = idf.get(t)
                if v is None:
                    return n_bands - 1
                return min(int(np.searchsorted(edges[1:-1], v, side="right")),
                           n_bands - 1)

        band_map = {t: band_of(t) for t in idf}
        examples[lang] = {
            b: [t for t in sorted(vocab, key=lambda x: -df[x])
                if band_map[t] == b][:8]
            for b in range(n_bands)
        }

        occ = texts[(texts["language"] == lang)
                    & (texts["conceptKind"] == "occupation")]
        occ_desc = dict(zip(occ["conceptUri"], occ["description"]))

        per_band: dict[int, list[float]] = {b: [] for b in range(n_bands)}
        gold_sizes: dict[int, list[int]] = {b: [] for b in range(n_bands)}

        for occ_uri in splits["conceptUri"]:
            q = set(tokenize(occ_desc[occ_uri], stemmer, stops))
            g: set[str] = set()
            for s in gold[occ_uri]:
                g |= skill_tokens[s]
            if not q or not g:
                continue
            shared = q & g
            for b in range(n_bands):
                gb = {t for t in g if band_map.get(t, n_bands - 1) == b}
                if not gb:
                    continue
                sb = shared & gb
                per_band[b].append(len(sb) / len(gb))
                gold_sizes[b].append(len(gb))

        for b in range(n_bands):
            v = np.array(per_band[b])
            lo, hi = bootstrap_ci(v)
            rows.append({
                "language": lang, "band": band_names[b], "band_index": b,
                "queries": len(v), "coverage": float(v.mean()),
                "coverage_lo": lo, "coverage_hi": hi,
                "mean_gold_terms": float(np.mean(gold_sizes[b])),
                "band_lo": float(edges[b]), "band_hi": float(edges[b + 1]),
            })
            print(f"  {lang} {band_names[b]:<14} coverage {v.mean():.4f} "
                  f"[{lo:.4f}, {hi:.4f}]  "
                  f"({np.mean(gold_sizes[b]):.0f} gold terms, "
                  f"range {edges[b]:.2f} to {edges[b+1]:.2f})")
        print()

    df_out = pd.DataFrame(rows)
    RESULTS.mkdir(exist_ok=True)
    df_out.to_csv(RESULTS / "idf_band_overlap.csv", index=False)
    (RESULTS / "idf_band_overlap.md").write_text(
        render(df_out, examples, band_names, args.split), encoding="utf-8")
    print(f"wrote results/idf_band_overlap.csv")
    print(f"wrote results/idf_band_overlap.md")


def render(df: pd.DataFrame, examples: dict, band_names: list[str],
           split: str) -> str:
    out: list[str] = []
    w = out.append
    g = df.set_index(["language", "band"])

    w("# Overlap by IDF band\n")
    w(f"Split `{split}`, `{VARIANT}`, stemmed, stopwords removed. The same "
      f"query-to-gold overlap as experiment 03, split by how discriminative "
      f"each term is. Bands are quantiles of the corpus vocabulary by IDF, so a "
      f"term sits in the same band for every query.")
    w("Intervals are 95% percentile bootstrap over queries.\n")

    w("## Gold vocabulary covered by the query, per band\n")
    w("| band | pt | en | en advantage | pt gold terms | en gold terms |")
    w("|---|---|---|---:|---:|---:|")
    for band in band_names:
        pt, en = g.loc[("pt", band)], g.loc[("en", band)]
        adv = en["coverage"] / pt["coverage"] - 1 if pt["coverage"] else float("nan")
        w(f"| {band} "
          f"| {pt['coverage']:.4f} [{pt['coverage_lo']:.4f}, {pt['coverage_hi']:.4f}] "
          f"| {en['coverage']:.4f} [{en['coverage_lo']:.4f}, {en['coverage_hi']:.4f}] "
          f"| {adv:+.1%} | {pt['mean_gold_terms']:.0f} | {en['mean_gold_terms']:.0f} |")
    w("")

    lows = [g.loc[("en", b), "coverage"] / g.loc[("pt", b), "coverage"] - 1
            for b in band_names[:-1]]
    high = g.loc[("en", band_names[-1]), "coverage"] / \
           g.loc[("pt", band_names[-1]), "coverage"] - 1
    w(f"English advantage in the rarest band is {high:+.1%}, against "
      f"{min(lows):+.1%} to {max(lows):+.1%} in the commoner bands.\n")

    w("## What the bands contain\n")
    w("Most frequent terms in each band, to show what the split is separating.\n")
    for lang in LANGUAGES:
        w(f"**{lang}**\n")
        for b, band in enumerate(band_names):
            terms = examples[lang][b]
            w(f"- *{band}*: `" + "` `".join(terms) + "`")
        w("")

    w("## Reading this\n")
    w("Rare terms carry most of a BM25 score. If Portuguese coverage matches "
      "English on common terms and falls behind on rare ones, then the two "
      "languages share comparable vocabulary overall while diverging precisely "
      "where ranking is decided. That is what inconsistent translation of "
      "technical terminology would produce, and it is invisible to a measure "
      "that counts every token type equally.\n")

    return "\n".join(out)


if __name__ == "__main__":
    main()