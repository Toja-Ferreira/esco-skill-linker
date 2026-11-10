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

**Stopwords** — off by default, which is how the baseline in
`experiments/01_bm25.py` was run. Experiments 03 and 04 found that Portuguese
and English share comparable vocabulary with their gold skills by token count,
but that the Portuguese overlap carries less IDF weight, because Portuguese
spreads its function words across more distinct high-frequency forms. Removing
them is therefore a language-sensitive intervention rather than a neutral one.

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

# NLTK's stopword corpus name per language. NLTK's lists derive from Snowball,
# so they pair with the stemmers above rather than being an unrelated choice.
STOPWORD_LANGS = {"pt": "portuguese", "en": "english"}


def get_stemmer(lang: str):
    """Snowball stemmer for `lang`, or None if unavailable."""
    import snowballstemmer

    name = STEMMER_LANGS.get(lang)
    if name is None:
        raise ValueError(f"No stemmer configured for language '{lang}'")
    return snowballstemmer.stemmer(name)


def get_stopwords(lang: str) -> frozenset[str]:
    """Curated stopword list for `lang`.

    Curated rather than frequency-derived on purpose. Cutting each corpus's top
    N terms removes different grammatical categories in each language, which
    reintroduces the asymmetry the list is meant to remove. Portuguese spreads
    its definite article across six high-frequency forms (o, a, os, as, do, da)
    where English has one, so a frequency cutoff treats the two languages
    unequally by construction.
    """
    from nltk.corpus import stopwords

    name = STOPWORD_LANGS.get(lang)
    if name is None:
        raise ValueError(f"No stopword list configured for language '{lang}'")
    try:
        return frozenset(stopwords.words(name))
    except LookupError as exc:
        raise RuntimeError(
            "NLTK stopwords corpus not present. Run:\n"
            "    python -c \"import nltk; nltk.download('stopwords')\""
        ) from exc


def tokenize(text: str, stemmer=None, stopwords: frozenset[str] | None = None) -> list[str]:
    """Lowercase, split on word characters, drop stopwords, optionally stem.

    Stopwords are removed before stemming, because the lists are of surface
    forms. Stemming first would leave stemmed function words that no longer
    match the list.
    """
    tokens = TOKEN_RE.findall(text.lower())
    if stopwords is not None:
        tokens = [t for t in tokens if t not in stopwords]
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

    Owns the tokeniser, stemmer and stopword list so queries cannot
    accidentally be processed differently from the documents they are matched
    against.
    """

    def __init__(self, uris: Sequence[str], documents: Sequence[str],
                 stemmer=None, stopwords: frozenset[str] | None = None):
        if len(uris) != len(documents):
            raise ValueError("uris and documents must be the same length")
        self.uris = np.asarray(uris)
        self.stemmer = stemmer
        self.stopwords = stopwords
        tokenised = [tokenize(d, stemmer, stopwords) for d in documents]
        self.empty = sum(1 for t in tokenised if not t)
        self.mean_length = float(np.mean([len(t) for t in tokenised]))
        self.bm25 = BM25Okapi(tokenised)

    def __len__(self) -> int:
        return len(self.uris)

    def search(self, query: str, k: int | None = None) -> list[str]:
        """Return skill URIs ranked best-first.

        Ties are not broken by corpus order. The top n are selected with
        `np.argpartition`, which does not preserve order, and then sorted with a
        stable sort, so tied skills keep the order argpartition left them in.
        That order is deterministic for a given score array and n, but depends
        on n: cutting the same scores at 50 and at 200 can order ties
        differently (see `results/figure_sources.md`).
        """
        tokens = tokenize(query, self.stemmer, self.stopwords)
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