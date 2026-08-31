# Results

Findings across experiments. Each entry interprets numbers that live in a
generated file alongside it; those files are overwritten on every run, this one
is not.

| # | experiment | generated output | script |
|---|---|---|---|
| 01 | BM25 lexical baseline | [`bm25.md`](bm25.md), [`bm25_summary.csv`](bm25_summary.csv), [`bm25_per_query.csv`](bm25_per_query.csv) | [`experiments/01_bm25.py`](../experiments/01_bm25.py) |

Also here: [`dataset_profile.md`](dataset_profile.md) and
[`split_profile.md`](split_profile.md), describing the release and the frozen
evaluation split.

---

## Reading the numbers

**Recall@k is capped well below 1.** Occupations carry ~22 essential skills on
average and only 10 fit in a top-10, so the highest recall@10 achievable on this
split is **0.543**. A recall@10 of 0.126 is 23% of what is reachable, not 13% of
anything. Ceilings for every k are in `bm25.md`.

| k | 1 | 3 | 5 | 10 | 20 | 50 |
|---|---:|---:|---:|---:|---:|---:|
| max recall@k | 0.056 | 0.167 | 0.278 | 0.543 | 0.856 | 0.993 |

**Precision and MRR disagree, and both are right.** BM25's best English run has
P@10 of 0.235 — most of what it shows is wrong — but MRR of 0.599, meaning the
first genuinely essential skill usually appears around rank 2 out of 13,939
candidates. Lexical matching finds *a* correct skill easily and *all* of them
poorly. Which matters depends on the application; for suggesting skills to a
human reviewer, MRR is closer to the thing that counts.

---

## 01 — BM25 lexical baseline

608 test occupations, full index of 13,939 skills, 16 conditions: 2 languages ×
4 document variants × stemmed/unstemmed. Best configuration in both languages is
labels + description with stemming.

| | nDCG@10 | 95% CI | R@10 | MRR |
|---|---:|---|---:|---:|
| **en** labels_desc stemmed | 0.309 | [0.293, 0.325] | 0.126 | 0.599 |
| **pt** labels_desc stemmed | 0.248 | [0.232, 0.262] | 0.099 | 0.506 |

English leads by 25% relative, intervals well separated. Below, what accounts
for that gap — and what does not.

### The alternative-label asymmetry behaves exactly as predicted

Adding ESCO's alternative labels to the preferred label transforms the English
index and does nothing at all for Portuguese:

| | preferred | + alt labels | change | tokens/doc |
|---|---:|---:|---:|---|
| pt, raw | 0.163 | 0.162 | **−0.5%** | 4.9 → 6.1 |
| en, raw | 0.189 | 0.227 | **+20.1%** | 3.6 → 29.3 |

English documents grow eightfold; Portuguese documents grow by roughly one
token, because only 8% of Portuguese skills carry any alternative label at all.
The 23.8× label asymmetry recorded in the dataset profile is not a curiosity —
it is worth a fifth of English's lexical retrieval quality, and Portuguese
cannot access any of it.

### But the label gap does not explain the whole deficit

The more interesting result. On document variants where ESCO treats both
languages equally, Portuguese has **more** text and still loses:

| condition | pt tokens | en tokens | pt nDCG@10 | en nDCG@10 | en advantage |
|---|---:|---:|---:|---:|---:|
| preferred, raw | 4.9 | 3.6 | 0.163 | 0.189 | +15.8% |
| description, raw | 25.2 | 22.2 | 0.188 | 0.230 | +22.4% |
| description, stemmed | 25.2 | 22.2 | 0.208 | 0.258 | +24.4% |

Portuguese preferred labels are 36% longer than English ones and score 16%
worse. Descriptions are 14% longer and score 24% worse. Every interval is
disjoint. Whatever is happening, it is not a shortage of text.

### Hypothesis: translation breaks terminological consistency

ESCO is authored in English and translated into the other 27 languages.
Occupation descriptions and skill entries are separate records, plausibly
translated independently. English inherits the source's vocabulary on both
sides, so an occupation description and its gold skill often share exact
strings. A Portuguese translator rendering the same concept in two records need
not choose the same word, and BM25 scores nothing for near-synonyms.

This is a hypothesis, not a measurement. The test: per language, compute token
overlap between each test occupation's description and the text of its gold
skills. If English overlap is materially higher on the description-only variant
— where both languages have equivalent coverage — the mechanism is confirmed.

It matters because it reframes the project's central question. Not merely *can
dense retrieval compensate for fewer labels*, but *can dense retrieval
compensate for translation drift* — which is much closer to what embeddings are
supposed to be good at, and makes the bi-encoder result informative whichever
way it falls.

### Stemming helps, and helps English more

Relative nDCG@10 gain from stemming:

| variant | pt | en |
|---|---:|---:|
| preferred | +13.6% | +23.4% |
| labels | +13.4% | +11.6% |
| labels_desc | +6.9% | +5.7% |
| description | +10.5% | +12.3% |

Portuguese is the more heavily inflected language, so the expectation was the
reverse. One plausible reading: English gains more on `preferred` because its
labels are terse and verb-initial ("manage budgets"), where a single stem match
carries most of the signal, while Portuguese labels carry more function words
that stemming does not help with. Reported as observed; not investigated
further.

### Micro-recall trails macro-recall everywhere

At the English best, macro 0.126 against micro 0.104. Micro-recall pools all
gold across queries, so occupations with large gold sets dominate it. The gap
means performance degrades as the gold set grows — unsurprising with a fixed
top-10 against gold sets ranging from 6 to 74, but worth watching, since
micro-recall is the form comparable to the Commission's published figures.

### Cost

26–50 ms per query, index build under 7 s, everything in memory. BM25 is free.
Any method that costs materially more has to earn it against these numbers, and
the comparison should be made on quality per unit latency rather than quality
alone.

### What this establishes

1. A floor: **0.309 nDCG@10 English, 0.248 Portuguese**, best configuration each.
2. The Portuguese lexical deficit is real, significant, and only partly caused
   by missing alternative labels.
3. A specific, testable hypothesis for the remainder, with a cheap diagnostic.
4. Confirmation that the harness works end to end — frozen split, graded gold,
   bootstrap intervals, per-query records committed.

### Next

- Run the overlap diagnostic to test the translation-drift hypothesis.
- Bi-encoder over the same split. The prediction that follows from the above:
  dense retrieval should close proportionally more of the gap on the
  description variant than on the labels variant, because that is where the
  deficit is semantic rather than volumetric.
