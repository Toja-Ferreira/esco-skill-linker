"""BM25 lexical retrieval over the ESCO skill corpus.

The floor any semantic method has to clear. Two axes are configurable, because
both bear on the Portuguese-versus-English question:

**Document variant** — what text represents each skill. ESCO's alternative
labels are abundant in English and sparse in Portuguese, so including them
changes the two languages very differently.

    preferred     preferred label only
    labels        preferred + alternative labels
    labels_desc   preferred + alternative labels + description
    description   description only

**Stemming** — Portuguese is more inflected than English, so exact-token
matching penalises it more. Running with and without separates the language
effect from the preprocessing effect.

Queries are occupation descriptions. Query and index must use the same
tokenisation, which `BM25Index` enforces by owning both.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence

import numpy as np
from rank_bm25 import BM25Okapi

VARIANTS = ("preferred", "labels", "labels_desc", "description")

# Unicode-aware: keeps accented characters, which Portuguese needs.
TOKEN_RE = re.compile(r"\w+", re.UNICODE)

# Snowball language names for the languages this project uses.
STEMMER_LANGS = {"pt": "portuguese", "en": "english"}


def get_stemmer(lang: str):
    """Snowball stemmer for `lang`, or None if unavailable."""
    import snowballstemmer

    name = STEMMER_LANGS.get(lang)
    if name is None:
        raise ValueError(f"No stemmer configured for language '{lang}'")
    return snowballstemmer.stemmer(name)


def tokenize(text: str, stemmer=None) -> list[str]:
    """Lowercase, split on word characters, optionally stem.

    No stopword removal: BM25's IDF term already discounts words that appear
    in most documents, so an explicit stoplist would add a language-specific
    choice without adding much.
    """
    tokens = TOKEN_RE.findall(text.lower())
    if stemmer is not None:
        tokens = stemmer.stemWords(tokens)
    return tokens


def build_documents(
    uris: Sequence[str],
    preferred: dict[str, str],
    alt: dict[str, list[str]],
    description: dict[str, str],
    variant: str,
) -> list[str]:
    """One text blob per skill, in the order given by `uris`."""
    if variant not in VARIANTS:
        raise ValueError(f"Unknown variant '{variant}'; expected one of {VARIANTS}")

    docs = []
    for u in uris:
        parts: list[str] = []
        if variant in ("preferred", "labels", "labels_desc"):
            parts.append(preferred.get(u, ""))
        if variant in ("labels", "labels_desc"):
            parts.extend(alt.get(u, []))
        if variant in ("labels_desc", "description"):
            parts.append(description.get(u, ""))
        docs.append(" ".join(p for p in parts if p))
    return docs


class BM25Index:
    """A fitted BM25 index over a fixed set of skill URIs.

    Owns the tokeniser so queries cannot accidentally be processed differently
    from the documents they are matched against.
    """

    def __init__(self, uris: Sequence[str], documents: Sequence[str], stemmer=None):
        if len(uris) != len(documents):
            raise ValueError("uris and documents must be the same length")
        self.uris = np.asarray(uris)
        self.stemmer = stemmer
        tokenised = [tokenize(d, stemmer) for d in documents]
        self.empty = sum(1 for t in tokenised if not t)
        self.mean_length = float(np.mean([len(t) for t in tokenised]))
        self.bm25 = BM25Okapi(tokenised)

    def __len__(self) -> int:
        return len(self.uris)

    def search(self, query: str, k: int | None = None) -> list[str]:
        """Return skill URIs ranked best-first.

        Ties are broken by the corpus order, which is stable across runs
        because the corpus is sorted by URI upstream.
        """
        tokens = tokenize(query, self.stemmer)
        if not tokens:
            return []
        scores = self.bm25.get_scores(tokens)
        n = len(scores) if k is None else min(k, len(scores))
        # argpartition then sort only the top n: much cheaper than a full sort
        # of 13,939 scores, repeated for every query and condition.
        top = np.argpartition(-scores, n - 1)[:n]
        top = top[np.argsort(-scores[top], kind="stable")]
        return self.uris[top].tolist()

    def search_many(self, queries: Iterable[str], k: int | None = None) -> list[list[str]]:
        return [self.search(q, k) for q in queries]