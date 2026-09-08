"""Dense bi-encoder retrieval over the ESCO skill corpus.

A bi-encoder embeds queries and documents independently, so the 13,939 skill
vectors are computed once and reused for every query. Only the query is encoded
at request time, which is what makes per-query latency comparable to BM25
despite a large one-off indexing cost.

**Prompts are per-model, not global.** E5 expects `query:` and `passage:`
prefixes, Qwen3 expects an instruction on the query side only, EmbeddingGemma
expects its own task strings. Omitting them costs several points and fails
silently, so each model carries its own in `MODELS` rather than relying on
model-card metadata being present and correct.

Embeddings are cached to disk keyed by model, language, document variant and
corpus size, so a re-run or a second experiment reuses them.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from pathlib import Path
from collections.abc import Sequence

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
CACHE = REPO_ROOT / "data" / "embeddings"


@dataclass(frozen=True)
class ModelSpec:
    """A checkpoint and the prompt conventions it was trained with."""

    key: str
    hf_name: str
    query_prefix: str = ""
    doc_prefix: str = ""
    note: str = ""
    encode_kwargs: dict = field(default_factory=dict)


# Task instruction used on the query side for instruction-aware models.
_TASK = "Given a course learning outcome, retrieve the skill or knowledge concepts it teaches"

MODELS: dict[str, ModelSpec] = {
    # Reference point. Closest current equivalent to the multilingual
    # Sentence-BERT model the Commission's phase 3 pilot evaluated.
    "e5-base": ModelSpec(
        key="e5-base",
        hf_name="intfloat/multilingual-e5-base",
        query_prefix="query: ",
        doc_prefix="passage: ",
        note="asymmetric prefixes are required; omitting them degrades retrieval",
    ),
    # Small, and the only sub-500M model with a measured Portuguese result
    # rather than an inferred one (13th of 93 on MTEB-BR).
    "embeddinggemma": ModelSpec(
        key="embeddinggemma",
        hf_name="google/embeddinggemma-300m",
        query_prefix="task: search result | query: ",
        doc_prefix="title: none | text: ",
        note="task strings follow the model card's retrieval prompts",
    ),
    # Leads its size group on MTEB Multilingual and MTEB English, 6th on
    # MTEB-BR. Instruction goes on the query side only.
    "qwen3-4b": ModelSpec(
        key="qwen3-4b",
        hf_name="Qwen/Qwen3-Embedding-4B",
        query_prefix=f"Instruct: {_TASK}\nQuery: ",
        doc_prefix="",
        note="instruction-aware; documents take no prefix",
    ),
}


def cache_path(model_key: str, lang: str, variant: str, n: int) -> Path:
    """Cache key includes corpus size so a changed release invalidates it."""
    tag = hashlib.sha256(
        f"{model_key}|{lang}|{variant}|{n}".encode()
    ).hexdigest()[:12]
    return CACHE / f"{model_key}_{lang}_{variant}_{tag}.npy"


class DenseIndex:
    """Embeddings for a fixed set of skill URIs, plus query-time search.

    Owns the model and its prompt conventions, so queries cannot be encoded
    under different conventions from the documents they are matched against.
    """

    def __init__(self, spec: ModelSpec, model=None, device: str | None = None,
                 batch_size: int = 64):
        self.spec = spec
        self.batch_size = batch_size
        self._model = model
        self._device = device
        self.uris: np.ndarray | None = None
        self.embeddings: np.ndarray | None = None
        self.encode_seconds: float = 0.0
        self.from_cache: bool = False

    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.spec.hf_name,
                                              device=self._device)
        return self._model

    def _encode(self, texts: Sequence[str], prefix: str) -> np.ndarray:
        prefixed = [prefix + t for t in texts] if prefix else list(texts)
        vecs = self.model.encode(
            prefixed,
            batch_size=self.batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,   # cosine becomes a dot product
            show_progress_bar=False,
            **self.spec.encode_kwargs,
        )
        return np.asarray(vecs, dtype=np.float32)

    def build(self, uris: Sequence[str], documents: Sequence[str], lang: str,
              variant: str, use_cache: bool = True) -> "DenseIndex":
        if len(uris) != len(documents):
            raise ValueError("uris and documents must be the same length")
        self.uris = np.asarray(uris)

        path = cache_path(self.spec.key, lang, variant, len(uris))
        if use_cache and path.exists():
            self.embeddings = np.load(path)
            self.from_cache = True
            if self.embeddings.shape[0] != len(uris):
                raise ValueError(
                    f"Cached embeddings at {path} have {self.embeddings.shape[0]} "
                    f"rows against {len(uris)} documents. Delete the cache."
                )
            return self

        t0 = time.perf_counter()
        self.embeddings = self._encode(documents, self.spec.doc_prefix)
        self.encode_seconds = time.perf_counter() - t0

        if use_cache:
            CACHE.mkdir(parents=True, exist_ok=True)
            np.save(path, self.embeddings)
        return self

    def encode_queries(self, texts: Sequence[str]) -> np.ndarray:
        return self._encode(texts, self.spec.query_prefix)

    def search_many(self, query_vecs: np.ndarray, k: int) -> list[list[str]]:
        """Rank all skills for each query. Both sides are L2-normalised, so the
        dot product is cosine similarity."""
        if self.embeddings is None or self.uris is None:
            raise RuntimeError("build() must be called before searching")
        scores = query_vecs @ self.embeddings.T
        n = min(k, scores.shape[1])
        out = []
        for row in scores:
            top = np.argpartition(-row, n - 1)[:n]
            top = top[np.argsort(-row[top], kind="stable")]
            out.append(self.uris[top].tolist())
        return out

    def scores_for(self, query_vec: np.ndarray) -> np.ndarray:
        return query_vec @ self.embeddings.T

    @property
    def index_mb(self) -> float:
        return self.embeddings.nbytes / 1e6 if self.embeddings is not None else 0.0

    @property
    def dim(self) -> int:
        return int(self.embeddings.shape[1]) if self.embeddings is not None else 0

    def unload(self) -> None:
        """Free the model. Useful when looping over several checkpoints."""
        self._model = None
        try:
            import gc

            import torch

            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass