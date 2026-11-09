"""Listwise reranking with a language model, local or via an API.

Experiment 14 showed two cross-encoders reproducing the first stage's ordering
without exceeding it. Both score candidates **independently**, which is the same
structural limit a bi-encoder has, with cross-attention added only between query
and one document. Neither can compare candidates against each other.

The oracle's advantage is entirely relative: it knows which of these particular
candidates outranks which. A listwise model sees the whole shortlist in one
context and can make exactly that comparison, so it is the first method in this
project with the capability the oracle's headroom requires.

**Output is indices, never text.** The model is shown numbered candidates and
returns an order. A malformed response is then an out-of-range integer, a
duplicate, or an omission, each detectable exactly. Asking for skill names
instead would require fuzzy matching back onto ESCO and would add an error term
on top of the thing being measured.

Two backends behind one interface, so the only difference between a local model
and a paid API is which class is constructed. That makes "does paying buy
quality, or only speed" a measurable question rather than an assumption.
"""

from __future__ import annotations

import json
import os
import re
import time
from collections.abc import Sequence
from dataclasses import dataclass, field


@dataclass
class RankingResult:
    """A returned order, plus what had to be repaired to use it."""

    order: list[int]
    invalid: int = 0        # indices outside the candidate range
    duplicates: int = 0     # indices returned more than once
    missing: int = 0        # candidates the model never mentioned
    unparsable: bool = False
    raw: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    seconds: float = 0.0


SYSTEM = (
    "You rank candidate skill concepts by how well each matches a course or "
    "occupation description. Answer with a JSON array of candidate numbers, "
    "most relevant first. Include every candidate exactly once. Output only "
    "the array, with no explanation."
)


def build_prompt(query: str, candidates: Sequence[str], top_k: int | None = None
                 ) -> str:
    """One query against its whole shortlist, candidates numbered from 1."""
    listing = "\n".join(f"{i}. {c}" for i, c in enumerate(candidates, start=1))
    ask = (f"Return the {top_k} most relevant, most relevant first."
           if top_k else "Return all candidates in order of relevance, "
                         "most relevant first.")
    return (f"Description:\n{query}\n\n"
            f"Candidates:\n{listing}\n\n{ask}\n"
            f"Answer with a JSON array of numbers, for example [3, 1, 7].")


def parse_ranking(text: str, n_candidates: int,
                  expected: int | None = None) -> RankingResult:
    """Recover an order from a model response, and count what was wrong.

    Models omit candidates, repeat them, invent numbers and wrap arrays in
    prose. All of that is recoverable, but silently repairing it would hide how
    often the method misbehaves, so each repair is counted. A method that
    mangles a tenth of its queries is not usable however good its mean looks.
    """
    res = RankingResult(order=[], raw=text)

    match = re.search(r"\[[^\[\]]*\]", text, re.S)
    if match:
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            parsed = [int(x) for x in re.findall(r"-?\d+", match.group(0))]
    else:
        parsed = [int(x) for x in re.findall(r"-?\d+", text)]
        if not parsed:
            res.unparsable = True
            res.missing = expected or n_candidates
            return res

    seen: set[int] = set()
    for value in parsed:
        try:
            i = int(value)
        except (TypeError, ValueError):
            res.invalid += 1
            continue
        if not 1 <= i <= n_candidates:
            res.invalid += 1
            continue
        if i in seen:
            res.duplicates += 1
            continue
        seen.add(i)
        res.order.append(i - 1)

    # When only the top k were requested, returning k is complete, not a
    # 40-way omission. Counting against the shortlist would make a correct
    # response look badly malformed.
    res.missing = max(0, (expected or n_candidates) - len(res.order))
    return res


def apply_ranking(candidates: Sequence[str], res: RankingResult,
                  ) -> list[int]:
    """Final order: what the model returned, then whatever it dropped.

    Omitted candidates keep their first-stage order and sit beneath the ranked
    block, which is the least destructive repair: it neither invents an opinion
    the model did not express nor discards candidates it ignored.
    """
    ranked = list(res.order)
    seen = set(ranked)
    ranked.extend(i for i in range(len(candidates)) if i not in seen)
    return ranked


@dataclass(frozen=True)
class LLMSpec:
    key: str
    name: str
    backend: str          # "local" or "api"
    note: str = ""
    max_new_tokens: int = 256
    extra: dict = field(default_factory=dict)


LLMS: dict[str, LLMSpec] = {
    # Local. Fits 12GB at fp16 with room for a listwise prompt.
    "qwen3-4b-local": LLMSpec(
        key="qwen3-4b-local",
        name="Qwen/Qwen3-4B-Instruct-2507",
        backend="local",
        note="runs on the GPU; no per-query cost",
    ),
    "qwen3-1.7b-local": LLMSpec(
        key="qwen3-1.7b-local",
        name="Qwen/Qwen3-1.7B",
        backend="local",
        note="smaller fallback if the 4B is slow",
    ),
    # API. DeepSeek is what the 2024 thesis used for its rerank stage, so this
    # is the direct comparison against the original system.
    "deepseek": LLMSpec(
        key="deepseek",
        name="deepseek-chat",
        backend="api",
        note="OpenAI-compatible; needs DEEPSEEK_API_KEY",
        extra={"base_url": "https://api.deepseek.com",
               "api_key_env": "DEEPSEEK_API_KEY"},
    ),
}


class LocalLLMReranker:
    """Listwise reranking with a local causal model, batched."""

    def __init__(self, spec: LLMSpec, device: str = "cuda",
                 batch_size: int = 4, fp16: bool = True):
        self.spec = spec
        self.device = device
        self.batch_size = batch_size
        self.fp16 = fp16
        self._tok = None
        self._model = None

    def _load(self):
        if self._model is not None:
            return
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self._tok = AutoTokenizer.from_pretrained(self.spec.name,
                                                  padding_side="left")
        if self._tok.pad_token is None:
            self._tok.pad_token = self._tok.eos_token
        self._model = AutoModelForCausalLM.from_pretrained(
            self.spec.name,
            dtype=torch.float16 if self.fp16 else torch.float32,
        ).to(self.device).eval()

    def rank(self, queries: Sequence[str],
             candidate_lists: Sequence[Sequence[str]],
             top_k: int | None = None) -> list[RankingResult]:
        import torch

        self._load()
        prompts = [
            self._tok.apply_chat_template(
                [{"role": "system", "content": SYSTEM},
                 {"role": "user", "content": build_prompt(q, c, top_k)}],
                tokenize=False, add_generation_prompt=True)
            for q, c in zip(queries, candidate_lists)
        ]

        out: list[RankingResult] = []
        for i in range(0, len(prompts), self.batch_size):
            batch = prompts[i:i + self.batch_size]
            cands = candidate_lists[i:i + self.batch_size]
            enc = self._tok(batch, return_tensors="pt", padding=True).to(
                self.device)
            t0 = time.perf_counter()
            with torch.no_grad():
                gen = self._model.generate(
                    **enc, max_new_tokens=self.spec.max_new_tokens,
                    do_sample=False,
                    pad_token_id=self._tok.pad_token_id)
            elapsed = time.perf_counter() - t0
            prompt_len = enc["input_ids"].shape[1]
            pad = self._tok.pad_token_id
            for j, c in enumerate(cands):
                new_ids = gen[j][prompt_len:]
                text = self._tok.decode(new_ids, skip_special_tokens=True)
                r = parse_ranking(text, len(c), top_k)
                r.seconds = elapsed / len(batch)
                # Real tokens only. The padded batch width would charge a
                # short prompt for the longest one it was batched with, and
                # the API reports unpadded counts, so the two would not compare.
                r.prompt_tokens = int(enc["attention_mask"][j].sum())
                r.completion_tokens = int((new_ids != pad).sum())
                out.append(r)
        return out

    def unload(self):
        self._tok = self._model = None
        try:
            import gc

            import torch

            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass


class APILLMReranker:
    """Listwise reranking through an OpenAI-compatible chat API."""

    def __init__(self, spec: LLMSpec, max_workers: int = 8,
                 temperature: float = 0.0):
        self.spec = spec
        self.max_workers = max_workers
        self.temperature = temperature
        self._client = None
        self.served_model: str | None = None

    @property
    def client(self):
        if self._client is None:
            from openai import OpenAI

            env = self.spec.extra.get("api_key_env", "OPENAI_API_KEY")
            key = os.environ.get(env)
            if not key:
                raise SystemExit(
                    f"{env} is not set. Export it before running this "
                    f"backend, or use a local model instead."
                )
            self._client = OpenAI(api_key=key,
                                  base_url=self.spec.extra.get("base_url"))
        return self._client

    def _one(self, query: str, candidates: Sequence[str],
             top_k: int | None) -> RankingResult:
        t0 = time.perf_counter()
        try:
            resp = self.client.chat.completions.create(
                model=self.spec.name,
                messages=[{"role": "system", "content": SYSTEM},
                          {"role": "user",
                           "content": build_prompt(query, candidates, top_k)}],
                temperature=self.temperature,
                max_tokens=self.spec.max_new_tokens,
            )
        except Exception as exc:  # noqa: BLE001
            r = RankingResult(order=[], unparsable=True,
                              missing=len(candidates), raw=f"ERROR: {exc}")
            r.seconds = time.perf_counter() - t0
            return r

        text = resp.choices[0].message.content or ""
        r = parse_ranking(text, len(candidates), top_k)
        r.seconds = time.perf_counter() - t0
        if resp.usage:
            r.prompt_tokens = resp.usage.prompt_tokens
            r.completion_tokens = resp.usage.completion_tokens
        return r

    def preflight(self) -> None:
        """One real request before the run, raising the actual error.

        Per-query failures are caught so one timeout cannot sink a run, which
        also means a missing package, a bad key or a wrong model name would
        fail every query quietly and still produce result files. This makes
        those fail loudly, once, before anything is written.
        """
        try:
            import openai  # noqa: F401
        except ImportError as exc:
            raise SystemExit("The openai package is not installed: "
                             "pip install openai") from exc
        resp = self.client.chat.completions.create(
            model=self.spec.name,
            messages=[{"role": "user", "content": "Reply with [1]."}],
            temperature=0.0, max_tokens=8)
        text = resp.choices[0].message.content or ""
        # An alias like deepseek-chat is repointed at newer models over time,
        # so the name the server reports is what identifies the run.
        self.served_model = getattr(resp, "model", None) or self.spec.name
        print(f"preflight ok: {self.spec.name} served by "
              f"{self.served_model}, replied {text.strip()!r}")

    def rank(self, queries: Sequence[str],
             candidate_lists: Sequence[Sequence[str]],
             top_k: int | None = None) -> list[RankingResult]:
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            return list(pool.map(
                lambda a: self._one(a[0], a[1], top_k),
                zip(queries, candidate_lists)))

    def unload(self):
        self._client = None


def build_llm_reranker(spec: LLMSpec, **kwargs):
    if spec.backend == "local":
        return LocalLLMReranker(spec, **kwargs)
    if spec.backend == "api":
        kwargs.pop("device", None)
        kwargs.pop("fp16", None)
        kwargs.pop("batch_size", None)
        return APILLMReranker(spec, **kwargs)
    raise ValueError(f"Unknown backend '{spec.backend}'")