"""Combining ranked lists from different retrieval runs.

Two methods, in increasing order of what they assume.

**Reciprocal rank fusion** uses only positions. A document's fused score is the
sum over runs of 1/(k + rank). It needs no score normalisation, which matters
here because BM25 scores and cosine similarities live on incomparable scales,
and it has no weight to tune, so it can be reported without touching the dev
split.

**Weighted score fusion** uses the scores themselves, normalised per query, and
takes a weighted sum. It can beat rank fusion when the scores are informative
beyond their ordering, but it needs per-query normalisation and a weight, so the
weight is selected on dev.

A "run" here is a mapping from query URI to a list of (document URI, score) in
rank order.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np

Run = Mapping[str, Sequence[tuple[str, float]]]

# Conventional constant from the original RRF paper. Damps the contribution of
# top ranks so that a single run cannot dominate the fusion.
RRF_K = 60


def reciprocal_rank_fusion(runs: Sequence[Run], k: int = RRF_K,
                           weights: Sequence[float] | None = None
                           ) -> dict[str, list[tuple[str, float]]]:
    """Fuse runs by rank position only.

    Documents absent from a run contribute nothing from it, rather than being
    treated as scoring zero, which is the behaviour that makes RRF robust to
    runs of different depths.
    """
    if weights is None:
        weights = [1.0] * len(runs)
    if len(weights) != len(runs):
        raise ValueError("weights must match the number of runs")

    queries: set[str] = set()
    for run in runs:
        queries |= set(run)

    fused: dict[str, list[tuple[str, float]]] = {}
    for q in queries:
        acc: dict[str, float] = {}
        for run, weight in zip(runs, weights):
            for rank, (doc, _score) in enumerate(run.get(q, []), start=1):
                acc[doc] = acc.get(doc, 0.0) + weight / (k + rank)
        fused[q] = sorted(acc.items(), key=lambda kv: -kv[1])
    return fused


def normalise(scores: np.ndarray, method: str = "minmax") -> np.ndarray:
    """Per-query score normalisation.

    Applied within one query's retrieved set, not across the corpus, because
    the absolute range of BM25 scores varies with query length while cosine
    similarity does not.
    """
    if len(scores) == 0:
        return scores
    if method == "minmax":
        lo, hi = scores.min(), scores.max()
        return (scores - lo) / (hi - lo) if hi > lo else np.zeros_like(scores)
    if method == "zscore":
        sd = scores.std()
        return (scores - scores.mean()) / sd if sd > 0 else np.zeros_like(scores)
    raise ValueError(f"Unknown normalisation '{method}'")


def weighted_score_fusion(runs: Sequence[Run], weights: Sequence[float],
                          norm: str = "minmax"
                          ) -> dict[str, list[tuple[str, float]]]:
    """Fuse runs by normalised score.

    A document missing from a run scores 0 for that run after min-max
    normalisation, which is the value the lowest-ranked retrieved document
    takes, so absence is treated as "no better than the worst retrieved".
    """
    if len(weights) != len(runs):
        raise ValueError("weights must match the number of runs")

    queries: set[str] = set()
    for run in runs:
        queries |= set(run)

    fused: dict[str, list[tuple[str, float]]] = {}
    for q in queries:
        acc: dict[str, float] = {}
        for run, weight in zip(runs, weights):
            items = run.get(q, [])
            if not items:
                continue
            docs = [d for d, _ in items]
            vals = normalise(np.array([s for _, s in items], dtype=float), norm)
            for doc, val in zip(docs, vals):
                acc[doc] = acc.get(doc, 0.0) + weight * float(val)
        fused[q] = sorted(acc.items(), key=lambda kv: -kv[1])
    return fused


def to_ranked_uris(fused: Mapping[str, Sequence[tuple[str, float]]],
                   query_order: Sequence[str], k: int) -> list[list[str]]:
    """Ranked URIs per query, in a fixed query order, for scoring."""
    return [[doc for doc, _ in fused.get(q, [])[:k]] for q in query_order]