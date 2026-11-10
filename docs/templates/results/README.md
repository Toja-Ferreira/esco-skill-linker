# Results

Findings across experiments. Each entry interprets numbers held in a generated
file alongside it. Generated files are overwritten on every run; this one is
not.

| # | experiment | generated output | script |
|---|---|---|---|
| 01 | BM25 lexical baseline | [`bm25.md`](bm25.md) | [`experiments/01_bm25.py`](../experiments/01_bm25.py) |
| 02 | Quality by gold set size | [`gold_size_slice.md`](gold_size_slice.md) | [`experiments/02_gold_size_slice.py`](../experiments/02_gold_size_slice.py) |
| 03 | Lexical overlap, query to gold | [`lexical_overlap.md`](lexical_overlap.md) | [`experiments/03_lexical_overlap.py`](../experiments/03_lexical_overlap.py) |
| 04 | IDF-weighted overlap | [`weighted_overlap.md`](weighted_overlap.md) | [`experiments/04_weighted_overlap.py`](../experiments/04_weighted_overlap.py) |
| 05 | BM25 with stopword removal | [`bm25_stopwords.md`](bm25_stopwords.md) | [`experiments/05_stopwords.py`](../experiments/05_stopwords.py) |
| 06 | Parameter sweep, dev tuned | [`bm25_sweep.md`](bm25_sweep.md) | [`experiments/06_bm25_sweep.py`](../experiments/06_bm25_sweep.py) |
| 07 | Score distribution, gold against field | [`score_distribution.md`](score_distribution.md) | [`experiments/07_score_distribution.py`](../experiments/07_score_distribution.py) |
| 08 | Failure cases, read directly | [`failure_cases.md`](failure_cases.md) | [`experiments/08_failure_cases.py`](../experiments/08_failure_cases.py) |
| 09 | Overlap by term rarity | [`idf_band_overlap.md`](idf_band_overlap.md) | [`experiments/09_idf_band_overlap.py`](../experiments/09_idf_band_overlap.py) |
| 10 | Bi-encoder retrieval | [`bi_encoder.md`](bi_encoder.md) | [`experiments/10_bi_encoder.py`](../experiments/10_bi_encoder.py) |
| 11 | Dense against lexical, per query | [`dense_vs_lexical.md`](dense_vs_lexical.md) | [`experiments/11_dense_vs_lexical.py`](../experiments/11_dense_vs_lexical.py) |
| 12 | Shape of the residual language gap | [`residual_gap.md`](residual_gap.md) | [`experiments/12_residual_gap.py`](../experiments/12_residual_gap.py) |
| 13 | Hybrid and bilingual fusion | [`fusion.md`](fusion.md) | [`experiments/13_fusion.py`](../experiments/13_fusion.py) |
| 14 | Cross-encoder reranking, and the ordering ceiling | [`rerank.md`](rerank.md), [`rerank_qwen3-0.6b.md`](rerank_qwen3-0.6b.md) | [`experiments/14_rerank.py`](../experiments/14_rerank.py) |
| 15 | Listwise LLM reranking, local and API | [`llm_rerank_qwen3-4b-local.md`](llm_rerank_qwen3-4b-local.md), [`llm_rerank_deepseek.md`](llm_rerank_deepseek.md) | [`experiments/15_llm_rerank.py`](../experiments/15_llm_rerank.py) |
| 16 | Local against API, per query | [`llm_compare.md`](llm_compare.md) | [`experiments/16_llm_compare.py`](../experiments/16_llm_compare.py) |

Figures in [`figures/`](figures/) are drawn from these result files by
[`experiments/make_figures.py`](../experiments/make_figures.py).
Every number in this file is rendered from them too;
[`figure_sources.md`](figure_sources.md) gives the source of each.

Also here: [`dataset_profile.md`](dataset_profile.md) and
[`split_profile.md`](split_profile.md), describing the release and the frozen
evaluation split.

## Current best

{{split.test.queries:.0f}} held-out occupation descriptions against all {{data.skills:,.0f}} skills, nDCG@10.

Experiment 14 measures what a flawless reranker would reach over the same
top-100 candidates: **{{oracle100.test.pt.ndcg10:.3f}} Portuguese and {{oracle100.test.en.ndcg10:.3f}} English**, more than double
the best first stage. The shortlist already contains a correct skill in its top
10 for roughly {{oracle10.test.pt.mrr:.0%}} of Portuguese queries and {{oracle10.test.en.mrr:.0%}} of English ones, so most of what is missing is ordering.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="figures/systems_dark.svg">
  <img alt="nDCG@10 per system and language, with the perfect-ordering ceilings at depth 20 and 100." src="figures/systems_light.svg">
</picture>

| system | English | Portuguese | gap | gap, relative |
|---|---:|---:|---:|---:|
| BM25, stemmed, stopwords removed | {{bm25.test.en.ndcg10:.4f}} | {{bm25.test.pt.ndcg10:.4f}} | {{gap.abs.bm25:.4f}} | {{gap.rel.bm25:+.1%}} |
| Bi-encoder, `embeddinggemma-300m` | {{bi.embeddinggemma.test.en.ndcg10:.4f}} | {{bi.embeddinggemma.test.pt.ndcg10:.4f}} | {{gap.abs.bi:.4f}} | {{gap.rel.bi:+.1%}} |
| Hybrid, weighted score fusion | {{hybrid.test.en.ndcg10:.4f}} | {{hybrid.test.pt.ndcg10:.4f}} | {{gap.abs.hybrid:.4f}} | {{gap.rel.hybrid:+.1%}} |
| Hybrid, reranked by Qwen3-4B (local) | {{qwen.test.en.ndcg10:.4f}} | {{qwen.test.pt.ndcg10:.4f}} | {{gap.abs.qwen:.4f}} | {{gap.rel.qwen:+.1%}} |
| **Hybrid, reranked by DeepSeek (API)** | **{{deepseek.test.en.ndcg10:.4f}}** | **{{deepseek.test.pt.ndcg10:.4f}}** | {{gap.abs.deepseek:.4f}} | {{gap.rel.deepseek:+.1%}} |

The best system is hybrid weighted score fusion followed by listwise reranking
of the top 20 with DeepSeek's API model, which costs about ${{deepseek.cost_per_prompt:.4f}} per
description. Where a paid API is not an option, the same reranking with a local
Qwen3-4B keeps about half the gain at no per-query cost and reproduces exactly.
Without an LLM, the recommended configuration is hybrid fusion in one language.
Fusing all four runs, both methods in both languages, scores marginally higher
at {{h2h.all4wsf_vs_hybenwsf.a_score:.4f}} but is not distinguishable from it (paired difference {{h2h.all4wsf_vs_hybenwsf.mean_delta:+.4f}}
[{{h2h.all4wsf_vs_hybenwsf.delta_lo:+.4f}}, {{h2h.all4wsf_vs_hybenwsf.delta_hi:+.4f}}]), so the simpler system is preferred.

Recall@10 is capped at {{ceiling.recall10:.3f}} on this split, so the English hybrid's {{hybrid.test.en.recall10:.3f}} is {{hybrid.test.en.recall_share:.0%}} of
what is reachable.

What the headline table does not show: dense retrieval closed about half of the
lexical language gap by compressing a tail of failing Portuguese queries, and
nothing after it, fusion or either reranker, measurably moved the gap again.

---

## Reading the numbers

**Recall@k is capped well below 1.** Occupations carry around {{split.test.essential_mean:.0f}} essential
skills on average and only 10 fit in a top-10, so the highest recall@10
achievable on this split is **{{ceiling.recall10:.3f}}**. EmbeddingGemma's English recall@10 of {{bi.embeddinggemma.test.en.recall10:.3f}} is {{bi.embeddinggemma.test.en.recall_share:.0%}} of what is
reachable.

| k | 1 | 3 | 5 | 10 | 20 | 50 |
|---|---:|---:|---:|---:|---:|---:|
| max recall@k | {{ceiling.recall1:.3f}} | {{ceiling.recall3:.3f}} | {{ceiling.recall5:.3f}} | {{ceiling.recall10:.3f}} | {{ceiling.recall20:.3f}} | {{ceiling.recall50:.3f}} |

**Arrows and bold.** ▲ and ▼ mark a change in retrieval quality against the
baseline the table names. Where a paired interval is given, the arrow appears
only when the interval excludes zero, so a change with no arrow is not
distinguishable from noise. Language gaps carry no arrow. Bold marks the best
value in a comparison.

**Precision and MRR answer different questions.** The best English run, DeepSeek reranking, has P@10
of {{deepseek.test.en.p10:.3f}}, so most of what it shows is wrong, alongside MRR of {{deepseek.test.en.mrr:.3f}}, meaning the
first genuinely essential skill usually appears at rank 1 or 2 out of {{data.skills:,.0f}}
candidates. Retrieval finds one correct skill easily and the full set poorly,
and which of those matters depends on the interface.

---

## 01: BM25 lexical baseline

{{split.test.queries:.0f}} test occupations, full index, {{bm25.conditions:.0f}} conditions covering 2 languages, 4 document
variants and stemmed against unstemmed. No stopword removal, which experiment 05
later revised.

### The alternative-label asymmetry behaves as predicted

Adding ESCO's alternative labels to the preferred label transforms the English
index and does nothing measurable for Portuguese:

| | preferred | plus alt labels | change | tokens/doc |
|---|---:|---:|---:|---|
| pt, raw | {{bm25x.pt.preferred.raw.kept.ndcg10:.3f}} | {{bm25x.pt.labels.raw.kept.ndcg10:.3f}} | ▼ {{bm25x.pt.alt_gain:+.1%}} | {{bm25x.pt.preferred.raw.kept.tokens:.1f}} to {{bm25x.pt.labels.raw.kept.tokens:.1f}} |
| en, raw | {{bm25x.en.preferred.raw.kept.ndcg10:.3f}} | {{bm25x.en.labels.raw.kept.ndcg10:.3f}} | ▲ {{bm25x.en.alt_gain:+.1%}} | {{bm25x.en.preferred.raw.kept.tokens:.1f}} to {{bm25x.en.labels.raw.kept.tokens:.1f}} |

English documents grow eightfold. Portuguese documents grow by roughly one
token, because only {{data.alt_share.pt.skills:.0%}} of Portuguese skills carry any alternative label. The
{{data.alt_ratio.skills:.1f}}x label asymmetry recorded in the dataset profile is worth a fifth of
English lexical retrieval quality, and Portuguese cannot access any of it.

### The label gap does not account for the whole deficit

On document variants where ESCO treats both languages equally, Portuguese has
more text and still scores lower:

| condition | pt tokens | en tokens | pt nDCG@10 | en nDCG@10 | en advantage |
|---|---:|---:|---:|---:|---:|
| preferred, raw | {{bm25x.pt.preferred.raw.kept.tokens:.1f}} | {{bm25x.en.preferred.raw.kept.tokens:.1f}} | {{bm25x.pt.preferred.raw.kept.ndcg10:.3f}} | {{bm25x.en.preferred.raw.kept.ndcg10:.3f}} | {{bm25x.gap.preferred.raw.kept:+.1%}} |
| description, raw | {{bm25x.pt.description.raw.kept.tokens:.1f}} | {{bm25x.en.description.raw.kept.tokens:.1f}} | {{bm25x.pt.description.raw.kept.ndcg10:.3f}} | {{bm25x.en.description.raw.kept.ndcg10:.3f}} | {{bm25x.gap.description.raw.kept:+.1%}} |
| description, stemmed | {{bm25x.pt.description.stemmed.kept.tokens:.1f}} | {{bm25x.en.description.stemmed.kept.tokens:.1f}} | {{bm25x.pt.description.stemmed.kept.ndcg10:.3f}} | {{bm25x.en.description.stemmed.kept.ndcg10:.3f}} | {{bm25x.gap.description.stemmed.kept:+.1%}} |

Portuguese preferred labels are {{bm25x.pt.preferred.longer:.0%}} longer than English ones and score {{bm25x.pt.preferred.lower:.0%}}
lower. Descriptions are {{bm25x.pt.description.longer:.0%}} longer and score {{bm25x.pt.description.lower:.0%}} lower. Every interval is
disjoint. A shortage of text does not explain this, which rules out the original
framing of the project's central question. Experiments 03 to 05 pursue the
cause.

### Stemming helps, and helps English more on short fields

Relative nDCG@10 gain from stemming, before stopword removal:

| variant | pt | en |
|---|---:|---:|
| preferred | ▲ {{bm25x.pt.preferred.stem_gain:+.1%}} | ▲ {{bm25x.en.preferred.stem_gain:+.1%}} |
| labels | ▲ {{bm25x.pt.labels.stem_gain:+.1%}} | ▲ {{bm25x.en.labels.stem_gain:+.1%}} |
| labels_desc | ▲ {{bm25x.pt.labels_desc.stem_gain:+.1%}} | ▲ {{bm25x.en.labels_desc.stem_gain:+.1%}} |
| description | ▲ {{bm25x.pt.description.stem_gain:+.1%}} | ▲ {{bm25x.en.description.stem_gain:+.1%}} |

Portuguese is the more heavily inflected language, so the expectation was that it
would gain more. On `preferred`, where a single stem match carries most of the
signal, it gains roughly half as much.

That observation was initially recorded as an unexplained curiosity. It is
better read as a candidate explanation for the language gap itself: a stemmer
that under-conflates would both gain less from being applied and depress the
language's scores throughout. Experiment 03 tests it directly.

### Preprocessing audit

Every cross-language claim depends on the two languages receiving identical
treatment. Recorded so it can be checked rather than assumed. Package versions
are pinned in [`requirements.txt`](../requirements.txt).

| | Portuguese | English |
|---|---|---|
| Tokeniser | `re.findall(r"\w+", text.lower())`, `re.UNICODE` | identical |
| Accent handling | preserved, not folded | preserved, not folded |
| Stemmer, stemmed runs | Snowball `portuguese` | Snowball `english` |
| Stopword list, experiment 01 | none | none |
| Stopword list, experiment 05 | NLTK `portuguese` | NLTK `english` |
| BM25 implementation | `rank_bm25.BM25Okapi` | identical |
| k1 / b / epsilon | 1.5 / 0.75 / 0.25 (defaults) | 1.5 / 0.75 / 0.25 (defaults) |
| Index contents | all {{data.skills:,.0f}} skills | all {{data.skills:,.0f}} skills |
| Query text | occupation `description` | occupation `description` |

Parameters are never passed explicitly, so both languages take the same library
defaults. The tokeniser, stemmer and stopword list live on `BM25Index`, which
applies them to documents at construction and to queries at search time, so the
two cannot diverge.

Three asymmetries remain that configuration cannot remove:

1. **The stemmers are different algorithms.** Snowball's Portuguese and English
   stemmers were developed separately and there is no reason to assume equal
   conflation quality. Experiment 03 measures this directly.
2. **`b = 0.75` normalises against each corpus's own mean length**, so there is
   no shared baseline penalising the longer language. But the corpora differ in
   scale rather than by a constant: under `labels` the English mean is {{bm25x.en.labels.raw.kept.tokens:.1f}}
   tokens against {{bm25x.pt.labels.raw.kept.tokens:.1f}} in Portuguese.
3. **`epsilon = 0.25` floors negative IDF values.** Terms appearing in more than
   half the corpus get a small positive score rather than a negative one. How
   often the floor is hit depends on term distribution, which differs between
   corpora. Not measured.

No parameter tuning has been done in either language.

### Cost

{{bm25.ms_per_query.min:.0f}} to {{bm25.ms_per_query.max:.0f}} ms per query, index build at most {{bm25.build_s.max:.1f}} s, everything in memory. Any method
costing materially more should be judged on quality per unit latency.

---

## 02: Quality by gold set size

The benchmark queries occupations carrying a mean of {{split.test.essential_mean:.0f}} essential skills. The
target application queries learning outcomes carrying 1 to 3. If method
behaviour shifts as gold sets shrink, the benchmark is a poor proxy. This slices
the recorded per-query results from experiment 01 into gold-size quartiles. No
retrieval is re-run.

| bucket | queries | essential skills | median | max recall@10 |
|---|---:|---|---:|---:|
| Q1 smallest | {{goldsize.q1.queries:.0f}} | {{goldsize.q1.gold_min:.0f}} to {{goldsize.q1.gold_max:.0f}} | {{goldsize.q1.gold_median:.0f}} | {{goldsize.q1.ceiling:.3f}} |
| Q2 | {{goldsize.q2.queries:.0f}} | {{goldsize.q2.gold_min:.0f}} to {{goldsize.q2.gold_max:.0f}} | {{goldsize.q2.gold_median:.0f}} | {{goldsize.q2.ceiling:.3f}} |
| Q3 | {{goldsize.q3.queries:.0f}} | {{goldsize.q3.gold_min:.0f}} to {{goldsize.q3.gold_max:.0f}} | {{goldsize.q3.gold_median:.0f}} | {{goldsize.q3.ceiling:.3f}} |
| Q4 largest | {{goldsize.q4.queries:.0f}} | {{goldsize.q4.gold_min:.0f}} to {{goldsize.q4.gold_max:.0f}} | {{goldsize.q4.gold_median:.0f}} | {{goldsize.q4.ceiling:.3f}} |

### The English advantage is uniform across gold set sizes

nDCG@10:

| bucket | pt | en | en advantage |
|---|---|---|---:|
| Q1 smallest | {{goldsize.q1.pt.ndcg10:.3f}} [{{goldsize.q1.pt.ndcg10_lo:.3f}}, {{goldsize.q1.pt.ndcg10_hi:.3f}}] | {{goldsize.q1.en.ndcg10:.3f}} [{{goldsize.q1.en.ndcg10_lo:.3f}}, {{goldsize.q1.en.ndcg10_hi:.3f}}] | {{goldsize.q1.adv:+.1%}} |
| Q2 | {{goldsize.q2.pt.ndcg10:.3f}} [{{goldsize.q2.pt.ndcg10_lo:.3f}}, {{goldsize.q2.pt.ndcg10_hi:.3f}}] | {{goldsize.q2.en.ndcg10:.3f}} [{{goldsize.q2.en.ndcg10_lo:.3f}}, {{goldsize.q2.en.ndcg10_hi:.3f}}] | {{goldsize.q2.adv:+.1%}} |
| Q3 | {{goldsize.q3.pt.ndcg10:.3f}} [{{goldsize.q3.pt.ndcg10_lo:.3f}}, {{goldsize.q3.pt.ndcg10_hi:.3f}}] | {{goldsize.q3.en.ndcg10:.3f}} [{{goldsize.q3.en.ndcg10_lo:.3f}}, {{goldsize.q3.en.ndcg10_hi:.3f}}] | {{goldsize.q3.adv:+.1%}} |
| Q4 largest | {{goldsize.q4.pt.ndcg10:.3f}} [{{goldsize.q4.pt.ndcg10_lo:.3f}}, {{goldsize.q4.pt.ndcg10_hi:.3f}}] | {{goldsize.q4.en.ndcg10:.3f}} [{{goldsize.q4.en.ndcg10_lo:.3f}}, {{goldsize.q4.en.ndcg10_hi:.3f}}] | {{goldsize.q4.adv:+.1%}} |

English leads in all four buckets, by between {{goldsize.adv.min:.0%}} and {{goldsize.adv.max:.0%}}, with no trend as gold
sets grow. Each bucket holds around 150 queries, so intervals are wider than the
pooled comparison and two buckets do not separate individually. The evidence is
the consistency of direction and magnitude across four independent buckets. The
pooled {{split.test.queries:.0f}}-query comparison separates the two languages cleanly.

### nDCG is flat across buckets; recall and precision are not

English nDCG@10 runs {{goldsize.en.ndcg10.min:.3f}} to {{goldsize.en.ndcg10.max:.3f}} with no trend, because nDCG normalises by
the ideal ranking and so places a query with {{goldsize.q1.gold_min:.0f}} gold and one with {{goldsize.q4.gold_max:.0f}} on the same
scale.

Recall@10 falls from {{goldsize.q1.en.recall10:.3f}} to {{goldsize.q4.en.recall10:.3f}} across the buckets while precision@10 rises
from {{goldsize.q1.en.p10:.3f}} to {{goldsize.q4.en.p10:.3f}}. Neither reflects the method changing. The recall ceiling
drops from {{goldsize.q1.ceiling:.3f}} to {{goldsize.q4.ceiling:.3f}} over the same range, and more gold means more chances
for any slot to hit. Raw recall and precision are not comparable across buckets.

### Bearing on the query shape limitation

Q1, with a median of {{goldsize.q1.gold_median:.0f}} essential skills, is the closest available
approximation to learning outcome density. Performance there matches the pooled
figures: English {{goldsize.q1.en.ndcg10:.3f}} against {{bm25x.en.labels_desc.stemmed.kept.ndcg10:.3f}} pooled, Portuguese {{goldsize.q1.pt.ndcg10:.3f}} against {{bm25x.pt.labels_desc.stemmed.kept.ndcg10:.3f}}.

For BM25 over `labels_desc`, stemmed and without stopword removal, behaviour is
stable as gold sets shrink toward the target task, across the range this
benchmark can test. That is the only configuration sliced. Dense retrieval,
fusion and reranking have not been sliced by gold set size, and query length
remains untested, since all queries here are full occupation descriptions.

---

## 03: How much vocabulary do queries share with their gold skills?

BM25 can only score a match on tokens present on both sides. If Portuguese
occupation descriptions share less vocabulary with their gold skills, that is
the mechanism behind the retrieval gap. Measures the share of an occupation's
gold-skill vocabulary that appears in its description. No retrieval is run.

| field | stemming | pt | en |
|---|---|---|---|
| description | raw | {{overlap.pt.raw.description.gold_coverage:.4f}} [{{overlap.pt.raw.description.gold_coverage_lo:.4f}}, {{overlap.pt.raw.description.gold_coverage_hi:.4f}}] | {{overlap.en.raw.description.gold_coverage:.4f}} [{{overlap.en.raw.description.gold_coverage_lo:.4f}}, {{overlap.en.raw.description.gold_coverage_hi:.4f}}] |
| description | stemmed | {{overlap.pt.stemmed.description.gold_coverage:.4f}} [{{overlap.pt.stemmed.description.gold_coverage_lo:.4f}}, {{overlap.pt.stemmed.description.gold_coverage_hi:.4f}}] | {{overlap.en.stemmed.description.gold_coverage:.4f}} [{{overlap.en.stemmed.description.gold_coverage_lo:.4f}}, {{overlap.en.stemmed.description.gold_coverage_hi:.4f}}] |
| labels | raw | {{overlap.pt.raw.labels.gold_coverage:.4f}} [{{overlap.pt.raw.labels.gold_coverage_lo:.4f}}, {{overlap.pt.raw.labels.gold_coverage_hi:.4f}}] | {{overlap.en.raw.labels.gold_coverage:.4f}} [{{overlap.en.raw.labels.gold_coverage_lo:.4f}}, {{overlap.en.raw.labels.gold_coverage_hi:.4f}}] |
| labels | stemmed | {{overlap.pt.stemmed.labels.gold_coverage:.4f}} [{{overlap.pt.stemmed.labels.gold_coverage_lo:.4f}}, {{overlap.pt.stemmed.labels.gold_coverage_hi:.4f}}] | {{overlap.en.stemmed.labels.gold_coverage:.4f}} [{{overlap.en.stemmed.labels.gold_coverage_lo:.4f}}, {{overlap.en.stemmed.labels.gold_coverage_hi:.4f}}] |

On `description`, where the gold vocabularies are comparable in size ({{overlap.pt.raw.description.mean_gold_vocab:.0f}} tokens
Portuguese against {{overlap.en.raw.description.mean_gold_vocab:.0f}} English), Portuguese overlap is equal on raw tokens and
higher once stemmed.

The `labels` rows are not comparable between languages, because English's gold
vocabulary is more than twice as large thanks to alternative label coverage, so
the denominators differ.

### Two explanations ruled out

**Translation drift is not supported.** If independently translated records had
diverged in word choice, Portuguese would share less vocabulary with its gold
skills. It shares the same or slightly more. The prediction was directional and
went the other way.

**Portuguese stemmer under-conflation is not supported.** The competing
explanation was that Snowball Portuguese conflates less than Snowball English,
leaving morphological variants unmatched. Stemming raises Portuguese coverage on
descriptions by {{overlap.pt.stem_coverage_gain:.1%}} against English's {{overlap.en.stem_coverage_gain:.1%}}, and shrinks the gold vocabulary
by {{overlap.pt.stem_vocab_shrink:.1%}} against {{overlap.en.stem_vocab_shrink:.1%}}. The Portuguese stemmer conflates at least as much.

So Portuguese shares as much vocabulary with its gold skills as English does,
and still retrieves worse. Counting token types was the wrong measure.

---

## 04: Is the shared vocabulary worth the same in both languages?

Experiment 03 counted token types, treating every shared token alike. BM25 does
not: each match is weighted by inverse document frequency, so a term appearing
throughout the corpus contributes almost nothing. This recomputes the same
overlap three ways.

On `description`:

| measure | pt raw | en raw | pt stemmed | en stemmed |
|---|---:|---:|---:|---:|
| type coverage | {{overlap.pt.raw.description.gold_coverage:.4f}} | {{overlap.en.raw.description.gold_coverage:.4f}} | {{overlap.pt.stemmed.description.gold_coverage:.4f}} | {{overlap.en.stemmed.description.gold_coverage:.4f}} |
| IDF-weighted | {{overlap.pt.raw.description.idf_coverage:.4f}} | **{{overlap.en.raw.description.idf_coverage:.4f}}** | {{overlap.pt.stemmed.description.idf_coverage:.4f}} | **{{overlap.en.stemmed.description.idf_coverage:.4f}}** |
| content-only | {{overlap.pt.raw.description.content_coverage:.4f}} | **{{overlap.en.raw.description.content_coverage:.4f}}** | {{overlap.pt.stemmed.description.content_coverage:.4f}} | **{{overlap.en.stemmed.description.content_coverage:.4f}}** |

**The ranking inverts.** Portuguese leads on token counts and loses on both
weighted measures. Equal vocabulary overlap, less usable signal.

Content-only coverage removes each corpus's {{overlap.top_terms_removed:.0f}} most frequent terms. Doing so
costs Portuguese {{overlap.pt.content_loss:.0%}} of its raw overlap against English's {{overlap.en.content_loss:.0%}}, so nearly half of
the Portuguese overlap was carried by the fifty commonest terms in the corpus.

### The mechanism

The most frequent terms in each description corpus, stemmed:

- **pt**: `de` `e` `a` `com` `par` `o` `os` `as` `em` `ou` `que` `da` `do` `utiliz` `dos`
- **en**: `and` `the` `of` `to` `in` `or` `a` `as` `for` `use` `such` `with` `on` `that` `by`

Both lists are dominated by function words, and in similar aggregate volume. The
difference is in how that volume is distributed. Portuguese carries `o`, `os`,
`as`, `da`, `do`, `dos` as six distinct high-frequency tokens where English has
`the` once. Each Portuguese form has its own document frequency and its own IDF,
so none is individually common enough to be discounted as heavily as `the` is,
and more of that mass survives into the score.

`utiliz` at {{overlap.freq.pt.utiliz:,.0f}} and `use` at {{overlap.freq.en.use:,.0f}} are the same content word at almost
identical frequency, which is a useful check that the two corpora really are
translations of each other.

This also explains why a frequency-derived stopword list would be the wrong
instrument. Cutting each corpus's top N terms removes different grammatical
categories in each language, rebuilding the asymmetry it is meant to remove.

---

## 05: Does stopword removal narrow the gap?

Experiment 01 used no stopword list in either language, on the reasoning that
IDF already discounts common terms. Experiment 04 showed that reasoning was
incomplete. This reruns all conditions with NLTK's curated lists, which derive
from Snowball and so pair with the stemmers already in use. Removal happens
before stemming, since the lists are surface forms.

The prediction, recorded before the run: removal helps Portuguese more, and the
gap narrows.

### The prediction held in all eight comparisons

Relative nDCG@10 gain from removing stopwords:

| documents | stemming | pt | en |
|---|---|---:|---:|
| preferred | raw | ▲ {{bm25x.pt.preferred.raw.stop_gain:+.1%}} | ▲ {{bm25x.en.preferred.raw.stop_gain:+.1%}} |
| preferred | stemmed | ▲ {{bm25x.pt.preferred.stemmed.stop_gain:+.1%}} | ▲ {{bm25x.en.preferred.stemmed.stop_gain:+.1%}} |
| labels | raw | ▲ {{bm25x.pt.labels.raw.stop_gain:+.1%}} | ▲ {{bm25x.en.labels.raw.stop_gain:+.1%}} |
| labels | stemmed | ▲ {{bm25x.pt.labels.stemmed.stop_gain:+.1%}} | ▲ {{bm25x.en.labels.stemmed.stop_gain:+.1%}} |
| labels_desc | raw | ▲ {{bm25x.pt.labels_desc.raw.stop_gain:+.1%}} | ▲ {{bm25x.en.labels_desc.raw.stop_gain:+.1%}} |
| labels_desc | stemmed | ▲ {{bm25x.pt.labels_desc.stemmed.stop_gain:+.1%}} | ▲ {{bm25x.en.labels_desc.stemmed.stop_gain:+.1%}} |
| description | raw | ▲ {{bm25x.pt.description.raw.stop_gain:+.1%}} | ▲ {{bm25x.en.description.raw.stop_gain:+.1%}} |
| description | stemmed | ▲ {{bm25x.pt.description.stemmed.stop_gain:+.1%}} | ▲ {{bm25x.en.description.stemmed.stop_gain:+.1%}} |

Portuguese gains more in every case. On `description` stemmed, more than twice
as much.

### The gap narrows everywhere, but does not close

English advantage in nDCG@10:

| documents | stemming | stops kept | stops removed | change |
|---|---|---:|---:|---:|
| preferred | raw | {{bm25x.gap.preferred.raw.kept:+.1%}} | {{bm25x.gap.preferred.raw.removed:+.1%}} | {{bm25x.gap_change_pp.preferred.raw:+.1f}} pp |
| preferred | stemmed | {{bm25x.gap.preferred.stemmed.kept:+.1%}} | {{bm25x.gap.preferred.stemmed.removed:+.1%}} | {{bm25x.gap_change_pp.preferred.stemmed:+.1f}} pp |
| labels | raw | {{bm25x.gap.labels.raw.kept:+.1%}} | {{bm25x.gap.labels.raw.removed:+.1%}} | {{bm25x.gap_change_pp.labels.raw:+.1f}} pp |
| labels | stemmed | {{bm25x.gap.labels.stemmed.kept:+.1%}} | {{bm25x.gap.labels.stemmed.removed:+.1%}} | {{bm25x.gap_change_pp.labels.stemmed:+.1f}} pp |
| labels_desc | raw | {{bm25x.gap.labels_desc.raw.kept:+.1%}} | {{bm25x.gap.labels_desc.raw.removed:+.1%}} | {{bm25x.gap_change_pp.labels_desc.raw:+.1f}} pp |
| labels_desc | stemmed | {{bm25x.gap.labels_desc.stemmed.kept:+.1%}} | {{bm25x.gap.labels_desc.stemmed.removed:+.1%}} | {{bm25x.gap_change_pp.labels_desc.stemmed:+.1f}} pp |
| description | raw | {{bm25x.gap.description.raw.kept:+.1%}} | {{bm25x.gap.description.raw.removed:+.1%}} | {{bm25x.gap_change_pp.description.raw:+.1f}} pp |
| description | stemmed | {{bm25x.gap.description.stemmed.kept:+.1%}} | {{bm25x.gap.description.stemmed.removed:+.1%}} | {{bm25x.gap_change_pp.description.stemmed:+.1f}} pp |

On `description` stemmed, the fairest comparison available, preprocessing
accounted for roughly a quarter of the gap: {{bm25x.stopword_pp_removed:.1f}} points of {{bm25x.gap_pp.description.stemmed.kept:.1f}}. The remaining
{{bm25x.gap.description.stemmed.removed:.1%}} persists with disjoint intervals.

### Confirmation in the token counts

Share of tokens removed as stopwords:

| documents | pt | en |
|---|---:|---:|
| preferred | {{bm25x.pt.preferred.stop_token_share:.1%}} | {{bm25x.en.preferred.stop_token_share:.1%}} |
| labels | {{bm25x.pt.labels.stop_token_share:.1%}} | {{bm25x.en.labels.stop_token_share:.1%}} |
| labels_desc | {{bm25x.pt.labels_desc.stop_token_share:.1%}} | {{bm25x.en.labels_desc.stop_token_share:.1%}} |
| description | {{bm25x.pt.description.stop_token_share:.1%}} | {{bm25x.en.description.stop_token_share:.1%}} |

Portuguese carries more function-word mass in every variant. The `preferred`
row is the most striking: nearly a third of a Portuguese skill label is
stopwords, against a ninth in English.

### What this settles

The absence of a stopword list was a genuine confound and a mistake in
experiment 01's configuration. It cost both languages performance and cost
Portuguese more. Correcting it changes the headline figures and narrows the gap
by about a quarter.

It does not explain the remainder. After correction, English still leads by
{{bm25x.gap.description.stemmed.removed:.1%}} on the description variant where both languages have complete coverage,
comparable vocabulary overlap, and now equivalent function-word handling. The
three cheapest explanations, missing labels, translation drift, and preprocessing
asymmetry, have each been tested and each accounts for only part or none of the
effect.

---

## 06: Parameter sweep, and is the baseline fair?

Comparing an untuned lexical baseline against a tuned dense model overstates the
dense gain, which is a common weakness in retrieval comparisons. This tunes k1
and b before that comparison is made.

**The sweep runs on dev.** Every earlier experiment scored on test, which was
sound because nothing was selected on the basis of those scores: all conditions
were reported. Choosing parameters by their score is fitting, so the test split
is touched once per language with the already-selected values. Dev had been
reserved for this and until now unused.

{{sweep.grid_points:.0f}} grid points per language on {{split.dev.queries:,.0f}} dev queries, `labels_desc`, stemmed,
stopwords removed.

### Tuning buys nothing

| language | selected | dev nDCG@10 | test tuned | test default | gain |
|---|---|---:|---:|---:|---:|
| pt | k1={{sweep.pt.k1}}, b={{sweep.pt.b}} | {{sweep.pt.dev:.4f}} | {{sweep.pt.test.tuned:.4f}} | {{sweep.pt.test.default:.4f}} | {{sweep.pt.gain:+.1%}} |
| en | k1={{sweep.en.k1}}, b={{sweep.en.b}} | {{sweep.en.dev:.4f}} | {{sweep.en.test.tuned:.4f}} | {{sweep.en.test.default:.4f}} | ▲ {{sweep.en.gain:+.1%}} |

Both gains sit far inside the confidence intervals. The library defaults were
already essentially optimal for this corpus.

This is a useful negative result. The lexical floor reported here is properly
calibrated rather than arbitrary, so the dense comparison that follows cannot be
dismissed as tuned-against-untuned. The reported baseline stays at the defaults,
since tuned parameters would add a configuration to explain for no measurable
return.

The baseline's configuration, `labels_desc`, stemmed, stopwords removed, was
first picked from experiment 05's test results. Rerunning all {{bm25dev.pt.configs:w}} configurations
per language on dev ([`bm25_stopwords_dev.md`](bm25_stopwords_dev.md)) selects the same one in both
languages, at {{bm25dev.pt.selected.ndcg10:.4f}} [{{bm25dev.pt.selected.ndcg10_lo:.4f}}, {{bm25dev.pt.selected.ndcg10_hi:.4f}}] in Portuguese and {{bm25dev.en.selected.ndcg10:.4f}} [{{bm25dev.en.selected.ndcg10_lo:.4f}}, {{bm25dev.en.selected.ndcg10_hi:.4f}}] in
English, against runners-up of {{bm25dev.pt.runner_up.ndcg10:.4f}} and {{bm25dev.en.runner_up.ndcg10:.4f}}, so the baseline is not
selected on test.

### Length normalisation is not the residual

The dev surfaces are nearly flat across the useful range of `b`. Portuguese
peaks at {{sweep.pt.b}}, with 0.9 giving {{sweep.pt.b0.9:.4f}} and 1.0 giving {{sweep.pt.b1.0:.4f}}. English peaks at
{{sweep.en.b}}, with 0.9 at {{sweep.en.b0.9:.4f}} and 0.75 at {{sweep.en.b0.75:.4f}}. Moving `b` between 0.75 and 1.0
changes nDCG@10 by at most {{sweep.b_span.max:.4f}} in either language, against a language gap of
roughly {{gap.abs.bm25:.2f}}.

The surfaces do differ in shape: English rises monotonically in `b` while
Portuguese turns over, which is consistent with the two corpora differing in
scale. But the magnitude is an order of magnitude too small to account for the
gap. Selecting on argmax alone would have over-read this.

### Corpus vocabulary size, from experiment 04's records

A further candidate was that translated text is lexically less varied than
original text, since translators converge on common renderings. A smaller
effective vocabulary would compress IDF corpus-wide and make concepts harder to
tell apart.

Distinct terms per corpus, already recorded in `weighted_overlap.csv`:

| field | stemming | pt | en |
|---|---|---:|---:|
| description | raw | {{overlap.pt.raw.description.corpus_vocab:,.0f}} | {{overlap.en.raw.description.corpus_vocab:,.0f}} |
| description | stemmed | {{overlap.pt.stemmed.description.corpus_vocab:,.0f}} | {{overlap.en.stemmed.description.corpus_vocab:,.0f}} |
| labels | raw | {{overlap.pt.raw.labels.corpus_vocab:,.0f}} | {{overlap.en.raw.labels.corpus_vocab:,.0f}} |
| labels | stemmed | {{overlap.pt.stemmed.labels.corpus_vocab:,.0f}} | {{overlap.en.stemmed.labels.corpus_vocab:,.0f}} |

On `description`, Portuguese vocabulary is **larger**, by {{overlap.vocab_larger.raw:.0%}} raw and {{overlap.vocab_larger.stemmed:.0%}}
stemmed. The prediction was directional and went the other way. The `labels`
rows differ for the already-known reason of alternative label coverage.

So Portuguese descriptions are more lexically varied than English ones and still
retrieve worse.

---

## 07 to 09: where the gap actually comes from

Experiments 01 to 06 established a Portuguese deficit and eliminated several
explanations for it, all by comparing averages. These three locate it instead.
They are written together because individually each reads as inconclusive and
together they are not.

### 07: gold does not separate as far from the field

Every earlier diagnostic measured the relationship between a query and its
**gold** skills. None measured the relationship to the roughly 13,000 **non-gold**
skills. Ranking is a contest, so only the numerator had been examined.

The scale-free measure is separation: mean gold score minus mean non-gold score,
in units of the non-gold standard deviation. Raw BM25 scores are not comparable
across two corpora; this is.

| language | separation | non-gold outranking best gold, mean | median | top flatness |
|---|---:|---:|---:|---:|
| pt | {{scores.pt.separation:.3f}} | {{scores.pt.n_outranking:.1f}} | {{scores.pt.n_outranking_median:.0f}} | {{scores.pt.top_flatness:.3f}} |
| en | {{scores.en.separation:.3f}} | {{scores.en.n_outranking:.1f}} | {{scores.en.n_outranking_median:.0f}} | {{scores.en.top_flatness:.3f}} |

English gold sits {{scores.separation_gain:.1%}} further above the field. Flatness is identical, so the
Portuguese score distribution is not compressed and the problem is not that
ordering is decided by noise.

**The medians are identical and the means differ by a factor of two.** On a
typical query both languages place a gold skill at rank {{scores.pt.median_rank:.0f}}. The distributions
separate only in the tail:

| percentile | en | pt |
|---|---:|---:|
| 50th | {{scores.en.outranking_p50:.0f}} | {{scores.pt.outranking_p50:.0f}} |
| 75th | {{scores.en.outranking_p75:.0f}} | {{scores.pt.outranking_p75:.0f}} |
| 90th | {{scores.en.outranking_p90:.0f}} | {{scores.pt.outranking_p90:.0f}} |
| 95th | {{scores.en.outranking_p95:.0f}} | {{scores.pt.outranking_p95:.0f}} |
| 99th | {{scores.en.outranking_p99:.0f}} | {{scores.pt.outranking_p99:.0f}} |
| max | {{scores.en.outranking_max:.0f}} | {{scores.pt.outranking_max:.0f}} |

Roughly 90% of Portuguese queries behave much like English ones. The aggregate
gap is produced by the worst 5 to 10%.

This also explains a pattern visible since experiment 01: MRR was always the
closest metric between the two languages, {{bm25.test.pt.mrr:.3f}} against {{bm25.test.en.mrr:.3f}} for the corrected BM25 baseline, because MRR
depends on the first hit, which is where the medians agree. nDCG@10 and recall@10
showed larger gaps because they depend on the whole top of the list, which is
where the tail damage lands.

Per-query counts of non-gold skills outranking the best gold skill correlate
{{scores.outranking_corr:.3f}} between the two languages. That statistic is a heavily skewed count
ranging to {{scores.pt.outranking_max:,.0f}}, so it overstates the independence: correlating nDCG@10 on the
same queries gives {{residual.bm25.correlation:.3f}}. The languages fail together more often than they fail
separately, and experiment 12 quantifies what is left over.

### 08: what goes wrong inside the tail

Aggregate statistics cannot go further, so the worst language-specific failures
were read directly. Selection is by excess, Portuguese count minus English count
on the same occupation, so occupations that are hard in both languages drop out.

One pattern accounts for most of them. The query and its gold skills use
different Portuguese renderings of the same term, where English uses one string
on both sides:

| occupation | query term | gold skill term | English |
|---|---|---|---|
| Leather goods CAD patternmaker | *cabedal* | *couro* | leather on both sides |
| Punch press operator | *puncionadora* | *prensa biela-manivela* | punch press on both sides |
| Move coordinator | *mudança* | *movimentação*, *deslocação*, *relocalização* | moving on both sides |
| Road maintenance worker | *estradas* | *rodoviária*, *trânsito* | road on both sides |

The punch press case is the clearest. In English "tend punch press" is retrieved
at rank {{failure.punch.en.rank:.0f}} with a score of {{failure.punch.en.score:.2f}}. In Portuguese the same gold skill shares no
tokens with the query at all, the best gold skill falls to rank {{failure.punch.pt.rank:.0f}}, and the top
of the ranking fills with *prensa hidráulica*, *prensa de forjar* and
*peças de máquinas de soldadura por pontos*, the last matching on *ponto morto*.

The move coordinator case adds a second effect. *Mudança* also means "change",
so the Portuguese ranking is led by *adaptar-se à mudança* and
*promover a mudança social*. A term that is unambiguous in English is polysemous
in translation.

These {{failure.cases:w}} cases are selected as the worst failures and are not a sample.

### 09: the divergence is real but too rare to show in aggregate

If terminology divergence were widespread, it should appear as lower Portuguese
coverage on rare, high-IDF terms, since those carry most of a BM25 score and are
where a translator has genuine choice. Common words translate consistently
because there is one obvious rendering.

Coverage of gold vocabulary, banded by how many skills a term appears in:

| band | pt | en | pt gold terms | en gold terms |
|---|---|---|---:|---:|
| df 1 | {{idfband.b1.pt.coverage:.4f}} [{{idfband.b1.pt.coverage_lo:.4f}}, {{idfband.b1.pt.coverage_hi:.4f}}] | {{idfband.b1.en.coverage:.4f}} [{{idfband.b1.en.coverage_lo:.4f}}, {{idfband.b1.en.coverage_hi:.4f}}] | {{idfband.b1.pt.mean_gold_terms:.0f}} | {{idfband.b1.en.mean_gold_terms:.0f}} |
| df 2 to 5 | {{idfband.b2.pt.coverage:.4f}} [{{idfband.b2.pt.coverage_lo:.4f}}, {{idfband.b2.pt.coverage_hi:.4f}}] | {{idfband.b2.en.coverage:.4f}} [{{idfband.b2.en.coverage_lo:.4f}}, {{idfband.b2.en.coverage_hi:.4f}}] | {{idfband.b2.pt.mean_gold_terms:.0f}} | {{idfband.b2.en.mean_gold_terms:.0f}} |
| df 6 to 50 | {{idfband.b3.pt.coverage:.4f}} [{{idfband.b3.pt.coverage_lo:.4f}}, {{idfband.b3.pt.coverage_hi:.4f}}] | {{idfband.b3.en.coverage:.4f}} [{{idfband.b3.en.coverage_lo:.4f}}, {{idfband.b3.en.coverage_hi:.4f}}] | {{idfband.b3.pt.mean_gold_terms:.0f}} | {{idfband.b3.en.mean_gold_terms:.0f}} |
| df 51+ | {{idfband.b4.pt.coverage:.4f}} [{{idfband.b4.pt.coverage_lo:.4f}}, {{idfband.b4.pt.coverage_hi:.4f}}] | {{idfband.b4.en.coverage:.4f}} [{{idfband.b4.en.coverage_lo:.4f}}, {{idfband.b4.en.coverage_hi:.4f}}] | {{idfband.b4.pt.mean_gold_terms:.0f}} | {{idfband.b4.en.mean_gold_terms:.0f}} |

**Portuguese is equal or ahead in every band, including the rarest.** The
hypothesis is not supported. Experiment 03's original conclusion stands.

An earlier version of this experiment banded by IDF quantiles, which does not
work: terms appearing in exactly one document all share the maximum IDF, and
that tie covers about a quarter of the vocabulary, so quantiles split it
arbitrarily. The document-frequency bands above are the corrected version. Both
give the same answer.

### What the three together establish

Terminology divergence between a query and its gold skills is a real failure
mode in Portuguese, it does severe damage where it occurs, and it is infrequent
enough to leave no trace in any aggregate overlap measure. The gap lives in a
tail, and the tail is invisible to means.

That is why experiments 03 and 09 found nothing while experiment 08 found
something obvious. They were measuring different populations.

---

## 10: Bi-encoder retrieval

The first non-lexical method, and the number comparable to the Commission's
pilot, which evaluated a multilingual sentence encoder in the native language.
Three checkpoints, document variant and checkpoint selected on dev, then scored
once per language on test.

Checkpoints chosen to span a range rather than to top a leaderboard.
`multilingual-e5-base` is the reference point, the closest current equivalent to
what the Commission tested. `embeddinggemma-300m` is the only sub-500M model
with a measured Portuguese result rather than an inferred one. `Qwen3-Embedding-4B`
leads its size group on MTEB Multilingual and MTEB English and places 6th on
MTEB-BR.

No leaderboard measures European Portuguese, and none measures retrieval over a
taxonomy of short concepts, so the boards were used to narrow the field and the
dev split decided.

### Results

| model | lang | documents | nDCG@10 | 95% CI | MRR | vs BM25 |
|---|---|---|---:|---|---:|---:|
| embeddinggemma | en | labels_desc | {{bi.embeddinggemma.test.en.ndcg10:.4f}} | [{{bi.embeddinggemma.test.en.ndcg10_lo:.4f}}, {{bi.embeddinggemma.test.en.ndcg10_hi:.4f}}] | {{bi.embeddinggemma.test.en.mrr:.3f}} | ▲ {{bi.embeddinggemma.test.en.vs_bm25:+.1%}} |
| qwen3-4b | en | preferred | {{bi.qwen3-4b.test.en.ndcg10:.4f}} | [{{bi.qwen3-4b.test.en.ndcg10_lo:.4f}}, {{bi.qwen3-4b.test.en.ndcg10_hi:.4f}}] | {{bi.qwen3-4b.test.en.mrr:.3f}} | ▼ {{bi.qwen3-4b.test.en.vs_bm25:+.1%}} |
| e5-base | en | labels_desc | {{bi.e5-base.test.en.ndcg10:.4f}} | [{{bi.e5-base.test.en.ndcg10_lo:.4f}}, {{bi.e5-base.test.en.ndcg10_hi:.4f}}] | {{bi.e5-base.test.en.mrr:.3f}} | ▼ {{bi.e5-base.test.en.vs_bm25:+.1%}} |
| embeddinggemma | pt | labels_desc | {{bi.embeddinggemma.test.pt.ndcg10:.4f}} | [{{bi.embeddinggemma.test.pt.ndcg10_lo:.4f}}, {{bi.embeddinggemma.test.pt.ndcg10_hi:.4f}}] | {{bi.embeddinggemma.test.pt.mrr:.3f}} | ▲ {{bi.embeddinggemma.test.pt.vs_bm25:+.1%}} |
| qwen3-4b | pt | preferred | {{bi.qwen3-4b.test.pt.ndcg10:.4f}} | [{{bi.qwen3-4b.test.pt.ndcg10_lo:.4f}}, {{bi.qwen3-4b.test.pt.ndcg10_hi:.4f}}] | {{bi.qwen3-4b.test.pt.mrr:.3f}} | ▲ {{bi.qwen3-4b.test.pt.vs_bm25:+.1%}} |
| e5-base | pt | labels_desc | {{bi.e5-base.test.pt.ndcg10:.4f}} | [{{bi.e5-base.test.pt.ndcg10_lo:.4f}}, {{bi.e5-base.test.pt.ndcg10_hi:.4f}}] | {{bi.e5-base.test.pt.mrr:.3f}} | ▼ {{bi.e5-base.test.pt.vs_bm25:+.1%}} |

### Dense retrieval closes most of the language gap

| method | pt | en | en advantage |
|---|---:|---:|---:|
| BM25 | {{bm25.test.pt.ndcg10:.4f}} | {{bm25.test.en.ndcg10:.4f}} | {{gap.rel.bm25:+.1%}} |
| e5-base | {{bi.e5-base.test.pt.ndcg10:.4f}} | {{bi.e5-base.test.en.ndcg10:.4f}} | {{gap.rel.e5:+.1%}} |
| embeddinggemma | {{bi.embeddinggemma.test.pt.ndcg10:.4f}} | {{bi.embeddinggemma.test.en.ndcg10:.4f}} | {{gap.rel.bi:+.1%}} |
| qwen3-4b | {{bi.qwen3-4b.test.pt.ndcg10:.4f}} | {{bi.qwen3-4b.test.en.ndcg10:.4f}} | {{gap.rel.qwen3emb:+.1%}} |

This answers the project's central question. EmbeddingGemma removes about half
of the lexical language gap: {{dense.gap_removed.abs:.0%}} in absolute nDCG@10, from {{gap.abs.bm25:.3f}} to {{gap.abs.bi:.3f}}, or
{{dense.gap_removed.rel:.0%}} measured as a relative gap, from {{gap.rel.bm25:.1%}} to {{gap.rel.bi:.1%}}. It removes it
asymmetrically: Portuguese gains {{dense.gain.pt:.1%}} over BM25 while English gains {{dense.gain.en:.1%}}.

Qwen3 shows the smallest gap at {{gap.rel.qwen3emb:.1%}}, a {{dense.qwen3emb.gap_removed.rel:.0%}} reduction, but that is not the
better result. It is worse than EmbeddingGemma in both languages, {{bi.qwen3-4b.test.en.ndcg10:.4f}} against
{{bi.embeddinggemma.test.en.ndcg10:.4f}} in English and {{bi.qwen3-4b.test.pt.ndcg10:.4f}} against {{bi.embeddinggemma.test.pt.ndcg10:.4f}} in Portuguese, so its narrower gap
comes from degrading the stronger language rather than from lifting the weaker
one. A small language gap is only meaningful read alongside the absolute
scores.

A study reporting only the English figure would have concluded
that dense retrieval offers a modest {{dense.gain.en:.0%}} improvement, and would have missed that
it does substantially different work in each language.

### A {{model.embeddinggemma.params_m:.0f}}M model beats a {{model.qwen3emb.params_b:.0f}}B one

EmbeddingGemma leads Qwen3-Embedding-4B by {{bi.gemma_over_qwen.en:.1%}} in English and {{bi.gemma_over_qwen.pt:.1%}} in
Portuguese, at a thirteenth of the parameters, a third of the index size and
{{bi.embeddinggemma.dim:.0f}} dimensions against {{bi.qwen3-4b.dim:.0f}}.

Qwen3 ranks higher than EmbeddingGemma on every leaderboard consulted. That is
the concrete cost of no European Portuguese retrieval benchmark existing, and it
is the reason the dev split rather than a published ranking made this choice.

`multilingual-e5-base` loses to BM25 in both languages, so "dense beats lexical"
is not true of this task in general. The checkpoint matters more than the
architecture.

### The best document representation is model-specific

| model | pt best | en best |
|---|---|---|
| e5-base | labels_desc | labels_desc |
| embeddinggemma | labels_desc | labels_desc |
| qwen3-4b | preferred | preferred |

Qwen3 is *worse* with more context: on Portuguese dev queries, {{bi.qwen3-4b.dev.pt.preferred.ndcg10:.4f}} on the preferred label alone against
{{bi.qwen3-4b.dev.pt.labels_desc.ndcg10:.4f}} with labels and description. The other two prefer the fuller text, as
BM25 does. Anyone deploying this cannot assume a document representation
transfers between checkpoints.

Qwen3 also has a distinctive metric profile, with MRR of {{bi.qwen3-4b.test.pt.mrr:.3f}} in Portuguese
against EmbeddingGemma's {{bi.embeddinggemma.test.pt.mrr:.3f}} while nDCG@10 differs by only {{bi.gemma_over_qwen.pt:.1%}}. It is worse
at placing a correct skill first while being comparable across the whole top 10,
which matters if the interface shows one suggestion rather than ten.

### Cost

| model | dims | index MB per language | ms/query, en / pt |
|---|---:|---:|---:|
| e5-base | {{bi.e5-base.dim:.0f}} | {{bi.e5-base.index_mb:.1f}} | {{bi.e5-base.test.en.ms_per_query:.2f}} / {{bi.e5-base.test.pt.ms_per_query:.2f}} |
| embeddinggemma | {{bi.embeddinggemma.dim:.0f}} | {{bi.embeddinggemma.index_mb:.1f}} | {{bi.embeddinggemma.test.en.ms_per_query:.2f}} / {{bi.embeddinggemma.test.pt.ms_per_query:.2f}} |
| qwen3-4b | {{bi.qwen3-4b.dim:.0f}} | {{bi.qwen3-4b.index_mb:.1f}} | {{bi.qwen3-4b.test.en.ms_per_query:.2f}} / {{bi.qwen3-4b.test.pt.ms_per_query:.2f}} |

Per-query latency is comparable to BM25 because the corpus is embedded once and
only the query is encoded at request time. The costs dense retrieval adds are a
one-off indexing pass and a resident index, not per-request latency. Timings
were taken on a shared GPU and should be treated as indicative.

---

## 11: Where the dense gain comes from

Experiment 10 recorded a prediction before running. Because the Portuguese
lexical gap is produced by a tail of queries where the two records use different
words for the same concept, dense retrieval should compress that tail rather
than lift the median. This compares per-query distributions over the same {{split.test.queries:.0f}}
occupations. No retrieval is re-run.

### The tail compresses

Per-query nDCG@10 distribution, and the share of queries scoring below {{failure.threshold:.2f}}:

| method | lang | p10 | p50 | p90 | failed |
|---|---|---:|---:|---:|---:|
| bm25 | pt | {{perquery.bm25.pt.p10:.4f}} | {{perquery.bm25.pt.p50:.4f}} | {{perquery.bm25.pt.p90:.4f}} | {{perquery.bm25.pt.failure_rate:.1%}} |
| embeddinggemma | pt | {{perquery.embeddinggemma.pt.p10:.4f}} | {{perquery.embeddinggemma.pt.p50:.4f}} | {{perquery.embeddinggemma.pt.p90:.4f}} | {{perquery.embeddinggemma.pt.failure_rate:.1%}} |
| bm25 | en | {{perquery.bm25.en.p10:.4f}} | {{perquery.bm25.en.p50:.4f}} | {{perquery.bm25.en.p90:.4f}} | {{perquery.bm25.en.failure_rate:.1%}} |
| embeddinggemma | en | {{perquery.embeddinggemma.en.p10:.4f}} | {{perquery.embeddinggemma.en.p50:.4f}} | {{perquery.embeddinggemma.en.p90:.4f}} | {{perquery.embeddinggemma.en.failure_rate:.1%}} |

The Portuguese failure rate falls by {{perquery.failure_drop.pt:.0%}} relative, the English by {{perquery.failure_drop.en:.0%}}. The
Portuguese 10th percentile moves from exactly zero to {{perquery.embeddinggemma.pt.p10:.3f}}, so more than a
tenth of Portuguese queries previously retrieved nothing useful at all and now
do.

Note the p90 column: {{perquery.bm25.pt.p90:.4f}} to {{perquery.embeddinggemma.pt.p90:.4f}} in Portuguese, and {{perquery.bm25.en.p90:.4f}} to {{perquery.embeddinggemma.en.p90:.4f}} in
English. The top of the distribution barely moves. The gain is in the bottom.

### Gains concentrate exactly where BM25 failed

Queries split into quartiles by their BM25 score, then compared against
themselves under EmbeddingGemma:

| lang | BM25 quartile | BM25 | dense | change | improved |
|---|---|---:|---:|---:|---:|
| pt | Q1 worst | {{quartile.embeddinggemma.pt.q1.bm25_mean:.4f}} | {{quartile.embeddinggemma.pt.q1.dense_mean:.4f}} | ▲ {{quartile.embeddinggemma.pt.q1.delta:+.4f}} | {{quartile.embeddinggemma.pt.q1.improved:.0%}} |
| pt | Q2 | {{quartile.embeddinggemma.pt.q2.bm25_mean:.4f}} | {{quartile.embeddinggemma.pt.q2.dense_mean:.4f}} | ▲ {{quartile.embeddinggemma.pt.q2.delta:+.4f}} | {{quartile.embeddinggemma.pt.q2.improved:.0%}} |
| pt | Q3 | {{quartile.embeddinggemma.pt.q3.bm25_mean:.4f}} | {{quartile.embeddinggemma.pt.q3.dense_mean:.4f}} | ▲ {{quartile.embeddinggemma.pt.q3.delta:+.4f}} | {{quartile.embeddinggemma.pt.q3.improved:.0%}} |
| pt | Q4 best | {{quartile.embeddinggemma.pt.q4.bm25_mean:.4f}} | {{quartile.embeddinggemma.pt.q4.dense_mean:.4f}} | ▼ {{quartile.embeddinggemma.pt.q4.delta:+.4f}} | {{quartile.embeddinggemma.pt.q4.improved:.0%}} |
| en | Q1 worst | {{quartile.embeddinggemma.en.q1.bm25_mean:.4f}} | {{quartile.embeddinggemma.en.q1.dense_mean:.4f}} | ▲ {{quartile.embeddinggemma.en.q1.delta:+.4f}} | {{quartile.embeddinggemma.en.q1.improved:.0%}} |
| en | Q2 | {{quartile.embeddinggemma.en.q2.bm25_mean:.4f}} | {{quartile.embeddinggemma.en.q2.dense_mean:.4f}} | ▲ {{quartile.embeddinggemma.en.q2.delta:+.4f}} | {{quartile.embeddinggemma.en.q2.improved:.0%}} |
| en | Q3 | {{quartile.embeddinggemma.en.q3.bm25_mean:.4f}} | {{quartile.embeddinggemma.en.q3.dense_mean:.4f}} | ▲ {{quartile.embeddinggemma.en.q3.delta:+.4f}} | {{quartile.embeddinggemma.en.q3.improved:.0%}} |
| en | Q4 best | {{quartile.embeddinggemma.en.q4.bm25_mean:.4f}} | {{quartile.embeddinggemma.en.q4.dense_mean:.4f}} | ▼ {{quartile.embeddinggemma.en.q4.delta:+.4f}} | {{quartile.embeddinggemma.en.q4.improved:.0%}} |

Monotonic in both languages, and the same shape holds for Qwen3 and for
e5-base, which loses overall while still gaining {{quartile.e5-base.pt.q1.delta:+.3f}} in the Portuguese
bottom quartile.

Dense retrieval is not uniformly better. It trades: rescuing queries that exact
string matching cannot handle, and damaging queries where string overlap was
already doing the job well.

### A caveat on the quartile table

Quartiles are defined on BM25 scores, so the comparison is subject to regression
to the mean. Any second method, including a worse one, would tend to score
higher than BM25 in BM25's worst quartile and lower in its best, because those
groups were selected partly on BM25's own noise. The monotonic pattern alone is
therefore not evidence.

What regression does not explain is the asymmetry between languages. The
Portuguese and English Q1 groups start at similar levels, {{quartile.embeddinggemma.pt.q1.bm25_mean:.3f}} and {{quartile.embeddinggemma.en.q1.bm25_mean:.3f}}, yet
Portuguese gains more from every checkpoint. And the failure rate is a threshold
count over the whole distribution rather than a quartile comparison, so
regression does not apply to it, and it falls further in Portuguese for all
three models.

### What this sets up

The two method families fail on different queries in a structured, measurable
way. EmbeddingGemma wins {{quartile.embeddinggemma.pt.q1.improved:.0%}} of BM25's worst Portuguese quartile and loses {{quartile.embeddinggemma.pt.q4.not_improved:.0%}}
of its best. That is the precondition for score fusion working, and it is a
stronger reason to try a hybrid than the usual observation that hybrids tend to
help.

---

## 12: What is left of the language gap

Dense retrieval leaves an {{gap.rel.bi:.1%}} residual with disjoint intervals. This asks
whether it has the same shape as the lexical gap it replaced. Paired on
occupation, which is exact because ESCO assigns one URI per concept and the gold
set is identical in both languages. No retrieval is re-run.

### The residual is uniform, not a tail

Absolute gap between English and Portuguese at each percentile of the per-query
score distribution:

| model | p10 | p25 | p50 | p75 | p90 | relative gap |
|---|---:|---:|---:|---:|---:|---:|
| bm25 | {{residual.bm25.gap_p10:+.4f}} | {{residual.bm25.gap_p25:+.4f}} | {{residual.bm25.gap_p50:+.4f}} | {{residual.bm25.gap_p75:+.4f}} | {{residual.bm25.gap_p90:+.4f}} | {{residual.bm25.gap_relative:+.1%}} |
| e5-base | {{residual.e5-base.gap_p10:+.4f}} | {{residual.e5-base.gap_p25:+.4f}} | {{residual.e5-base.gap_p50:+.4f}} | {{residual.e5-base.gap_p75:+.4f}} | {{residual.e5-base.gap_p90:+.4f}} | {{residual.e5-base.gap_relative:+.1%}} |
| embeddinggemma | {{residual.embeddinggemma.gap_p10:+.4f}} | {{residual.embeddinggemma.gap_p25:+.4f}} | {{residual.embeddinggemma.gap_p50:+.4f}} | {{residual.embeddinggemma.gap_p75:+.4f}} | {{residual.embeddinggemma.gap_p90:+.4f}} | {{residual.embeddinggemma.gap_relative:+.1%}} |
| qwen3-4b | {{residual.qwen3-4b.gap_p10:+.4f}} | {{residual.qwen3-4b.gap_p25:+.4f}} | {{residual.qwen3-4b.gap_p50:+.4f}} | {{residual.qwen3-4b.gap_p75:+.4f}} | {{residual.qwen3-4b.gap_p90:+.4f}} | {{residual.qwen3-4b.gap_relative:+.1%}} |

Under EmbeddingGemma the gap is roughly flat across the distribution and small
everywhere, between {{residual.embeddinggemma.gap.min:.3f}} and {{residual.embeddinggemma.gap.max:.3f}}. The lexical gap it replaced was {{residual.bm25_over_gemma.min:.1f}} to
{{residual.bm25_over_gemma.max:.1f}} times larger at every percentile, and its p10 figure understates the
damage because Portuguese p10 under BM25 was pinned at exactly {{perquery.bm25.pt.p10:.4f}}.

So the terminology explanation developed in experiments 07 to 09 does not carry
over. What remains affects Portuguese queries broadly and mildly rather than
destroying a minority of them. That is the signature of a model representing one
language slightly better than the other, not of a data problem concentrated in
specific records.

Qwen3 is worth noting: its gap reverses at p90, where Portuguese scores higher
than English. Consistent with its narrower overall gap coming from degraded
English rather than improved Portuguese.

### A correction to the correlation figure

Experiment 07 reported that per-query difficulty correlates {{scores.outranking_corr:.3f}} between the
languages, and earlier write-ups used that as evidence the two fail on largely
different queries.

That statistic was the correlation of `n_outranking`, a count ranging from 0 to
{{scores.pt.outranking_max:,.0f}} and heavily skewed, which understates agreement. Correlating nDCG@10 on
the same queries gives **{{residual.bm25.correlation:.3f}}** under BM25 and **{{residual.embeddinggemma.correlation:.3f}}** under EmbeddingGemma.
The languages fail together far more often than they fail separately.

### What bilingual fusion could actually recover

| model | pt fails | en fails | both | pt only | en only |
|---|---:|---:|---:|---:|---:|
| bm25 | {{residual.bm25.pt_fails:.1%}} | {{residual.bm25.en_fails:.1%}} | {{residual.bm25.both_fail:.1%}} | {{residual.bm25.pt_only_fails:.1%}} | {{residual.bm25.en_only_fails:.1%}} |
| e5-base | {{residual.e5-base.pt_fails:.1%}} | {{residual.e5-base.en_fails:.1%}} | {{residual.e5-base.both_fail:.1%}} | {{residual.e5-base.pt_only_fails:.1%}} | {{residual.e5-base.en_only_fails:.1%}} |
| embeddinggemma | {{residual.embeddinggemma.pt_fails:.1%}} | {{residual.embeddinggemma.en_fails:.1%}} | {{residual.embeddinggemma.both_fail:.1%}} | {{residual.embeddinggemma.pt_only_fails:.1%}} | {{residual.embeddinggemma.en_only_fails:.1%}} |
| qwen3-4b | {{residual.qwen3-4b.pt_fails:.1%}} | {{residual.qwen3-4b.en_fails:.1%}} | {{residual.qwen3-4b.both_fail:.1%}} | {{residual.qwen3-4b.pt_only_fails:.1%}} | {{residual.qwen3-4b.en_only_fails:.1%}} |

A query counts as failed below {{failure.threshold:.2f}} nDCG@10.

Under the best model, {{residual.embeddinggemma.pt_only_fails:.1%}} of occupations fail in Portuguese while succeeding in
English, and {{residual.embeddinggemma.en_only_fails:.1%}} the reverse. An oracle choosing the better language per query
would fix about {{residual.embeddinggemma.pt_only_fails:.0%}} of Portuguese cases; a real fusion method recovers less.

The headroom shrinks as the model improves. EmbeddingGemma has both the smallest
share of language-specific failures and the highest cross-language correlation,
so a better model has already absorbed some of what fusion would otherwise
recover.

Fusion remains worth measuring, because the headroom is real and the deployment
setting supplies both texts at no extra cost. But the case for it is smaller
than the earlier correlation figure implied, and it is now measured rather than
inferred.

---

## 13: Fusion

Two combinations, each justified by an earlier measurement rather than by the
general observation that fusion tends to help. Experiment 11 showed BM25 and
EmbeddingGemma fail on structurally different queries. Experiment 12 measured
the bilingual headroom at {{residual.embeddinggemma.pt_only_fails:.1%}} of occupations failing in Portuguese while
succeeding in English.

Runs are produced at depth {{fusion.run_depth:.0f}} and fused. Reciprocal rank fusion has no weight,
so it is scored on test directly. Weighted score fusion has its weight selected
on dev and applied once to test.

### Weighted score fusion works; rank fusion needs tuning too

Every combination is scored on the identical 608 queries, so the comparison is
paired. Marginal intervals are a weak test here, since two overlapping intervals
can still correspond to a difference holding on most queries. The interval below
is on the per-query difference against the stronger of the runs being combined.

| combination | fusion | fused | gain over better input | paired difference (95% CI) |
|---|---|---:|---:|---|
| hybrid pt | rrf | {{fusion.hybrid_pt.rrf.fused_score:.4f}} | {{fusion.hybrid_pt.rrf.gain:+.1%}} | {{fusion.hybrid_pt.rrf.mean_delta:+.4f}} [{{fusion.hybrid_pt.rrf.delta_lo:+.4f}}, {{fusion.hybrid_pt.rrf.delta_hi:+.4f}}] |
| hybrid en | rrf | {{fusion.hybrid_en.rrf.fused_score:.4f}} | {{fusion.hybrid_en.rrf.gain:+.1%}} | ▲ {{fusion.hybrid_en.rrf.mean_delta:+.4f}} [{{fusion.hybrid_en.rrf.delta_lo:+.4f}}, {{fusion.hybrid_en.rrf.delta_hi:+.4f}}] |
| bilingual gemma | rrf | {{fusion.bilingual_gemma.rrf.fused_score:.4f}} | {{fusion.bilingual_gemma.rrf.gain:+.1%}} | {{fusion.bilingual_gemma.rrf.mean_delta:+.4f}} [{{fusion.bilingual_gemma.rrf.delta_lo:+.4f}}, {{fusion.bilingual_gemma.rrf.delta_hi:+.4f}}] |
| bilingual bm25 | rrf | {{fusion.bilingual_bm25.rrf.fused_score:.4f}} | {{fusion.bilingual_bm25.rrf.gain:+.1%}} | {{fusion.bilingual_bm25.rrf.mean_delta:+.4f}} [{{fusion.bilingual_bm25.rrf.delta_lo:+.4f}}, {{fusion.bilingual_bm25.rrf.delta_hi:+.4f}}] |
| all four | rrf | {{fusion.all_four.rrf.fused_score:.4f}} | {{fusion.all_four.rrf.gain:+.1%}} | {{fusion.all_four.rrf.mean_delta:+.4f}} [{{fusion.all_four.rrf.delta_lo:+.4f}}, {{fusion.all_four.rrf.delta_hi:+.4f}}] |
| hybrid pt | wsf | {{fusion.hybrid_pt.wsf.fused_score:.4f}} | {{fusion.hybrid_pt.wsf.gain:+.1%}} | ▲ {{fusion.hybrid_pt.wsf.mean_delta:+.4f}} [{{fusion.hybrid_pt.wsf.delta_lo:+.4f}}, {{fusion.hybrid_pt.wsf.delta_hi:+.4f}}] |
| **hybrid en** | **wsf** | **{{fusion.hybrid_en.wsf.fused_score:.4f}}** | **{{fusion.hybrid_en.wsf.gain:+.1%}}** | **▲ {{fusion.hybrid_en.wsf.mean_delta:+.4f}} [{{fusion.hybrid_en.wsf.delta_lo:+.4f}}, {{fusion.hybrid_en.wsf.delta_hi:+.4f}}]** |
| bilingual gemma | wsf | {{fusion.bilingual_gemma.wsf.fused_score:.4f}} | {{fusion.bilingual_gemma.wsf.gain:+.1%}} | ▲ {{fusion.bilingual_gemma.wsf.mean_delta:+.4f}} [{{fusion.bilingual_gemma.wsf.delta_lo:+.4f}}, {{fusion.bilingual_gemma.wsf.delta_hi:+.4f}}] |
| bilingual bm25 | wsf | {{fusion.bilingual_bm25.wsf.fused_score:.4f}} | {{fusion.bilingual_bm25.wsf.gain:+.1%}} | ▲ {{fusion.bilingual_bm25.wsf.mean_delta:+.4f}} [{{fusion.bilingual_bm25.wsf.delta_lo:+.4f}}, {{fusion.bilingual_bm25.wsf.delta_hi:+.4f}}] |
| **all four** | **wsf** | **{{fusion.all_four.wsf.fused_score:.4f}}** | **{{fusion.all_four.wsf.gain:+.1%}}** | **▲ {{fusion.all_four.wsf.mean_delta:+.4f}} [{{fusion.all_four.wsf.delta_lo:+.4f}}, {{fusion.all_four.wsf.delta_hi:+.4f}}]** |

At its conventional constant, k = {{fusion.rrf.k_default:.0f}} with equal weights, only {{fusion.rrf.cleared:w}} of {{fusion.rrf.combinations:w}} rank-fusion
combinations clears zero. `all four` under RRF looks
like a {{fusion.all_four.rrf.gain:+.1%}} gain but its interval spans zero and it wins on {{fusion.all_four.rrf.share_positive:.1%}} of
queries, which is a coin flip. All {{fusion.wsf.cleared:w}} weighted combinations clear zero.

Reciprocal rank fusion is often presented as the safe parameter-free default,
and an earlier version of this section concluded that on this task the
parameter-free method mostly failed and the tuned one worked. But that
comparison gave weighted fusion a weight tuned on dev and RRF none, the
tuned-against-untuned comparison experiment 06 guards against for BM25. Tuning
RRF's constant k and its run weights on dev the same way, then scoring once on
test ([`fusion_rrf_tuned.md`](fusion_rrf_tuned.md)):

| combination | k | weight | fused | over better input (95% CI) | minus weighted fusion (95% CI) |
|---|---:|---:|---:|---|---|
| hybrid pt | {{fusion.hybrid_pt.rrft.k:.0f}} | {{fusion.hybrid_pt.rrft.weight:.1f}} | {{fusion.hybrid_pt.rrft.ndcg10:.4f}} | ▲ {{fusion.hybrid_pt.rrft.mean_delta:+.4f}} [{{fusion.hybrid_pt.rrft.delta_lo:+.4f}}, {{fusion.hybrid_pt.rrft.delta_hi:+.4f}}] | ▼ {{fusion.hybrid_pt.rrft.vs_wsf_mean_delta:+.4f}} [{{fusion.hybrid_pt.rrft.vs_wsf_delta_lo:+.4f}}, {{fusion.hybrid_pt.rrft.vs_wsf_delta_hi:+.4f}}] |
| hybrid en | {{fusion.hybrid_en.rrft.k:.0f}} | {{fusion.hybrid_en.rrft.weight:.1f}} | {{fusion.hybrid_en.rrft.ndcg10:.4f}} | ▲ {{fusion.hybrid_en.rrft.mean_delta:+.4f}} [{{fusion.hybrid_en.rrft.delta_lo:+.4f}}, {{fusion.hybrid_en.rrft.delta_hi:+.4f}}] | ▼ {{fusion.hybrid_en.rrft.vs_wsf_mean_delta:+.4f}} [{{fusion.hybrid_en.rrft.vs_wsf_delta_lo:+.4f}}, {{fusion.hybrid_en.rrft.vs_wsf_delta_hi:+.4f}}] |
| bilingual gemma | {{fusion.bilingual_gemma.rrft.k:.0f}} | {{fusion.bilingual_gemma.rrft.weight:.1f}} | {{fusion.bilingual_gemma.rrft.ndcg10:.4f}} | ▲ {{fusion.bilingual_gemma.rrft.mean_delta:+.4f}} [{{fusion.bilingual_gemma.rrft.delta_lo:+.4f}}, {{fusion.bilingual_gemma.rrft.delta_hi:+.4f}}] | {{fusion.bilingual_gemma.rrft.vs_wsf_mean_delta:+.4f}} [{{fusion.bilingual_gemma.rrft.vs_wsf_delta_lo:+.4f}}, {{fusion.bilingual_gemma.rrft.vs_wsf_delta_hi:+.4f}}] |
| bilingual bm25 | {{fusion.bilingual_bm25.rrft.k:.0f}} | {{fusion.bilingual_bm25.rrft.weight:.1f}} | {{fusion.bilingual_bm25.rrft.ndcg10:.4f}} | {{fusion.bilingual_bm25.rrft.mean_delta:+.4f}} [{{fusion.bilingual_bm25.rrft.delta_lo:+.4f}}, {{fusion.bilingual_bm25.rrft.delta_hi:+.4f}}] | {{fusion.bilingual_bm25.rrft.vs_wsf_mean_delta:+.4f}} [{{fusion.bilingual_bm25.rrft.vs_wsf_delta_lo:+.4f}}, {{fusion.bilingual_bm25.rrft.vs_wsf_delta_hi:+.4f}}] |
| all four | {{fusion.all_four.rrft.k:.0f}} | {{fusion.all_four.rrft.weight:.1f}}, pt {{fusion.all_four.rrft.beta:.1f}} | {{fusion.all_four.rrft.ndcg10:.4f}} | ▲ {{fusion.all_four.rrft.mean_delta:+.4f}} [{{fusion.all_four.rrft.delta_lo:+.4f}}, {{fusion.all_four.rrft.delta_hi:+.4f}}] | {{fusion.all_four.rrft.vs_wsf_mean_delta:+.4f}} [{{fusion.all_four.rrft.vs_wsf_delta_lo:+.4f}}, {{fusion.all_four.rrft.vs_wsf_delta_hi:+.4f}}] |

The weight is on the first input named, BM25 in a hybrid and Portuguese in a
bilingual pair; for `all four` it is the lexical share, with the Portuguese
share alongside, as in the weighted sweep below.

Tuned, RRF clears its better input in {{fusion.rrft.cleared:w}} of {{fusion.rrf.combinations:w}} combinations. Dev selects k between
{{fusion.rrft.k.min:.0f}} and {{fusion.rrft.k.max:.0f}} everywhere, far below the conventional {{fusion.rrf.k_default:.0f}}, which flattens the
difference between the top ranks this task depends on. Bilingual gemma selected
the smallest k in the grid, so its optimum may lie at or beyond the edge.

Weighted score fusion stays ahead: significantly for both hybrids, which is
where the recommended system lives, and indistinguishably for the other three.
So the recommendation stands, but the reason changes. Rank fusion did not fail
as a method on this task; its conventional constant did, and an untuned default
compared against a tuned alternative would have hidden that.

### The two best configurations are not separable

Comparing each configuration against a shared baseline leaves their difference
from one another undetermined, since those comparisons are correlated. Direct
paired comparisons:

| a | b | a | b | difference (95% CI) | a wins |
|---|---|---:|---:|---|---:|
| all four (wsf) | hybrid en (wsf) | {{h2h.all4wsf_vs_hybenwsf.a_score:.4f}} | {{h2h.all4wsf_vs_hybenwsf.b_score:.4f}} | {{h2h.all4wsf_vs_hybenwsf.mean_delta:+.4f}} [{{h2h.all4wsf_vs_hybenwsf.delta_lo:+.4f}}, {{h2h.all4wsf_vs_hybenwsf.delta_hi:+.4f}}] | {{h2h.all4wsf_vs_hybenwsf.share_positive:.0%}} |
| all four (wsf) | hybrid en (rrf) | {{h2h.all4wsf_vs_hybenrrf.a_score:.4f}} | {{h2h.all4wsf_vs_hybenrrf.b_score:.4f}} | ▲ {{h2h.all4wsf_vs_hybenrrf.mean_delta:+.4f}} [{{h2h.all4wsf_vs_hybenrrf.delta_lo:+.4f}}, {{h2h.all4wsf_vs_hybenrrf.delta_hi:+.4f}}] | {{h2h.all4wsf_vs_hybenrrf.share_positive:.0%}} |
| hybrid en (wsf) | bilingual gemma (wsf) | {{h2h.hybenwsf_vs_bigemmawsf.a_score:.4f}} | {{h2h.hybenwsf_vs_bigemmawsf.b_score:.4f}} | ▲ {{h2h.hybenwsf_vs_bigemmawsf.mean_delta:+.4f}} [{{h2h.hybenwsf_vs_bigemmawsf.delta_lo:+.4f}}, {{h2h.hybenwsf_vs_bigemmawsf.delta_hi:+.4f}}] | {{h2h.hybenwsf_vs_bigemmawsf.share_positive:.0%}} |
| hybrid en (rrf) | bilingual gemma (wsf) | {{h2h.hybenrrf_vs_bigemmawsf.a_score:.4f}} | {{h2h.hybenrrf_vs_bigemmawsf.b_score:.4f}} | {{h2h.hybenrrf_vs_bigemmawsf.mean_delta:+.4f}} [{{h2h.hybenrrf_vs_bigemmawsf.delta_lo:+.4f}}, {{h2h.hybenrrf_vs_bigemmawsf.delta_hi:+.4f}}] | {{h2h.hybenrrf_vs_bigemmawsf.share_positive:.0%}} |

`all four` scores higher than `hybrid en` but the difference spans zero and it
wins on only {{h2h.all4wsf_vs_hybenwsf.share_positive:.0%}} of queries. They are not distinguishable on this split.

That has a practical consequence. `hybrid en` needs one language and two
retrievers; `all four` needs two languages and four. Given no measurable
difference, the simpler system is the better recommendation.

### Fusion lifts a minority of queries, not most of them

The **wins** column is more informative than the mean. `all four` gains {{fusion.all_four.wsf.gain:.1%}} on
the mean while winning on {{fusion.all_four.wsf.share_positive:.0%}} of queries. `bilingual gemma` wins on only {{fusion.bilingual_gemma.wsf.share_positive:.0%}},
losing slightly on the majority, and still shows a significant positive mean.

That is tail recovery, and it matches experiment 12 exactly: bilingual fusion's
headroom was {{residual.embeddinggemma.pt_only_fails:.1%}} of occupations where Portuguese fails and English does not. It
cannot improve the queries that already work, and it does not try to.

### The fusion surface has an interior optimum on both axes

The four-way sweep is parameterised over two axes: how much weight goes to
lexical against dense, and how much to Portuguese against English.

| lexical \ pt | 0.0 | 0.2 | 0.4 | 0.6 | 0.8 | 1.0 |
|---|---:|---:|---:|---:|---:|---:|
| 0.0 | {{fusion.dev.all_four.w0.0.b0.0:.4f}} | {{fusion.dev.all_four.w0.0.b0.2:.4f}} | {{fusion.dev.all_four.w0.0.b0.4:.4f}} | {{fusion.dev.all_four.w0.0.b0.6:.4f}} | {{fusion.dev.all_four.w0.0.b0.8:.4f}} | {{fusion.dev.all_four.w0.0.b1.0:.4f}} |
| 0.2 | {{fusion.dev.all_four.w0.2.b0.0:.4f}} | {{fusion.dev.all_four.w0.2.b0.2:.4f}} | {{fusion.dev.all_four.w0.2.b0.4:.4f}} | {{fusion.dev.all_four.w0.2.b0.6:.4f}} | {{fusion.dev.all_four.w0.2.b0.8:.4f}} | {{fusion.dev.all_four.w0.2.b1.0:.4f}} |
| **0.4** | {{fusion.dev.all_four.w0.4.b0.0:.4f}} | **{{fusion.dev.all_four.w0.4.b0.2:.4f}}** | {{fusion.dev.all_four.w0.4.b0.4:.4f}} | {{fusion.dev.all_four.w0.4.b0.6:.4f}} | {{fusion.dev.all_four.w0.4.b0.8:.4f}} | {{fusion.dev.all_four.w0.4.b1.0:.4f}} |
| 0.6 | {{fusion.dev.all_four.w0.6.b0.0:.4f}} | {{fusion.dev.all_four.w0.6.b0.2:.4f}} | {{fusion.dev.all_four.w0.6.b0.4:.4f}} | {{fusion.dev.all_four.w0.6.b0.6:.4f}} | {{fusion.dev.all_four.w0.6.b0.8:.4f}} | {{fusion.dev.all_four.w0.6.b1.0:.4f}} |
| 0.8 | {{fusion.dev.all_four.w0.8.b0.0:.4f}} | {{fusion.dev.all_four.w0.8.b0.2:.4f}} | {{fusion.dev.all_four.w0.8.b0.4:.4f}} | {{fusion.dev.all_four.w0.8.b0.6:.4f}} | {{fusion.dev.all_four.w0.8.b0.8:.4f}} | {{fusion.dev.all_four.w0.8.b1.0:.4f}} |
| 1.0 | {{fusion.dev.all_four.w1.0.b0.0:.4f}} | {{fusion.dev.all_four.w1.0.b0.2:.4f}} | {{fusion.dev.all_four.w1.0.b0.4:.4f}} | {{fusion.dev.all_four.w1.0.b0.6:.4f}} | {{fusion.dev.all_four.w1.0.b0.8:.4f}} | {{fusion.dev.all_four.w1.0.b1.0:.4f}} |

Smooth, with a single interior peak at lexical {{fusion.all_four.weight}} and Portuguese {{fusion.all_four.beta}}. Interior
on both axes means all four runs contribute; a peak at an edge would have meant
one input was dead weight.

The Portuguese weight of {{fusion.all_four.beta}} is a deployment finding in itself. Given both texts,
the best fused system leans heavily on the English one.

### Fusion does not measurably change the language gap

| system | en | pt | gap | gap, relative |
|---|---:|---:|---:|---:|
| BM25 | {{bm25.test.en.ndcg10:.4f}} | {{bm25.test.pt.ndcg10:.4f}} | {{gap.abs.bm25:.4f}} | {{gap.rel.bm25:+.1%}} |
| EmbeddingGemma | {{bi.embeddinggemma.test.en.ndcg10:.4f}} | {{bi.embeddinggemma.test.pt.ndcg10:.4f}} | {{gap.abs.bi:.4f}} | {{gap.rel.bi:+.1%}} |
| hybrid, wsf | {{hybrid.test.en.ndcg10:.4f}} | {{hybrid.test.pt.ndcg10:.4f}} | {{gap.abs.hybrid:.4f}} | {{gap.rel.hybrid:+.1%}} |

Read off the means, adding lexical retrieval back in helps English more than
Portuguese, {{hybrid.gain_over_bi.en:+.1%}} against {{hybrid.gain_over_bi.pt:+.1%}}, and the gap rises from {{gap.abs.bi:.4f}} to {{gap.abs.hybrid:.4f}}. An
earlier version of this section concluded that fusion re-imports part of the
gap dense retrieval had removed, and that the best-performing configuration is
not the most language-equitable one. Both rested on point estimates.

The change in the gap, paired on occupation (experiment 16):

| change in the gap | mean (95% CI) |
|---|---|
| EmbeddingGemma minus BM25 | {{gap.change.dense.mean:+.4f}} [{{gap.change.dense.lo:+.4f}}, {{gap.change.dense.hi:+.4f}}] |
| hybrid minus EmbeddingGemma | {{gap.change.fusion.mean:+.4f}} [{{gap.change.fusion.lo:+.4f}}, {{gap.change.fusion.hi:+.4f}}] |
| hybrid minus BM25 | {{gap.change.hybrid_vs_bm25.mean:+.4f}} [{{gap.change.hybrid_vs_bm25.lo:+.4f}}, {{gap.change.hybrid_vs_bm25.hi:+.4f}}] |

Dense retrieval's reduction is clear. Fusion's increase is not distinguishable
from zero, and the hybrid has a smaller English lead than EmbeddingGemma on
{{gap.change.fusion.lost:.0%}} of occupations. The hybrid's gap stays clearly below BM25's, keeping about
{{gap.change.fusion_keeps:.0%}} of the reduction dense retrieval made. So fusion raises both languages
without a measurable cost in equity.

The lexical diagnosis in experiments 01 to 09 would predict some widening,
since bringing BM25 back in brings back the vocabulary-matching problem it
carries. If that widening exists, it is smaller than this split can detect: at
most about {{gap.change.fusion.hi:.3f}} nDCG@10.

For a Portuguese-only deployment the relevant number is different again: hybrid
Portuguese at {{hybrid.test.pt.ndcg10:.4f}} is {{hybrid.gain_over_bm25.pt:.1%}} above the Portuguese lexical baseline, and is the
best available without an English text.

---

## 14: Cross-encoder reranking, and the ordering ceiling

A bi-encoder embeds query and document independently, so a rare technical term
contributes a small share of one fixed vector. A cross-encoder reads the pair
together with full attention, which is the mechanism that could bridge
*puncionadora* against *prensa biela-manivela*. Reranking is therefore a
targeted test of the diagnosis as well as a standard second stage.

Two checkpoints, chosen to differ in architecture rather than only in size:

| checkpoint | licence | scoring |
|---|---|---|
| `BAAI/bge-reranker-v2-m3` | Apache 2.0 | regression head, {{model.bge.params_m:.0f}}M |
| `Qwen/Qwen3-Reranker-0.6B` | Apache 2.0 | causal LM answering yes or no |

Jina's v3.5 is smaller and stronger on BEIR but its weights are CC-BY-NC-4.0,
which rules it out for a public institution. Qwen3 has no regression head: it is
prompted to judge relevance and answer yes or no, and the score is the
probability mass on "yes". Loading it through the CrossEncoder API would attach
a randomly initialised head and produce confident-looking noise, so it has its
own scoring path, guarded by a sanity check that scores a known-relevant pair
against a known-irrelevant one before any real work.

Both rerank the hybrid weighted fusion first stage. Depth selected on a dev
subsample, applied once to test.

### Neither checkpoint beats the first stage

| checkpoint | language | first stage | reranked | gain | paired difference (95% CI) | won |
|---|---|---:|---:|---:|---|---:|
| bge-m3 | pt | {{hybrid.test.pt.ndcg10:.4f}} | {{ce.bge.pt.ndcg10:.4f}} | {{ce.bge.pt.gain:+.1%}} | {{ce.bge.pt.mean_delta:+.4f}} [{{ce.bge.pt.delta_lo:+.4f}}, {{ce.bge.pt.delta_hi:+.4f}}] | {{ce.bge.pt.won:.0%}} |
| bge-m3 | en | {{hybrid.test.en.ndcg10:.4f}} | {{ce.bge.en.ndcg10:.4f}} | {{ce.bge.en.gain:+.1%}} | {{ce.bge.en.mean_delta:+.4f}} [{{ce.bge.en.delta_lo:+.4f}}, {{ce.bge.en.delta_hi:+.4f}}] | {{ce.bge.en.won:.0%}} |
| qwen3-0.6b | pt | {{hybrid.test.pt.ndcg10:.4f}} | {{ce.qwen06.pt.ndcg10:.4f}} | {{ce.qwen06.pt.gain:+.1%}} | ▼ {{ce.qwen06.pt.mean_delta:+.4f}} [{{ce.qwen06.pt.delta_lo:+.4f}}, {{ce.qwen06.pt.delta_hi:+.4f}}] | {{ce.qwen06.pt.won:.0%}} |
| qwen3-0.6b | en | {{hybrid.test.en.ndcg10:.4f}} | {{ce.qwen06.en.ndcg10:.4f}} | {{ce.qwen06.en.gain:+.1%}} | {{ce.qwen06.en.mean_delta:+.4f}} [{{ce.qwen06.en.delta_lo:+.4f}}, {{ce.qwen06.en.delta_hi:+.4f}}] | {{ce.qwen06.en.won:.0%}} |

bge-m3 does nothing: both intervals span zero. Qwen3 is significantly worse
than not reranking at all in Portuguese, and in the same direction in English.
Neither wins on half the queries.

### Both degrade as the shortlist deepens

Dev sweep, nDCG@10:

| depth | bge pt | bge en | qwen pt | qwen en |
|---|---:|---:|---:|---:|
| 0, no rerank | {{ce.bge.dev.pt.d0:.4f}} | {{ce.bge.dev.en.d0:.4f}} | {{ce.qwen06.dev.pt.d0:.4f}} | {{ce.qwen06.dev.en.d0:.4f}} |
| 10 | {{ce.bge.dev.pt.d10:.4f}} | {{ce.bge.dev.en.d10:.4f}} | {{ce.qwen06.dev.pt.d10:.4f}} | {{ce.qwen06.dev.en.d10:.4f}} |
| 20 | {{ce.bge.dev.pt.d20:.4f}} | {{ce.bge.dev.en.d20:.4f}} | {{ce.qwen06.dev.pt.d20:.4f}} | {{ce.qwen06.dev.en.d20:.4f}} |
| 50 | {{ce.bge.dev.pt.d50:.4f}} | {{ce.bge.dev.en.d50:.4f}} | {{ce.qwen06.dev.pt.d50:.4f}} | {{ce.qwen06.dev.en.d50:.4f}} |
| 100 | {{ce.bge.dev.pt.d100:.4f}} | {{ce.bge.dev.en.d100:.4f}} | {{ce.qwen06.dev.pt.d100:.4f}} | {{ce.qwen06.dev.en.d100:.4f}} |

The more candidates a cross-encoder is allowed to reorder, the worse the
outcome, and depth selection lands on 10 and 20, the shallowest options
available.

### This is not an implementation error, and the models are not blind

A null result of this shape invites two very different explanations, and the
headline numbers cannot tell them apart. Two checks separate them.

A **random baseline** shuffles each shortlist instead of reranking it. A model
with weak but genuine signal should land between random and the first stage.
Landing at random would mean no signal; landing below random would mean an
inverted or misaligned implementation, which would make this a bug.

**Gold-versus-rest AUC** is the probability that a randomly chosen gold
candidate outscores a randomly chosen non-gold one from the same shortlist. It
sidesteps the ranking machinery entirely and asks only whether the model can
separate the two classes.

| checkpoint | language | random | reranked | first stage | recovered | AUC |
|---|---|---:|---:|---:|---:|---:|
| bge-m3 | pt | {{ce.bge.pt.random_ndcg:.4f}} | {{ce.bge.pt.ndcg10:.4f}} | {{hybrid.test.pt.ndcg10:.4f}} | {{ce.bge.pt.recovered:.0%}} | {{ce.bge.pt.auc:.3f}} |
| bge-m3 | en | {{ce.bge.en.random_ndcg:.4f}} | {{ce.bge.en.ndcg10:.4f}} | {{hybrid.test.en.ndcg10:.4f}} | {{ce.bge.en.recovered:.0%}} | {{ce.bge.en.auc:.3f}} |
| qwen3-0.6b | pt | {{ce.qwen06.pt.random_ndcg:.4f}} | {{ce.qwen06.pt.ndcg10:.4f}} | {{hybrid.test.pt.ndcg10:.4f}} | {{ce.qwen06.pt.recovered:.0%}} | {{ce.qwen06.pt.auc:.3f}} |
| qwen3-0.6b | en | {{ce.qwen06.en.random_ndcg:.4f}} | {{ce.qwen06.en.ndcg10:.4f}} | {{hybrid.test.en.ndcg10:.4f}} | {{ce.qwen06.en.recovered:.0%}} | {{ce.qwen06.en.auc:.3f}} |

Both checks come back clearly positive. Every configuration sits far above
random, and every AUC is well above chance, with mean gold scores above mean
non-gold throughout.

So the result is **not** that cross-encoder reranking fails here. The rerankers
rank competently. They reproduce between {{ce.recovered.min:.0%}} and {{ce.recovered.max:.0%}} of the ordering quality
the first stage already achieves, and then stop. An off-the-shelf reranker
matches a dev-tuned hybrid fusion without exceeding it.

Read that way, the depth degradation also makes sense. The deeper the
shortlist, the more of the fusion's ordering the reranker replaces with its own,
and since its own is no better, the result drifts down toward what its
standalone quality would give.

### A hypothesis for why they do not exceed it

The query and document shapes are inverted relative to what these rerankers are
trained on. Both are trained on short queries against long passages. Here the
query is a {{query.words_approx:.0f}}-word occupation description and the document is a skill label
plus one sentence, around {{doc.tokens_approx:.0f}} tokens.

Qwen3's own calibration is consistent with that. Its sanity check passed with a
{{ce.qwen06.sanity_margin:.0f}}-fold margin, so the scoring path is sound, but a clearly relevant pair
received P(yes) = {{ce.qwen06.sanity_p_yes:.3f}}: the model answers "no" with {{ce.qwen06.sanity_p_no:.0%}} confidence on a correct
match. Only ordering matters for ranking, so this does not invalidate the
scores, but it suggests the pairs are unlike what it was trained to judge.

This remains a hypothesis. Testing it would mean reranking with short queries,
for instance single sentences from the occupation description, and seeing
whether the models then exceed the first stage.

### The ordering headroom is enormous

The oracle sorts each shortlist by true relevance, so it is what a flawless
reranker would reach over the same candidates. No model, just a sort over the
recorded runs.

| language | first stage | oracle @10 | oracle @20 | oracle @50 | oracle @100 |
|---|---:|---:|---:|---:|---:|
| pt | {{hybrid.test.pt.ndcg10:.4f}} | {{oracle10.test.pt.ndcg10:.4f}} | {{oracle20.test.pt.ndcg10:.4f}} | {{oracle50.test.pt.ndcg10:.4f}} | {{oracle100.test.pt.ndcg10:.4f}} |
| en | {{hybrid.test.en.ndcg10:.4f}} | {{oracle10.test.en.ndcg10:.4f}} | {{oracle20.test.en.ndcg10:.4f}} | {{oracle50.test.en.ndcg10:.4f}} | {{oracle100.test.en.ndcg10:.4f}} |

Perfect ordering over a top-100 shortlist would raise nDCG@10 by **{{oracle100.gain.pt:.0%}} in
Portuguese and {{oracle100.gain.en:.0%}} in English**. Share of the headroom captured, against the oracle at each reranker's own depth:

| checkpoint | pt | en |
|---|---:|---:|
| bge-m3 | {{ce.bge.pt.captured:+.1%}} | {{ce.bge.en.captured:+.1%}} |
| qwen3-0.6b | ▼ {{ce.qwen06.pt.captured:+.1%}} | {{ce.qwen06.en.captured:+.1%}} |

That distinction matters. "Reranking did not help" and "there is nothing left to
gain from reranking" look identical in the headline number and point at
completely different work. Here the shortlist is far from exhausted, and the
rerankers that do rank competently still capture none of what is available.

### The shortlist is good; the ranking is bad

Oracle MRR at depth 10 is {{oracle10.test.pt.mrr:.3f}} in Portuguese and {{oracle10.test.en.mrr:.3f}} in English. Sorting the
top 10 by relevance puts any gold skill at rank 1, so those figures say a gold
skill is **already inside the first stage's top 10 for roughly {{oracle10.test.pt.mrr:.0%}} of Portuguese queries and {{oracle10.test.en.mrr:.0%}} of English ones**.
The measured MRR is {{hybrid.test.pt.mrr:.3f}} and {{hybrid.test.en.mrr:.3f}}. Qwen3 lowered it further, to
{{ce.qwen06.pt.mrr:.3f}} and {{ce.qwen06.en.mrr:.3f}}, and bge-m3 left it where it was.

The system finds correct answers and fails to put them first. For an interface
showing a teacher a handful of suggestions, that is the gap that matters.

### Ordering may account for part of the residual language gap

| | pt | en | gap | gap, relative | share of gap removed (95% CI) |
|---|---:|---:|---:|---:|---|
| first stage | {{hybrid.test.pt.ndcg10:.4f}} | {{hybrid.test.en.ndcg10:.4f}} | {{gap.abs.hybrid:.4f}} | {{gap.rel.hybrid:+.1%}} | |
| oracle @10 | {{oracle10.test.pt.ndcg10:.4f}} | {{oracle10.test.en.ndcg10:.4f}} | {{gap.abs.oracle10:.4f}} | {{gap.rel.oracle10:+.1%}} | {{gap.removed.oracle10.mean:.0%}} [{{gap.removed.oracle10.lo:.0%}}, {{gap.removed.oracle10.hi:.0%}}] |
| oracle @20 | {{oracle20.test.pt.ndcg10:.4f}} | {{oracle20.test.en.ndcg10:.4f}} | {{gap.abs.oracle20:.4f}} | {{gap.rel.oracle20:+.1%}} | {{gap.removed.oracle20.mean:.0%}} [{{gap.removed.oracle20.lo:.0%}}, {{gap.removed.oracle20.hi:.0%}}] |
| oracle @50 | {{oracle50.test.pt.ndcg10:.4f}} | {{oracle50.test.en.ndcg10:.4f}} | {{gap.abs.oracle50:.4f}} | {{gap.rel.oracle50:+.1%}} | {{gap.removed.oracle50.mean:.0%}} [{{gap.removed.oracle50.lo:.0%}}, {{gap.removed.oracle50.hi:.0%}}] |
| oracle @100 | {{oracle100.test.pt.ndcg10:.4f}} | {{oracle100.test.en.ndcg10:.4f}} | {{gap.abs.oracle100:.4f}} | {{gap.rel.oracle100:+.1%}} | {{gap.removed.oracle100.mean:.0%}} [{{gap.removed.oracle100.lo:.0%}}, {{gap.removed.oracle100.hi:.0%}}] |

Intervals are paired on occupation, with the first stage's gap and the oracle's
resampled on the same queries (experiment 16).

This speaks directly to the residual experiment 12 left unexplained. The
Portuguese shortlist contains nearly as much gold as the English one, recall@100
of {{shortlist.pt.recall100:.3f}} against {{shortlist.en.recall100:.3f}}, a {{shortlist.recall100.ratio:.1%}} difference. Give both perfect ordering of the top
100 and the absolute gap falls from {{gap.abs.hybrid:.4f}} to {{gap.abs.oracle100:.4f}}, a point estimate of {{gap.removed.oracle100.mean:.0%}}.
The interval runs from {{gap.removed.oracle100.lo:.0%}} to {{gap.removed.oracle100.hi:.0%}}: perfect ordering may remove up to about half of
the gap at depth 100, but the effect is not distinguishable from zero on this
split.

**Correction.** This section originally said most of the residual gap was
ordering, because the relative gap falls from {{gap.rel.hybrid:.1%}} to {{gap.rel.oracle100:.1%}}. That reading was
wrong. Perfect ordering more than doubles both scores, so the relative gap
shrinks even where the distance between the languages barely moves. A later
version said ordering accounts for about a third of the residual in absolute
terms. That was a point estimate, and the paired interval includes zero at
every depth. At a depth of 20, perfect ordering leaves the gap where it was,
which experiment 15 confirms from the other side.

### Cost

| checkpoint | language | depth | pairs scored | ms/query |
|---|---|---:|---:|---:|
| bge-m3 | pt | {{ce.bge.pt.depth:.0f}} | {{ce.bge.pt.pairs:,.0f}} | {{ce.bge.pt.ms_per_query:.1f}} |
| bge-m3 | en | {{ce.bge.en.depth:.0f}} | {{ce.bge.en.pairs:,.0f}} | {{ce.bge.en.ms_per_query:.1f}} |
| qwen3-0.6b | pt | {{ce.qwen06.pt.depth:.0f}} | {{ce.qwen06.pt.pairs:,.0f}} | {{ce.qwen06.pt.ms_per_query:.1f}} |
| qwen3-0.6b | en | {{ce.qwen06.en.depth:.0f}} | {{ce.qwen06.en.pairs:,.0f}} | {{ce.qwen06.en.ms_per_query:.1f}} |

On the same {{ce.bge.en.pairs:,.0f}} pairs in English, Qwen3 is about {{ce.qwen_over_bge.en.ms:.1f}} times slower than bge and
scores lower. Added to what the first stage already costs, both
are expensive for no gain. A cross-encoder scores every pair individually, so
nothing is precomputed and cost scales directly with depth.

### What this experiment concludes

Cross-encoder reranking is not worth its cost on this task, and the reason is
specific rather than general. The rerankers work: they separate gold from non-gold well above
chance and reproduce {{ce.recovered.min:.0%}} to {{ce.recovered.max:.0%}} of the first stage's ordering quality. They
simply do not improve on a hybrid fusion that was already tuned on dev, while
adding {{ce.ms.min:.0f}} to {{ce.ms.max:.0f}} ms per query.

Meanwhile the oracle says perfect ordering of the same candidates would more
than double the score. The ordering problem is large, real, and untouched by
off-the-shelf cross-encoders.

---

## 15: Listwise LLM reranking, local and API

The cross-encoders in experiment 14 score each candidate on its own, and did no
better than the first stage's ordering. A listwise reranker gets the occupation
description and the whole shortlist in one prompt and returns the numbers of the
10 best candidates, so it can compare candidates against each other, which a
pointwise model cannot. Whether that is what makes the difference is a separate
question, taken up after the results.

The model answers with candidate numbers, never skill names, so a malformed
response is an out-of-range number, a repeat or an omission, and each is
counted. Candidates the model leaves out keep their first-stage order below the
ones it ranked.

Two models run behind the same interface: `Qwen3-4B-Instruct-2507` on a local
12 GB GPU, and DeepSeek through its API. DeepSeek is the model the 2024 thesis
used for this stage. `deepseek-chat` is an alias the provider repoints, and the
run reported here was served by `deepseek-flash` on {{deepseek.run_date:date}}.

Depth was chosen on {{llm.dev_queries:.0f}} dev queries between shortlists of 10 and 20. A depth of
50 crashed the local machine even at batch size 2, so it was not tested.

### Results

| language | first stage | Qwen3-4B | DeepSeek | bge-m3 (exp. 14) |
|---|---:|---:|---:|---:|
| pt | {{hybrid.test.pt.ndcg10:.4f}} | {{qwen.test.pt.ndcg10:.4f}} (▲ {{qwen.gain.pt:+.1%}}) | **{{deepseek.test.pt.ndcg10:.4f}} (▲ {{deepseek.gain.pt:+.1%}})** | {{ce.bge.pt.ndcg10:.4f}} |
| en | {{hybrid.test.en.ndcg10:.4f}} | {{qwen.test.en.ndcg10:.4f}} (▲ {{qwen.gain.en:+.1%}}) | **{{deepseek.test.en.ndcg10:.4f}} (▲ {{deepseek.gain.en:+.1%}})** | {{ce.bge.en.ndcg10:.4f}} |

nDCG@10 on the {{split.test.queries:.0f}} test queries. Dev selected depth 20 for both models in both
languages. Paired against the first stage, Qwen gains {{qwen.test.pt.mean_delta:+.4f}} [{{qwen.test.pt.delta_lo:+.4f}},
{{qwen.test.pt.delta_hi:+.4f}}] in Portuguese and {{qwen.test.en.mean_delta:+.4f}} [{{qwen.test.en.delta_lo:+.4f}}, {{qwen.test.en.delta_hi:+.4f}}] in English; DeepSeek's
paired intervals are in [`llm_rerank_deepseek.md`](llm_rerank_deepseek.md), and
its margin over Qwen is tested directly in experiment 16.

Selection on dev did not overfit. Qwen's gain went from {{qwen.dev_gain.pt:+.1%}} on dev to {{qwen.gain.pt:+.1%}}
on test in Portuguese and from {{qwen.dev_gain.en:+.1%}} to {{qwen.gain.en:+.1%}} in English; DeepSeek's from {{deepseek.dev_gain.pt:+.1%}}
to {{deepseek.gain.pt:+.1%}} and from {{deepseek.dev_gain.en:+.1%}} to {{deepseek.gain.en:+.1%}}.

This is the first method in the project to improve on the tuned hybrid. Both
models were given the same 20 candidates the cross-encoders saw, so the
difference is in what the model does with them.

**What this does not establish** is that listwise scoring is the reason. The
cross-encoders are much smaller models, trained as rerankers; the listwise
models are a 4B instruction-tuned model and a far larger API model, from
different families and trained for different tasks. Model size, family and
training are confounded with listwise against pointwise, so the gain cannot yet
be attributed to comparing candidates with each other. The control is
`Qwen3-Reranker-4B`: built on the same Qwen3 4B base as the local listwise
model, scoring one pair at a time, through the scoring path experiment 14
already uses for its smaller sibling. Until it is run, the listwise explanation is
a hypothesis.

### Headroom captured

A reranker that sees 20 candidates cannot recover a skill ranked 21st, so the
fair ceiling is the oracle at depth 20: {{oracle20.test.pt.ndcg10:.4f}} in Portuguese, {{oracle20.test.en.ndcg10:.4f}} in English.

| model | pt | en |
|---|---:|---:|
| Qwen3-4B | {{qwen.captured.pt:.0%}} | {{qwen.captured.en:.0%}} |
| DeepSeek | **{{deepseek.captured.pt:.0%}}** | **{{deepseek.captured.en:.0%}}** |

### Output reliability

Neither model returned an unparsable response in either language. Qwen repeated
or dropped a candidate in about one query in a hundred in Portuguese and in
{{qwen.test.en.duplicate_queries:w}} of {{split.test.queries:.0f}} in English. DeepSeek's repair counts are in its generated file.

### Reproducibility

Qwen decodes greedily and reproduced its test scores exactly across runs at the
same batch size. Batch size itself matters: it changes padding, and therefore
fp16 rounding, which moved one dev figure from {{qwen.dev.pt.d10:.4f}} to {{qwen.dev.pt.d10.other_batch:.4f}}.

DeepSeek is not deterministic at temperature 0. Two identical runs scored
{{deepseek.rerun.pt:.4f}} and {{deepseek.test.pt.ndcg10:.4f}} in Portuguese, {{deepseek.rerun.en:.4f}} and {{deepseek.test.en.ndcg10:.4f}} in English. That drift is
about a twentieth of its lead over Qwen, so it does not affect any conclusion,
but the exact figures cannot be reproduced.

### A silent slowdown worth recording

At depth 20 a batch of {{qwen.slow.batch:.0f}} prompts does not fit on a 12 GB card. Under WSL the
driver does not raise an out-of-memory error; it moves the overflow into system
RAM. Generation slowed from {{qwen.slow.s_per_query.before:.2f}} s/query to over {{qwen.slow.s_per_query.alone:.0f}} running alone, and to {{qwen.slow.s_per_query.shared:.2f}}
alongside another job, with no error at all.
`nvidia-smi` showed memory at {{qwen.slow.gpu_mem_used_gb:.1f}} of {{qwen.slow.gpu_mem_total_gb:.1f}} GB and the GPU at {{qwen.slow.gpu_watts:.0f}} W of {{qwen.slow.gpu_watts_max:.0f}} W,
busy waiting for data. A batch of {{qwen.batch:.0f}} fits, and is now the default.

### Cost

| model | s/query on test | money |
|---|---:|---:|
| Qwen3-4B, laptop RTX 5070 | {{qwen.s_per_query.min:.1f}} to {{qwen.s_per_query.max:.1f}} | none per query |
| DeepSeek, 8 concurrent requests | {{deepseek.s_per_query.max:.2f}} | ${{deepseek.cost_usd:.2f}} for the experiment |

The ${{deepseek.cost_usd:.2f}} covers the whole experiment: {{llm.prompts:,.0f}} prompts across the dev sweep and
the test split in both languages, about ${{deepseek.cost_per_prompt:.4f}} per description. Local timings
varied between runs of identical work ({{qwen.earlier_run.pt.s_per_query:.2f}} and {{qwen.test.pt.s_per_query:.2f}} s/query for the same
Portuguese test split), so the speed ratio is approximate.

Portuguese prompts are {{deepseek.prompt_ratio:.0%}} to {{qwen.prompt_ratio:.0%}} longer in tokens than English ones under both
tokenisers ({{deepseek.test.pt.prompt_tokens:,.0f}} against {{deepseek.test.en.prompt_tokens:,.0f}} for DeepSeek on test), so on a paid API
Portuguese costs more per description. Longer Portuguese descriptions and
English-centred tokenisers both contribute, and this experiment does not
separate them.

---

## 16: Local against API, per query

Both models reranked the same first stage at the same depth on the same {{split.test.queries:.0f}}
queries, so the comparison is paired.

| language | DeepSeek minus Qwen3-4B, nDCG@10 (95% CI) |
|---|---|
| pt | ▲ {{llm.ds_minus_qwen.pt.mean:+.4f}} [{{llm.ds_minus_qwen.pt.lo:+.4f}}, {{llm.ds_minus_qwen.pt.hi:+.4f}}] |
| en | ▲ {{llm.ds_minus_qwen.en.mean:+.4f}} [{{llm.ds_minus_qwen.en.lo:+.4f}}, {{llm.ds_minus_qwen.en.hi:+.4f}}] |

DeepSeek is better in both languages, by about as much as Qwen gains over the
first stage.

### Neither model narrows the language gap

Every occupation exists in both languages, so the gap can be measured per
occupation, English minus Portuguese, and compared between systems as a
difference of differences.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="figures/language_gap_dark.svg">
  <img alt="English minus Portuguese nDCG@10 per system, with paired intervals for the hybrid and both rerankers, and the perfect-ordering gaps at depth 20 and 100." src="figures/language_gap_light.svg">
</picture>

| system | EN minus PT (95% CI) | relative |
|---|---|---:|
| first stage | {{llm.gap.hybrid.mean:+.4f}} [{{llm.gap.hybrid.lo:+.4f}}, {{llm.gap.hybrid.hi:+.4f}}] | {{gap.rel.hybrid:+.1%}} |
| Qwen3-4B | {{llm.gap.qwen.mean:+.4f}} [{{llm.gap.qwen.lo:+.4f}}, {{llm.gap.qwen.hi:+.4f}}] | {{gap.rel.qwen:+.1%}} |
| DeepSeek | {{llm.gap.deepseek.mean:+.4f}} [{{llm.gap.deepseek.lo:+.4f}}, {{llm.gap.deepseek.hi:+.4f}}] | {{gap.rel.deepseek:+.1%}} |

| change in the gap | 95% CI |
|---|---|
| Qwen3-4B minus first stage | {{llm.gap.change.qwen.mean:+.4f}} [{{llm.gap.change.qwen.lo:+.4f}}, {{llm.gap.change.qwen.hi:+.4f}}] |
| DeepSeek minus first stage | {{llm.gap.change.deepseek.mean:+.4f}} [{{llm.gap.change.deepseek.lo:+.4f}}, {{llm.gap.change.deepseek.hi:+.4f}}] |
| DeepSeek minus Qwen3-4B | {{llm.gap.change.ds_minus_qwen.mean:+.4f}} [{{llm.gap.change.ds_minus_qwen.lo:+.4f}}, {{llm.gap.change.ds_minus_qwen.hi:+.4f}}] |

The relative gap falls from {{gap.rel.hybrid:.1%}} to {{gap.rel.deepseek:.1%}} under DeepSeek, which reads like
narrowing. In absolute terms the gap is unchanged: the same distance divided by
a higher Portuguese score. The first reading of these results made exactly that
mistake, and this experiment was written to test it.

The null result is what experiment 14's oracle predicts. At depth 20, perfect
ordering would not narrow the gap either.

### What the two experiments conclude

Paying bought quality as well as speed: about {{llm.ds_minus_qwen.pt.mean:.2f}} nDCG@10 in both languages,
roughly double the local model's gain over the first stage, at more than ten
times the speed, for ${{deepseek.cost_usd:.2f}}. The local model is free per query, reproduces
exactly, and keeps course documentation on the institution's own hardware,
which may matter more than the score in a university deployment.

Neither changes the language gap. Whatever puts Portuguese behind English is
already fixed by the time the shortlist reaches the reranker.

---

## Where this leaves the central question

The project set out to ask whether dense retrieval could compensate for a {{data.alt_ratio.skills:.1f}}x
deficit in Portuguese alternative labels. Measurement changed the question twice
and then answered it.

**The label deficit was not the main effect.** It is worth about a fifth of
English's lexical quality when retrieval runs over labels alone, but the gap
persists on description-only retrieval where both languages have complete
coverage.

**The residual is a tail phenomenon, not a uniform deficit.** Candidates tested:

| candidate | verdict |
|---|---|
| Missing alternative labels | Accounts for the `labels` gap, not the `description` gap |
| Translation drift, measured in aggregate | Not supported, in any rarity band (03, 09) |
| Portuguese stemmer under-conflates | Not supported. It conflates at least as much (03) |
| Function word density | Real. About a quarter of the gap, corrected (04, 05) |
| Length normalisation | Negligible. Surfaces flat across `b` (06) |
| Lexical impoverishment from translation | Not supported. Portuguese vocabulary is larger (06) |
| Compressed score distribution | Not supported. Flatness identical (07) |
| Terminology divergence in a tail of queries | Supported (07, 08), and confirmed by 10 and 11 |

**Dense retrieval removes about half of it, in the way the diagnosis
predicted.** The gap falls from {{gap.rel.bm25:.1%}} to {{gap.rel.bi:.1%}}, or from {{gap.abs.bm25:.3f}} to {{gap.abs.bi:.3f}} nDCG@10 in
absolute terms, the Portuguese failure rate from {{perquery.bm25.pt.failure_rate:.1%}} to {{perquery.embeddinggemma.pt.failure_rate:.1%}},
and the gains concentrate in exactly the queries where lexical matching failed.
A method that had improved the mean while leaving the distribution shape
unchanged would have been doing something else.

**Fusion adds quality without measurably moving the gap.** Combining lexical
with dense retrieval is the best-scoring first stage, {{hybrid.test.en.ndcg10:.4f}} in English and
{{hybrid.test.pt.ndcg10:.4f}} in Portuguese. Read off the means it helps English more, and the relative
gap rises to {{gap.rel.hybrid:.1%}}, which earlier versions reported as fusion widening the gap
again. Paired on occupation the change is {{gap.change.fusion.mean:+.4f}} [{{gap.change.fusion.lo:+.4f}}, {{gap.change.fusion.hi:+.4f}}], so that
reading rested on point estimates.

**Ordering may account for part of the residual.** Experiment 12 showed it is
uniform across the score distribution rather than concentrated in a tail, so the
terminology explanation does not carry over. Experiment 14 finds the Portuguese
shortlist contains nearly as much gold as the English one, recall@100 of {{shortlist.pt.recall100:.3f}}
against {{shortlist.en.recall100:.3f}}. Perfect ordering of the top 100 may remove up to about half of
the absolute gap, but the effect is not distinguishable from zero on this split
({{gap.removed.oracle100.mean:.0%}}, [{{gap.removed.oracle100.lo:.0%}}, {{gap.removed.oracle100.hi:.0%}}]). The residual is unexplained.

**LLM reranking lifts both languages by the same amount.** Listwise reranking is
the only reranking method here that beats the first stage, by about {{qwen.gain.mean:.0%}} with a
local 4B model and {{deepseek.gain.en:.0%}} to {{deepseek.gain.pt:.0%}} with DeepSeek. Neither moves the gap, and at the
depth they work at, the oracle says no reranker could.