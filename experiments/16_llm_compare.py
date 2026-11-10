"""Local against API reranking, query by query.

Experiment 15 ran each model against the first stage. This compares the two
models directly, on the same 608 test queries, so every difference is paired:
the same occupation scored by both systems.

Two questions:

1. **Does the API model rank better, or only faster?** The per-query difference
   in nDCG@10 between the two rerankers, with a paired bootstrap interval.
2. **Does any stage narrow or widen the language gap?** Every occupation exists in
   both languages, so the gap is itself paired: English minus Portuguese for the
   same occupation. A change in that gap between two systems is a difference of
   differences, and gets its own interval. Comparing two relative gaps read off
   aggregate means would mix a change in the gap with a change in the
   denominator.

Reads the per-query files experiments 05, 10, 14 and 15 wrote and recomputes the
first stage from its runs, so nothing is copied by hand. BM25 and
EmbeddingGemma are the two inputs to the first stage, in the configurations
experiment 13 fuses, so the gap can be followed through every stage of the
pipeline: lexical, dense, hybrid, reranked.

Writes:
    results/llm_compare.csv
    results/llm_compare.md

Usage:
    python -m experiments.16_llm_compare
"""

from __future__ import annotations

import importlib
from pathlib import Path

import numpy as np
import pandas as pd

exp13 = importlib.import_module("experiments.13_fusion")
exp15 = importlib.import_module("experiments.15_llm_rerank")

REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS = REPO_ROOT / "results"
METRIC = "ndcg@10"
DENSE_LABEL = "EmbeddingGemma"
# Perfect ordering of the first stage's shortlist at these depths (experiment 14).
ORACLE_DEPTHS = (10, 20, 50, 100)
MODELS = {"qwen3-4b-local": "Qwen3-4B (local)", "deepseek": "DeepSeek (API)"}
N_BOOT = 2000
SEED = 42


def paired(diffs: np.ndarray) -> dict:
    """Mean of per-query differences with a percentile bootstrap interval."""
    rng = np.random.default_rng(SEED)
    idx = rng.integers(0, len(diffs), size=(N_BOOT, len(diffs)))
    means = diffs[idx].mean(axis=1)
    return {"mean": float(diffs.mean()),
            "lo": float(np.quantile(means, 0.025)),
            "hi": float(np.quantile(means, 0.975)),
            "won": float((diffs > 0).mean()),
            "lost": float((diffs < 0).mean()),
            "n": int(len(diffs))}


def paired_share(removed: np.ndarray, base: np.ndarray) -> dict:
    """Share of the mean of `base` that `removed` accounts for, a ratio of
    means, with both resampled on the same queries."""
    rng = np.random.default_rng(SEED)
    idx = rng.integers(0, len(base), size=(N_BOOT, len(base)))
    shares = removed[idx].mean(axis=1) / base[idx].mean(axis=1)
    return {"mean": float(removed.mean() / base.mean()),
            "lo": float(np.quantile(shares, 0.025)),
            "hi": float(np.quantile(shares, 0.975)),
            "won": float((removed > 0).mean()),
            "lost": float((removed < 0).mean()),
            "n": int(len(base))}


def first_stage_scores(lang: str, test_uris: list[str], gold) -> dict:
    fused = exp15.first_stage(lang, "test")
    k = max(exp15.DEFAULT_KS)
    return {q: exp15.evaluate_query([d for d, _ in fused[q]][:k],
                                    gold[q])[METRIC]
            for q in test_uris if fused.get(q)}


def per_query(file: str, **where) -> dict[str, dict[str, float]]:
    """Per-query scores by language from a committed per-query file, for
    the rows matching `where`."""
    df = pd.read_csv(RESULTS / file)
    for col, v in where.items():
        df = df[df[col] == v]
    out = {lang: dict(zip(sub["occupationUri"], sub[METRIC]))
           for lang, sub in df.groupby("language")}
    if any(len(v) != len(set(v)) for v in out.values()) or not out:
        raise SystemExit(f"{file} {where}: expected one row per query")
    return out


def model_scores(model: str) -> dict[str, dict[str, float]]:
    path = RESULTS / f"llm_rerank_per_query_{model}.csv"
    if not path.exists():
        raise SystemExit(f"{path.name} is missing. Run experiment 15 with "
                         f"--model {model} first.")
    df = pd.read_csv(path)
    return {lang: dict(zip(sub["occupationUri"], sub[METRIC]))
            for lang, sub in df.groupby("language")}


def main() -> None:
    splits, _, gold = exp15.load()
    test_uris = splits[splits["split"] == "test"]["conceptUri"].tolist()

    # The first stage's inputs, as experiment 13 configures them: BM25 stemmed
    # with stopwords removed (experiment 05), and the default dense model.
    dense = exp13.DENSE_DEFAULT
    systems: dict[str, dict[str, dict[str, float]]] = {
        "BM25": per_query("bm25_stopwords_per_query.csv", variant=exp13.BM25_VARIANT,
                          stemming="stemmed", stopwords="removed"),
        DENSE_LABEL: per_query("bi_encoder_per_query.csv", model=dense,
                               variant=exp13.DENSE_VARIANT[dense]),
        "first stage": {lang: first_stage_scores(lang, test_uris, gold)
                        for lang in exp15.LANGUAGES}}
    for key, label in MODELS.items():
        systems[label] = model_scores(key)
    for d in ORACLE_DEPTHS:
        systems[f"oracle@{d}"] = per_query("rerank_oracle_per_query.csv", depth=d)

    rows = []

    # 1. Model against model, per language.
    a, b = MODELS["deepseek"], MODELS["qwen3-4b-local"]
    for lang in exp15.LANGUAGES:
        shared = sorted(set(systems[a][lang]) & set(systems[b][lang]))
        d = np.array([systems[a][lang][q] - systems[b][lang][q]
                      for q in shared])
        rows.append({"comparison": f"{a} minus {b}", "language": lang,
                     **paired(d)})

    # 2. Language gap within each system: English minus Portuguese, per
    #    occupation.
    gaps: dict[str, dict[str, float]] = {}
    for name, by_lang in systems.items():
        shared = sorted(set(by_lang["pt"]) & set(by_lang["en"]))
        gaps[name] = {q: by_lang["en"][q] - by_lang["pt"][q] for q in shared}
        g = np.array(list(gaps[name].values()))
        pt_mean = float(np.mean([by_lang["pt"][q] for q in shared]))
        rows.append({"comparison": f"language gap, {name}", "language": "en-pt",
                     **paired(g), "relative": float(g.mean()) / pt_mean})

    # 3. Change in the gap between systems: a difference of differences.
    pairs = [("BM25", DENSE_LABEL), (DENSE_LABEL, "first stage"), ("BM25", "first stage"),
             ("first stage", b), ("first stage", a), (b, a)]
    for lo_sys, hi_sys in pairs:
        shared = sorted(set(gaps[lo_sys]) & set(gaps[hi_sys]))
        d = np.array([gaps[hi_sys][q] - gaps[lo_sys][q] for q in shared])
        rows.append({"comparison": f"gap change, {hi_sys} minus {lo_sys}",
                     "language": "en-pt", **paired(d)})

    # 4. Share of the first stage's gap that perfect ordering removes.
    base = gaps["first stage"]
    for d in ORACLE_DEPTHS:
        o = gaps[f"oracle@{d}"]
        shared = sorted(set(base) & set(o))
        b_arr = np.array([base[q] for q in shared])
        rows.append({"comparison": f"gap removed, oracle@{d}", "language": "en-pt",
                     **paired_share(b_arr - np.array([o[q] for q in shared]), b_arr)})

    out = pd.DataFrame(rows)
    RESULTS.mkdir(exist_ok=True)
    out.to_csv(RESULTS / "llm_compare.csv", index=False)

    cost = []
    for key, label in MODELS.items():
        t = pd.read_csv(RESULTS / f"llm_rerank_test_{key}.csv")
        for _, r in t[t["stage"] == "llm reranked"].iterrows():
            cost.append({"system": label, "language": r["language"],
                         "s_per_query": r["s_per_query"],
                         "prompt_tokens": int(r["prompt_tokens"]),
                         "completion_tokens": int(r["completion_tokens"])})
    (RESULTS / "llm_compare.md").write_text(render(out, pd.DataFrame(cost)),
                                            encoding="utf-8")

    for _, r in out.iterrows():
        print(f"{r['comparison']:<52} {r['language']:<6} "
              f"{r['mean']:+.4f} [{r['lo']:+.4f}, {r['hi']:+.4f}]")
    print("\nwrote results/llm_compare.csv")
    print("wrote results/llm_compare.md")


def fmt(r) -> str:
    return f"{r['mean']:+.4f} [{r['lo']:+.4f}, {r['hi']:+.4f}]"


def render(out: pd.DataFrame, cost: pd.DataFrame) -> str:
    lines: list[str] = []
    w = lines.append
    w("# Local against API reranking\n")
    w("Both models rerank the same first stage at depth 20 on the same 608 "
      "test queries, so every comparison here is paired by query. Intervals "
      "are 95% percentile bootstrap over queries. The first stage is hybrid "
      "weighted score fusion of BM25 and EmbeddingGemma (experiment 13); "
      "those two inputs are included so the language gap can be followed "
      "through every stage.\n")

    w("## Model against model\n")
    w("| language | DeepSeek minus Qwen3-4B, nDCG@10 (95% CI) | DeepSeek better | Qwen better |")
    w("|---|---|---:|---:|")
    for _, r in out[out["comparison"].str.contains(" minus Qwen")
                    & ~out["comparison"].str.startswith("gap")].iterrows():
        w(f"| {r['language']} | {fmt(r)} | {r['won']:.0%} | {r['lost']:.0%} |")
    w("")

    w("## Language gap\n")
    w("English minus Portuguese for the same occupation. Relative is the mean "
      "gap over the Portuguese mean.\n")
    w("| system | gap, nDCG@10 (95% CI) | relative |")
    w("|---|---|---:|")
    for _, r in out[out["comparison"].str.startswith("language gap")].iterrows():
        w(f"| {r['comparison'].removeprefix('language gap, ')} | {fmt(r)} "
          f"| {r['relative']:+.1%} |")
    w("")

    w("## Change in the gap\n")
    w("A negative value means the second system has a smaller English lead "
      "than the first. An interval that crosses zero means the change is not "
      "distinguishable from noise at this sample size.\n")
    w("| comparison | change (95% CI) |")
    w("|---|---|")
    for _, r in out[out["comparison"].str.startswith("gap change")].iterrows():
        w(f"| {r['comparison'].removeprefix('gap change, ')} | {fmt(r)} |")
    w("")

    w("## Gap removed by perfect ordering\n")
    w("The oracle sorts the first stage's top d candidates by true relevance "
      "(experiment 14). Share removed is one minus the oracle's mean gap over "
      "the first stage's, with both resampled on the same occupations.\n")
    w("| depth | share of the gap removed (95% CI) |")
    w("|---|---|")
    for _, r in out[out["comparison"].str.startswith("gap removed")].iterrows():
        w(f"| {r['comparison'].removeprefix('gap removed, oracle@')} "
          f"| {r['mean']:.0%} [{r['lo']:.0%}, {r['hi']:.0%}] |")
    w("")

    if len(cost):
        w("## Cost on the test split\n")
        w("Seconds per query are wall time divided by queries: batched on the "
          "local GPU, eight concurrent requests for the API. Token counts "
          "come from different tokenisers, so compare them within a model, "
          "not across.\n")
        w("| system | language | s/query | prompt tokens | completion tokens |")
        w("|---|---|---:|---:|---:|")
        for _, r in cost.iterrows():
            w(f"| {r['system']} | {r['language']} | {r['s_per_query']} "
              f"| {r['prompt_tokens']:,} | {r['completion_tokens']:,} |")
        w("")
    return "\n".join(lines)


if __name__ == "__main__":
    main()