"""Does stopword removal narrow the Portuguese retrieval gap?

Experiment 01 ran BM25 with no stopword list in either language, on the
reasoning that IDF already discounts common terms. Experiments 03 and 04 showed
that reasoning was incomplete: Portuguese and English share comparable
vocabulary with their gold skills by token count, but Portuguese's shared tokens
carry markedly less IDF weight. Removing 50 frequent terms costs Portuguese 47%
of its overlap against English's 36%.

The mechanism is that Portuguese spreads one grammatical function across more
token types. Six high-frequency forms of the definite article and its
contractions (o, a, os, as, do, da) each carry their own document frequency, so
each is discounted more weakly than English's single `the`, and more of that
mass survives into the score.

**Prediction, recorded before running:** removing stopwords improves Portuguese
more than English, and the Portuguese to English gap narrows. If it narrows
substantially, the gap reported in experiment 01 was in part an artefact of a
preprocessing choice rather than a property of ESCO's Portuguese content.

Stopword lists are NLTK's, which derive from Snowball and so pair with the
stemmers already in use. Curated rather than frequency-derived, because a top-N
cutoff removes different grammatical categories in each language and would
reintroduce the asymmetry under test.

32 conditions: 2 languages x 4 document variants x stemmed/raw x stopwords
on/off. Writes:

    results/bm25_stopwords_per_query.csv
    results/bm25_stopwords_summary.csv
    results/bm25_stopwords.md

Usage:
    python -m experiments.05_stopwords
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.eval.metrics import DEFAULT_KS, aggregate, bootstrap_ci, evaluate_query
from src.retrieval.bm25 import (VARIANTS, BM25Index, build_documents,
                                get_stemmer, get_stopwords)

REPO_ROOT = Path(__file__).resolve().parents[1]
PROCESSED = REPO_ROOT / "data" / "processed"
BENCHMARK = REPO_ROOT / "data" / "benchmark"
RESULTS = REPO_ROOT / "results"

LANGUAGES = ("pt", "en")
GRADES = {"essential": 2, "optional": 1}
HEADLINE = ["precision@10", "recall@10", "mrr", "ndcg@10", "micro_recall@10"]


def load(split: str):
    splits = pd.read_csv(BENCHMARK / "splits.csv")
    splits = splits[splits["split"] == split]
    texts = pd.read_parquet(PROCESSED / "texts.parquet")
    labels = pd.read_parquet(PROCESSED / "labels.parquet")
    skills = pd.read_parquet(PROCESSED / "skills.parquet")
    rel = pd.read_parquet(PROCESSED / "occupation_skill_relations.parquet")

    rel = rel[rel["occupationUri"].isin(splits["conceptUri"])]
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
    return skill_uris, preferred, alt, description


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="test", choices=["test", "dev"])
    ap.add_argument("--top-k", type=int, default=max(DEFAULT_KS))
    ap.add_argument("--render-only", action="store_true",
                    help="rebuild the markdown report from the saved summary "
                         "CSV without re-running retrieval")
    args = ap.parse_args()

    if args.render_only:
        summary = pd.read_csv(RESULTS / "bm25_stopwords_summary.csv")
        splits = pd.read_csv(BENCHMARK / "splits.csv")
        n_queries = int((splits["split"] == args.split).sum())
        n_skills = len(pd.read_parquet(PROCESSED / "skills.parquet"))
        (RESULTS / "bm25_stopwords.md").write_text(
            render(summary, args.split, n_queries, n_skills), encoding="utf-8")
        print("rewrote results/bm25_stopwords.md from the saved summary")
        return

    splits, texts, labels, skills, gold = load(args.split)
    print(f"{args.split} split: {len(splits):,} queries | "
          f"index: {len(skills):,} skills\n")

    rows, summaries = [], []

    for lang in LANGUAGES:
        skill_uris, preferred, alt, description = language_data(
            texts, labels, skills, lang)
        occ = texts[(texts["language"] == lang)
                    & (texts["conceptKind"] == "occupation")]
        occ_desc = dict(zip(occ["conceptUri"], occ["description"]))
        queries = [(u, occ_desc[u]) for u in splits["conceptUri"]]

        for use_stops in (False, True):
            stops = get_stopwords(lang) if use_stops else None
            for stemming in (False, True):
                stemmer = get_stemmer(lang) if stemming else None
                for variant in VARIANTS:
                    docs = build_documents(skill_uris, preferred, alt,
                                           description, variant)
                    index = BM25Index(skill_uris, docs, stemmer, stops)

                    per_query = []
                    for occ_uri, qtext in queries:
                        ranked = index.search(qtext, k=args.top_k)
                        scores = evaluate_query(ranked, gold[occ_uri])
                        per_query.append(scores)
                        rows.append({
                            "language": lang, "variant": variant,
                            "stemming": "stemmed" if stemming else "raw",
                            "stopwords": "removed" if use_stops else "kept",
                            "occupationUri": occ_uri,
                            **{k: v for k, v in scores.items()
                               if not k.startswith("_")},
                        })

                    agg = aggregate(per_query)
                    lo, hi = bootstrap_ci(per_query, "ndcg@10")
                    summaries.append({
                        "language": lang, "variant": variant,
                        "stemming": "stemmed" if stemming else "raw",
                        "stopwords": "removed" if use_stops else "kept",
                        **{m: agg[m] for m in HEADLINE},
                        "ndcg@10_lo": lo, "ndcg@10_hi": hi,
                        "mean_doc_tokens": round(index.mean_length, 1),
                        "empty_docs": index.empty,
                    })
                    print(f"  {lang} / {variant:<12} / "
                          f"{'stem' if stemming else 'raw ':<4} / "
                          f"{'stops removed' if use_stops else 'stops kept  '} "
                          f"nDCG@10 {agg['ndcg@10']:.4f} [{lo:.4f}, {hi:.4f}]  "
                          f"({index.mean_length:.0f} tok/doc)")

    RESULTS.mkdir(exist_ok=True)
    pd.DataFrame(rows).to_csv(
        RESULTS / "bm25_stopwords_per_query.csv", index=False)
    summary = pd.DataFrame(summaries)
    summary.to_csv(RESULTS / "bm25_stopwords_summary.csv", index=False)
    (RESULTS / "bm25_stopwords.md").write_text(
        render(summary, args.split, len(splits), len(skills)), encoding="utf-8")

    print(f"\nwrote results/bm25_stopwords_per_query.csv")
    print(f"wrote results/bm25_stopwords_summary.csv")
    print(f"wrote results/bm25_stopwords.md")


def render(s: pd.DataFrame, split: str, n_queries: int, n_skills: int) -> str:
    out: list[str] = []
    w = out.append
    g = s.set_index(["language", "variant", "stemming", "stopwords"])

    w("# BM25 with and without stopword removal\n")
    w(f"Split `{split}`, {n_queries:,} occupation-description queries against "
      f"all {n_skills:,} skills. Stopword lists are NLTK's, which derive from "
      f"Snowball and pair with the stemmers in use. Removal happens before "
      f"stemming, since the lists are of surface forms.")
    w("Intervals are 95% percentile bootstrap over queries.\n")

    w("## Effect of removing stopwords\n")
    w("nDCG@10, and the relative change from keeping them.\n")
    w("| lang | documents | stemming | kept | removed | change |")
    w("|---|---|---|---:|---:|---:|")
    for lang in LANGUAGES:
        for variant in VARIANTS:
            for stemming in ("raw", "stemmed"):
                kept = g.loc[(lang, variant, stemming, "kept"), "ndcg@10"]
                rem = g.loc[(lang, variant, stemming, "removed"), "ndcg@10"]
                w(f"| {lang} | {variant} | {stemming} | {kept:.4f} | "
                  f"{rem:.4f} | {rem/kept - 1:+.1%} |")
    w("")

    w("## Does the Portuguese gap narrow?\n")
    w("English advantage in nDCG@10, before and after removal. The prediction "
      "under test is that removal helps Portuguese more, so the advantage "
      "shrinks.\n")
    w("| documents | stemming | gap, stops kept | gap, stops removed | change |")
    w("|---|---|---:|---:|---:|")
    for variant in VARIANTS:
        for stemming in ("raw", "stemmed"):
            gaps = {}
            for stops in ("kept", "removed"):
                pt = g.loc[("pt", variant, stemming, stops), "ndcg@10"]
                en = g.loc[("en", variant, stemming, stops), "ndcg@10"]
                gaps[stops] = en / pt - 1.0
            delta = gaps["removed"] - gaps["kept"]
            w(f"| {variant} | {stemming} | {gaps['kept']:+.1%} | "
              f"{gaps['removed']:+.1%} | {100 * delta:+.1f} pp |")
    w("")

    w("## Full results\n")
    w("| lang | documents | stemming | stopwords | P@10 | R@10 | MRR | nDCG@10 (95% CI) | tok/doc |")
    w("|---|---|---|---|---:|---:|---:|---:|---:|")
    for _, r in s.iterrows():
        w(f"| {r['language']} | {r['variant']} | {r['stemming']} | "
          f"{r['stopwords']} | {r['precision@10']:.3f} | {r['recall@10']:.3f} | "
          f"{r['mrr']:.3f} | {r['ndcg@10']:.3f} "
          f"[{r['ndcg@10_lo']:.3f}, {r['ndcg@10_hi']:.3f}] | "
          f"{r['mean_doc_tokens']} |")
    w("")

    return "\n".join(out)


if __name__ == "__main__":
    main()