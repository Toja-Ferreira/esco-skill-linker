# Results

Findings across experiments. Each entry interprets numbers held in a generated
file alongside it. Generated files are overwritten on every run; this one is
not.

| # | experiment | generated output | script |
|---|---|---|---|
| 01 | BM25 lexical baseline | [`bm25.md`](bm25.md), [`bm25_summary.csv`](bm25_summary.csv), [`bm25_per_query.csv`](bm25_per_query.csv) | [`experiments/01_bm25.py`](../experiments/01_bm25.py) |
| 02 | Quality by gold set size | [`gold_size_slice.md`](gold_size_slice.md), [`gold_size_slice.csv`](gold_size_slice.csv) | [`experiments/02_gold_size_slice.py`](../experiments/02_gold_size_slice.py) |

Also here: [`dataset_profile.md`](dataset_profile.md) and
[`split_profile.md`](split_profile.md), describing the release and the frozen
evaluation split.

---

## Reading the numbers

**Recall@k is capped well below 1.** Occupations carry around 22 essential
skills on average and only 10 fit in a top-10, so the highest recall@10
achievable on this split is **0.543**. A recall@10 of 0.126 is 23% of what is
reachable.

| k | 1 | 3 | 5 | 10 | 20 | 50 |
|---|---:|---:|---:|---:|---:|---:|
| max recall@k | 0.056 | 0.167 | 0.278 | 0.543 | 0.856 | 0.993 |

**Precision and MRR answer different questions.** BM25's best English run has
P@10 of 0.235, so most of what it shows is wrong, alongside MRR of 0.599,
meaning the first genuinely essential skill usually appears around rank 2 out of
13,939 candidates. Lexical matching finds one correct skill easily and the full
set poorly. Which of those matters depends on the application. For suggesting
skills to a human reviewer, MRR is closer to the quantity of interest.

---

## 01: BM25 lexical baseline

608 test occupations, full index of 13,939 skills, 16 conditions covering 2
languages, 4 document variants and stemmed against unstemmed. Best configuration
in both languages is labels plus description with stemming.

| | nDCG@10 | 95% CI | R@10 | MRR |
|---|---:|---|---:|---:|
| **en** labels_desc stemmed | 0.309 | [0.293, 0.325] | 0.126 | 0.599 |
| **pt** labels_desc stemmed | 0.248 | [0.232, 0.262] | 0.099 | 0.506 |

English leads by 25% relative, with well separated intervals.

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
framing of the project's central question but does not by itself identify the
cause.

### Two candidate explanations, currently not separable

The description-only gap has at least two possible causes, and the numbers above
cannot distinguish them.

**Candidate A: translation breaks terminological consistency.** ESCO is authored
in English and translated into the other 27 languages. Occupation descriptions
and skill entries are separate records, plausibly translated independently.
English inherits the source vocabulary on both sides, so an occupation
description and its gold skill often share exact strings. A Portuguese
translator rendering the same concept in two records need not choose the same
word, and BM25 scores nothing for near-synonyms.

**Candidate B: the Portuguese preprocessing in this repository is weaker than
the English.** Both languages run through the same code path, but that path is
not equally good at both:

- *Stemmer quality.* Snowball's Portuguese stemmer and its English stemmer are
  different algorithms of different maturity. If Portuguese under-conflates,
  morphological variants of the same term stay distinct and score nothing. The
  stemming table above is consistent with this: Portuguese is the more heavily
  inflected language and gains *less* from stemming, which is what
  under-conflation would look like. That observation was recorded as unexplained
  before this confound was identified.
- *Tokenisation.* A single `\w+` regex is applied to both languages. It keeps
  accented characters, but makes no other language-specific accommodation.
- *Length normalisation.* BM25 normalises each document against its own corpus
  mean, so the two languages are not penalised against a shared baseline.
  However, the corpora differ enormously in scale: under `labels` the English
  mean is 29.3 tokens against 6.1 in Portuguese. Length normalisation and IDF
  behave differently at those scales, so the two runs are not the same retrieval
  problem with the language swapped.

No stopword list is used in either language, so that particular asymmetry is
ruled out.

Until A and B are separated, "Portuguese retrieves worse" and "this
repository's Portuguese preprocessing is worse" are indistinguishable from these
results. The finding as it stands is that a like-for-like BM25 configuration
performs worse in Portuguese, which is a real and reportable result about this
pipeline. It is not yet evidence about ESCO's translation quality.

### Tests that would separate them

**Token overlap diagnostic, raw and stemmed.** Per language, measure token
overlap between each test occupation's description and the text of its gold
skills. Running it on raw tokens as well as stemmed matters: raw alone conflates
vocabulary choice with morphology, and the difference between the two is itself
a measure of what stemming recovers in each language. Cheap, no new
infrastructure. If Portuguese overlap is not lower than English, candidate A is
already in difficulty.

**Machine-translation control.** Translate the English occupation descriptions
and skill texts into Portuguese with a single MT system, then score that corpus
against official ESCO Portuguese. One MT system renders a given source term the
same way every time, which is exactly the consistency candidate A claims human
translators lost. Both conditions pass through identical Portuguese
tokenisation, stemming and BM25 parameters, so candidate B is controlled by
construction.

The prediction can fail, which is what makes it worth running. If MT Portuguese
beats official Portuguese, candidate A is supported and the result says
something about ESCO's multilingual quality. If it does not, candidate A is
wrong.

A reverse control is worth running alongside: translate official Portuguese into
English and score against official English. If MT English also beats official
English, the effect is about MT normalising vocabulary in general rather than
about ESCO translation specifically, and neither candidate is supported.

### Stemming helps, and helps English more

Relative nDCG@10 gain from stemming:

| variant | pt | en |
|---|---:|---:|
| preferred | +13.6% | +23.4% |
| labels | +13.4% | +11.6% |
| labels_desc | +6.9% | +5.7% |
| description | +10.5% | +12.3% |

Portuguese is the more heavily inflected language, so the expectation was that
it would gain more. On `preferred`, where a single stem match carries most of
the signal, it gains roughly half as much.

This was initially recorded as an unexplained curiosity. It is better read as
evidence for candidate B above: a stemmer that under-conflates would both gain
less from being applied and depress the language's scores throughout. The two
observations have the same possible cause, and the diagnostics listed above test
both at once.

### Micro-recall trails macro-recall

At the English best, macro 0.126 against micro 0.104. Micro-recall pools all
gold across queries, so occupations with large gold sets dominate it. The gap
means performance degrades as the gold set grows, which is expected with a fixed
top-10 against gold sets ranging from 6 to 74. Worth watching, since
micro-recall is the form comparable to the Commission's published figures.

### Cost

26 to 50 ms per query, index build under 7 s, everything in memory. Any method
costing materially more should be judged on quality per unit latency rather than
quality alone.

---

## 02: Quality by gold set size

The benchmark queries occupations carrying a mean of 22 essential skills. The
target application queries learning outcomes carrying 1 to 3. If method
behaviour shifts as gold sets shrink, the benchmark is a poor proxy. This slices
the recorded per-query results from experiment 01 into gold-size quartiles. No
retrieval is re-run, so the numbers are the ones already committed.

| bucket | queries | essential skills | median | max recall@10 |
|---|---:|---|---:|---:|
| Q1 smallest | 159 | 6 to 14 | 12 | 0.861 |
| Q2 | 163 | 15 to 20 | 18 | 0.577 |
| Q3 | 139 | 21 to 27 | 24 | 0.419 |
| Q4 largest | 147 | 28 to 74 | 34 | 0.279 |

### The English advantage is uniform across gold set sizes

nDCG@10, best configuration:

| bucket | pt | en | en advantage |
|---|---|---|---:|
| Q1 smallest | 0.237 [0.210, 0.265] | 0.308 [0.277, 0.339] | +29.7% |
| Q2 | 0.247 [0.215, 0.278] | 0.310 [0.275, 0.344] | +25.4% |
| Q3 | 0.224 [0.196, 0.254] | 0.289 [0.261, 0.318] | +28.9% |
| Q4 largest | 0.281 [0.250, 0.314] | 0.330 [0.296, 0.364] | +17.2% |

English leads in all four buckets, by between 17% and 30%, with no trend as gold
sets grow. Precision@10 and recall@10 show the same pattern at similar
magnitudes.

Each bucket holds around 150 queries, roughly a quarter of the split, so
intervals are wider than the pooled comparison and two buckets do not separate
individually. The evidence is the consistency of direction and magnitude across
four independent buckets, not any single bucket. The pooled 608-query comparison
separates the two languages cleanly.

A uniform effect is consistent with a systematic cause such as translation drift
rather than something that only bites in one regime.

### nDCG is flat across buckets; recall and precision are not

English nDCG@10 runs 0.289 to 0.330 with no trend, because nDCG normalises by
the ideal ranking and so places a query with 6 gold and a query with 74 on the
same scale.

Recall@10 falls from 0.188 to 0.076 across the buckets while precision@10 rises
from 0.208 to 0.271. Neither movement reflects the method changing. The recall
ceiling drops from 0.861 to 0.279 across the same buckets, and more gold means
more chances for any given slot to hit. Raw recall and precision are not
comparable across buckets for this reason.

### Bearing on the query shape limitation

Q1, with a median of 12 essential skills, is the closest available approximation
to learning outcome density, which the Commission's pilot reports place at 1 to
3 concepts. Performance there matches the pooled figures closely: English 0.308
against 0.309 pooled, Portuguese 0.237 against 0.248.

Method behaviour is therefore stable as gold sets shrink toward the target task,
across the range this benchmark can test. Query *length* remains untested, since
all queries here are full occupation descriptions rather than the 10 to 15 word
statements the application would receive.