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

Also here: [`dataset_profile.md`](dataset_profile.md) and
[`split_profile.md`](split_profile.md), describing the release and the frozen
evaluation split.

## Current best lexical baseline

BM25, labels plus description, stemmed, stopwords removed. 608 held-out
occupation descriptions against all 13,939 skills.

| | nDCG@10 | 95% CI | P@10 | R@10 | MRR |
|---|---:|---|---:|---:|---:|
| English | 0.325 | [0.308, 0.342] | 0.250 | 0.134 | 0.611 |
| Portuguese | 0.266 | [0.250, 0.281] | 0.203 | 0.107 | 0.524 |

English leads by 22.3%. Experiment 01 reported 0.309 and 0.248 with a 25.0% gap;
those figures used no stopword list, which experiment 05 showed to be a
suboptimal configuration for both languages and a worse one for Portuguese.

---

## Reading the numbers

**Recall@k is capped well below 1.** Occupations carry around 22 essential
skills on average and only 10 fit in a top-10, so the highest recall@10
achievable on this split is **0.543**. A recall@10 of 0.134 is 25% of what is
reachable.

| k | 1 | 3 | 5 | 10 | 20 | 50 |
|---|---:|---:|---:|---:|---:|---:|
| max recall@k | 0.056 | 0.167 | 0.278 | 0.543 | 0.856 | 0.993 |

**Precision and MRR answer different questions.** The best English run has P@10
of 0.250, so most of what it shows is wrong, alongside MRR of 0.611, meaning the
first genuinely essential skill usually appears around rank 2 out of 13,939
candidates. Lexical matching finds one correct skill easily and the full set
poorly.

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
| description, stemmed | 25.2 | 22.2 | 0.208 | 0.258 | +24.4% |

Portuguese preferred labels are 36% longer than English ones and score 16%
lower. Descriptions are 14% longer and score 24% lower. Every interval is
disjoint. A shortage of text does not explain this, which rules out the original
framing of the project's central question. Experiments 03 to 05 pursue the
cause.

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

## Where this leaves the central question

The project set out to ask whether dense retrieval could compensate for a 23.8x
deficit in Portuguese alternative labels. That framing survives only partly.

What the label deficit costs is measured: about a fifth of English's lexical
quality on the `labels` variant, and Portuguese cannot access any of it. That
part of the original question stands.

On `description`, where ESCO gives both languages complete and comparable
coverage, English still retrieves 18.2% better. Six candidate explanations have
been tested:

| candidate | verdict |
|---|---|
| Missing alternative labels | Accounts for the `labels` gap, not the `description` gap |
| Translation drift in word choice | Not supported. Portuguese shares as much gold vocabulary (03) |
| Portuguese stemmer under-conflates | Not supported. It conflates at least as much (03) |
| Function word density | Real. Accounts for about a quarter of the gap, now corrected (04, 05) |
| Length normalisation | Negligible. Surfaces flat across `b` (06) |
| Lexical impoverishment from translation | Not supported. Portuguese vocabulary is larger (06) |

What has not been measured is the competition. Experiments 03 and 04 both
measured overlap between a query and its **gold** skills. Neither measured
overlap between a query and the roughly 13,000 **non-gold** skills. Ranking is a
contest: a gold skill scoring well ranks poorly if many distractors score
similarly. Only the numerator has been examined.

That is the remaining lexical hypothesis. Portuguese gold skills may score as
well as English ones in absolute terms while Portuguese distractors also score
well, so gold does not separate from the field. Experiment 07 measures it
directly.

For the retrieval work that follows, the useful framing is narrower than the
original: a lexical method carries a Portuguese penalty that survives careful
preprocessing and parameter tuning, and the question is how much of it a dense
multilingual model removes.