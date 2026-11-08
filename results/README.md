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

Also here: [`dataset_profile.md`](dataset_profile.md) and
[`split_profile.md`](split_profile.md), describing the release and the frozen
evaluation split.

## Current best

608 held-out occupation descriptions against all 13,939 skills, nDCG@10.

The headline number is not the most important one here. Experiment 14 measures
what a flawless reranker would reach over the same top-100 candidates: **0.797
Portuguese and 0.821 English**, more than double the best system. The shortlist
already contains a correct skill in its top 10 for roughly 91% of queries. The
unsolved problem is ordering, not retrieval.

| system | English | Portuguese | gap |
|---|---:|---:|---:|
| BM25, stemmed, stopwords removed | 0.3252 | 0.2659 | +22.3% |
| Bi-encoder, `embeddinggemma-300m` | 0.3576 | 0.3284 | +8.9% |
| **Hybrid, weighted score fusion** | **0.3794** | **0.3439** | +10.3% |

The recommended configuration is hybrid weighted score fusion, combining BM25
with the bi-encoder in one language. Fusing all four runs, both methods in both
languages, scores marginally higher at 0.3817 but is not distinguishable from it
(paired difference +0.0023 [−0.0010, +0.0056]), so the simpler system is
preferred.

Recall@10 is capped at 0.543 on this split, so the leading figure of 0.155 is
29% of what is reachable.

Two things the headline table does not show. Dense retrieval closed 60% of the
lexical language gap by compressing a tail of failing Portuguese queries, and
fusion then widened it again, because lexical retrieval helps English more.

---

## Reading the numbers

**Recall@k is capped well below 1.** Occupations carry around 22 essential
skills on average and only 10 fit in a top-10, so the highest recall@10
achievable on this split is **0.543**. A recall@10 of 0.145 is 27% of what is
reachable.

| k | 1 | 3 | 5 | 10 | 20 | 50 |
|---|---:|---:|---:|---:|---:|---:|
| max recall@k | 0.056 | 0.167 | 0.278 | 0.543 | 0.856 | 0.993 |

**Precision and MRR answer different questions.** The best English run has P@10
of 0.270, so most of what it shows is wrong, alongside MRR of 0.678, meaning the
first genuinely essential skill usually appears at rank 1 or 2 out of 13,939
candidates. Retrieval finds one correct skill easily and the full set poorly,
and which of those matters depends on the interface.

---

## 01: BM25 lexical baseline

608 test occupations, full index, 16 conditions covering 2 languages, 4 document
variants and stemmed against unstemmed. No stopword removal, which experiment 05
later revised.

### The alternative-label asymmetry behaves as predicted

Adding ESCO's alternative labels to the preferred label transforms the English
index and does nothing measurable for Portuguese:

| | preferred | plus alt labels | change | tokens/doc |
|---|---:|---:|---:|---|
| pt, raw | 0.163 | 0.162 | −0.5% | 4.9 to 6.1 |
| en, raw | 0.189 | 0.227 | +20.1% | 3.6 to 29.3 |

English documents grow eightfold. Portuguese documents grow by roughly one
token, because only 8% of Portuguese skills carry any alternative label. The
23.8x label asymmetry recorded in the dataset profile is worth a fifth of
English lexical retrieval quality, and Portuguese cannot access any of it.

### The label gap does not account for the whole deficit

On document variants where ESCO treats both languages equally, Portuguese has
more text and still scores lower:

| condition | pt tokens | en tokens | pt nDCG@10 | en nDCG@10 | en advantage |
|---|---:|---:|---:|---:|---:|
| preferred, raw | 4.9 | 3.6 | 0.163 | 0.189 | +15.8% |
| description, raw | 25.2 | 22.2 | 0.188 | 0.230 | +22.4% |
| description, stemmed | 25.2 | 22.2 | 0.208 | 0.258 | +24.3% |

Portuguese preferred labels are 36% longer than English ones and score 16%
lower. Descriptions are 14% longer and score 24% lower. Every interval is
disjoint. A shortage of text does not explain this, which rules out the original
framing of the project's central question. Experiments 03 to 05 pursue the
cause.

### Stemming helps, and helps English more on short fields

Relative nDCG@10 gain from stemming, before stopword removal:

| variant | pt | en |
|---|---:|---:|
| preferred | +13.5% | +23.3% |
| labels | +13.5% | +11.6% |
| labels_desc | +6.9% | +5.7% |
| description | +10.6% | +12.3% |

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
| Index contents | all 13,939 skills | all 13,939 skills |
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
   scale rather than by a constant: under `labels` the English mean is 29.3
   tokens against 6.1 in Portuguese.
3. **`epsilon = 0.25` floors negative IDF values.** Terms appearing in more than
   half the corpus get a small positive score rather than a negative one. How
   often the floor is hit depends on term distribution, which differs between
   corpora. Not measured.

No parameter tuning has been done in either language.

### Cost

26 to 50 ms per query, index build under 7 s, everything in memory. Any method
costing materially more should be judged on quality per unit latency.

---

## 02: Quality by gold set size

The benchmark queries occupations carrying a mean of 22 essential skills. The
target application queries learning outcomes carrying 1 to 3. If method
behaviour shifts as gold sets shrink, the benchmark is a poor proxy. This slices
the recorded per-query results from experiment 01 into gold-size quartiles. No
retrieval is re-run.

| bucket | queries | essential skills | median | max recall@10 |
|---|---:|---|---:|---:|
| Q1 smallest | 159 | 6 to 14 | 12 | 0.861 |
| Q2 | 163 | 15 to 20 | 18 | 0.577 |
| Q3 | 139 | 21 to 27 | 24 | 0.419 |
| Q4 largest | 147 | 28 to 74 | 34 | 0.279 |

### The English advantage is uniform across gold set sizes

nDCG@10:

| bucket | pt | en | en advantage |
|---|---|---|---:|
| Q1 smallest | 0.237 [0.210, 0.265] | 0.308 [0.277, 0.339] | +29.7% |
| Q2 | 0.247 [0.215, 0.278] | 0.310 [0.275, 0.344] | +25.4% |
| Q3 | 0.224 [0.196, 0.254] | 0.289 [0.261, 0.318] | +28.9% |
| Q4 largest | 0.281 [0.250, 0.314] | 0.330 [0.296, 0.364] | +17.2% |

English leads in all four buckets, by between 17% and 30%, with no trend as gold
sets grow. Each bucket holds around 150 queries, so intervals are wider than the
pooled comparison and two buckets do not separate individually. The evidence is
the consistency of direction and magnitude across four independent buckets. The
pooled 608-query comparison separates the two languages cleanly.

### nDCG is flat across buckets; recall and precision are not

English nDCG@10 runs 0.289 to 0.330 with no trend, because nDCG normalises by
the ideal ranking and so places a query with 6 gold and one with 74 on the same
scale.

Recall@10 falls from 0.188 to 0.076 across the buckets while precision@10 rises
from 0.208 to 0.271. Neither reflects the method changing. The recall ceiling
drops from 0.861 to 0.279 over the same range, and more gold means more chances
for any slot to hit. Raw recall and precision are not comparable across buckets.

### Bearing on the query shape limitation

Q1, with a median of 12 essential skills, is the closest available
approximation to learning outcome density. Performance there matches the pooled
figures: English 0.308 against 0.309 pooled, Portuguese 0.237 against 0.248.

Method behaviour is stable as gold sets shrink toward the target task, across
the range this benchmark can test. Query length remains untested, since all
queries here are full occupation descriptions.

---

## 03: How much vocabulary do queries share with their gold skills?

BM25 can only score a match on tokens present on both sides. If Portuguese
occupation descriptions share less vocabulary with their gold skills, that is
the mechanism behind the retrieval gap. Measures the share of an occupation's
gold-skill vocabulary that appears in its description. No retrieval is run.

| field | stemming | pt | en |
|---|---|---|---|
| description | raw | 0.0798 [0.0770, 0.0830] | 0.0789 [0.0758, 0.0822] |
| description | stemmed | 0.1051 [0.1015, 0.1090] | 0.0982 [0.0946, 0.1021] |
| labels | raw | 0.1654 [0.1597, 0.1710] | 0.0912 [0.0880, 0.0945] |
| labels | stemmed | 0.2146 [0.2071, 0.2218] | 0.1245 [0.1200, 0.1289] |

On `description`, where the gold vocabularies are comparable in size (271 tokens
Portuguese against 257 English), Portuguese overlap is equal on raw tokens and
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
descriptions by 31.7% against English's 24.5%, and shrinks the gold vocabulary
by 12.5% against 11.7%. The Portuguese stemmer conflates at least as much.

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
| type coverage | 0.0798 | 0.0789 | 0.1051 | 0.0982 |
| IDF-weighted | 0.0481 | **0.0534** | 0.0687 | **0.0702** |
| content-only | 0.0424 | **0.0506** | 0.0616 | **0.0636** |

**The ranking inverts.** Portuguese leads on token counts and loses on both
weighted measures. Equal vocabulary overlap, less usable signal.

Content-only coverage removes each corpus's 50 most frequent terms. Doing so
costs Portuguese 47% of its raw overlap against English's 36%, so nearly half of
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

`utiliz` at 2,591 and `use` at 2,691 are the same content word at almost
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
| preferred | raw | +35.0% | +33.6% |
| preferred | stemmed | +26.7% | +24.3% |
| labels | raw | +36.4% | +20.4% |
| labels | stemmed | +29.1% | +14.2% |
| labels_desc | raw | +8.9% | +6.2% |
| labels_desc | stemmed | +7.4% | +5.1% |
| description | raw | +13.4% | +7.5% |
| description | stemmed | +10.2% | +4.7% |

Portuguese gains more in every case. On `description` stemmed, more than twice
as much.

### The gap narrows everywhere, but does not close

English advantage in nDCG@10:

| documents | stemming | stops kept | stops removed | change |
|---|---|---:|---:|---:|
| preferred | raw | +15.8% | +14.6% | −1.2 pp |
| preferred | stemmed | +25.8% | +23.4% | −2.4 pp |
| labels | raw | +39.8% | +23.4% | −16.4 pp |
| labels | stemmed | +37.5% | +21.7% | −15.8 pp |
| labels_desc | raw | +26.4% | +23.3% | −3.1 pp |
| labels_desc | stemmed | +25.0% | +22.3% | −2.7 pp |
| description | raw | +22.4% | +16.0% | −6.4 pp |
| description | stemmed | +24.3% | +18.2% | −6.1 pp |

On `description` stemmed, the fairest comparison available, preprocessing
accounted for roughly a quarter of the gap: 6.1 points of 24.3. The remaining
18.2% persists with disjoint intervals.

### Confirmation in the token counts

Share of tokens removed as stopwords:

| documents | pt | en |
|---|---:|---:|
| preferred | 30.6% | 11.1% |
| labels | 29.5% | 15.4% |
| labels_desc | 39.0% | 24.9% |
| description | 41.3% | 37.4% |

Portuguese carries more function-word mass in every variant. The `preferred`
row is the most striking: nearly a third of a Portuguese skill label is
stopwords, against a ninth in English.

### What this settles

The absence of a stopword list was a genuine confound and a mistake in
experiment 01's configuration. It cost both languages performance and cost
Portuguese more. Correcting it changes the headline figures and narrows the gap
by about a quarter.

It does not explain the remainder. After correction, English still leads by
18.2% on the description variant where both languages have complete coverage,
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

42 grid points per language on 2,431 dev queries, `labels_desc`, stemmed,
stopwords removed.

### Tuning buys nothing

| language | selected | dev nDCG@10 | test tuned | test default | gain |
|---|---|---:|---:|---:|---:|
| pt | k1=1.8, b=0.75 | 0.2802 | 0.2658 | 0.2658 | 0.0% |
| en | k1=2.1, b=1.0 | 0.3356 | 0.3273 | 0.3252 | +0.7% |

Both gains sit far inside the confidence intervals. The library defaults were
already essentially optimal for this corpus.

This is a useful negative result. The lexical floor reported here is properly
calibrated rather than arbitrary, so the dense comparison that follows cannot be
dismissed as tuned-against-untuned. The reported baseline stays at the defaults,
since tuned parameters would add a configuration to explain for no measurable
return.

### Length normalisation is not the residual

The dev surfaces are nearly flat across the useful range of `b`. Portuguese
peaks at 0.75, with 0.9 giving 0.2787 and 1.0 giving 0.2761. English peaks at
1.0, with 0.9 at 0.3349 and 0.75 at 0.3334. Moving `b` between 0.75 and 1.0
changes nDCG@10 by under 0.005 in either language, against a language gap of
roughly 0.06.

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
| description | raw | 17,315 | 15,349 |
| description | stemmed | 9,517 | 8,930 |
| labels | raw | 7,694 | 12,369 |
| labels | stemmed | 5,336 | 7,609 |

On `description`, Portuguese vocabulary is **larger**, by 13% raw and 7%
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
| pt | 3.167 | 14.1 | 1 | 0.271 |
| en | 3.817 | 6.9 | 1 | 0.276 |

English gold sits 20.5% further above the field. Flatness is identical, so the
Portuguese score distribution is not compressed and the problem is not that
ordering is decided by noise.

**The medians are identical and the means differ by a factor of two.** On a
typical query both languages place a gold skill at rank 2. The distributions
separate only in the tail:

| percentile | en | pt |
|---|---:|---:|
| 50th | 1 | 1 |
| 75th | 4 | 6 |
| 90th | 15 | 23 |
| 95th | 27 | 58 |
| 99th | 80 | 223 |
| max | 586 | 1162 |

Roughly 90% of Portuguese queries behave much like English ones. The aggregate
gap is produced by the worst 5 to 10%.

This also explains a pattern visible since experiment 01: MRR was always the
closest metric between the two languages, 0.524 against 0.611, because MRR
depends on the first hit, which is where the medians agree. nDCG@10 and recall@10
showed larger gaps because they depend on the whole top of the list, which is
where the tail damage lands.

Per-query counts of non-gold skills outranking the best gold skill correlate
0.321 between the two languages. That statistic is a heavily skewed count
ranging to 1,162, so it overstates the independence: correlating nDCG@10 on the
same queries gives 0.737. The languages fail together more often than they fail
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
at rank 2 with a score of 67.99. In Portuguese the same gold skill shares no
tokens with the query at all, the best gold skill falls to rank 478, and the top
of the ranking fills with *prensa hidráulica*, *prensa de forjar* and
*peças de máquinas de soldadura por pontos*, the last matching on *ponto morto*.

The move coordinator case adds a second effect. *Mudança* also means "change",
so the Portuguese ranking is led by *adaptar-se à mudança* and
*promover a mudança social*. A term that is unambiguous in English is polysemous
in translation.

These eight cases are selected as the worst failures and are not a sample.

### 09: the divergence is real but too rare to show in aggregate

If terminology divergence were widespread, it should appear as lower Portuguese
coverage on rare, high-IDF terms, since those carry most of a BM25 score and are
where a translator has genuine choice. Common words translate consistently
because there is one obvious rendering.

Coverage of gold vocabulary, banded by how many skills a term appears in:

| band | pt | en | pt gold terms | en gold terms |
|---|---|---|---:|---:|
| df 1 | 0.0159 [0.0095, 0.0235] | 0.0140 [0.0085, 0.0204] | 5 | 6 |
| df 2 to 5 | 0.0312 [0.0244, 0.0391] | 0.0237 [0.0179, 0.0305] | 9 | 10 |
| df 6 to 50 | 0.0447 [0.0413, 0.0482] | 0.0452 [0.0412, 0.0493] | 52 | 53 |
| df 51+ | 0.0794 [0.0761, 0.0828] | 0.0719 [0.0690, 0.0749] | 153 | 176 |

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
| embeddinggemma | en | labels_desc | 0.3576 | [0.3419, 0.3744] | 0.678 | +10.0% |
| qwen3-4b | en | preferred | 0.3203 | [0.3038, 0.3361] | 0.604 | −1.5% |
| e5-base | en | labels_desc | 0.3145 | [0.2987, 0.3307] | 0.634 | −3.3% |
| embeddinggemma | pt | labels_desc | 0.3284 | [0.3122, 0.3448] | 0.640 | +23.5% |
| qwen3-4b | pt | preferred | 0.3026 | [0.2862, 0.3185] | 0.567 | +13.8% |
| e5-base | pt | labels_desc | 0.2630 | [0.2466, 0.2784] | 0.551 | −1.1% |

### Dense retrieval closes most of the language gap

| method | pt | en | en advantage |
|---|---:|---:|---:|
| BM25 | 0.2658 | 0.3252 | +22.3% |
| e5-base | 0.2630 | 0.3145 | +19.6% |
| embeddinggemma | 0.3284 | 0.3576 | +8.9% |
| qwen3-4b | 0.3026 | 0.3203 | +5.9% |

This answers the project's central question. EmbeddingGemma removes 60% of the
lexical language gap, from 22.3% to 8.9%, and removes it asymmetrically:
Portuguese gains 23.5% over BM25 while English gains 10.0%.

Qwen3 shows the smallest gap at 5.9%, a 74% reduction, but that is not the
better result. It is worse than EmbeddingGemma in both languages, 0.3203 against
0.3576 in English and 0.3026 against 0.3284 in Portuguese, so its narrower gap
comes from degrading the stronger language rather than from lifting the weaker
one. A small language gap is only meaningful read alongside the absolute
scores.

A study reporting only a pooled figure across languages would have concluded
that dense retrieval offers a modest 10% improvement, and would have missed that
it does substantially different work in each language.

### A 308M model beats a 4B one

EmbeddingGemma leads Qwen3-Embedding-4B by 11.6% in English and 8.5% in
Portuguese, at a thirteenth of the parameters, a third of the index size and
768 dimensions against 2560.

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

Qwen3 is *worse* with more context: 0.2973 on the preferred label alone against
0.2600 with labels and description. The other two prefer the fuller text, as
BM25 does. Anyone deploying this cannot assume a document representation
transfers between checkpoints.

Qwen3 also has a distinctive metric profile, with MRR of 0.567 in Portuguese
against EmbeddingGemma's 0.640 while nDCG@10 differs by only 8.5%. It is worse
at placing a correct skill first while being comparable across the whole top 10,
which matters if the interface shows one suggestion rather than ten.

### Cost

| model | dims | index MB per language | ms/query |
|---|---:|---:|---:|
| e5-base | 768 | 42.8 | 0.08 |
| embeddinggemma | 768 | 42.8 | 0.07 |
| qwen3-4b | 2560 | 142.7 | 0.09 |

Per-query latency is comparable to BM25 because the corpus is embedded once and
only the query is encoded at request time. The costs dense retrieval adds are a
one-off indexing pass and a resident index, not per-request latency. Timings
were taken on a shared GPU and should be treated as indicative.

---

## 11: Where the dense gain comes from

Experiment 10 recorded a prediction before running. Because the Portuguese
lexical gap is produced by a tail of queries where the two records use different
words for the same concept, dense retrieval should compress that tail rather
than lift the median. This compares per-query distributions over the same 608
occupations. No retrieval is re-run.

### The tail compresses

Per-query nDCG@10 distribution, and the share of queries scoring below 0.10:

| method | lang | p10 | p50 | p90 | failed |
|---|---|---:|---:|---:|---:|
| bm25 | pt | 0.0000 | 0.2413 | 0.5549 | 25.2% |
| embeddinggemma | pt | 0.0694 | 0.3223 | 0.5947 | 15.3% |
| bm25 | en | 0.0367 | 0.3188 | 0.6124 | 18.8% |
| embeddinggemma | en | 0.0831 | 0.3536 | 0.6180 | 12.3% |

The Portuguese failure rate falls by 39% relative, the English by 34%. The
Portuguese 10th percentile moves from exactly zero to 0.069, so more than a
tenth of Portuguese queries previously retrieved nothing useful at all and now
do.

Note the p90 column: 0.5549 to 0.5947 in Portuguese, and 0.6124 to 0.6180 in
English. The top of the distribution barely moves. The gain is in the bottom.

### Gains concentrate exactly where BM25 failed

Queries split into quartiles by their BM25 score, then compared against
themselves under EmbeddingGemma:

| lang | BM25 quartile | BM25 | dense | change | improved |
|---|---|---:|---:|---:|---:|
| pt | Q1 worst | 0.0320 | 0.1830 | +0.1510 | 80% |
| pt | Q2 | 0.1743 | 0.2634 | +0.0891 | 68% |
| pt | Q3 | 0.3226 | 0.3668 | +0.0442 | 59% |
| pt | Q4 best | 0.5344 | 0.5005 | −0.0339 | 44% |
| en | Q1 worst | 0.0618 | 0.1831 | +0.1213 | 75% |
| en | Q2 | 0.2434 | 0.2954 | +0.0520 | 62% |
| en | Q3 | 0.3946 | 0.4036 | +0.0090 | 48% |
| en | Q4 best | 0.6008 | 0.5481 | −0.0528 | 35% |

Monotonic in both languages, and the same shape holds for Qwen3 and for
e5-base, which loses overall while still gaining +0.106 in the Portuguese
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
Portuguese and English Q1 groups start at similar levels, 0.032 and 0.062, yet
Portuguese gains more from every checkpoint. And the failure rate is a threshold
count over the whole distribution rather than a quartile comparison, so
regression does not apply to it, and it falls further in Portuguese for all
three models.

### What this sets up

The two method families fail on different queries in a structured, measurable
way. EmbeddingGemma wins 80% of BM25's worst Portuguese quartile and loses 56%
of its best. That is the precondition for score fusion working, and it is a
stronger reason to try a hybrid than the usual observation that hybrids tend to
help.

---

## 12: What is left of the language gap

Dense retrieval leaves an 8.9% residual with disjoint intervals. This asks
whether it has the same shape as the lexical gap it replaced. Paired on
occupation, which is exact because ESCO assigns one URI per concept and the gold
set is identical in both languages. No retrieval is re-run.

### The residual is uniform, not a tail

Absolute gap between English and Portuguese at each percentile of the per-query
score distribution:

| model | p10 | p25 | p50 | p75 | p90 | relative gap |
|---|---:|---:|---:|---:|---:|---:|
| bm25 | +0.0367 | +0.0691 | +0.0775 | +0.0707 | +0.0575 | +22.3% |
| e5-base | +0.0650 | +0.0568 | +0.0561 | +0.0657 | +0.0600 | +19.6% |
| embeddinggemma | +0.0137 | +0.0374 | +0.0314 | +0.0243 | +0.0233 | +8.9% |
| qwen3-4b | +0.0377 | +0.0373 | +0.0334 | +0.0171 | −0.0054 | +5.9% |

Under EmbeddingGemma the gap is roughly flat across the distribution and small
everywhere, between 0.014 and 0.037. The lexical gap it replaced was two to
three times larger at every percentile, and its p10 figure understates the
damage because Portuguese p10 under BM25 was pinned at exactly 0.0000.

So the terminology explanation developed in experiments 07 to 09 does not carry
over. What remains affects Portuguese queries broadly and mildly rather than
destroying a minority of them. That is the signature of a model representing one
language slightly better than the other, not of a data problem concentrated in
specific records.

Qwen3 is worth noting: its gap reverses at p90, where Portuguese scores higher
than English. Consistent with its narrower overall gap coming from degraded
English rather than improved Portuguese.

### A correction to the correlation figure

Experiment 07 reported that per-query difficulty correlates 0.321 between the
languages, and earlier write-ups used that as evidence the two fail on largely
different queries.

That statistic was the correlation of `n_outranking`, a count ranging from 0 to
1,162 and heavily skewed, which understates agreement. Correlating nDCG@10 on
the same queries gives **0.737** under BM25 and **0.825** under EmbeddingGemma.
The languages fail together far more often than they fail separately.

### What bilingual fusion could actually recover

| model | pt fails | en fails | both | pt only | en only |
|---|---:|---:|---:|---:|---:|
| bm25 | 25.2% | 18.8% | 13.5% | 11.7% | 5.3% |
| e5-base | 25.2% | 16.9% | 11.7% | 13.5% | 5.3% |
| embeddinggemma | 15.3% | 12.3% | 9.0% | 6.2% | 3.3% |
| qwen3-4b | 21.5% | 16.0% | 10.2% | 11.3% | 5.8% |

A query counts as failed below 0.10 nDCG@10.

Under the best model, 6.2% of occupations fail in Portuguese while succeeding in
English, and 3.3% the reverse. An oracle choosing the better language per query
would fix about 6% of Portuguese cases; a real fusion method recovers less.

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
the bilingual headroom at 6.2% of occupations failing in Portuguese while
succeeding in English.

Runs are produced at depth 200 and fused. Reciprocal rank fusion has no weight,
so it is scored on test directly. Weighted score fusion has its weight selected
on dev and applied once to test.

### Weighted score fusion works; rank fusion mostly does not

Every combination is scored on the identical 608 queries, so the comparison is
paired. Marginal intervals are a weak test here, since two overlapping intervals
can still correspond to a difference holding on most queries. The interval below
is on the per-query difference against the stronger of the runs being combined.

| combination | fusion | fused | gain over better input | paired difference (95% CI) |
|---|---|---:|---:|---|
| hybrid pt | rrf | 0.3271 | −0.4% | −0.0013 [−0.0103, +0.0080] |
| hybrid en | rrf | 0.3684 | +3.0% | +0.0108 [+0.0020, +0.0196] |
| bilingual gemma | rrf | 0.3563 | −0.4% | −0.0013 [−0.0077, +0.0051] |
| bilingual bm25 | rrf | 0.3194 | −1.8% | −0.0058 [−0.0138, +0.0026] |
| all four | rrf | 0.3637 | +1.7% | +0.0061 [−0.0033, +0.0158] |
| hybrid pt | wsf | 0.3439 | +4.7% | +0.0155 [+0.0097, +0.0211] |
| **hybrid en** | **wsf** | **0.3794** | **+6.1%** | **+0.0218 [+0.0152, +0.0287]** |
| bilingual gemma | wsf | 0.3647 | +2.0% | +0.0071 [+0.0028, +0.0115] |
| bilingual bm25 | wsf | 0.3295 | +1.3% | +0.0044 [+0.0007, +0.0082] |
| **all four** | **wsf** | **0.3817** | **+6.8%** | **+0.0241 [+0.0173, +0.0310]** |

Only one of five rank-fusion combinations clears zero. `all four` under RRF looks
like a +1.7% gain but its interval spans zero and it wins on exactly 50% of
queries, which is a coin flip. All five weighted combinations clear zero.

That is worth stating because reciprocal rank fusion is often presented as the
safe parameter-free default. On this task the parameter-free method mostly
failed and the tuned one worked, and reporting point estimates alone would have
hidden it.

### The two best configurations are not separable

Comparing each configuration against a shared baseline leaves their difference
from one another undetermined, since those comparisons are correlated. Direct
paired comparisons:

| a | b | a | b | difference (95% CI) | a wins |
|---|---|---:|---:|---|---:|
| all four (wsf) | hybrid en (wsf) | 0.3817 | 0.3794 | +0.0023 [−0.0010, +0.0056] | 42% |
| all four (wsf) | hybrid en (rrf) | 0.3817 | 0.3684 | +0.0133 [+0.0082, +0.0182] | 51% |
| hybrid en (wsf) | bilingual gemma (wsf) | 0.3794 | 0.3647 | +0.0147 [+0.0074, +0.0215] | 55% |
| hybrid en (rrf) | bilingual gemma (wsf) | 0.3684 | 0.3647 | +0.0037 [−0.0054, +0.0124] | 51% |

`all four` scores higher than `hybrid en` but the difference spans zero and it
wins on only 42% of queries. They are not distinguishable on this split.

That has a practical consequence. `hybrid en` needs one language and two
retrievers; `all four` needs two languages and four. Given no measurable
difference, the simpler system is the better recommendation.

### Fusion lifts a minority of queries, not most of them

The **wins** column is more informative than the mean. `all four` gains 6.8% on
the mean while winning on 59% of queries. `bilingual gemma` wins on only 47%,
losing slightly on the majority, and still shows a significant positive mean.

That is tail recovery, and it matches experiment 12 exactly: bilingual fusion's
headroom was 6.2% of occupations where Portuguese fails and English does not. It
cannot improve the queries that already work, and it does not try to.

### The fusion surface has an interior optimum on both axes

The four-way sweep is parameterised over two axes: how much weight goes to
lexical against dense, and how much to Portuguese against English.

| lexical \ pt | 0.0 | 0.2 | 0.4 | 0.6 | 0.8 | 1.0 |
|---|---:|---:|---:|---:|---:|---:|
| 0.0 | 0.3616 | 0.3637 | 0.3611 | 0.3524 | 0.3364 | 0.3210 |
| 0.2 | 0.3758 | 0.3788 | 0.3754 | 0.3647 | 0.3519 | 0.3347 |
| **0.4** | 0.3797 | **0.3830** | 0.3814 | 0.3719 | 0.3555 | 0.3375 |
| 0.6 | 0.3708 | 0.3767 | 0.3745 | 0.3642 | 0.3458 | 0.3242 |
| 0.8 | 0.3534 | 0.3607 | 0.3597 | 0.3474 | 0.3243 | 0.3035 |
| 1.0 | 0.3303 | 0.3385 | 0.3376 | 0.3226 | 0.3007 | 0.2798 |

Smooth, with a single interior peak at lexical 0.4 and Portuguese 0.2. Interior
on both axes means all four runs contribute; a peak at an edge would have meant
one input was dead weight.

The Portuguese weight of 0.2 is a deployment finding in itself. Given both texts,
the best fused system leans heavily on the English one.

### Fusion widens the language gap

| system | en | pt | gap |
|---|---:|---:|---:|
| BM25 | 0.3252 | 0.2659 | +22.3% |
| EmbeddingGemma | 0.3576 | 0.3284 | +8.9% |
| hybrid, wsf | 0.3794 | 0.3439 | +10.3% |

Adding lexical retrieval back in helps English more than Portuguese, +6.1%
against +4.7%, so it re-imports part of the gap that dense retrieval had removed.
The best-performing configuration is not the most language-equitable one, which
follows directly from the lexical diagnosis in experiments 01 to 09.

For a Portuguese-only deployment the relevant number is different again: hybrid
Portuguese at 0.3439 is 29.3% above the Portuguese lexical baseline, and is the
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
| `BAAI/bge-reranker-v2-m3` | Apache 2.0 | regression head, 568M |
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
| bge-m3 | pt | 0.3439 | 0.3482 | +1.2% | +0.0042 [−0.0043, +0.0132] | 49% |
| bge-m3 | en | 0.3794 | 0.3793 | −0.0% | −0.0001 [−0.0056, +0.0051] | 46% |
| qwen3-0.6b | pt | 0.3439 | 0.3351 | −2.6% | **−0.0088 [−0.0141, −0.0033]** | 41% |
| qwen3-0.6b | en | 0.3794 | 0.3746 | −1.3% | −0.0048 [−0.0098, +0.0009] | 43% |

bge-m3 does nothing: both intervals span zero. Qwen3 is significantly worse
than not reranking at all in Portuguese, and in the same direction in English.
Neither wins on half the queries.

### Both degrade as the shortlist deepens

Dev sweep, nDCG@10:

| depth | bge pt | bge en | qwen pt | qwen en |
|---|---:|---:|---:|---:|
| 0, no rerank | 0.3551 | 0.3933 | 0.3551 | 0.3933 |
| 10 | 0.3589 | 0.3868 | 0.3484 | 0.3793 |
| 20 | 0.3603 | 0.3681 | 0.3346 | 0.3689 |
| 50 | 0.3394 | 0.3403 | 0.3188 | 0.3480 |
| 100 | 0.3305 | 0.3138 | 0.3094 | 0.3311 |

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
| bge-m3 | pt | 0.2161 | 0.3482 | 0.3439 | 103% | 0.717 |
| bge-m3 | en | 0.3258 | 0.3793 | 0.3794 | 100% | 0.695 |
| qwen3-0.6b | pt | 0.2939 | 0.3351 | 0.3439 | 82% | 0.668 |
| qwen3-0.6b | en | 0.3258 | 0.3746 | 0.3794 | 91% | 0.680 |

Both checks come back clearly positive. Every configuration sits far above
random, and every AUC is well above chance, with mean gold scores above mean
non-gold throughout.

So the result is **not** that cross-encoder reranking fails here. The rerankers
rank competently. They reproduce between 82% and 103% of the ordering quality
the first stage already achieves, and then stop. An off-the-shelf reranker
matches a dev-tuned hybrid fusion without exceeding it.

Read that way, the depth degradation also makes sense. The deeper the
shortlist, the more of the fusion's ordering the reranker replaces with its own,
and since its own is no better, the result drifts down toward what its
standalone quality would give.

### A hypothesis for why they do not exceed it

The query and document shapes are inverted relative to what these rerankers are
trained on. Both are trained on short queries against long passages. Here the
query is a 100-word occupation description and the document is a skill label
plus one sentence, around 25 tokens.

Qwen3's own calibration is consistent with that. Its sanity check passed with a
370-fold margin, so the scoring path is sound, but a clearly relevant pair
received P(yes) = 0.037: the model answers "no" with 96% confidence on a correct
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
| pt | 0.3439 | 0.4307 | 0.5540 | 0.7066 | 0.7968 |
| en | 0.3794 | 0.4648 | 0.5932 | 0.7342 | 0.8212 |

Perfect ordering over a top-100 shortlist would raise nDCG@10 by **132% in
Portuguese and 116% in English**. Share of that headroom captured:

| checkpoint | pt | en |
|---|---:|---:|
| bge-m3 | +2.0% | −0.1% |
| qwen3-0.6b | −10.1% | −5.6% |

That distinction matters. "Reranking did not help" and "there is nothing left to
gain from reranking" look identical in the headline number and point at
completely different work. Here the shortlist is far from exhausted, and the
rerankers that do rank competently still capture none of what is available.

### The shortlist is good; the ranking is bad

Oracle MRR at depth 10 is 0.912 in Portuguese and 0.926 in English. Sorting the
top 10 by relevance puts any gold skill at rank 1, so those figures say a gold
skill is **already inside the first stage's top 10 for roughly 91% of queries**.
The measured MRR is 0.654 and 0.700, and both rerankers lowered it further, to
0.628 and 0.683 under Qwen3.

The system finds correct answers and fails to put them first. For an interface
showing a teacher a handful of suggestions, that is the gap that matters.

### Most of the residual language gap is ordering, not retrieval

| | pt | en | gap |
|---|---:|---:|---:|
| first stage | 0.3439 | 0.3794 | +10.3% |
| oracle @10 | 0.4307 | 0.4648 | +7.9% |
| oracle @20 | 0.5540 | 0.5932 | +7.1% |
| oracle @50 | 0.7066 | 0.7342 | +3.9% |
| oracle @100 | 0.7968 | 0.8212 | +3.1% |

This speaks directly to the residual experiment 12 left unexplained. The
Portuguese shortlist contains nearly as much gold as the English one, recall@100
of 0.361 against 0.388, a 7.5% difference. Give both perfect ordering and the
nDCG gap falls from 10.3% to 3.1%.

So what survived dense retrieval is largely a ranking failure rather than a
retrieval failure. Portuguese candidates are being found and then ordered worse.

### Cost

| checkpoint | language | depth | pairs scored | ms/query |
|---|---|---:|---:|---:|
| bge-m3 | pt | 20 | 12,160 | 49.8 |
| bge-m3 | en | 10 | 6,080 | 20.4 |
| qwen3-0.6b | pt | 10 | 6,080 | 141.8 |
| qwen3-0.6b | en | 10 | 6,080 | 95.1 |

On the same 6,080 pairs in English, Qwen3 is about 4.7 times slower than bge and
scores lower. Against a first stage answering in well under a millisecond, both
are expensive for no gain. A cross-encoder scores every pair individually, so
nothing is precomputed and cost scales directly with depth.

### What this experiment concludes

Reranking is not worth its cost on this task, and the reason is specific rather
than general. The rerankers work: they separate gold from non-gold well above
chance and reproduce 82% to 103% of the first stage's ordering quality. They
simply do not improve on a hybrid fusion that was already tuned on dev, while
adding 20 to 140 ms per query.

Meanwhile the oracle says perfect ordering of the same candidates would more
than double the score. The ordering problem is large, real, and untouched by
off-the-shelf cross-encoders.

---

## Where this leaves the central question

The project set out to ask whether dense retrieval could compensate for a 23.8x
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

**Dense retrieval removes 60% of it, in the way the diagnosis predicted.** The
gap falls from 22.3% to 8.9%, the Portuguese failure rate from 25.2% to 15.3%,
and the gains concentrate in exactly the queries where lexical matching failed.
A method that had improved the mean while leaving the distribution shape
unchanged would have been doing something else.

**Fusion then widens the gap again.** Combining lexical with dense retrieval is
the best-scoring system, 0.3794 in English and 0.3439 in Portuguese, but it
helps English more, so the gap returns to 10.3%. The highest-scoring
configuration and the most language-equitable one are not the same, which
follows directly from the lexical diagnosis: bringing BM25 back in brings back
the vocabulary-matching problem it carries.

**The residual is largely an ordering failure.** Experiment 12 showed it is
uniform across the score distribution rather than concentrated in a tail, so the
terminology explanation does not carry over. Experiment 14 locates it: the
Portuguese shortlist contains nearly as much gold as the English one, recall@100
of 0.361 against 0.388, and under perfect ordering of that shortlist the nDCG
gap falls from 10.3% to 3.1%. Portuguese candidates are being retrieved and then
ranked worse, which is a different problem from being missed.