"""Retrieval metrics.

Pure functions over (ranked URIs, gold grades). No retrieval, no I/O, so they
can be checked by hand, see `python -m src.eval.metrics --selftest`.

Relevance grading follows ESCO's own distinction:

    essential -> 2
    optional  -> 1
    unrelated -> 0

Binary metrics (precision, recall, MRR, success) score **essential-only**, so a
system is not credited for optional skills. nDCG uses the graded scale, so it
is credited partially. Reporting both side by side shows whether an advantage
is real or comes from surfacing optional skills.

Two recall variants are reported because they answer different questions:

    recall@k        per-query recall, then averaged. Every occupation counts
                    equally regardless of how many gold skills it has.
                    
    micro_recall@k  total gold found / total gold. Occupations with more gold
                    contribute more. This is the form the Commission's pilot
                    reported ("the selected concept appeared in the top k"),
                    so it is the number comparable to their published figures.
"""

from __future__ import annotations

import argparse
import math
from collections.abc import Mapping, Sequence

import numpy as np

DEFAULT_KS = (1, 3, 5, 10, 20, 50)

ESSENTIAL, OPTIONAL = 2, 1


def dcg(grades: Sequence[float]) -> float:
    """Discounted cumulative gain, exponential-gain convention:

        sum_i (2^rel_i - 1) / log2(i + 1),  i starting at 1
    """
    return sum((2.0**g - 1.0) / math.log2(i + 2) for i, g in enumerate(grades))


def evaluate_query(
    ranked: Sequence[str],
    gold: Mapping[str, int],
    ks: Sequence[int] = DEFAULT_KS,
) -> dict[str, float]:
    """Score one ranked list against one gold set.

    `ranked` is skill URIs best-first. `gold` maps URI to grade; URIs absent
    from it are graded 0.
    """
    essential = {u for u, g in gold.items() if g == ESSENTIAL}
    if not essential:
        raise ValueError("query has no essential gold; it should not be in the benchmark")

    grades = [gold.get(u, 0) for u in ranked]
    ideal = sorted(gold.values(), reverse=True)

    out: dict[str, float] = {}

    # Rank of the first essential hit, 1-based. 0 means none found.
    first = next((i + 1 for i, u in enumerate(ranked) if u in essential), 0)
    out["mrr"] = 1.0 / first if first else 0.0
    out["first_rank"] = float(first)

    n_essential = len(essential)
    for k in ks:
        top = ranked[:k]
        hits = sum(1 for u in top if u in essential)

        out[f"precision@{k}"] = hits / k
        out[f"recall@{k}"] = hits / n_essential
        out[f"success@{k}"] = 1.0 if hits else 0.0

        # Numerator and denominator kept separately so micro-recall can be
        # aggregated correctly across queries; a mean of per-query recalls is
        # a different quantity.
        out[f"_hits@{k}"] = float(hits)

        out[f"ndcg@{k}"] = (
            dcg(grades[:k]) / dcg(ideal[:k]) if dcg(ideal[:k]) > 0 else 0.0
        )

    out["_n_essential"] = float(n_essential)
    return out


def aggregate(per_query: Sequence[Mapping[str, float]],
              ks: Sequence[int] = DEFAULT_KS) -> dict[str, float]:
    """Mean over queries, plus micro-averaged recall."""
    if not per_query:
        raise ValueError("nothing to aggregate")

    keys = [k for k in per_query[0] if not k.startswith("_") and k != "first_rank"]
    out = {k: float(np.mean([q[k] for q in per_query])) for k in keys}

    total_gold = sum(q["_n_essential"] for q in per_query)
    for k in ks:
        found = sum(q[f"_hits@{k}"] for q in per_query)
        out[f"micro_recall@{k}"] = found / total_gold if total_gold else 0.0

    out["n_queries"] = float(len(per_query))
    return out


def bootstrap_ci(
    per_query: Sequence[Mapping[str, float]],
    metric: str,
    n_resamples: int = 2000,
    confidence: float = 0.95,
    seed: int = 42,
) -> tuple[float, float]:
    """Percentile bootstrap CI for a per-query metric, resampling queries.

    Two systems whose intervals overlap substantially should not be reported as
    one beating the other.
    """
    values = np.array([q[metric] for q in per_query], dtype=float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(values), size=(n_resamples, len(values)))
    means = values[idx].mean(axis=1)
    lo = (1.0 - confidence) / 2.0
    return float(np.quantile(means, lo)), float(np.quantile(means, 1.0 - lo))


def _selftest() -> None:
    """Worked examples, checkable by hand."""
    print("Self-test\n" + "-" * 60)

    # 10 candidates. Gold: a, b essential; c optional.
    ranked = list("abcdefghij")
    gold = {"a": ESSENTIAL, "b": ESSENTIAL, "c": OPTIONAL}
    r = evaluate_query(ranked, gold, ks=(1, 3, 5))

    print("\nPerfect ranking — gold at positions 1, 2, 3")
    checks = [
        ("precision@1", r["precision@1"], 1.0, "1 essential in top 1, of 1"),
        ("precision@3", r["precision@3"], 2 / 3, "2 essential in top 3, of 3"),
        ("recall@3", r["recall@3"], 1.0, "both essential found, of 2"),
        ("mrr", r["mrr"], 1.0, "first essential at rank 1"),
        ("ndcg@3", r["ndcg@3"], 1.0, "ranking is the ideal ordering"),
    ]
    for name, got, want, why in checks:
        ok = "ok " if abs(got - want) < 1e-9 else "FAIL"
        print(f"  [{ok}] {name:<14} {got:.4f}  expected {want:.4f}   ({why})")

    # Same gold, pushed down the list.
    ranked2 = list("xyzabcdefg")
    r2 = evaluate_query(ranked2, gold, ks=(1, 3, 5))
    print("\nSame gold at positions 4, 5, 6")
    checks2 = [
        ("precision@1", r2["precision@1"], 0.0, "nothing gold in top 1"),
        ("recall@3", r2["recall@3"], 0.0, "no essential in top 3"),
        ("recall@5", r2["recall@5"], 1.0, "both essential by rank 5"),
        ("mrr", r2["mrr"], 0.25, "first essential at rank 4"),
        ("success@3", r2["success@3"], 0.0, "no hit in top 3"),
        ("success@5", r2["success@5"], 1.0, "at least one hit by 5"),
    ]
    for name, got, want, why in checks2:
        ok = "ok " if abs(got - want) < 1e-9 else "FAIL"
        print(f"  [{ok}] {name:<14} {got:.4f}  expected {want:.4f}   ({why})")

    # nDCG must reward the graded ordering: essential above optional.
    good = evaluate_query(["a", "c", "z"], {"a": ESSENTIAL, "c": OPTIONAL}, ks=(2,))
    bad = evaluate_query(["c", "a", "z"], {"a": ESSENTIAL, "c": OPTIONAL}, ks=(2,))
    print("\nGraded ordering")
    print(f"  ndcg@2 essential-then-optional: {good['ndcg@2']:.4f}")
    print(f"  ndcg@2 optional-then-essential: {bad['ndcg@2']:.4f}")
    print(f"  [{'ok ' if good['ndcg@2'] > bad['ndcg@2'] else 'FAIL'}] "
          f"putting the essential skill first scores higher")
    print(f"  [{'ok ' if abs(good['ndcg@2'] - 1.0) < 1e-9 else 'FAIL'}] "
          f"and the correct order is the ideal, so ndcg = 1")

    # Macro vs micro recall diverge when gold set sizes differ.
    q_small = evaluate_query(["a", "z", "y"], {"a": ESSENTIAL}, ks=(3,))
    q_large = evaluate_query(["b", "z", "y"],
                             {f"b{i}": ESSENTIAL for i in range(9)} | {"b": ESSENTIAL},
                             ks=(3,))
    agg = aggregate([q_small, q_large], ks=(3,))
    print("\nMacro vs micro recall — one query with 1 gold, one with 10")
    print(f"  recall@3       {agg['recall@3']:.4f}   mean of 1.0 and 0.1")
    print(f"  micro_recall@3 {agg['micro_recall@3']:.4f}   2 found of 11 total")
    print(f"  [{'ok ' if abs(agg['recall@3'] - 0.55) < 1e-9 else 'FAIL'}] macro = 0.55")
    print(f"  [{'ok ' if abs(agg['micro_recall@3'] - 2/11) < 1e-9 else 'FAIL'}] micro = 2/11")

    print("\n" + "-" * 60)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    if ap.parse_args().selftest:
        _selftest()
    else:
        ap.print_help()