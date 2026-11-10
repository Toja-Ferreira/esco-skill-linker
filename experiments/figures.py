"""Registry of every figure quoted in the hand-written READMEs.

Each figure has a stable name and one definition:

- a lookup: one cell of a committed file under results/, given as file, row
  filter and column;
- a formula over other named figures, written as an expression in which
  `{name}` stands for that figure's full-precision value;
- a computation over a committed per-query file (percentiles, correlations),
  described in words;
- a constant, with a note on where it comes from. Constants whose value is not
  reproducible from results/ say so in their source.

Derived figures are always computed from full-precision values, never from the
rounded numbers a README displays.

`experiments/render_docs.py` fills the README templates from this registry and
writes `results/figure_sources.md`, which lists every figure with its value and
source.

Usage:
    python -m experiments.figures            print every figure
    python -m experiments.figures NAME ...   print the named figures
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS = REPO_ROOT / "results"

LANGS = ("pt", "en")
METRICS = {"ndcg10": "ndcg@10", "mrr": "mrr", "recall10": "recall@10",
           "p10": "precision@10", "ndcg10_lo": "ndcg@10_lo",
           "ndcg10_hi": "ndcg@10_hi"}


@dataclass
class Figure:
    name: str
    source: str
    compute: Callable[[], float]
    kind: str  # lookup, formula, computed, constant


REGISTRY: dict[str, Figure] = {}

# Notes that explain a choice of source; printed in figure_sources.md.
NOTES: list[str] = []


def _add(name: str, source: str, compute: Callable[[], float], kind: str) -> None:
    if name in REGISTRY:
        raise ValueError(f"figure defined twice: {name}")
    REGISTRY[name] = Figure(name, source, compute, kind)


@lru_cache(None)
def read_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(RESULTS / name)


@lru_cache(None)
def read_md(name: str) -> str:
    return (RESULTS / name).read_text(encoding="utf-8")


def cell(file: str, column: str, **where) -> float:
    d = read_csv(file)
    mask = np.ones(len(d), bool)
    for k, v in where.items():
        mask &= np.isclose(d[k], v) if isinstance(v, float) else (d[k] == v).to_numpy()
    rows = d.loc[mask, column]
    if len(rows) != 1:
        raise LookupError(f"{file} {where} {column}: {len(rows)} rows match")
    return float(rows.iloc[0])


def lookup(name: str, file: str, column: str, **where) -> None:
    flt = ", ".join(f"{k}={v}" for k, v in where.items())
    _add(name, f"`{file}` [{flt}] `{column}`",
         lambda: cell(file, column, **where), "lookup")


def md_lookup(name: str, file: str, pattern: str, what: str) -> None:
    """A figure that only exists in a generated markdown file."""
    def compute() -> float:
        m = re.search(pattern, read_md(file), re.M)
        if not m:
            raise LookupError(f"{file}: no match for {pattern!r}")
        return float(m.group(1).replace(",", ""))
    _add(name, f"`{file}`, {what}", compute, "lookup")


_REF = re.compile(r"\{([^{}]+)\}")


def formula(name: str, expr: str) -> None:
    """`expr` is Python with `{figure.name}` references and min/max/abs/round."""
    def compute() -> float:
        code = _REF.sub(lambda m: f"_v({m.group(1)!r})", expr)
        return float(eval(code, {"_v": value, "min": min, "max": max, "abs": abs, "round": round}))
    _add(name, expr, compute, "formula")


def computed(name: str, source: str, fn: Callable[[], float]) -> None:
    _add(name, source, fn, "computed")


def constant(name: str, v: float, source: str) -> None:
    _add(name, source, lambda: float(v), "constant")


@lru_cache(None)
def value(name: str) -> float:
    if name not in REGISTRY:
        raise KeyError(f"unknown figure: {name}")
    return REGISTRY[name].compute()


# --------------------------------------------------------------- profiles

def profile_count(name: str, file: str, pattern: str, what: str) -> None:
    md_lookup(name, file, pattern, what)


def table_row(file: str, first_cell: str, col: int, after: str | None = None) -> str:
    """Pattern for column `col` (1-based, after the label) of a markdown table
    row whose first cell is `first_cell`, optionally after a heading line."""
    lead = rf"{re.escape(after)}[\s\S]*?" if after else ""
    cells = r"\s*[^|]*\|" * (col - 1)
    return rf"{lead}^\| {re.escape(first_cell)} \|{cells}\s*([\d,.]+)"


DP, SP = "dataset_profile.md", "split_profile.md"
profile_count("data.skills", DP, r"^- Skills: ([\d,]+)", "Skills")
profile_count("data.occupations", DP, r"^- Occupations: ([\d,]+)", "Occupations")
profile_count("data.relations", DP, r"^- Occupation-skill relations: ([\d,]+)", "relations")
for v in ("skill/competence", "knowledge"):
    profile_count(f"data.skilltype.{v}", DP, table_row(DP, v, 1), f"skillType `{v}`")
profile_count("data.skilltype.blank", DP, table_row(DP, "(blank)", 1, "### Skill type"), "skillType blank")
for v in ("sector-specific", "cross-sector", "occupation-specific", "transversal"):
    profile_count(f"data.reuse.{v}", DP, table_row(DP, v, 1), f"reuseLevel `{v}`")
profile_count("data.reuse.blank", DP, table_row(DP, "(blank)", 1, "### Reusability level"), "reuseLevel blank")
for v in ("essential", "optional"):
    profile_count(f"data.relations.{v}", DP, table_row(DP, v, 1), f"relationType `{v}`")
profile_count("data.occ_with_essential", DP, r">=1 essential skill: ([\d,]+) of", "occupations with an essential skill")
profile_count("data.essential_per_occ.mean", DP, r"Essential per occupation: mean ([\d.]+)", "essential per occupation, mean")
profile_count("data.essential_per_occ.median", DP, r"Essential per occupation: .*median (\d+)", "median")
profile_count("data.essential_per_occ.min", DP, r"Essential per occupation: .*min (\d+)", "min")
profile_count("data.essential_per_occ.max", DP, r"Essential per occupation: .*max (\d+)", "max")
profile_count("data.gold_skills", DP, r"Distinct skills used as gold: ([\d,]+)", "distinct gold skills")
profile_count("data.never_gold", DP, r"Skills never gold.*: ([\d,]+)", "skills never gold")
for lang in LANGS:
    for i, kind in enumerate(("preferred", "alt", "hidden", "descriptions"), start=1):
        profile_count(f"data.skill_labels.{lang}.{kind}", DP,
                      table_row(DP, lang, i, "## Text availability, skills"),
                      f"text availability, skills, {lang} {kind}")
        profile_count(f"data.occ_labels.{lang}.{kind}", DP,
                      table_row(DP, lang, i, "## Text availability, occupations"),
                      f"text availability, occupations, {lang} {kind}")
    for i, k in enumerate(("files", "skill_rows", "skill_uris", "occ_rows", "occ_uris"), start=1):
        profile_count(f"data.raw.{lang}.{k}", DP, table_row(DP, lang, i, "## Raw release"),
                      f"raw release, {lang} {k}")
    for i, stem in enumerate(("skills", "occupations"), start=1):
        profile_count(f"data.alt_covered.{lang}.{stem}", DP,
                      table_row(DP, lang, i, "### Concepts with at least one alternative label"),
                      f"{stem} with an alt label, {lang}")
    for stem in ("skills", "occupations"):
        for i, field in enumerate(("definition", "scopeNote"), start=1):
            profile_count(f"data.nonempty.{lang}.{stem}.{field}", DP,
                          rf"^\| {lang} \| {stem} \|" + r"\s*[^|]*\|" * (i - 1) + r"\s*([\d,]+)",
                          f"non-empty `{field}`, {lang} {stem}")
formula("data.raw.skill_dupes", "{data.raw.pt.skill_rows} - {data.raw.pt.skill_uris}")
formula("data.raw.occ_dupes", "{data.raw.pt.occ_rows} - {data.raw.pt.occ_uris}")
formula("data.alt_ratio.skills", "{data.skill_labels.en.alt} / {data.skill_labels.pt.alt}")
formula("data.alt_ratio.occupations", "{data.occ_labels.en.alt} / {data.occ_labels.pt.alt}")
for lang in LANGS:
    formula(f"data.alt_share.{lang}.skills", f"{{data.alt_covered.{lang}.skills}} / {{data.skills}}")
    formula(f"data.desc_share.{lang}.skills", f"{{data.skill_labels.{lang}.descriptions}} / {{data.skills}}")
formula("data.occ_with_essential.share", "{data.occ_with_essential} / {data.occupations}")
formula("data.gold_skills.share", "{data.gold_skills} / {data.skills}")
for split in ("dev", "test"):
    profile_count(f"split.{split}.queries", SP, table_row(SP, split, 1), f"{split} queries")
    profile_count(f"split.{split}.essential_mean", SP, table_row(SP, split, 4), f"{split} essential per query")
    profile_count(f"split.{split}.essential", SP, table_row(SP, split, 2), f"{split} essential relations")
profile_count("split.seed", SP, r"^Seed (\d+)", "seed")

# ------------------------------------------------------- 01, 05: BM25 grids

VARIANTS = ("preferred", "labels", "labels_desc", "description")
for lang in LANGS:
    for var in VARIANTS:
        for stem in ("raw", "stemmed"):
            for stops in ("kept", "removed"):
                key = f"bm25x.{lang}.{var}.{stem}.{stops}"
                where = dict(language=lang, variant=var, stemming=stem, stopwords=stops)
                for m in ("ndcg10", "mrr"):
                    lookup(f"{key}.{m}", "bm25_stopwords_summary.csv", METRICS[m], **where)
                lookup(f"{key}.tokens", "bm25_stopwords_summary.csv", "mean_doc_tokens", **where)

# The reported BM25 baseline: labels_desc, stemmed, stopwords removed, defaults.
NOTES.append(
    "**BM25 baseline source.** Every BM25 figure reads `bm25_stopwords_summary.csv` "
    "(experiment 05), which agrees with `bm25_tuned_test.csv [setting=default]`, "
    "`dense_vs_lexical.csv` and `residual_gap.csv`. `fusion_test.csv [combination=bm25 pt]` "
    "gives 0.265888 rather than 0.265817 for the same configuration. The cause is tie order: "
    "`BM25Index.search` and experiment 13's `top_n` both take `np.argpartition` and then a "
    "stable sort of the partition, and `argpartition` does not keep corpus order, so skills "
    "with equal scores come out in an order that depends on the cut-off. Experiment 05 cuts "
    "at 50 and experiment 13 at 200, which reorders the top 10 for 8 of the 608 Portuguese "
    "test queries (6 of them have a tie between ranks 10 and 11). Recomputing both from the "
    "same scores reproduces 0.265817 at depth 50 and 0.265888 at depth 200; breaking ties "
    "by corpus order would give 0.265918. English is unaffected at the fourth decimal.")
for lang in LANGS:
    for m in ("ndcg10", "mrr", "recall10", "p10"):
        lookup(f"bm25.test.{lang}.{m}", "bm25_stopwords_summary.csv", METRICS[m],
               language=lang, variant="labels_desc", stemming="stemmed", stopwords="removed")

# Experiment 01's own cost table.
computed("bm25.ms_per_query.min", "min of `bm25_summary.csv` `ms_per_query`",
         lambda: read_csv("bm25_summary.csv")["ms_per_query"].min())
computed("bm25.ms_per_query.max", "max of `bm25_summary.csv` `ms_per_query`",
         lambda: read_csv("bm25_summary.csv")["ms_per_query"].max())
computed("bm25.build_s.max", "max of `bm25_summary.csv` `build_s`",
         lambda: read_csv("bm25_summary.csv")["build_s"].max())
computed("bm25.conditions", "rows of `bm25_summary.csv`", lambda: len(read_csv("bm25_summary.csv")))

for lang in LANGS:
    for var in VARIANTS:
        formula(f"bm25x.{lang}.{var}.stem_gain",
                f"{{bm25x.{lang}.{var}.stemmed.kept.ndcg10}} / {{bm25x.{lang}.{var}.raw.kept.ndcg10}} - 1")
        for stem in ("raw", "stemmed"):
            formula(f"bm25x.{lang}.{var}.{stem}.stop_gain",
                    f"{{bm25x.{lang}.{var}.{stem}.removed.ndcg10}} / {{bm25x.{lang}.{var}.{stem}.kept.ndcg10}} - 1")
            if stem == "stemmed":
                formula(f"bm25x.{lang}.{var}.stop_token_share",
                        f"1 - {{bm25x.{lang}.{var}.stemmed.removed.tokens}} / {{bm25x.{lang}.{var}.stemmed.kept.tokens}}")
    formula(f"bm25x.{lang}.alt_gain",
            f"{{bm25x.{lang}.labels.raw.kept.ndcg10}} / {{bm25x.{lang}.preferred.raw.kept.ndcg10}} - 1")
for var in VARIANTS:
    for stem in ("raw", "stemmed"):
        for stops in ("kept", "removed"):
            formula(f"bm25x.gap.{var}.{stem}.{stops}",
                    f"{{bm25x.en.{var}.{stem}.{stops}.ndcg10}} / {{bm25x.pt.{var}.{stem}.{stops}.ndcg10}} - 1")
        formula(f"bm25x.gap_change_pp.{var}.{stem}",
                f"100 * ({{bm25x.gap.{var}.{stem}.removed}} - {{bm25x.gap.{var}.{stem}.kept}})")
formula("bm25x.en.labels_token_growth",
        "{bm25x.en.labels.raw.kept.tokens} / {bm25x.en.preferred.raw.kept.tokens}")
formula("bm25x.pt.labels_token_growth_abs",
        "{bm25x.pt.labels.raw.kept.tokens} - {bm25x.pt.preferred.raw.kept.tokens}")
formula("bm25x.pt.preferred.longer",
        "{bm25x.pt.preferred.raw.kept.tokens} / {bm25x.en.preferred.raw.kept.tokens} - 1")
formula("bm25x.pt.description.longer",
        "{bm25x.pt.description.raw.kept.tokens} / {bm25x.en.description.raw.kept.tokens} - 1")
formula("bm25x.pt.preferred.lower",
        "1 - {bm25x.pt.preferred.raw.kept.ndcg10} / {bm25x.en.preferred.raw.kept.ndcg10}")
formula("bm25x.pt.description.lower",
        "1 - {bm25x.pt.description.stemmed.kept.ndcg10} / {bm25x.en.description.stemmed.kept.ndcg10}")
formula("bm25x.stopword_pp_removed", "-{bm25x.gap_change_pp.description.stemmed}")
formula("bm25x.gap_pp.description.stemmed.kept", "100 * {bm25x.gap.description.stemmed.kept}")
formula("bm25x.stopword_share_of_gap",
        "-{bm25x.gap_change_pp.description.stemmed} / (100 * {bm25x.gap.description.stemmed.kept})")

# ----------------------------------------------- recall ceiling, all systems

@lru_cache(None)
def gold_counts() -> pd.Series:
    """Essential skills per test query, recovered from committed per-query
    files: a query with h hits in its top k and recall r has h / r = k * P@k / r
    essential skills. Every query has a hit in some run."""
    n: dict[str, float] = {}
    for f in sorted(RESULTS.glob("*per_query*.csv")):
        q = pd.read_csv(f)
        if "precision@50" not in q:
            continue
        for k in (50, 20, 10, 5, 3, 1):
            r = q[q[f"recall@{k}"] > 0]
            est = (r[f"precision@{k}"] * k / r[f"recall@{k}"]).round(6)
            for uri, v in est.groupby(r["occupationUri"]).min().items():
                n.setdefault(uri, v)
    s = pd.Series(n)
    if len(s) != value("split.test.queries") or s.sum() != value("split.test.essential"):
        raise ValueError("gold counts recovered from per-query files do not match split_profile.md")
    return s


for k in (1, 3, 5, 10, 20, 50):
    computed(f"ceiling.recall{k}",
             f"mean over test queries of min({k}, n) / n, n = essential skills per query, "
             "recovered from the committed `*per_query*.csv` files (h / r = k P@k / recall@k) "
             "and checked against `split_profile.md` (608 queries, 13,682 essential)",
             lambda k=k: float((np.minimum(k, gold_counts()) / gold_counts()).mean()))

# ---------------------------------------------------------- 02: gold size

GS = "gold_size_slice.csv"
for q, bucket in enumerate(("Q1 smallest", "Q2", "Q3", "Q4 largest"), start=1):
    for col, key in (("queries", "queries"), ("gold_min", "gold_min"), ("gold_max", "gold_max"),
                     ("gold_median", "gold_median"), ("recall@10_ceiling", "ceiling")):
        lookup(f"goldsize.q{q}.{key}", GS, col, bucket=bucket, language="pt")
    for lang in LANGS:
        for col in ("ndcg@10", "ndcg@10_lo", "ndcg@10_hi", "recall@10", "precision@10"):
            lookup(f"goldsize.q{q}.{lang}.{col.replace('@', '').replace('precision', 'p')}",
                   GS, col, bucket=bucket, language=lang)
    formula(f"goldsize.q{q}.adv", f"{{goldsize.q{q}.en.ndcg10}} / {{goldsize.q{q}.pt.ndcg10}} - 1")
formula("goldsize.adv.min", "min(" + ", ".join(f"{{goldsize.q{q}.adv}}" for q in range(1, 5)) + ")")
formula("goldsize.adv.max", "max(" + ", ".join(f"{{goldsize.q{q}.adv}}" for q in range(1, 5)) + ")")
formula("goldsize.en.ndcg10.min", "min(" + ", ".join(f"{{goldsize.q{q}.en.ndcg10}}" for q in range(1, 5)) + ")")
formula("goldsize.en.ndcg10.max", "max(" + ", ".join(f"{{goldsize.q{q}.en.ndcg10}}" for q in range(1, 5)) + ")")
formula("goldsize.queries.min", "min(" + ", ".join(f"{{goldsize.q{q}.queries}}" for q in range(1, 5)) + ")")
formula("goldsize.queries.max", "max(" + ", ".join(f"{{goldsize.q{q}.queries}}" for q in range(1, 5)) + ")")

# --------------------------------------------------- 03, 04: overlap

for lang in LANGS:
    for stem in ("raw", "stemmed"):
        for field in ("description", "labels"):
            key = f"overlap.{lang}.{stem}.{field}"
            for col in ("gold_coverage", "gold_coverage_lo", "gold_coverage_hi", "mean_gold_vocab"):
                lookup(f"{key}.{col}", "lexical_overlap.csv", col, language=lang, stemming=stem, field=field)
            for col in ("idf_coverage", "content_coverage", "corpus_vocab"):
                lookup(f"{key}.{col}", "weighted_overlap.csv", col, language=lang, stemming=stem, field=field)
    formula(f"overlap.{lang}.stem_coverage_gain",
            f"{{overlap.{lang}.stemmed.description.gold_coverage}} / {{overlap.{lang}.raw.description.gold_coverage}} - 1")
    formula(f"overlap.{lang}.stem_vocab_shrink",
            f"1 - {{overlap.{lang}.stemmed.description.mean_gold_vocab}} / {{overlap.{lang}.raw.description.mean_gold_vocab}}")
    formula(f"overlap.{lang}.content_loss",
            f"1 - {{overlap.{lang}.raw.description.content_coverage}} / {{overlap.{lang}.raw.description.gold_coverage}}")
formula("overlap.labels_vocab_ratio",
        "{overlap.en.raw.labels.mean_gold_vocab} / {overlap.pt.raw.labels.mean_gold_vocab}")
for stem in ("raw", "stemmed"):
    formula(f"overlap.vocab_larger.{stem}",
            f"{{overlap.pt.{stem}.description.corpus_vocab}} / {{overlap.en.{stem}.description.corpus_vocab}} - 1")
constant("overlap.top_terms_removed", 50, "content-only coverage drops each corpus's 50 most "
         "frequent terms, a parameter of `experiments/04_weighted_overlap.py`")
md_lookup("overlap.freq.pt.utiliz", "weighted_overlap.md", r"`utiliz\((\d+)\)`", "`utiliz` in the pt term list")
md_lookup("overlap.freq.en.use", "weighted_overlap.md", r"`use\((\d+)\)`", "`use` in the en term list")

# ---------------------------------------------------------- 06: sweep

SW = "bm25_sweep_dev.csv"
computed("sweep.grid_points", f"rows of `{SW}` per language", lambda: len(read_csv(SW)) / 2)
for lang in LANGS:
    def best(lang=lang):
        d = read_csv(SW)
        return d[d["language"] == lang].sort_values("ndcg@10").iloc[-1]
    computed(f"sweep.{lang}.k1", f"k1 at the max `ndcg@10` of `{SW}` [{lang}]", lambda b=best: b()["k1"])
    computed(f"sweep.{lang}.b", f"b at the max `ndcg@10` of `{SW}` [{lang}]", lambda b=best: b()["b"])
    computed(f"sweep.{lang}.dev", f"max `ndcg@10` of `{SW}` [{lang}]", lambda b=best: b()["ndcg@10"])
    for setting in ("tuned", "default"):
        lookup(f"sweep.{lang}.test.{setting}", "bm25_tuned_test.csv", "ndcg@10", language=lang, setting=setting)
    formula(f"sweep.{lang}.gain", f"{{sweep.{lang}.test.tuned}} / {{sweep.{lang}.test.default}} - 1")
for lang, k1 in (("pt", 1.8), ("en", 2.1)):
    for b in (0.75, 0.9, 1.0):
        lookup(f"sweep.{lang}.b{b}", SW, "ndcg@10", language=lang, k1=k1, b=b)
formula("sweep.b_span.max", "max(abs({sweep.pt.b0.75} - {sweep.pt.b1.0}), abs({sweep.en.b0.75} - {sweep.en.b1.0}))")

# ------------------------------------------------- 07 to 09: the tail

SD, SDQ = "score_distribution.csv", "score_distribution_per_query.csv"
for lang in LANGS:
    for col in ("separation", "n_outranking", "n_outranking_median", "top_flatness"):
        lookup(f"scores.{lang}.{col}", SD, col, language=lang)
    for p in (50, 75, 90, 95, 99):
        computed(f"scores.{lang}.outranking_p{p}",
                 f"`np.percentile` ({p}th, linear) of `{SDQ}` [language={lang}] `n_outranking`",
                 lambda lang=lang, p=p: np.percentile(read_csv(SDQ).query("language == @lang")["n_outranking"], p))
    computed(f"scores.{lang}.outranking_max", f"max of `{SDQ}` [language={lang}] `n_outranking`",
             lambda lang=lang: read_csv(SDQ).query("language == @lang")["n_outranking"].max())
    formula(f"scores.{lang}.median_rank", f"{{scores.{lang}.n_outranking_median}} + 1")
formula("scores.separation_gain", "{scores.en.separation} / {scores.pt.separation} - 1")
formula("scores.outranking_ratio", "{scores.pt.n_outranking} / {scores.en.n_outranking}")


def _outranking_corr() -> float:
    p = read_csv(SDQ).pivot(index="occupationUri", columns="language", values="n_outranking")
    return p["pt"].corr(p["en"])


computed("scores.outranking_corr", f"Pearson correlation of `{SDQ}` `n_outranking`, pt against en, paired on occupation", _outranking_corr)
PUNCH = "http://data.europa.eu/esco/occupation/fd2dd3e9-498f-490f-8589-8c1eea05aa3f"
for lang in LANGS:
    lookup(f"failure.punch.{lang}.outranking", SDQ, "n_outranking", language=lang, occupationUri=PUNCH)
    formula(f"failure.punch.{lang}.rank", f"{{failure.punch.{lang}.outranking}} + 1")
md_lookup("failure.punch.en.score", "failure_cases.md",
          r"in en: \*tend punch press\* at rank \d+, score (\d+\.\d+)", "punch press operator, en best gold score")
computed("failure.cases", "occupations in `failure_cases.md`",
         lambda: len(re.findall(r"^non-gold outranking best gold", read_md("failure_cases.md"), re.M)))

IB = "idf_band_overlap.csv"
for i, band in enumerate(("df 1", "df 2 to 5", "df 6 to 50", "df 51+"), start=1):
    for lang in LANGS:
        for col in ("coverage", "coverage_lo", "coverage_hi", "mean_gold_terms"):
            lookup(f"idfband.b{i}.{lang}.{col}", IB, col, language=lang, band=band)

# ---------------------------------------------------------- 10: bi-encoders

BI = "bi_encoder_test.csv"
MODELS = ("e5-base", "embeddinggemma", "qwen3-4b")
for m in MODELS:
    for lang in LANGS:
        for k, col in METRICS.items():
            lookup(f"bi.{m}.test.{lang}.{k}", BI, col, model=m, language=lang)
        lookup(f"bi.{m}.test.{lang}.ms_per_query", BI, "ms_per_query", model=m, language=lang)
        formula(f"bi.{m}.test.{lang}.vs_bm25", f"{{bi.{m}.test.{lang}.ndcg10}} / {{bm25.test.{lang}.ndcg10}} - 1")
    lookup(f"bi.{m}.dim", BI, "dim", model=m, language="en")
    lookup(f"bi.{m}.index_mb", BI, "index_mb", model=m, language="en")
for var in ("preferred", "labels_desc"):
    lookup(f"bi.qwen3-4b.dev.pt.{var}.ndcg10", "bi_encoder_dev.csv", "ndcg@10",
           model="qwen3-4b", language="pt", variant=var)
formula("bi.gemma_over_qwen.en", "{bi.embeddinggemma.test.en.ndcg10} / {bi.qwen3-4b.test.en.ndcg10} - 1")
formula("bi.gemma_over_qwen.pt", "{bi.embeddinggemma.test.pt.ndcg10} / {bi.qwen3-4b.test.pt.ndcg10} - 1")
formula("bi.index_ratio", "{bi.embeddinggemma.index_mb} / {bi.qwen3-4b.index_mb}")
constant("model.embeddinggemma.params_m", 308, "EmbeddingGemma-300M model card: 308M parameters")
constant("model.qwen3emb.params_b", 4, "Qwen3-Embedding-4B model card: 4B parameters")
constant("model.bge.params_m", 568, "BAAI/bge-reranker-v2-m3 model card: 568M parameters")

# ---------------------------------------------- systems in the headline table

SYSTEMS = {
    "bm25": "bm25.test.{}.ndcg10",
    "bi": "bi.embeddinggemma.test.{}.ndcg10",
    "e5": "bi.e5-base.test.{}.ndcg10",
    "qwen3emb": "bi.qwen3-4b.test.{}.ndcg10",
    "hybrid": "hybrid.test.{}.ndcg10",
    "qwen": "qwen.test.{}.ndcg10",
    "deepseek": "deepseek.test.{}.ndcg10",
    "oracle10": "oracle10.test.{}.ndcg10",
    "oracle20": "oracle20.test.{}.ndcg10",
    "oracle50": "oracle50.test.{}.ndcg10",
    "oracle100": "oracle100.test.{}.ndcg10",
}
RT = "rerank_test.csv"
for lang in LANGS:
    for k, col in METRICS.items():
        lookup(f"hybrid.test.{lang}.{k}", RT, col, language=lang, stage="first stage")
        for d in (10, 20, 50, 100):
            lookup(f"oracle{d}.test.{lang}.{k}", RT, col, language=lang, stage="oracle", depth=d)
    for key, file in (("qwen", "llm_rerank_test_qwen3-4b-local.csv"),
                      ("deepseek", "llm_rerank_test_deepseek.csv")):
        for k, col in list(METRICS.items()) + [(c, c) for c in (
                "mean_delta", "delta_lo", "delta_hi", "s_per_query", "prompt_tokens",
                "duplicates_per_query")]:
            lookup(f"{key}.test.{lang}.{k}", file, col, language=lang, stage="llm reranked")
for s, pat in SYSTEMS.items():
    en, pt = "{" + pat.format("en") + "}", "{" + pat.format("pt") + "}"
    formula(f"gap.abs.{s}", f"{en} - {pt}")
    formula(f"gap.rel.{s}", f"{en} / {pt} - 1")

formula("dense.gap_removed.abs", "1 - {gap.abs.bi} / {gap.abs.bm25}")
formula("dense.gap_removed.rel", "1 - {gap.rel.bi} / {gap.rel.bm25}")
formula("dense.qwen3emb.gap_removed.rel", "1 - {gap.rel.qwen3emb} / {gap.rel.bm25}")
for lang in LANGS:
    formula(f"dense.gain.{lang}", f"{{bi.embeddinggemma.test.{lang}.ndcg10}} / {{bm25.test.{lang}.ndcg10}} - 1")
    formula(f"hybrid.gain_over_bi.{lang}", f"{{hybrid.test.{lang}.ndcg10}} / {{bi.embeddinggemma.test.{lang}.ndcg10}} - 1")
    formula(f"hybrid.gain_over_bm25.{lang}", f"{{hybrid.test.{lang}.ndcg10}} / {{bm25.test.{lang}.ndcg10}} - 1")
    formula(f"hybrid.test.{lang}.recall_share", f"{{hybrid.test.{lang}.recall10}} / {{ceiling.recall10}}")
formula("bi.embeddinggemma.test.en.recall_share", "{bi.embeddinggemma.test.en.recall10} / {ceiling.recall10}")

# ------------------------------------------------------ 11, 12: per query

DV, DVP, RG = "dense_vs_lexical.csv", "dense_vs_lexical_paired.csv", "residual_gap.csv"
for m in ("bm25",) + MODELS:
    for lang in LANGS:
        for col in ("p10", "p50", "p90", "failure_rate"):
            lookup(f"perquery.{m}.{lang}.{col}", DV, col, method=m, language=lang)
    for col in ("gap_p10", "gap_p25", "gap_p50", "gap_p75", "gap_p90", "gap_relative", "correlation",
                "pt_fails", "en_fails", "both_fail", "pt_only_fails", "en_only_fails"):
        lookup(f"residual.{m}.{col}", RG, col, model=m)
for lang in LANGS:
    formula(f"perquery.failure_drop.{lang}",
            f"1 - {{perquery.embeddinggemma.{lang}.failure_rate}} / {{perquery.bm25.{lang}.failure_rate}}")
for m in MODELS:
    for lang in LANGS:
        for q, quart in enumerate(("Q1 worst", "Q2", "Q3", "Q4 best"), start=1):
            for col in ("bm25_mean", "dense_mean", "delta", "improved"):
                lookup(f"quartile.{m}.{lang}.q{q}.{col}", DVP, col, model=m, language=lang, bm25_quartile=quart)
formula("quartile.embeddinggemma.pt.q4.not_improved", "1 - {quartile.embeddinggemma.pt.q4.improved}")
GAPS = [f"{{residual.embeddinggemma.gap_{p}}}" for p in ("p10", "p25", "p50", "p75", "p90")]
formula("residual.embeddinggemma.gap.min", f"min({', '.join(GAPS)})")
formula("residual.embeddinggemma.gap.max", f"max({', '.join(GAPS)})")
RATIOS = [f"{{residual.bm25.gap_{p}}} / {{residual.embeddinggemma.gap_{p}}}" for p in ("p10", "p25", "p50", "p75", "p90")]
formula("residual.bm25_over_gemma.min", f"min({', '.join(RATIOS)})")
formula("residual.bm25_over_gemma.max", f"max({', '.join(RATIOS)})")
constant("failure.threshold", 0.10, "a query counts as failed below this nDCG@10, "
         "set in `experiments/11_dense_vs_lexical.py` and `12_residual_gap.py`")

# ---------------------------------------------------------- 13: fusion

FP, H2H, FD, FT = "fusion_paired.csv", "fusion_head_to_head.csv", "fusion_dev.csv", "fusion_test.csv"
COMBOS = {"hybrid pt": "hybrid_pt", "hybrid en": "hybrid_en",
          "bilingual embeddinggemma": "bilingual_gemma", "bilingual bm25": "bilingual_bm25",
          "all four": "all_four"}
for combo, key in COMBOS.items():
    for fusion in ("rrf", "wsf"):
        k = f"fusion.{key}.{fusion}"
        for col in ("fused_score", "baseline_score", "mean_delta", "delta_lo", "delta_hi", "share_positive"):
            lookup(f"{k}.{col}", FP, col, combination=combo, fusion=fusion)
        formula(f"{k}.gain", f"{{{k}.fused_score}} / {{{k}.baseline_score}} - 1")
for fusion in ("rrf", "wsf"):
    computed(f"fusion.{fusion}.cleared", f"rows of `{FP}` [fusion={fusion}] with `delta_lo` > 0",
             lambda f=fusion: float((read_csv(FP).query("fusion == @f")["delta_lo"] > 0).sum()))
    computed(f"fusion.{fusion}.combinations", f"rows of `{FP}` [fusion={fusion}]",
             lambda f=fusion: float(len(read_csv(FP).query("fusion == @f"))))
formula("fusion.rrf.failed", "{fusion.rrf.combinations} - {fusion.rrf.cleared}")
H2H_KEYS = {
    ("all four (wsf)", "hybrid en (wsf)"): "all4wsf_vs_hybenwsf",
    ("all four (wsf)", "hybrid en (rrf)"): "all4wsf_vs_hybenrrf",
    ("hybrid en (wsf)", "bilingual embeddinggemma (wsf)"): "hybenwsf_vs_bigemmawsf",
    ("hybrid en (rrf)", "bilingual embeddinggemma (wsf)"): "hybenrrf_vs_bigemmawsf",
}
for (a, b), key in H2H_KEYS.items():
    for col in ("a_score", "b_score", "mean_delta", "delta_lo", "delta_hi", "share_positive"):
        lookup(f"h2h.{key}.{col}", H2H, col, a=a, b=b)
for w in (0.0, 0.2, 0.4, 0.6, 0.8, 1.0):
    for beta in (0.0, 0.2, 0.4, 0.6, 0.8, 1.0):
        lookup(f"fusion.dev.all_four.w{w}.b{beta}", FD, "ndcg@10", combination="all four", weight=w, beta=beta)
lookup("fusion.all_four.weight", FT, "weight", combination="all four", fusion="wsf")
lookup("fusion.all_four.beta", FT, "beta", combination="all four", fusion="wsf")
constant("fusion.run_depth", 200, "`RUN_DEPTH` in `experiments/13_fusion.py`")

# ---------------------------------------------------- 14: cross-encoders

RQ = "rerank_test_qwen3-0.6b.csv"
RERANKERS = {"bge": (RT, "rerank_diagnostics.csv", "rerank_dev.csv"),
             "qwen06": (RQ, "rerank_diagnostics_qwen3-0.6b.csv", "rerank_dev_qwen3-0.6b.csv")}
for key, (test, diag, dev) in RERANKERS.items():
    for lang in LANGS:
        k = f"ce.{key}.{lang}"
        for col in ("ndcg@10", "mrr", "mean_delta", "delta_lo", "delta_hi", "won", "depth", "pairs", "ms_per_query"):
            lookup(f"{k}.{col.replace('@', '')}", test, col, language=lang, stage="reranked")
        for col in ("random_ndcg", "auc"):
            lookup(f"{k}.{col}", diag, col, language=lang)
        formula(f"{k}.gain", f"{{{k}.ndcg10}} / {{hybrid.test.{lang}.ndcg10}} - 1")
        formula(f"{k}.recovered", f"({{{k}.ndcg10}} - {{{k}.random_ndcg}}) / ({{hybrid.test.{lang}.ndcg10}} - {{{k}.random_ndcg}})")
        formula(f"{k}.mrr_change", f"{{{k}.mrr}} - {{hybrid.test.{lang}.mrr}}")
        for d in (0, 10, 20, 50, 100):
            lookup(f"ce.{key}.dev.{lang}.d{d}", dev, "ndcg@10", language=lang, depth=d)
# Captured headroom is measured against the oracle at each run's own depth.
for key in RERANKERS:
    for lang in LANGS:
        k = f"ce.{key}.{lang}"
        def cap(k=k, lang=lang):
            d = int(value(f"{k}.depth"))
            return (value(f"{k}.ndcg10") - value(f"hybrid.test.{lang}.ndcg10")) / (
                value(f"oracle{d}.test.{lang}.ndcg10") - value(f"hybrid.test.{lang}.ndcg10"))
        computed(f"{k}.captured", f"({k}.ndcg10 - hybrid.test.{lang}.ndcg10) / "
                 f"(oracle at depth {k}.depth - hybrid.test.{lang}.ndcg10)", cap)
RECOVERED = ", ".join(f"{{ce.{r}.{l}.recovered}}" for r in RERANKERS for l in LANGS)
formula("ce.recovered.min", f"min({RECOVERED})")
formula("ce.recovered.max", f"max({RECOVERED})")
MS = ", ".join(f"{{ce.{r}.{l}.ms_per_query}}" for r in RERANKERS for l in LANGS)
formula("ce.ms.min", f"min({MS})")
formula("ce.ms.max", f"max({MS})")
formula("ce.qwen_over_bge.en.ms", "{ce.qwen06.en.ms_per_query} / {ce.bge.en.ms_per_query}")
for lang in LANGS:
    formula(f"oracle100.gain.{lang}", f"{{oracle100.test.{lang}.ndcg10}} / {{hybrid.test.{lang}.ndcg10}} - 1")
for d in (10, 20, 50, 100):
    formula(f"oracle{d}.gap_removed", f"1 - {{gap.abs.oracle{d}}} / {{gap.abs.hybrid}}")
for lang in LANGS:
    computed(f"shortlist.{lang}.recall100", f"mean of `rerank_ceiling.csv` [language={lang}] column `100`",
             lambda lang=lang: read_csv("rerank_ceiling.csv").query("language == @lang")["100"].mean())
formula("shortlist.recall100.ratio", "{shortlist.en.recall100} / {shortlist.pt.recall100} - 1")
constant("ce.qwen06.sanity_margin", 370, "Qwen3-Reranker sanity check printed by "
         "`experiments/14_rerank.py` at run time. In the run log only; not reproducible from results/")
constant("ce.qwen06.sanity_p_yes", 0.037, "P(yes) for the known-relevant sanity pair, from the same run log. "
         "Not reproducible from results/")
formula("ce.qwen06.sanity_p_no", "1 - {ce.qwen06.sanity_p_yes}")
constant("ce.dev_sample", 200, "`--dev-sample` default in `experiments/14_rerank.py`; "
         "`rerank_dev.csv` `queries` = 200")

# ---------------------------------------------------- 15, 16: LLM rerankers

for key, k in (("qwen", "qwen3-4b-local"), ("deepseek", "deepseek")):
    for lang in LANGS:
        formula(f"{key}.gain.{lang}", f"{{{key}.test.{lang}.ndcg10}} / {{hybrid.test.{lang}.ndcg10}} - 1")
        formula(f"{key}.captured.{lang}",
                f"({{{key}.test.{lang}.ndcg10}} - {{hybrid.test.{lang}.ndcg10}}) / "
                f"({{oracle20.test.{lang}.ndcg10}} - {{hybrid.test.{lang}.ndcg10}})")
        for d in (0, 10, 20):
            lookup(f"{key}.dev.{lang}.d{d}", f"llm_rerank_dev_{k}.csv", "ndcg@10", language=lang, depth=d)
        formula(f"{key}.dev_gain.{lang}", f"{{{key}.dev.{lang}.d20}} / {{{key}.dev.{lang}.d0}} - 1")
    formula(f"{key}.prompt_ratio", f"{{{key}.test.pt.prompt_tokens}} / {{{key}.test.en.prompt_tokens}} - 1")
    formula(f"{key}.gain.mean", f"({{{key}.gain.pt}} + {{{key}.gain.en}}) / 2")
    formula(f"{key}.s_per_query.min", f"min({{{key}.test.pt.s_per_query}}, {{{key}.test.en.s_per_query}})")
    formula(f"{key}.s_per_query.max", f"max({{{key}.test.pt.s_per_query}}, {{{key}.test.en.s_per_query}})")
for lang in LANGS:
    formula(f"qwen.share_of_deepseek_gain.{lang}",
            f"({{qwen.test.{lang}.ndcg10}} - {{hybrid.test.{lang}.ndcg10}}) / ({{deepseek.test.{lang}.ndcg10}} - {{hybrid.test.{lang}.ndcg10}})")
formula("qwen.test.en.duplicate_queries", "round({qwen.test.en.duplicates_per_query} * {split.test.queries})")
constant("query.words_approx", 100, "approximate length of an occupation description in words. "
         "Query length is not recorded in any file; not reproducible from results/")
constant("doc.tokens_approx", 25, "approximate length of a skill label plus its description, close to "
         "`bm25_summary.csv` `mean_doc_tokens` for `description` (25.2 pt, 22.2 en)")
formula("llm.speed_ratio.min", "{qwen.s_per_query.min} / {deepseek.s_per_query.max}")
formula("oracle100.mean", "({oracle100.test.pt.ndcg10} + {oracle100.test.en.ndcg10}) / 2")
LC = "llm_compare.csv"
for lang in LANGS:
    for col in ("mean", "lo", "hi"):
        lookup(f"llm.ds_minus_qwen.{lang}.{col}", LC, col,
               comparison="DeepSeek (API) minus Qwen3-4B (local)", language=lang)
for key, comp in (("hybrid", "language gap, first stage"), ("qwen", "language gap, Qwen3-4B (local)"),
                  ("deepseek", "language gap, DeepSeek (API)"),
                  ("change.qwen", "gap change, Qwen3-4B (local) minus first stage"),
                  ("change.deepseek", "gap change, DeepSeek (API) minus first stage"),
                  ("change.ds_minus_qwen", "gap change, DeepSeek (API) minus Qwen3-4B (local)")):
    for col in ("mean", "lo", "hi"):
        lookup(f"llm.gap.{key}.{col}", LC, col, comparison=comp, language="en-pt")
for lang in LANGS:
    formula(f"deepseek.over_qwen_gain.{lang}",
            f"({{deepseek.test.{lang}.ndcg10}} - {{hybrid.test.{lang}.ndcg10}}) / ({{qwen.test.{lang}.ndcg10}} - {{hybrid.test.{lang}.ndcg10}})")
computed("deepseek.run_date", "`llm_rerank_test_deepseek.csv` [language=pt, stage=llm reranked] `run_date`",
         lambda: read_csv("llm_rerank_test_deepseek.csv").dropna(subset=["run_date"])["run_date"].iloc[0])
constant("llm.dev_queries", 200, "dev subsample size, `experiments/15_llm_rerank.py`")
formula("llm.prompts", "2 * 2 * {llm.dev_queries} + 2 * {split.test.queries}")
formula("llm.prompts.thousands", "round({llm.prompts}, -3)")
constant("deepseek.cost_usd", 0.37, "provider billing for the whole of experiment 15's DeepSeek arm, "
         "9 November 2026. Not recorded in any file; not reproducible from results/")
formula("deepseek.cost_per_prompt", "{deepseek.cost_usd} / {llm.prompts}")
constant("deepseek.rerun.pt", 0.4120, "nDCG@10 of a second, identical DeepSeek test run. That run was "
         "kept outside the repo; not reproducible from results/")
constant("deepseek.rerun.en", 0.4445, "nDCG@10 of a second, identical DeepSeek test run. That run was "
         "kept outside the repo; not reproducible from results/")
formula("deepseek.rerun.max_drift",
        "max(abs({deepseek.rerun.pt} - {deepseek.test.pt.ndcg10}), abs({deepseek.rerun.en} - {deepseek.test.en.ndcg10}))")
constant("qwen.dev.pt.d10.other_batch", 0.3756, "Qwen dev nDCG@10 at depth 10 from a run at another "
         "batch size, kept outside the repo; not reproducible from results/")
constant("qwen.slow.s_per_query.before", 0.92, "s/query before the slowdown, from the run log; "
         "not reproducible from results/")
constant("qwen.slow.s_per_query.alone", 6, "s/query with batch 8 running alone, from the run log; "
         "not reproducible from results/")
constant("qwen.slow.s_per_query.shared", 12.19, "s/query with batch 8 alongside another job, "
         "from the run log; not reproducible from results/")
constant("qwen.slow.batch", 8, "batch size of the slow run, from the run log")
constant("qwen.batch", 4, "default `--batch-size` in `experiments/15_llm_rerank.py`")
constant("qwen.slow.gpu_mem_used_gb", 11.7, "`nvidia-smi` observation during the slow run; not reproducible from results/")
constant("qwen.slow.gpu_mem_total_gb", 12.2, "`nvidia-smi` observation during the slow run; not reproducible from results/")
constant("qwen.slow.gpu_watts", 43, "`nvidia-smi` observation during the slow run; not reproducible from results/")
constant("qwen.slow.gpu_watts_max", 140, "`nvidia-smi` power limit; not reproducible from results/")
constant("qwen.earlier_run.pt.s_per_query", 0.94, "s/query of an earlier run of the same Portuguese test "
         "split, from the run log; not reproducible from results/")

# ------------------------------------------------- external and setup facts

for name, v, src in (
    ("pilot.p2.qualifications", 367, "phase 2 report"), ("pilot.p2.languages", 9, "phase 2 report"),
    ("pilot.p3.mapped", 443, "phase 3 report"), ("pilot.p3.qualifications", 1038, "phase 3 report"),
    ("pilot.p3.languages", 12, "phase 3 report"),
    ("pilot.p2.top1", 0.30, "phase 2 report"), ("pilot.p3.top1", 0.4465, "phase 3 report"),
    ("pilot.p2.top3", 0.48, "phase 2 report"), ("pilot.p3.top3", 0.6398, "phase 3 report"),
    ("pilot.p2.top5", 0.56, "phase 2 report"), ("pilot.p3.top5", 0.7035, "phase 3 report"),
    ("pilot.p2.top10", 0.66, "phase 2 report"),
    ("pilot.p3.outcomes", 8499, "phase 3 report"), ("pilot.p3.links", 29894, "phase 3 report"),
    ("pilot.p3.exact_share", 0.26, "phase 3 report"),
):
    constant(name, v, f"European Commission pilot, {src} (linked in the README's prior art section)")

# --------------------------------------------------------------------- CLI


def main() -> None:
    names = sys.argv[1:] or sorted(REGISTRY)
    for n in names:
        print(f"{n:<55} {value(n)!r:<24} {REGISTRY[n].source}")


if __name__ == "__main__":
    main()
