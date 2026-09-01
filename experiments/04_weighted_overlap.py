"""Does shared vocabulary carry the same weight in both languages?

Experiment 03 found Portuguese occupation descriptions share as much vocabulary
with their gold skills as English ones do, slightly more once stemmed, while
retrieving 24% worse. Counting token types treats every shared token alike. BM25
does not: it weights each match by inverse document frequency, so a match on a
term appearing in most of the corpus contributes almost nothing.

The hypothesis this tests: Portuguese shared tokens are more heavily function
words, so equal type overlap produces less usable signal. Portuguese has higher
function word density than English and no stopword list is applied in either
language, so those tokens survive into both the query and the documents and
overlap almost by default.

Three measures, each over the same token sets as experiment 03:

    type coverage       share of gold vocabulary present in the query
                        (reproduces 03, as a control)
    idf-weighted        the same, with each token weighted by its IDF in that
                        language's skill corpus
    content-only        type coverage after removing the most frequent corpus
                        terms, which stands in for a stopword list

If Portuguese leads on type coverage and loses on the weighted measure, the
retrieval gap is a weighting effect rather than a vocabulary one, and it is a
property of this pipeline rather than of ESCO's Portuguese content.

Writes:
    results/weighted_overlap.csv
    results/weighted_overlap.md

Usage:
    python -m experiments.04_weighted_overlap
    python -m experiments.04_weighted_overlap --top-n 100
"""

from __future__ import annotations

import argparse
import math
from collections import Counter
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


def skill_texts(texts, labels, lang: str) -> dict[str, dict[str, str]]:
    t = texts[(texts["language"] == lang) & (texts["conceptKind"] == "skill")]
    out = {u: {"labels": p, "description": d}
           for u, p, d in zip(t["conceptUri"], t["preferredLabel"], t["description"])}
    a = labels[(labels["language"] == lang) & (labels["labelType"] == "alt")]
    for uri, label in zip(a["conceptUri"], a["label"]):
        if uri in out:
            out[uri]["labels"] += " " + label
    return out


def corpus_stats(skill_tokens: dict[str, set[str]]) -> tuple[dict[str, float], Counter]:
    """Document frequency over the skill corpus, and IDF from it.

    Uses the same smoothed form as BM25 Okapi so the weights correspond to what
    the retriever actually applies:  log(1 + (N - df + 0.5) / (df + 0.5))
    """
    n = len(skill_tokens)
    df: Counter = Counter()
    for toks in skill_tokens.values():
        df.update(toks)
    idf = {t: math.log(1 + (n - d + 0.5) / (d + 0.5)) for t, d in df.items()}
    return idf, df


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="test", choices=["test", "dev"])
    ap.add_argument("--top-n", type=int, default=50,
                    help="most frequent corpus terms treated as stopwords")
    args = ap.parse_args()

    splits = pd.read_csv(BENCHMARK / "splits.csv")
    splits = splits[splits["split"] == args.split]
    texts = pd.read_parquet(PROCESSED / "texts.parquet")
    labels_df = pd.read_parquet(PROCESSED / "labels.parquet")
    rel = pd.read_parquet(PROCESSED / "occupation_skill_relations.parquet")

    ess = rel[(rel["relationType"] == "essential")
              & rel["occupationUri"].isin(splits["conceptUri"])]
    gold: dict[str, list[str]] = {}
    for occ, skill in zip(ess["occupationUri"], ess["skillUri"]):
        gold.setdefault(occ, []).append(skill)

    rows, frequent_terms = [], {}

    for lang in LANGUAGES:
        skills = skill_texts(texts, labels_df, lang)
        occ = texts[(texts["language"] == lang) & (texts["conceptKind"] == "occupation")]
        occ_desc = dict(zip(occ["conceptUri"], occ["description"]))

        for stemming in ("raw", "stemmed"):
            stemmer = get_stemmer(lang) if stemming == "stemmed" else None

            for field in FIELDS:
                skill_tokens = {u: set(tokenize(v[field], stemmer))
                                for u, v in skills.items()}
                idf, df = corpus_stats(skill_tokens)
                stop = {t for t, _ in df.most_common(args.top_n)}
                frequent_terms[(lang, stemming, field)] = df.most_common(15)

                type_cov, idf_cov, content_cov = [], [], []

                for occ_uri in splits["conceptUri"]:
                    q = set(tokenize(occ_desc[occ_uri], stemmer))
                    g: set[str] = set()
                    for s in gold.get(occ_uri, []):
                        g |= skill_tokens[s]
                    if not q or not g:
                        continue

                    shared = q & g
                    type_cov.append(len(shared) / len(g))

                    # Same ratio, but each token counts for its IDF.
                    total_w = sum(idf.get(t, 0.0) for t in g)
                    shared_w = sum(idf.get(t, 0.0) for t in shared)
                    idf_cov.append(shared_w / total_w if total_w else 0.0)

                    gc, sc = g - stop, shared - stop
                    content_cov.append(len(sc) / len(gc) if gc else 0.0)

                measures = {
                    "type_coverage": np.array(type_cov),
                    "idf_coverage": np.array(idf_cov),
                    "content_coverage": np.array(content_cov),
                }
                row = {"language": lang, "stemming": stemming, "field": field,
                       "queries": len(type_cov), "corpus_vocab": len(df)}
                for name, vals in measures.items():
                    lo, hi = bootstrap_ci(vals)
                    row[name] = float(vals.mean())
                    row[f"{name}_lo"], row[f"{name}_hi"] = lo, hi
                rows.append(row)

                print(f"  {lang} / {stemming:<8} / {field:<12} "
                      f"type {row['type_coverage']:.4f}  "
                      f"idf {row['idf_coverage']:.4f}  "
                      f"content {row['content_coverage']:.4f}")

    df_out = pd.DataFrame(rows)
    RESULTS.mkdir(exist_ok=True)
    df_out.to_csv(RESULTS / "weighted_overlap.csv", index=False)
    (RESULTS / "weighted_overlap.md").write_text(
        render(df_out, frequent_terms, args.split, args.top_n), encoding="utf-8")
    print(f"\nwrote results/weighted_overlap.csv")
    print(f"wrote results/weighted_overlap.md")


def render(df: pd.DataFrame, frequent: dict, split: str, top_n: int) -> str:
    out: list[str] = []
    w = out.append
    g = df.set_index(["language", "stemming", "field"])

    w("# Weighted lexical overlap\n")
    w(f"Split `{split}`. Experiment 03 measured how many gold tokens the query "
      f"reaches. This measures how much those tokens are worth.")
    w("No retrieval is run. IDF is computed over each language's skill corpus "
      "using the same smoothed form BM25 Okapi applies.")
    w("Intervals are 95% percentile bootstrap over queries.\n")

    w("## Three measures of the same overlap\n")
    for measure, title, note in [
        ("type_coverage", "Type coverage",
         "Share of gold tokens present in the query. Every token counts once. "
         "Reproduces experiment 03."),
        ("idf_coverage", "IDF-weighted coverage",
         "The same ratio with each token weighted by its IDF, so common terms "
         "contribute little. Closer to what BM25 acts on."),
        ("content_coverage", "Content-only coverage",
         f"Type coverage after removing each corpus's {top_n} most frequent "
         f"terms, standing in for a stopword list."),
    ]:
        w(f"### {title}\n")
        w(f"{note}\n")
        w("| field | stemming | pt | en | en advantage |")
        w("|---|---|---|---|---:|")
        for field in FIELDS:
            for stemming in ("raw", "stemmed"):
                pt, en = g.loc[("pt", stemming, field)], g.loc[("en", stemming, field)]
                adv = en[measure] / pt[measure] - 1.0 if pt[measure] else float("nan")
                w(f"| {field} | {stemming} "
                  f"| {pt[measure]:.4f} [{pt[f'{measure}_lo']:.4f}, "
                  f"{pt[f'{measure}_hi']:.4f}] "
                  f"| {en[measure]:.4f} [{en[f'{measure}_lo']:.4f}, "
                  f"{en[f'{measure}_hi']:.4f}] | {adv:+.1%} |")
        w("")

    w("## Most frequent corpus terms\n")
    w("The terms the weighting discounts. If the Portuguese list is dominated "
      "by function words while the English list carries content words, that is "
      "the mechanism.\n")
    for lang in LANGUAGES:
        terms = frequent[(lang, "stemmed", "description")]
        w(f"**{lang}, stemmed, description corpus**  ")
        w("`" + "` `".join(f"{t}({n})" for t, n in terms) + "`\n")

    w("## Vocabulary size\n")
    w("| field | stemming | pt | en |")
    w("|---|---|---:|---:|")
    for field in FIELDS:
        for stemming in ("raw", "stemmed"):
            w(f"| {field} | {stemming} "
              f"| {int(g.loc[('pt', stemming, field), 'corpus_vocab']):,} "
              f"| {int(g.loc[('en', stemming, field), 'corpus_vocab']):,} |")
    w("")

    return "\n".join(out)


if __name__ == "__main__":
    main()