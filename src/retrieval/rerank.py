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


# Instruction given to instruction-aware rerankers on the query side.
TASK = ("Given a course learning outcome or occupation description, judge "
        "whether the skill or knowledge concept is one it teaches or requires")


@dataclass(frozen=True)
class RerankerSpec:
    """A checkpoint and how it expects to be called.

    `kind` selects the scoring path. `cross-encoder` models expose a
    regression head and work through the plain CrossEncoder API.
    `causal-yes-no` models have no such head: they are causal language models
    asked to answer yes or no, and the relevance score is the probability mass
    they put on "yes". The two cannot share an implementation.
    """

    key: str
    hf_name: str
    licence: str
    kind: str = "cross-encoder"
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
    # Scores far higher than bge-reranker on MMTEB-R (66.4 against 58.4) but
    # has no regression head: it is a causal LM answering yes or no, so it
    # needs the CausalYesNoReranker path below.
    "qwen3-0.6b": RerankerSpec(
        key="qwen3-0.6b",
        hf_name="Qwen/Qwen3-Reranker-0.6B",
        licence="Apache-2.0",
        kind="causal-yes-no",
        note="generative scoring; instruction-aware on the query side",
        max_length=1024,
    ),
    "qwen3-4b": RerankerSpec(
        key="qwen3-4b",
        hf_name="Qwen/Qwen3-Reranker-4B",
        licence="Apache-2.0",
        kind="causal-yes-no",
        note="about 8GB at fp16; fits 12GB but leaves little headroom",
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


class CausalYesNoReranker:
    """Scores pairs with a causal LM asked to answer yes or no.

    Qwen3-Reranker has no regression head. It is prompted with the query and
    document and judges relevance by answering "yes" or "no", so the score is
    the probability mass on the "yes" token at the final position, normalised
    against "no". Loading such a model through the CrossEncoder API would
    attach a randomly initialised classification head and produce meaningless
    scores, which is why this path exists separately.

    The prompt format follows the model card. If a future release changes it,
    scores degrade silently rather than erroring, so `sanity_check` compares a
    clearly relevant pair against a clearly irrelevant one before any real
    scoring happens.
    """

    PREFIX = (
        "<|im_start|>system\nJudge whether the Document meets the "
        "requirements based on the Query and the Instruct provided. Note that "
        "the answer can only be \"yes\" or \"no\".<|im_end|>\n"
        "<|im_start|>user\n"
    )
    SUFFIX = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"

    def __init__(self, spec: RerankerSpec, device: str | None = None,
                 batch_size: int = 16, fp16: bool = True,
                 progress: bool = True, task: str = TASK):
        self.spec = spec
        self.device = device or "cuda"
        self.batch_size = batch_size
        self.fp16 = fp16
        self.progress = progress
        self.task = task
        self._tok = None
        self._model = None
        self._yes = None
        self._no = None
        self._logits_kw = None

    def _load(self):
        if self._model is not None:
            return
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self._tok = AutoTokenizer.from_pretrained(self.spec.hf_name,
                                                  padding_side="left")
        self._model = AutoModelForCausalLM.from_pretrained(
            self.spec.hf_name,
            torch_dtype=torch.float16 if self.fp16 else torch.float32,
        ).to(self.device).eval()
        # transformers renamed this between versions; without it the model
        # materialises logits for every position.
        import inspect

        params = inspect.signature(self._model.forward).parameters
        self._logits_kw = next(
            (k for k in ("logits_to_keep", "num_logits_to_keep")
             if k in params), None)
        if self._logits_kw is None:
            print("  ! this transformers version takes neither "
                  "logits_to_keep nor num_logits_to_keep; memory use will be "
                  "much higher, so keep --batch-size small")

        self._yes = self._tok.convert_tokens_to_ids("yes")
        self._no = self._tok.convert_tokens_to_ids("no")
        if self._yes is None or self._no is None:
            raise RuntimeError(
                "Could not resolve the 'yes'/'no' token ids for "
                f"{self.spec.hf_name}. The scoring path assumes them."
            )

    @property
    def actual_device(self) -> str:
        self._load()
        return str(next(self._model.parameters()).device)

    def _format(self, query: str, doc: str) -> str:
        return (f"{self.PREFIX}<Instruct>: {self.task}\n"
                f"<Query>: {query}\n<Document>: {doc}{self.SUFFIX}")

    def score_pairs(self, pairs: Sequence[tuple[str, str]]) -> list[float]:
        if not pairs:
            return []
        import torch

        self._load()
        texts = [self._format(q, d) for q, d in pairs]

        # Group similar lengths together. Padding is to the longest item in a
        # batch, so mixing a 200-token pair with an 800-token one pays the
        # 800-token cost for both. Order is restored before returning.
        order = sorted(range(len(texts)), key=lambda i: len(texts[i]))
        scores = [0.0] * len(texts)

        rng = range(0, len(order), self.batch_size)
        if self.progress:
            try:
                from tqdm.auto import tqdm

                rng = tqdm(rng, desc="Pairs", unit="batch")
            except ImportError:
                pass

        with torch.no_grad():
            for i in rng:
                idx = order[i:i + self.batch_size]
                batch = [texts[j] for j in idx]
                enc = self._tok(batch, return_tensors="pt", padding=True,
                                truncation=True,
                                max_length=self.spec.max_length).to(self.device)
                # Only the final position matters, and asking for every
                # position allocates [batch, seq_len, vocab]: at batch 32,
                # 800 tokens and a 152k vocabulary that is about 8GB of fp16
                # for one row of use. The keyword was renamed across
                # transformers versions, so both spellings are tried.
                kw = {self._logits_kw: 1} if self._logits_kw else {}
                logits = self._model(**enc, **kw).logits[:, -1, :]
                pair = torch.stack([logits[:, self._no],
                                    logits[:, self._yes]], dim=1).float()
                vals = torch.log_softmax(pair, dim=1)[:, 1].exp().tolist()
                for j, v in zip(idx, vals):
                    scores[j] = float(v)
                del enc, logits, pair
        return scores

    def sanity_check(self) -> tuple[float, float]:
        """Score one obviously relevant and one obviously irrelevant pair.

        A silently wrong prompt format or token id produces scores that look
        plausible but carry no signal, and a null result would then be
        indistinguishable from a broken implementation. This fails loudly
        instead.
        """
        q = ("Os operadores de puncionadora instalam e cuidam de puncionadoras "
             "para cortar as pecas na forma desejada.")
        good = "assegurar o correto funcionamento da prensa biela-manivela"
        bad = "tocar violino numa orquestra sinfonica"
        s_good, s_bad = self.score_pairs([(q, good), (q, bad)])
        if not s_good > s_bad:
            raise RuntimeError(
                f"Sanity check failed for {self.spec.hf_name}: a relevant pair "
                f"scored {s_good:.4f} against {s_bad:.4f} for an irrelevant "
                f"one. The prompt format or token ids are probably wrong; "
                f"check them against the model card before trusting any "
                f"result from this checkpoint."
            )
        return s_good, s_bad

    def unload(self) -> None:
        self._tok = self._model = None
        try:
            import gc

            import torch

            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass


def build_reranker(spec: RerankerSpec, **kwargs):
    """Return the scorer matching this checkpoint's scoring kind."""
    if spec.kind == "cross-encoder":
        return CrossEncoderReranker(spec, **kwargs)
    if spec.kind == "causal-yes-no":
        return CausalYesNoReranker(spec, **kwargs)
    raise ValueError(f"Unknown scoring kind '{spec.kind}' for {spec.key}")


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