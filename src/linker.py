"""Link a learning outcome to ESCO skills with the benchmark's best pipeline.

This is the configuration the experiments selected, assembled for one query
at a time:

1. BM25 over labels and descriptions, stemmed, stopwords removed (exp. 05, 06)
2. EmbeddingGemma over the same text (exp. 10)
3. Weighted score fusion with the dev-tuned weight, read from experiment 13's
   own results so it cannot drift from what was measured
4. Optionally, listwise LLM reranking of the top 20 (exp. 15)

The indexes load once, so in interactive mode each further query costs only
its own retrieval.

Usage:
    python -m src.linker --lang pt "Desenvolver modelos de aprendizagem automática"
    python -m src.linker --lang en --rerank qwen3-4b-local
    python -m src.linker --lang pt --rerank deepseek
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from src.retrieval.bm25 import (BM25Index, build_documents, get_stemmer,
                                get_stopwords, tokenize)
from src.retrieval.dense import MODELS, DenseIndex
from src.retrieval.fusion import weighted_score_fusion
from src.retrieval.llm_rerank import LLMS, apply_ranking, build_llm_reranker

REPO_ROOT = Path(__file__).resolve().parents[1]
PROCESSED = REPO_ROOT / "data" / "processed"
RESULTS = REPO_ROOT / "results"

# The selected configuration. Changing any of these means the demo no longer
# runs the system the results describe.
VARIANT = "labels_desc"
DENSE = "embeddinggemma"
RUN_DEPTH = 200      # fusion input depth, as in experiment 13
RERANK_DEPTH = 20    # dev-selected in experiment 15 for both models
RERANK_TOP_K = 10
CANDIDATE_WORDS = 40

# ESCO's own names for its two concept types, in the query language.
TYPE_NAME = {"pt": {"skill": "competência", "knowledge": "conhecimento"},
             "en": {"skill": "skill", "knowledge": "knowledge"}}


def fusion_weight(lang: str) -> float:
    """BM25's weight in the hybrid, as selected on dev in experiment 13."""
    path = RESULTS / "fusion_dev.csv"
    if not path.exists():
        raise SystemExit("results/fusion_dev.csv is missing; it ships with "
                         "the repository, so check the clone is complete.")
    dev = pd.read_csv(path)
    sub = dev[dev["combination"] == f"hybrid {lang}"]
    if "beta" in sub.columns:
        sub = sub[sub["beta"].isna()]
    return float(sub.loc[sub["ndcg@10"].idxmax(), "weight"])


def top_n(scores: np.ndarray, uris: np.ndarray, n: int) -> list[tuple[str, float]]:
    n = min(n, len(scores))
    idx = np.argpartition(-scores, n - 1)[:n]
    idx = idx[np.argsort(-scores[idx], kind="stable")]
    return [(uris[i], float(scores[i])) for i in idx]


def truncate(text: str, words: int = CANDIDATE_WORDS) -> str:
    parts = text.split()
    return " ".join(parts[:words]) + ("..." if len(parts) > words else "")


class SkillLinker:
    def __init__(self, lang: str, rerank: str | None = None,
                 device: str | None = None):
        if lang not in ("pt", "en"):
            raise ValueError("lang must be 'pt' or 'en'")
        self.lang = lang
        other = "en" if lang == "pt" else "pt"

        texts = pd.read_parquet(PROCESSED / "texts.parquet")
        labels = pd.read_parquet(PROCESSED / "labels.parquet")
        skills = pd.read_parquet(PROCESSED / "skills.parquet")

        self.uris = np.asarray(sorted(skills["conceptUri"]))
        t = texts[(texts["language"] == lang)
                  & (texts["conceptKind"] == "skill")]
        preferred = dict(zip(t["conceptUri"], t["preferredLabel"]))
        description = dict(zip(t["conceptUri"], t["description"]))
        a = labels[(labels["language"] == lang) & (labels["labelType"] == "alt")]
        alt: dict[str, list[str]] = {}
        for uri, label in zip(a["conceptUri"], a["label"]):
            alt.setdefault(uri, []).append(label)

        o = texts[(texts["language"] == other)
                  & (texts["conceptKind"] == "skill")]
        self.label = preferred
        self.other_label = dict(zip(o["conceptUri"], o["preferredLabel"]))
        self.skill_type = dict(zip(skills["conceptUri"], skills["skillType"]))
        self.candidate = {u: truncate(f"{preferred[u]}. {description[u]}"
                                      if description.get(u) else preferred[u])
                          for u in self.uris}

        docs = build_documents(list(self.uris), preferred, alt, description,
                               VARIANT)
        self.bm25 = BM25Index(list(self.uris), docs, get_stemmer(lang),
                              get_stopwords(lang))
        self.dense = DenseIndex(MODELS[DENSE], device=device).build(
            list(self.uris), docs, lang, VARIANT)
        self.weight = fusion_weight(lang)

        self.reranker = None
        if rerank:
            spec = LLMS[rerank]
            kwargs = ({"device": device or "cuda", "batch_size": 1}
                      if spec.backend == "local" else {"max_workers": 1})
            self.reranker = build_llm_reranker(spec, **kwargs)
            if hasattr(self.reranker, "preflight"):
                self.reranker.preflight()

        self._warm_up(rerank)

    def _warm_up(self, rerank: str | None) -> None:
        """Load every model now, so query timings measure queries.

        Both models load lazily on first use, which would otherwise charge
        the first query for loading weights and initialising the GPU.
        """
        try:
            from transformers.utils import logging as hf_logging

            hf_logging.disable_progress_bar()
        except ImportError:
            pass
        self.dense.encode_queries(["warm up"])
        if self.reranker is not None and LLMS[rerank].backend == "local":
            self.reranker.rank(["warm up"], [["first", "second"]], top_k=1)

    def first_stage(self, text: str) -> list[tuple[str, float]]:
        tokens = tokenize(text, self.bm25.stemmer, self.bm25.stopwords)
        # A query made only of stopwords has no lexical signal; leaving the
        # BM25 run empty lets the dense run decide alone.
        lexical = ({"q": top_n(self.bm25.bm25.get_scores(tokens), self.uris,
                               RUN_DEPTH)} if tokens else {})
        qvec = self.dense.encode_queries([text])[0]
        dense = {"q": top_n(self.dense.scores_for(qvec), self.uris, RUN_DEPTH)}
        return weighted_score_fusion([lexical, dense],
                                     [self.weight, 1.0 - self.weight])["q"]

    def link(self, text: str, k: int = 10) -> tuple[list[str], dict]:
        info: dict = {}
        t0 = time.perf_counter()
        ranked = [u for u, _ in self.first_stage(text)]
        info["retrieval_s"] = time.perf_counter() - t0

        if self.reranker is not None:
            cands = ranked[:RERANK_DEPTH]
            t0 = time.perf_counter()
            res = self.reranker.rank([text], [[self.candidate[c] for c in cands]],
                                     top_k=RERANK_TOP_K)[0]
            info["rerank_s"] = time.perf_counter() - t0
            info["unparsable"] = res.unparsable
            order = apply_ranking(cands, res)
            ranked = [cands[i] for i in order] + ranked[RERANK_DEPTH:]
        return ranked[:k], info

    def show(self, text: str, k: int = 10) -> None:
        uris, info = self.link(text, k)
        print()
        for i, u in enumerate(uris, start=1):
            kind = "knowledge" if self.skill_type.get(u) == "knowledge" else "skill"
            other_lang = "en" if self.lang == "pt" else "pt"
            print(f"  {i:>2}. {self.label.get(u, u)}  "
                  f"({TYPE_NAME[self.lang][kind]})")
            print(f"      {self.other_label.get(u, '')}  "
                  f"({TYPE_NAME[other_lang][kind]})")
        timing = f"retrieval {info['retrieval_s'] * 1000:.0f} ms"
        if "rerank_s" in info:
            timing += f", reranking {info['rerank_s']:.1f} s"
            if info["unparsable"]:
                timing += " (response unusable, first-stage order kept)"
        print(f"\n  {timing}\n")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Link a learning outcome to ESCO skills.")
    ap.add_argument("text", nargs="*",
                    help="learning outcome; omit for interactive mode")
    ap.add_argument("--lang", default="pt", choices=["pt", "en"],
                    help="language of the learning outcome")
    ap.add_argument("--rerank", choices=list(LLMS), default=None,
                    help="rerank the top 20 with an LLM")
    ap.add_argument("-k", type=int, default=10, help="how many skills to show")
    ap.add_argument("--device", default=None)
    args = ap.parse_args()

    t0 = time.perf_counter()
    print(f"loading {args.lang} indexes"
          + (f" and {args.rerank}" if args.rerank else "") + "...")
    linker = SkillLinker(args.lang, args.rerank, args.device)
    print(f"ready in {time.perf_counter() - t0:.1f} s "
          f"(BM25 weight {linker.weight:.1f})")

    if args.text:
        linker.show(" ".join(args.text), args.k)
        return

    print("type a learning outcome and press enter; an empty line quits")
    while True:
        try:
            text = input("\noutcome> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not text:
            break
        linker.show(text, args.k)


if __name__ == "__main__":
    sys.exit(main())