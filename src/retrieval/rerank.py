"""Cross-encoder reranking over a first-stage shortlist.

A bi-encoder embeds query and document independently, so a rare technical term
contributes a small share of one fixed vector. A cross-encoder reads the pair
together with full attention, which is what lets it recognise that
*puncionadora* and *prensa biela-manivela* refer to the same machine. That is
the failure mode experiments 07 to 09 identified, so reranking is a targeted
test as well as a standard second stage.

The cost is that nothing can be precomputed: scoring one query against all
13,939 skills means 13,939 forward passes. So a cross-encoder reranks a
shortlist rather than retrieving, and the first stage's recall at that depth is
a hard ceiling on what reranking can reach.

**Depth is free to sweep.** A pair's score does not depend on how many other
pairs were scored, so scoring once at the maximum depth and truncating gives
every shallower depth at no extra cost. `rerank_at_depth` does that, keeping
documents below the reranked block in their first-stage order.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field


@dataclass(frozen=True)
class RerankerSpec:
    """A checkpoint and how it expects to be called."""

    key: str
    hf_name: str
    licence: str
    note: str = ""
    max_length: int = 512
    predict_kwargs: dict = field(default_factory=dict)


RERANKERS: dict[str, RerankerSpec] = {
    # The Apache 2.0 default for self-hosted multilingual reranking.
    # XLM-RoBERTa, 568M, distilled from BGE-M3.
    "bge-m3": RerankerSpec(
        key="bge-m3",
        hf_name="BAAI/bge-reranker-v2-m3",
        licence="Apache-2.0",
        note="standard pointwise cross-encoder; plain CrossEncoder API",
        max_length=512,
    ),
    # Stronger on MMTEB-R but uses a generative yes/no formulation rather than
    # a regression head, so it needs its own scoring path. Left here as a
    # declared option; loading it through CrossEncoder may not give the
    # intended scores.
    "qwen3-0.6b": RerankerSpec(
        key="qwen3-0.6b",
        hf_name="Qwen/Qwen3-Reranker-0.6B",
        licence="Apache-2.0",
        note="generative scoring; verify the scoring path before trusting it",
        max_length=1024,
    ),
}

# Jina rerankers are deliberately absent: jina-reranker-v3.5 is strong and
# small, but its weights are CC-BY-NC-4.0, which rules it out for a public
# institution deployment.


def resolve_device(requested: str | None, allow_cpu: bool = False) -> str:
    """Pick a device, and refuse to fall back to CPU without being told to.

    A cross-encoder scores every pair individually, so CPU is not merely
    slower: at roughly 3 pairs per second it turns a three-minute run into
    several hours with no visible difference until it finishes. Silent
    fallback is therefore a failure, not a degradation, and the usual cause is
    a CPU-only torch wheel installed over a CUDA one by a later dependency.
    """
    import torch

    if requested:
        return requested
    if torch.cuda.is_available():
        return "cuda"
    if allow_cpu:
        return "cpu"
    raise SystemExit(
        f"CUDA is not available (torch {torch.__version__}).\n"
        f"A cross-encoder on CPU runs at roughly 3 pairs per second, so this\n"
        f"would take hours. Check the install:\n"
        f"    python -c \"import torch; print(torch.__version__, "
        f"torch.cuda.is_available())\"\n"
        f"A '+cpu' in the version string means a CPU wheel was installed over\n"
        f"the CUDA one. Reinstall from the CUDA index, or pass --allow-cpu to\n"
        f"run anyway."
    )


class CrossEncoderReranker:
    """Scores (query, document) pairs with a cross-encoder."""

    def __init__(self, spec: RerankerSpec, device: str | None = None,
                 batch_size: int = 64, fp16: bool = True,
                 progress: bool = True):
        self.spec = spec
        self.device = device
        self.batch_size = batch_size
        self.fp16 = fp16
        self.progress = progress
        self._model = None

    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import CrossEncoder

            kwargs = {}
            if self.fp16 and self.device and self.device.startswith("cuda"):
                kwargs["model_kwargs"] = {"torch_dtype": "float16"}
            self._model = CrossEncoder(self.spec.hf_name, device=self.device,
                                       max_length=self.spec.max_length,
                                       **kwargs)
        return self._model

    @property
    def actual_device(self) -> str:
        return str(self.model.model.device)

    def score_pairs(self, pairs: Sequence[tuple[str, str]]) -> list[float]:
        if not pairs:
            return []
        scores = self.model.predict(
            list(pairs), batch_size=self.batch_size,
            show_progress_bar=self.progress,
            **self.spec.predict_kwargs,
        )
        return [float(s) for s in scores]

    def unload(self) -> None:
        self._model = None
        try:
            import gc

            import torch

            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass


def rerank_at_depth(first_stage: Sequence[str],
                    scores: Mapping[str, float],
                    depth: int) -> list[str]:
    """Reorder the top `depth` of a first-stage list by reranker score.

    Documents below `depth` keep their first-stage order and sit beneath the
    reranked block, which is what a deployed system would do and what makes
    metrics at a cutoff deeper than `depth` meaningful.
    """
    head = list(first_stage[:depth])
    tail = list(first_stage[depth:])
    head.sort(key=lambda d: -scores.get(d, float("-inf")))
    return head + tail


def recall_at_depths(first_stage: Sequence[str], gold: set[str],
                     depths: Sequence[int]) -> dict[int, float]:
    """Share of gold reachable at each shortlist depth.

    This is the ceiling: a reranker cannot promote what the first stage never
    retrieved.
    """
    if not gold:
        return {d: 0.0 for d in depths}
    out = {}
    for d in depths:
        found = sum(1 for u in first_stage[:d] if u in gold)
        out[d] = found / len(gold)
    return out