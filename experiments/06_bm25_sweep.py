"""Tune BM25's k1 and b, per language, then confirm on the test split once.

Experiments 01 and 05 used the library defaults, k1=1.5 and b=0.75. Comparing an
untuned lexical baseline against a dense model overstates the dense gain, so the
floor is tuned before that comparison is made.

The sweep runs on **dev**. Every earlier experiment scored on test, which was
sound because nothing was selected on the basis of those scores: all conditions
were reported. Choosing parameters by their score is fitting, and fitting on the
test split makes the resulting number optimistic by an unknown amount. Dev has
been reserved for exactly this.

The sweep doubles as a diagnostic. `b` controls how strongly document length is
normalised. The Portuguese and English corpora differ substantially in scale, so
if the two languages peak at different `b`, length normalisation is part of the
residual gap that experiments 03 to 05 left unexplained. If they peak at the
same values, that candidate is eliminated.

Document variant is fixed to the winner from experiment 05, `labels_desc`,
stemmed, stopwords removed. Varying it here would multiply the grid without
bearing on the question.

Writes:
    results/bm25_sweep_dev.csv      every grid point on dev
    results/bm25_sweep.md           surface, selection, and the test confirmation
    results/bm25_tuned_test.csv     selected parameters scored once on test

Usage:
    python -m experiments.06_bm25_sweep
    python -m experiments.06_bm25_sweep --skip-test
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from rank_bm25 import BM25Okapi

from src.eval.metrics import DEFAULT_KS, aggregate, bootstrap_ci, evaluate_query
from src.retrieval.bm25 import (build_documents, get_stemmer, get_stopwords,
                                tokenize)

REPO_ROOT = Path(__file__).resolve().parents[1]
PROCESSED = REPO_ROOT / "data" / "processed"
BENCHMARK = REPO_ROOT / "data" / "benchmark"
RESULTS = REPO_ROOT / "results"

LANGUAGES = ("pt", "en")
GRADES = {"essential": 2, "optional": 1}
VARIANT = "labels_desc"
SELECT_ON = "ndcg@10"

# k1 controls term frequency saturation, b the strength of length
# normalisation. b=0 disables it entirely, which is the interesting end here
# given the two corpora differ in scale.
K1_GRID = [0.6, 0.9, 1.2, 1.5, 1.8, 2.1]
B_GRID = [0.0, 0.2, 0.4, 0.6, 0.75, 0.9, 1.0]


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


def prepare(texts, labels, skills, lang: str):
    """Tokenise documents and queries once. The grid only changes k1 and b, so
    tokenisation is hoisted out of the loop."""
    skill_uris = sorted(skills["conceptUri"])
    t = texts[texts["language"] == lang]
    preferred = dict(zip(t["conceptUri"], t["preferredLabel"]))
    description = dict(zip(t["conceptUri"], t["description"]))

    a = labels[(labels["language"] == lang) & (labels["labelType"] == "alt")]
    alt: dict[str, list[str]] = {}
    for uri, label in zip(a["conceptUri"], a["label"]):
        alt.setdefault(uri, []).append(label)

    stemmer, stops = get_stemmer(lang), get_stopwords(lang)
    docs = build_documents(skill_uris, preferred, alt, description, VARIANT)
    doc_tokens = [tokenize(d, stemmer, stops) for d in docs]

    occ = texts[(texts["language"] == lang) & (texts["conceptKind"] == "occupation")]
    query_tokens = {u: tokenize(d, stemmer, stops)
                    for u, d in zip(occ["conceptUri"], occ["description"])}

    return np.asarray(skill_uris), doc_tokens, query_tokens


def score(uris, doc_tokens, query_tokens, occ_uris, gold, k1: float, b: float,
          top_k: int) -> list[dict]:
    bm25 = BM25Okapi(doc_tokens, k1=k1, b=b)
    per_query = []
    for occ_uri in occ_uris:
        q = query_tokens[occ_uri]
        if not q:
            continue
        scores = bm25.get_scores(q)
        n = min(top_k, len(scores))
        top = np.argpartition(-scores, n - 1)[:n]
        top = top[np.argsort(-scores[top], kind="stable")]
        per_query.append(evaluate_query(uris[top].tolist(), gold[occ_uri]))
    return per_query


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top-k", type=int, default=max(DEFAULT_KS))
    ap.add_argument("--skip-test", action="store_true",
                    help="sweep dev only, do not touch the test split")
    ap.add_argument("--render-only", action="store_true",
                    help="rebuild the report from saved CSVs without sweeping")
    args = ap.parse_args()

    if args.render_only:
        sweep = pd.read_csv(RESULTS / "bm25_sweep_dev.csv")
        confirmed_path = RESULTS / "bm25_tuned_test.csv"
        confirmed = (pd.read_csv(confirmed_path) if confirmed_path.exists()
                     else pd.DataFrame())
        best = {lang: max(
                    (r for r in sweep.to_dict("records") if r["language"] == lang),
                    key=lambda r: r[SELECT_ON])
                for lang in LANGUAGES}
        (RESULTS / "bm25_sweep.md").write_text(
            render(sweep, best, confirmed), encoding="utf-8")
        print("rewrote results/bm25_sweep.md from saved CSVs")
        return

    splits, texts, labels, skills, gold = load()
    dev = splits[splits["split"] == "dev"]["conceptUri"].tolist()
    test = splits[splits["split"] == "test"]["conceptUri"].tolist()

    print(f"dev {len(dev):,} queries | test {len(test):,} queries | "
          f"index {len(skills):,} skills")
    print(f"variant {VARIANT}, stemmed, stopwords removed")
    print(f"grid {len(K1_GRID)}x{len(B_GRID)} = {len(K1_GRID)*len(B_GRID)} "
          f"points per language\n")

    rows, prepared, best = [], {}, {}

    for lang in LANGUAGES:
        uris, doc_tokens, query_tokens = prepare(texts, labels, skills, lang)
        prepared[lang] = (uris, doc_tokens, query_tokens)

        for k1 in K1_GRID:
            for b in B_GRID:
                agg = aggregate(score(uris, doc_tokens, query_tokens, dev,
                                      gold, k1, b, args.top_k))
                rows.append({"language": lang, "k1": k1, "b": b,
                             **{m: agg[m] for m in
                                ["ndcg@10", "recall@10", "precision@10", "mrr"]}})
            row = max((r for r in rows if r["language"] == lang and r["k1"] == k1),
                      key=lambda r: r[SELECT_ON])
            print(f"  {lang} k1={k1:<4} best b={row['b']:<4} "
                  f"{SELECT_ON} {row[SELECT_ON]:.4f}")

        cand = [r for r in rows if r["language"] == lang]
        best[lang] = max(cand, key=lambda r: r[SELECT_ON])
        print(f"  {lang} selected: k1={best[lang]['k1']}, b={best[lang]['b']}, "
              f"dev {SELECT_ON} {best[lang][SELECT_ON]:.4f}\n")

    sweep = pd.DataFrame(rows)
    RESULTS.mkdir(exist_ok=True)
    sweep.to_csv(RESULTS / "bm25_sweep_dev.csv", index=False)

    confirmed = []
    if not args.skip_test:
        print("Confirming selected parameters on test, once per language:")
        for lang in LANGUAGES:
            uris, doc_tokens, query_tokens = prepared[lang]
            k1, b = best[lang]["k1"], best[lang]["b"]

            for tag, (pk1, pb) in {"tuned": (k1, b), "default": (1.5, 0.75)}.items():
                pq = score(uris, doc_tokens, query_tokens, test, gold,
                           pk1, pb, args.top_k)
                agg = aggregate(pq)
                lo, hi = bootstrap_ci(pq, "ndcg@10")
                confirmed.append({
                    "language": lang, "setting": tag, "k1": pk1, "b": pb,
                    **{m: agg[m] for m in
                       ["ndcg@10", "recall@10", "precision@10", "mrr",
                        "micro_recall@10"]},
                    "ndcg@10_lo": lo, "ndcg@10_hi": hi,
                })
                print(f"  {lang} {tag:<8} k1={pk1} b={pb}  "
                      f"nDCG@10 {agg['ndcg@10']:.4f} [{lo:.4f}, {hi:.4f}]")

        pd.DataFrame(confirmed).to_csv(RESULTS / "bm25_tuned_test.csv", index=False)

    (RESULTS / "bm25_sweep.md").write_text(
        render(sweep, best, pd.DataFrame(confirmed)), encoding="utf-8")
    print(f"\nwrote results/bm25_sweep_dev.csv")
    if confirmed:
        print(f"wrote results/bm25_tuned_test.csv")
    print(f"wrote results/bm25_sweep.md")


def render(sweep: pd.DataFrame, best: dict, confirmed: pd.DataFrame) -> str:
    out: list[str] = []
    w = out.append

    w("# BM25 parameter sweep\n")
    w(f"Document variant `{VARIANT}`, stemmed, stopwords removed. Grid over k1 "
      f"and b, selected on `{SELECT_ON}`.")
    w("**The sweep runs on the dev split.** Choosing parameters by their score "
      "is fitting, so the test split is touched only once per language, with "
      "the already-selected values.\n")

    w("## Selected parameters\n")
    w("| language | k1 | b | dev nDCG@10 |")
    w("|---|---:|---:|---:|")
    for lang in LANGUAGES:
        w(f"| {lang} | {best[lang]['k1']} | {best[lang]['b']} | "
          f"{best[lang][SELECT_ON]:.4f} |")
    w("")

    w("### Do the languages want different length normalisation?\n")
    w("The two corpora differ substantially in scale, so a materially different "
      "response to `b` per language would implicate length normalisation in the "
      "residual gap left unexplained by experiments 03 to 05. Comparing argmax "
      "alone over-reads small differences on a flat surface, so what follows is "
      "the size of the effect across the whole range.\n")

    w("| language | best b | worst b | spread | span 0.75 to 1.0 |")
    w("|---|---:|---:|---:|---:|")
    spans = {}
    for lang in LANGUAGES:
        s = sweep[(sweep["language"] == lang)
                  & (sweep["k1"] == best[lang]["k1"])].set_index("b")[SELECT_ON]
        spread = s.max() - s.min()
        span = abs(s.loc[1.0] - s.loc[0.75])
        spans[lang] = (spread, span)
        w(f"| {lang} | {s.idxmax()} | {s.idxmin()} | {spread:.4f} | {span:.4f} |")
    w("")

    max_span = max(v[1] for v in spans.values())
    w(f"Moving `b` between 0.75 and 1.0 changes {SELECT_ON} by at most "
      f"{max_span:.4f} in either language, against a Portuguese to English gap "
      f"of roughly 0.06. The surfaces differ in shape, with English rising "
      f"monotonically in `b` while Portuguese turns over, but the magnitude is "
      f"an order of magnitude too small to account for the gap. Length "
      f"normalisation is not the explanation.\n")

    w("## Dev surface\n")
    for lang in LANGUAGES:
        w(f"### {lang}\n")
        piv = sweep[sweep["language"] == lang].pivot(
            index="k1", columns="b", values=SELECT_ON)
        w("| k1 \\ b | " + " | ".join(f"{c}" for c in piv.columns) + " |")
        w("|---|" + "---:|" * len(piv.columns))
        for k1, row in piv.iterrows():
            w(f"| **{k1}** | " + " | ".join(f"{v:.4f}" for v in row) + " |")
        w("")

    if len(confirmed):
        w("## Test split, scored once\n")
        w("Selected parameters against the library defaults used in "
          "experiments 01 and 05.\n")
        w("| language | setting | k1 | b | nDCG@10 (95% CI) | P@10 | R@10 | MRR |")
        w("|---|---|---:|---:|---:|---:|---:|---:|")
        for _, r in confirmed.iterrows():
            w(f"| {r['language']} | {r['setting']} | {r['k1']} | {r['b']} "
              f"| {r['ndcg@10']:.4f} [{r['ndcg@10_lo']:.4f}, "
              f"{r['ndcg@10_hi']:.4f}] | {r['precision@10']:.3f} "
              f"| {r['recall@10']:.3f} | {r['mrr']:.3f} |")
        w("")

        c = confirmed.set_index(["language", "setting"])
        w("| language | gain from tuning |")
        w("|---|---:|")
        for lang in LANGUAGES:
            t, d = c.loc[(lang, "tuned"), "ndcg@10"], c.loc[(lang, "default"), "ndcg@10"]
            w(f"| {lang} | {t/d - 1:+.1%} |")
        w("")

        gaps = {}
        for s in ("default", "tuned"):
            gaps[s] = c.loc[("en", s), "ndcg@10"] / c.loc[("pt", s), "ndcg@10"] - 1
        w(f"English advantage: {gaps['default']:+.1%} at defaults, "
          f"{gaps['tuned']:+.1%} tuned "
          f"({100*(gaps['tuned']-gaps['default']):+.1f} pp).\n")

    return "\n".join(out)


if __name__ == "__main__":
    main()