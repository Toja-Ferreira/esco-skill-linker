"""BM25 baseline: 2 languages x 4 document variants x 2 stemming settings.

Queries are occupation descriptions from the frozen test split. Every
condition searches the full index of all skills. Writes:

    results/bm25_per_query.csv   one row per query per condition
    results/bm25.md              summary table with bootstrap CIs

Usage:
    python -m experiments.01_bm25
    python -m experiments.01_bm25 --split dev
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import pandas as pd

from src.eval.metrics import DEFAULT_KS, aggregate, bootstrap_ci, evaluate_query
from src.retrieval.bm25 import VARIANTS, BM25Index, build_documents, get_stemmer

REPO_ROOT = Path(__file__).resolve().parents[1]
PROCESSED = REPO_ROOT / "data" / "processed"
BENCHMARK = REPO_ROOT / "data" / "benchmark"
RESULTS = REPO_ROOT / "results"

LANGUAGES = ("pt", "en")
GRADES = {"essential": 2, "optional": 1}

# Reported in the summary table. The full set is written per-query.
HEADLINE = ["precision@10", "recall@10", "mrr", "ndcg@10", "micro_recall@10"]


def load(split: str):
    splits = pd.read_csv(BENCHMARK / "splits.csv")
    splits = splits[splits["split"] == split]

    texts = pd.read_parquet(PROCESSED / "texts.parquet")
    labels = pd.read_parquet(PROCESSED / "labels.parquet")
    skills = pd.read_parquet(PROCESSED / "skills.parquet")
    rel = pd.read_parquet(PROCESSED / "occupation_skill_relations.parquet")

    # Gold: occupation URI -> {skill URI: grade}
    rel = rel[rel["occupationUri"].isin(splits["conceptUri"])]
    gold: dict[str, dict[str, int]] = {}
    for occ_uri, skill_uri, rtype in zip(
        rel["occupationUri"], rel["skillUri"], rel["relationType"]
    ):
        gold.setdefault(occ_uri, {})[skill_uri] = GRADES[rtype]

    return splits, texts, labels, skills, gold


def language_data(texts, labels, skills, lang: str):
    """Per-language lookups for building documents and queries."""
    skill_uris = sorted(skills["conceptUri"])

    t = texts[texts["language"] == lang]
    preferred = dict(zip(t["conceptUri"], t["preferredLabel"]))
    description = dict(zip(t["conceptUri"], t["description"]))

    a = labels[(labels["language"] == lang) & (labels["labelType"] == "alt")]
    alt: dict[str, list[str]] = {}
    for uri, label in zip(a["conceptUri"], a["label"]):
        alt.setdefault(uri, []).append(label)

    return skill_uris, preferred, alt, description


def recall_ceilings(gold: dict[str, dict[str, int]], uris) -> dict[int, float]:
    """Highest recall@k any system could reach on this split.

    With a mean of ~22 essential skills per occupation, only 10 of them can fit
    in the top 10, so recall@10 is capped well below 1. Without this the
    absolute numbers read as far worse than they are.
    """
    sizes = [sum(1 for g in gold[u].values() if g == 2) for u in uris]
    return {k: float(sum(min(n, k) / n for n in sizes) / len(sizes))
            for k in DEFAULT_KS}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="test", choices=["test", "dev"])
    ap.add_argument("--top-k", type=int, default=max(DEFAULT_KS))
    args = ap.parse_args()

    splits, texts, labels, skills, gold = load(args.split)
    print(f"{args.split} split: {len(splits):,} queries | "
          f"index: {len(skills):,} skills\n")

    rows: list[dict] = []
    summaries: list[dict] = []

    for lang in LANGUAGES:
        skill_uris, preferred, alt, description = language_data(
            texts, labels, skills, lang
        )

        # Queries are occupation descriptions, in the same language as the index.
        occ_text = texts[(texts["language"] == lang) &
                         (texts["conceptKind"] == "occupation")]
        occ_desc = dict(zip(occ_text["conceptUri"], occ_text["description"]))
        queries = [(u, occ_desc[u]) for u in splits["conceptUri"]]

        for stemming in (False, True):
            stemmer = get_stemmer(lang) if stemming else None

            for variant in VARIANTS:
                label = f"{lang} / {variant} / {'stemmed' if stemming else 'raw'}"
                docs = build_documents(skill_uris, preferred, alt, description, variant)

                t0 = time.perf_counter()
                index = BM25Index(skill_uris, docs, stemmer)
                build_s = time.perf_counter() - t0

                t0 = time.perf_counter()
                per_query = []
                for occ_uri, query_text in queries:
                    ranked = index.search(query_text, k=args.top_k)
                    scores = evaluate_query(ranked, gold[occ_uri])
                    per_query.append(scores)
                    rows.append({
                        "language": lang, "variant": variant,
                        "stemming": "stemmed" if stemming else "raw",
                        "occupationUri": occ_uri,
                        **{k: v for k, v in scores.items() if not k.startswith("_")},
                    })
                search_s = time.perf_counter() - t0

                agg = aggregate(per_query)
                lo, hi = bootstrap_ci(per_query, "ndcg@10")
                summaries.append({
                    "language": lang, "variant": variant,
                    "stemming": "stemmed" if stemming else "raw",
                    **{m: agg[m] for m in HEADLINE},
                    "ndcg@10_lo": lo, "ndcg@10_hi": hi,
                    "empty_docs": index.empty,
                    "mean_doc_tokens": round(index.mean_length, 1),
                    "build_s": round(build_s, 1),
                    "ms_per_query": round(1000 * search_s / len(queries), 1),
                })
                print(f"  {label:<34} nDCG@10 {agg['ndcg@10']:.4f} "
                      f"[{lo:.4f}, {hi:.4f}]  R@10 {agg['recall@10']:.4f}  "
                      f"({index.mean_length:.0f} tok/doc, "
                      f"{1000*search_s/len(queries):.0f} ms/q)")

    RESULTS.mkdir(exist_ok=True)
    per_query_df = pd.DataFrame(rows)
    per_query_df.to_csv(RESULTS / "bm25_per_query.csv", index=False)

    ceilings = recall_ceilings(gold, splits["conceptUri"])
    summary = pd.DataFrame(summaries)
    summary.to_csv(RESULTS / "bm25_summary.csv", index=False)
    (RESULTS / "bm25.md").write_text(
        render(summary, args.split, len(splits), len(skills), ceilings),
        encoding="utf-8")

    print(f"\nwrote results/bm25_per_query.csv ({len(per_query_df):,} rows)")
    print(f"wrote results/bm25_summary.csv")
    print(f"wrote results/bm25.md")


def render(s: pd.DataFrame, split: str, n_queries: int, n_skills: int,
           ceilings: dict[int, float]) -> str:
    out: list[str] = []
    w = out.append

    w("# BM25 baseline\n")
    w(f"Split `{split}`, {n_queries:,} occupation-description queries against "
      f"all {n_skills:,} skills.")
    w("Binary metrics score essential relations only; nDCG uses the graded "
      "scale (essential 2, optional 1).")
    w("Intervals are 95% percentile bootstrap over queries.\n")

    w("## Recall ceilings\n")
    w("Occupations carry ~22 essential skills on average, so only a fraction "
      "can fit in the top k. These are the highest recall@k values any system "
      "could reach on this split, and recall figures below should be read "
      "against them.\n")
    w("| k | " + " | ".join(str(k) for k in DEFAULT_KS) + " |")
    w("|---|" + "---:|" * len(DEFAULT_KS))
    w("| max recall@k | " + " | ".join(f"{ceilings[k]:.3f}" for k in DEFAULT_KS) + " |")
    w("")

    w("## Results\n")
    w("| lang | documents | stemming | P@10 | R@10 | % of ceiling | micro-R@10 | MRR | nDCG@10 (95% CI) |")
    w("|---|---|---|---:|---:|---:|---:|---:|---:|")
    for _, r in s.iterrows():
        w(f"| {r['language']} | {r['variant']} | {r['stemming']} | "
          f"{r['precision@10']:.3f} | {r['recall@10']:.3f} | "
          f"{r['recall@10'] / ceilings[10]:.1%} | "
          f"{r['micro_recall@10']:.3f} | {r['mrr']:.3f} | "
          f"{r['ndcg@10']:.3f} [{r['ndcg@10_lo']:.3f}, {r['ndcg@10_hi']:.3f}] |")
    w("")

    w("## Corpus size by condition\n")
    w("Mean tokens per indexed skill. The gap between languages under "
      "`labels` is the alternative-label asymmetry made concrete.\n")
    w("| lang | documents | stemming | mean tokens/doc | empty docs |")
    w("|---|---|---|---:|---:|")
    for _, r in s.iterrows():
        w(f"| {r['language']} | {r['variant']} | {r['stemming']} | "
          f"{r['mean_doc_tokens']} | {r['empty_docs']} |")
    w("")

    w("## Cost\n")
    w("| lang | documents | stemming | index build (s) | ms/query |")
    w("|---|---|---|---:|---:|")
    for _, r in s.iterrows():
        w(f"| {r['language']} | {r['variant']} | {r['stemming']} | "
          f"{r['build_s']} | {r['ms_per_query']} |")
    w("")

    return "\n".join(out)


if __name__ == "__main__":
    main()