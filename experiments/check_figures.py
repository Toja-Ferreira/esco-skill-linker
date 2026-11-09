"""Recompute the derived figures quoted in the write-ups, from source.

`results/README.md` is written by hand and quotes ratios and percentages that
are derived from the generated CSVs. Those CSVs hold full precision while the
markdown tables display three or four decimals, so a figure computed by hand
from a displayed value can differ from the same figure computed from source in
the last digit.

This prints every such figure at full precision so the prose can be checked
against it. It asserts nothing and changes nothing; it is a reference to
reconcile against.

Usage:
    python -m experiments.check_figures
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS = REPO_ROOT / "results"


def pct(new: float, old: float) -> str:
    return f"{new / old - 1:+.2%}"


def section(title: str) -> None:
    print(f"\n{title}\n" + "-" * len(title))


def main() -> None:
    # BM25, experiment 05, every document variant and setting.
    p = RESULTS / "bm25_stopwords_summary.csv"
    if p.exists():
        s = pd.read_csv(p).set_index(
            ["language", "variant", "stemming", "stopwords"])

        section("BM25: effect of alternative labels (raw, stops kept)")
        for lang in ("pt", "en"):
            a = s.loc[(lang, "preferred", "raw", "kept"), "ndcg@10"]
            b = s.loc[(lang, "labels", "raw", "kept"), "ndcg@10"]
            print(f"  {lang}  {a:.6f} -> {b:.6f}   {pct(b, a)}")

        section("BM25: language gap by variant")
        for variant in ("preferred", "labels", "labels_desc", "description"):
            for stem in ("raw", "stemmed"):
                for stops in ("kept", "removed"):
                    try:
                        pt = s.loc[(("pt", variant, stem, stops)), "ndcg@10"]
                        en = s.loc[(("en", variant, stem, stops)), "ndcg@10"]
                    except KeyError:
                        continue
                    print(f"  {variant:<12} {stem:<8} {stops:<8} "
                          f"pt {pt:.6f}  en {en:.6f}  {pct(en, pt)}")

        section("BM25: effect of stemming (stops kept)")
        for variant in ("preferred", "labels", "labels_desc", "description"):
            for lang in ("pt", "en"):
                a = s.loc[(lang, variant, "raw", "kept"), "ndcg@10"]
                b = s.loc[(lang, variant, "stemmed", "kept"), "ndcg@10"]
                print(f"  {variant:<12} {lang}  {pct(b, a)}")

        section("BM25: effect of stopword removal (stemmed)")
        for variant in ("preferred", "labels", "labels_desc", "description"):
            for lang in ("pt", "en"):
                a = s.loc[(lang, variant, "stemmed", "kept"), "ndcg@10"]
                b = s.loc[(lang, variant, "stemmed", "removed"), "ndcg@10"]
                print(f"  {variant:<12} {lang}  {pct(b, a)}")

    # BM25 reference on test, experiment 06.
    p = RESULTS / "bm25_tuned_test.csv"
    bm25 = {}
    if p.exists():
        d = pd.read_csv(p)
        d = d[d["setting"] == "default"].set_index("language")
        bm25 = d["ndcg@10"].to_dict()
        section("BM25 on test, default parameters")
        for lang, v in bm25.items():
            print(f"  {lang}  {v:.6f}")
        if {"pt", "en"} <= set(bm25):
            print(f"  language gap  {pct(bm25['en'], bm25['pt'])}")

    # Bi-encoders, experiment 10.
    p = RESULTS / "bi_encoder_test.csv"
    if p.exists():
        t = pd.read_csv(p).set_index(["model", "language"])

        section("Bi-encoder on test")
        for (model, lang), r in t.iterrows():
            line = f"  {model:<16} {lang}  {r['ndcg@10']:.6f}"
            if lang in bm25:
                line += f"   vs BM25 {pct(r['ndcg@10'], bm25[lang])}"
            print(line)

        section("Bi-encoder language gaps")
        for model in t.index.get_level_values(0).unique():
            try:
                pt = t.loc[(model, "pt"), "ndcg@10"]
                en = t.loc[(model, "en"), "ndcg@10"]
            except KeyError:
                continue
            print(f"  {model:<16} pt {pt:.6f}  en {en:.6f}  {pct(en, pt)}")
        if {"pt", "en"} <= set(bm25):
            base = bm25["en"] / bm25["pt"] - 1
            print()
            for model in t.index.get_level_values(0).unique():
                try:
                    pt = t.loc[(model, "pt"), "ndcg@10"]
                    en = t.loc[(model, "en"), "ndcg@10"]
                except KeyError:
                    continue
                gap = en / pt - 1
                print(f"  {model:<16} closes {(base - gap) / base:.1%} "
                      f"of the BM25 gap")

        section("Model against model")
        models = list(t.index.get_level_values(0).unique())
        for i, a in enumerate(models):
            for b in models[i + 1:]:
                for lang in ("pt", "en"):
                    try:
                        va = t.loc[(a, lang), "ndcg@10"]
                        vb = t.loc[(b, lang), "ndcg@10"]
                    except KeyError:
                        continue
                    print(f"  {a} vs {b}  {lang}  {pct(va, vb)}")

    # Dataset ratios, experiment 04's records.
    p = RESULTS / "weighted_overlap.csv"
    if p.exists():
        w = pd.read_csv(p).set_index(["language", "stemming", "field"])
        section("Corpus vocabulary")
        for field in ("description", "labels"):
            for stem in ("raw", "stemmed"):
                pt = w.loc[("pt", stem, field), "corpus_vocab"]
                en = w.loc[("en", stem, field), "corpus_vocab"]
                print(f"  {field:<12} {stem:<8} pt {pt:,.0f}  en {en:,.0f}  "
                      f"pt/en {pt/en:.3f}")

    # Failure rates, experiment 11.
    p = RESULTS / "dense_vs_lexical.csv"
    if p.exists():
        d = pd.read_csv(p).set_index(["method", "language"])
        section("Failure rate, share below threshold")
        for (method, lang), r in d.iterrows():
            print(f"  {method:<16} {lang}  {r['failure_rate']:.4f}")
        section("Failure rate reduction against BM25")
        for lang in ("pt", "en"):
            try:
                base = d.loc[("bm25", lang), "failure_rate"]
            except KeyError:
                continue
            for method in d.index.get_level_values(0).unique():
                if method == "bm25":
                    continue
                try:
                    v = d.loc[(method, lang), "failure_rate"]
                except KeyError:
                    continue
                print(f"  {method:<16} {lang}  {base:.4f} -> {v:.4f}   "
                      f"{(base - v) / base:.1%} relative")

    # Language gap, absolute and relative, for every system at its own score
    # level. A relative gap shrinks whenever both scores rise, even if the
    # distance between the languages does not move, so any claim that a
    # system narrows the gap has to hold in the absolute column too.
    systems: dict[str, dict[str, float]] = {}
    if bm25:
        systems["bm25"] = bm25
    for key in ("qwen3-4b-local", "deepseek"):
        p = RESULTS / f"llm_rerank_test_{key}.csv"
        if not p.exists():
            continue
        d = pd.read_csv(p)
        fs = d[d["stage"] == "first stage"].set_index("language")["ndcg@10"]
        systems["first stage"] = fs.to_dict()
        rr = d[d["stage"] == "llm reranked"].set_index("language")
        systems[f"llm {key}"] = rr["ndcg@10"].to_dict()
    oracle: dict[int, dict[str, float]] = {}
    p = RESULTS / "rerank_test.csv"
    if p.exists():
        d = pd.read_csv(p)
        for _, r in d[d["stage"] == "oracle"].iterrows():
            oracle.setdefault(int(r["depth"]), {})[r["language"]] = r["ndcg@10"]
        for depth, v in sorted(oracle.items()):
            systems[f"oracle @{depth}"] = v

    if systems:
        section("Language gap, absolute and relative")
        ref = systems.get("first stage")
        for name, v in systems.items():
            if "pt" not in v or "en" not in v:
                continue
            gap = v["en"] - v["pt"]
            line = (f"  {name:<22} pt {v['pt']:.4f}  en {v['en']:.4f}  "
                    f"abs {gap:+.4f}  rel {pct(v['en'], v['pt'])}")
            # BM25 is an earlier stage, so "removed" relative to the hybrid
            # would read as a meaningless negative.
            if ref and name not in ("first stage", "bm25"):
                ref_gap = ref["en"] - ref["pt"]
                line += f"  abs gap removed vs first stage {1 - gap / ref_gap:+.1%}"
            print(line)

    if "first stage" in systems and oracle:
        section("LLM reranking: gain and headroom captured at the same depth")
        fs = systems["first stage"]
        for key in ("qwen3-4b-local", "deepseek"):
            p = RESULTS / f"llm_rerank_test_{key}.csv"
            if not p.exists():
                continue
            d = pd.read_csv(p)
            for _, r in d[d["stage"] == "llm reranked"].iterrows():
                lang, depth = r["language"], int(r["depth"])
                o = oracle.get(depth, {}).get(lang)
                cap = ((r["ndcg@10"] - fs[lang]) / (o - fs[lang])
                       if o is not None else float("nan"))
                print(f"  {key:<16} {lang}  depth {depth}  "
                      f"gain {pct(r['ndcg@10'], fs[lang])}  "
                      f"captured {cap:.1%}")
        a = systems.get("llm deepseek")
        b = systems.get("llm qwen3-4b-local")
        if a and b:
            for lang in ("pt", "en"):
                print(f"  deepseek over qwen  {lang}  {pct(a[lang], b[lang])}")

    print()


if __name__ == "__main__":
    main()