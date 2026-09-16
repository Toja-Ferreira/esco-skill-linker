# Fusion

BM25 and `embeddinggemma` combined two ways: lexical with dense within a language, and Portuguese with English for the same occupation. Runs are produced at depth 200 and fused, then scored at the usual cutoffs.
Reciprocal rank fusion has no weight, so it is scored on test directly. Weighted score fusion has its weight selected on dev and applied once to test.
Intervals are 95% percentile bootstrap over queries.

## Test results

| combination | fusion | weight | nDCG@10 (95% CI) | P@10 | R@10 | MRR |
|---|---|---:|---:|---:|---:|---:|
| bm25 pt | single |  | 0.2659 [0.2501, 0.2807] | 0.203 | 0.107 | 0.524 |
| bm25 en | single |  | 0.3252 [0.3084, 0.3416] | 0.250 | 0.134 | 0.611 |
| embeddinggemma pt | single |  | 0.3284 [0.3122, 0.3448] | 0.248 | 0.130 | 0.640 |
| embeddinggemma en | single |  | 0.3576 [0.3419, 0.3744] | 0.270 | 0.145 | 0.678 |
| hybrid pt | rrf |  | 0.3271 [0.3112, 0.3423] | 0.257 | 0.135 | 0.595 |
| hybrid en | rrf |  | 0.3684 [0.3519, 0.3850] | 0.285 | 0.152 | 0.676 |
| bilingual embeddinggemma | rrf |  | 0.3563 [0.3400, 0.3732] | 0.271 | 0.143 | 0.671 |
| bilingual bm25 | rrf |  | 0.3194 [0.3028, 0.3353] | 0.246 | 0.131 | 0.604 |
| all four | rrf |  | 0.3637 [0.3472, 0.3800] | 0.284 | 0.150 | 0.654 |
| hybrid pt | wsf | 0.3 | 0.3439 [0.3279, 0.3603] | 0.262 | 0.138 | 0.654 |
| hybrid en | wsf | 0.4 | 0.3794 [0.3629, 0.3960] | 0.292 | 0.155 | 0.700 |
| bilingual embeddinggemma | wsf | 0.3 | 0.3647 [0.3486, 0.3818] | 0.278 | 0.148 | 0.682 |
| bilingual bm25 | wsf | 0.2 | 0.3295 [0.3122, 0.3458] | 0.254 | 0.136 | 0.613 |
| all four | wsf | 0.4 | 0.3817 [0.3654, 0.3988] | 0.295 | 0.157 | 0.696 |

## Gain over the better input

Fusion is only worth its cost if it beats the stronger of the two runs it combines, not merely the weaker one.

Every combination is scored on the identical 608 queries, so the comparison is paired. Marginal confidence intervals are a weak test here: two overlapping intervals can still correspond to a difference that holds on most queries. The interval below is on the per-query difference, and **won** is the share of queries where fusion beat the baseline.

| combination | fusion | baseline | baseline | fused | gain | paired difference (95% CI) | won |
|---|---|---|---:|---:|---:|---|---:|
| hybrid pt | rrf | embeddinggemma pt | 0.3284 | 0.3271 | -0.4% | -0.0013 [-0.0103, +0.0080] | 49% |
| hybrid en | rrf | embeddinggemma en | 0.3576 | 0.3684 | +3.0% | +0.0108 [+0.0020, +0.0196] | 56% |
| bilingual embeddinggemma | rrf | embeddinggemma en | 0.3576 | 0.3563 | -0.4% | -0.0013 [-0.0077, +0.0051] | 47% |
| bilingual bm25 | rrf | bm25 en | 0.3252 | 0.3194 | -1.8% | -0.0058 [-0.0138, +0.0026] | 42% |
| all four | rrf | embeddinggemma en | 0.3576 | 0.3637 | +1.7% | +0.0061 [-0.0033, +0.0158] | 50% |
| hybrid pt | wsf | embeddinggemma pt | 0.3284 | 0.3439 | +4.7% | +0.0155 [+0.0097, +0.0211] | 53% |
| hybrid en | wsf | embeddinggemma en | 0.3576 | 0.3794 | +6.1% | +0.0218 [+0.0152, +0.0287] | 59% |
| bilingual embeddinggemma | wsf | embeddinggemma en | 0.3576 | 0.3647 | +2.0% | +0.0071 [+0.0028, +0.0115] | 47% |
| bilingual bm25 | wsf | bm25 en | 0.3252 | 0.3295 | +1.3% | +0.0044 [+0.0007, +0.0082] | 43% |
| all four | wsf | embeddinggemma en | 0.3576 | 0.3817 | +6.8% | +0.0241 [+0.0173, +0.0310] | 59% |

An interval that spans zero means the improvement is not distinguishable from none on this split, whatever the point estimate.

## Head to head

The table above compares each configuration against a shared baseline, which leaves their difference from one another undetermined: two comparisons against the same baseline are correlated. These are direct paired comparisons between the strongest configurations.

| a | b | a | b | difference (95% CI) | a wins |
|---|---|---:|---:|---|---:|
| all four (wsf) | hybrid en (wsf) | 0.3817 | 0.3794 | +0.0023 [-0.0010, +0.0056] | 42% |
| all four (wsf) | hybrid en (rrf) | 0.3817 | 0.3684 | +0.0133 [+0.0082, +0.0182]** | 51% |
| all four (wsf) | bilingual embeddinggemma (wsf) | 0.3817 | 0.3647 | +0.0170 [+0.0102, +0.0234]** | 55% |
| hybrid en (wsf) | hybrid en (rrf) | 0.3794 | 0.3684 | +0.0110 [+0.0064, +0.0154]** | 49% |
| hybrid en (wsf) | bilingual embeddinggemma (wsf) | 0.3794 | 0.3647 | +0.0147 [+0.0074, +0.0215]** | 55% |
| hybrid en (rrf) | bilingual embeddinggemma (wsf) | 0.3684 | 0.3647 | +0.0037 [-0.0054, +0.0124] | 51% |

Bold marks a difference whose interval excludes zero. Where the interval spans zero the two configurations are not separable on this split, whatever their point estimates.

## Weight sweep on dev, pairs

Weight applies to the first run in each pair; the second takes one minus it. A selected weight at 0.0 or 1.0 would mean fusion did not beat using one run alone.

| weight | bilingual bm25 | bilingual embeddinggemma | hybrid en | hybrid pt |
|---|---:|---:|---:|---:|
| 0.0 | 0.3303 | 0.3616 | 0.3616 | 0.3210 |
| 0.1 | 0.3352 | 0.3634 | 0.3692 | 0.3277 |
| 0.2 | 0.3385 | 0.3637 | 0.3758 | 0.3347 |
| 0.3 | 0.3385 | 0.3641 | 0.3794 | 0.3381 |
| 0.4 | 0.3376 | 0.3611 | 0.3797 | 0.3375 |
| 0.5 | 0.3321 | 0.3569 | 0.3766 | 0.3323 |
| 0.6 | 0.3226 | 0.3524 | 0.3708 | 0.3242 |
| 0.7 | 0.3121 | 0.3446 | 0.3627 | 0.3144 |
| 0.8 | 0.3007 | 0.3364 | 0.3534 | 0.3035 |
| 0.9 | 0.2908 | 0.3287 | 0.3426 | 0.2914 |
| 1.0 | 0.2798 | 0.3210 | 0.3303 | 0.2798 |

## Weight sweep on dev, four-way

Rows are the weight on lexical against dense, columns the weight on Portuguese against English. Each cell's four weights are the product of the two, so they sum to one.

| lexical \ pt | 0.0 | 0.2 | 0.4 | 0.6 | 0.8 | 1.0 |
|---|---:|---:|---:|---:|---:|---:|
| **0.0** | 0.3616 | 0.3637 | 0.3611 | 0.3524 | 0.3364 | 0.3210 |
| **0.2** | 0.3758 | 0.3788 | 0.3754 | 0.3647 | 0.3519 | 0.3347 |
| **0.4** | 0.3797 | 0.3830 | 0.3814 | 0.3719 | 0.3555 | 0.3375 |
| **0.6** | 0.3708 | 0.3767 | 0.3745 | 0.3642 | 0.3458 | 0.3242 |
| **0.8** | 0.3534 | 0.3607 | 0.3597 | 0.3474 | 0.3243 | 0.3035 |
| **1.0** | 0.3303 | 0.3385 | 0.3376 | 0.3226 | 0.3007 | 0.2798 |
