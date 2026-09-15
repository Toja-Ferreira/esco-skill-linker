"""Bi-encoder retrieval: three multilingual checkpoints, selected on dev.

The first non-lexical method. It answers the project's central question, how
much of the Portuguese vocabulary mismatch penalty dense retrieval removes, and
it is the number comparable to the Commission's pilot, which evaluated a
multilingual sentence encoder in the native language.

**Selection runs on dev.** Choosing a checkpoint by its score is fitting, so the
test split is scored once per language with the already-selected configuration,
alongside the BM25 baseline for reference.

Checkpoints, and why these three:

    e5-base         reference point, the closest current equivalent to the
                    multilingual Sentence-BERT the Commission evaluated
    embeddinggemma  308M, 13th of 93 on MTEB-BR, so the only small model with a
                    measured Portuguese result rather than an inferred one
    qwen3-4b        leads its size group on MTEB Multilingual and English, 6th
                    on MTEB-BR

No leaderboard measures European Portuguese, and none measures retrieval over a
taxonomy of short concepts, so the boards are used to narrow the field and the
dev split decides.

**Predictions, recorded before the run.** Experiments 07 to 09 found the
Portuguese gap is produced by a tail of queries where the occupation description
and its gold skills use different words for the same concept. Embeddings do not
require string identity, so dense retrieval should compress the Portuguese tail
rather than lift the median. A method that improves the mean while leaving the
distribution shape unchanged is doing something else. Per-query results are
written so this can be checked directly.

Writes:
    results/bi_encoder_dev.csv
    results/bi_encoder_per_query.csv
    results/bi_encoder.md

Usage:
    python -m experiments.10_bi_encoder
    python -m experiments.10_bi_encoder --models e5-base
    python -m experiments.10_bi_encoder --render-only
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np
import pandas as pd

from src.eval.metrics import DEFAULT_KS, aggregate, bootstrap_ci, evaluate_query
from src.retrieval.bm25 import VARIANTS, build_documents
from src.retrieval.dense import MODELS, DenseIndex

REPO_ROOT = Path(__file__).resolve().parents[1]
PROCESSED = REPO_ROOT / "data" / "processed"
BENCHMARK = REPO_ROOT / "data" / "benchmark"
RESULTS = REPO_ROOT / "results"

LANGUAGES = ("pt", "en")
GRADES = {"essential": 2, "optional": 1}
SELECT_ON = "ndcg@10"

# Fixed for this experiment. The lexical sweep showed labels and description
# carry most of the signal; `preferred` is kept because a dense model handles
# short text well and may not need the extra context.
DOC_VARIANTS = ("preferred", "labels_desc", "description")

HEADLINE = ["precision@10", "recall@10", "mrr", "ndcg@10", "micro_recall@10"]


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


def score_split(index: DenseIndex, query_vecs, occ_uris, gold, top_k):
    t0 = time.perf_counter()
    ranked = index.search_many(query_vecs, top_k)
    search_s = time.perf_counter() - t0
    per_query = [evaluate_query(r, gold[u]) for r, u in zip(ranked, occ_uris)]
    return per_query, 1000 * search_s / max(len(occ_uris), 1)


def merge(existing_path: Path, new: pd.DataFrame,
          keys: list[str]) -> pd.DataFrame:
    """Combine a run's results with earlier ones.

    Each invocation only knows about the models passed to it, so writing the
    frame directly would discard every model run separately. Rows matching this
    run's model set are replaced; everything else is kept.
    """
    if not existing_path.exists():
        return new
    old = pd.read_csv(existing_path)
    if new.empty:
        return old
    rerun = set(new["model"].unique())
    kept = old[~old["model"].isin(rerun)]
    combined = pd.concat([kept, new], ignore_index=True)
    return combined.sort_values(keys).reset_index(drop=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=list(MODELS))
    ap.add_argument("--variants", nargs="+", default=list(DOC_VARIANTS))
    ap.add_argument("--top-k", type=int, default=max(DEFAULT_KS))
    ap.add_argument("--batch-size", type=int, default=64)
    ap.add_argument("--device", default=None)
    ap.add_argument("--no-cache", action="store_true")
    ap.add_argument("--render-only", action="store_true")
    args = ap.parse_args()

    if args.render_only:
        dev = pd.read_csv(RESULTS / "bi_encoder_dev.csv")
        test = pd.read_csv(RESULTS / "bi_encoder_test.csv")
        (RESULTS / "bi_encoder.md").write_text(render(dev, test), encoding="utf-8")
        print("rewrote results/bi_encoder.md from saved CSVs")
        return

    for m in args.models:
        if m not in MODELS:
            raise SystemExit(f"Unknown model '{m}'. Known: {', '.join(MODELS)}")
    for v in args.variants:
        if v not in VARIANTS:
            raise SystemExit(f"Unknown variant '{v}'. Known: {', '.join(VARIANTS)}")

    splits, texts, labels, skills, gold = load()
    dev_uris = splits[splits["split"] == "dev"]["conceptUri"].tolist()
    test_uris = splits[splits["split"] == "test"]["conceptUri"].tolist()

    print(f"dev {len(dev_uris):,} | test {len(test_uris):,} | "
          f"index {len(skills):,} skills")
    print(f"models: {', '.join(args.models)}")
    print(f"variants: {', '.join(args.variants)}\n")

    dev_rows, test_rows, per_query_rows = [], [], []

    for model_key in args.models:
        spec = MODELS[model_key]
        print(f"=== {model_key} ({spec.hf_name})")
        index = DenseIndex(spec, device=args.device, batch_size=args.batch_size)

        for lang in LANGUAGES:
            skill_uris, preferred, alt, description, occ_desc = language_data(
                texts, labels, skills, lang)

            # Queries do not depend on the document variant, so encode once.
            t0 = time.perf_counter()
            dev_q = index.encode_queries([occ_desc[u] for u in dev_uris])
            test_q = index.encode_queries([occ_desc[u] for u in test_uris])
            q_seconds = time.perf_counter() - t0

            for variant in args.variants:
                docs = build_documents(skill_uris, preferred, alt, description,
                                       variant)
                index.build(skill_uris, docs, lang, variant,
                            use_cache=not args.no_cache)

                pq, ms = score_split(index, dev_q, dev_uris, gold, args.top_k)
                agg = aggregate(pq)
                dev_rows.append({
                    "model": model_key, "language": lang, "variant": variant,
                    **{m: agg[m] for m in HEADLINE},
                    "dim": index.dim, "index_mb": round(index.index_mb, 1),
                    "encode_s": round(index.encode_seconds, 1),
                    "cached": index.from_cache,
                    "query_encode_s": round(q_seconds, 1),
                    "ms_per_query": round(ms, 2),
                })
                print(f"  dev  {lang} / {variant:<12} "
                      f"{SELECT_ON} {agg[SELECT_ON]:.4f}  "
                      f"({index.dim}d, {index.index_mb:.0f} MB, "
                      f"{'cached' if index.from_cache else f'{index.encode_seconds:.0f}s encode'})")

            # Best variant for this model and language, then score test once.
            cand = [r for r in dev_rows
                    if r["model"] == model_key and r["language"] == lang]
            best = max(cand, key=lambda r: r[SELECT_ON])
            docs = build_documents(skill_uris, preferred, alt, description,
                                   best["variant"])
            index.build(skill_uris, docs, lang, best["variant"],
                        use_cache=not args.no_cache)
            pq, ms = score_split(index, test_q, test_uris, gold, args.top_k)
            agg = aggregate(pq)
            lo, hi = bootstrap_ci(pq, "ndcg@10")
            test_rows.append({
                "model": model_key, "language": lang,
                "variant": best["variant"],
                **{m: agg[m] for m in HEADLINE},
                "ndcg@10_lo": lo, "ndcg@10_hi": hi,
                "dim": index.dim, "index_mb": round(index.index_mb, 1),
                "ms_per_query": round(ms, 2),
            })
            for occ_uri, scores in zip(test_uris, pq):
                per_query_rows.append({
                    "model": model_key, "language": lang,
                    "variant": best["variant"], "occupationUri": occ_uri,
                    **{k: v for k, v in scores.items() if not k.startswith("_")},
                })
            print(f"  TEST {lang} / {best['variant']:<12} "
                  f"{SELECT_ON} {agg[SELECT_ON]:.4f} [{lo:.4f}, {hi:.4f}]\n")

        index.unload()

    RESULTS.mkdir(exist_ok=True)
    dev = merge(RESULTS / "bi_encoder_dev.csv", pd.DataFrame(dev_rows),
                ["model", "language", "variant"])
    test = merge(RESULTS / "bi_encoder_test.csv", pd.DataFrame(test_rows),
                 ["model", "language"])
    per_query = merge(RESULTS / "bi_encoder_per_query.csv",
                      pd.DataFrame(per_query_rows),
                      ["model", "language", "occupationUri"])

    dev.to_csv(RESULTS / "bi_encoder_dev.csv", index=False)
    test.to_csv(RESULTS / "bi_encoder_test.csv", index=False)
    per_query.to_csv(RESULTS / "bi_encoder_per_query.csv", index=False)
    (RESULTS / "bi_encoder.md").write_text(render(dev, test), encoding="utf-8")

    print(f"\nresults now cover: {', '.join(sorted(test['model'].unique()))}")
    print("wrote results/bi_encoder_dev.csv")
    print("wrote results/bi_encoder_test.csv")
    print("wrote results/bi_encoder_per_query.csv")
    print("wrote results/bi_encoder.md")


def bm25_reference() -> dict[str, float]:
    """BM25 at its best configuration on test, read from experiment 06's
    recorded results rather than hardcoded, so the comparison cannot drift or
    lose precision."""
    path = RESULTS / "bm25_tuned_test.csv"
    if not path.exists():
        return {}
    df = pd.read_csv(path)
    df = df[df["setting"] == "default"]
    return dict(zip(df["language"], df["ndcg@10"]))


def render(dev: pd.DataFrame, test: pd.DataFrame) -> str:
    out: list[str] = []
    w = out.append
    bm25 = bm25_reference()

    w("# Bi-encoder retrieval\n")
    w("Three multilingual checkpoints. Checkpoint and document variant selected "
      "on the dev split, then scored once per language on test.")
    w("Prompts are per-model: E5 takes `query:` and `passage:` prefixes, Qwen3 "
      "an instruction on the query side only, EmbeddingGemma its own task "
      "strings.")
    w("Intervals are 95% percentile bootstrap over queries.\n")

    w("## Test results\n")
    w("| model | lang | documents | nDCG@10 (95% CI) | P@10 | R@10 | MRR | vs BM25 |")
    w("|---|---|---|---:|---:|---:|---:|---:|")
    for _, r in test.sort_values(["language", "ndcg@10"],
                                 ascending=[True, False]).iterrows():
        base = bm25.get(r["language"])
        delta = f"{r['ndcg@10'] / base - 1:+.1%}" if base else ""
        w(f"| {r['model']} | {r['language']} | {r['variant']} "
          f"| {r['ndcg@10']:.4f} [{r['ndcg@10_lo']:.4f}, {r['ndcg@10_hi']:.4f}] "
          f"| {r['precision@10']:.3f} | {r['recall@10']:.3f} | {r['mrr']:.3f} "
          f"| {delta} |")
    w("")
    if bm25:
        w(f"BM25 reference, best configuration on the same split: "
          f"pt {bm25['pt']:.4f}, en {bm25['en']:.4f}.\n")

    if len(test):
        w("## Language gap\n")
        w("| model | pt | en | en advantage |")
        w("|---|---:|---:|---:|")
        for model in test["model"].unique():
            sub = test[test["model"] == model].set_index("language")
            if {"pt", "en"} <= set(sub.index):
                pt, en = sub.loc["pt", "ndcg@10"], sub.loc["en", "ndcg@10"]
                w(f"| {model} | {pt:.4f} | {en:.4f} | {en/pt - 1:+.1%} |")
        if bm25:
            w(f"| *BM25* | {bm25['pt']:.4f} | {bm25['en']:.4f} "
              f"| {bm25['en']/bm25['pt'] - 1:+.1%} |")
        w("")
        w("A smaller language gap is not automatically better. It can be "
          "reached by degrading the stronger language rather than improving "
          "the weaker one, so this table should be read alongside the "
          "absolute scores above.\n")

    w("## Dev sweep\n")
    w("Used for selection only. Test numbers above come from the best row per "
      "model and language.\n")
    w("| model | lang | documents | nDCG@10 | R@10 | MRR |")
    w("|---|---|---|---:|---:|---:|")
    for _, r in dev.iterrows():
        w(f"| {r['model']} | {r['language']} | {r['variant']} "
          f"| {r['ndcg@10']:.4f} | {r['recall@10']:.3f} | {r['mrr']:.3f} |")
    w("")

    w("## Cost\n")
    w("Index size is the corpus embedding matrix held in memory. Encoding is "
      "one-off; only the query is encoded per request.\n")
    w("| model | dims | index MB | ms/query |")
    w("|---|---:|---:|---:|")
    for model in dev["model"].unique():
        r = dev[dev["model"] == model].iloc[0]
        w(f"| {model} | {r['dim']} | {r['index_mb']} | {r['ms_per_query']} |")
    w("")

    return "\n".join(out)


if __name__ == "__main__":
    main()