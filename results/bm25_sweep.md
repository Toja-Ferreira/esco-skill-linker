# BM25 parameter sweep

Document variant `labels_desc`, stemmed, stopwords removed. Grid over k1 and b, selected on `ndcg@10`.
**The sweep runs on the dev split.** Choosing parameters by their score is fitting, so the test split is touched only once per language, with the already-selected values.

## Selected parameters

| language | k1 | b | dev nDCG@10 |
|---|---:|---:|---:|
| pt | 1.8 | 0.75 | 0.2802 |
| en | 2.1 | 1.0 | 0.3356 |

### Do the languages want different length normalisation?

The two corpora differ substantially in scale, so a materially different response to `b` per language would implicate length normalisation in the residual gap left unexplained by experiments 03 to 05. Comparing argmax alone over-reads small differences on a flat surface, so what follows is the size of the effect across the whole range.

| language | best b | worst b | spread | span 0.75 to 1.0 |
|---|---:|---:|---:|---:|
| pt | 0.75 | 0.0 | 0.0237 | 0.0041 |
| en | 1.0 | 0.0 | 0.0257 | 0.0022 |

Moving `b` between 0.75 and 1.0 changes ndcg@10 by at most 0.0041 in either language, against a Portuguese to English gap of roughly 0.06. The surfaces differ in shape, with English rising monotonically in `b` while Portuguese turns over, but the magnitude is an order of magnitude too small to account for the gap. Length normalisation is not the explanation.

## Dev surface

### pt

| k1 \ b | 0.0 | 0.2 | 0.4 | 0.6 | 0.75 | 0.9 | 1.0 |
|---|---:|---:|---:|---:|---:|---:|---:|
| **0.6** | 0.2518 | 0.2597 | 0.2647 | 0.2681 | 0.2707 | 0.2716 | 0.2715 |
| **0.9** | 0.2548 | 0.2658 | 0.2705 | 0.2750 | 0.2765 | 0.2766 | 0.2761 |
| **1.2** | 0.2563 | 0.2677 | 0.2735 | 0.2777 | 0.2782 | 0.2778 | 0.2768 |
| **1.5** | 0.2568 | 0.2694 | 0.2753 | 0.2784 | 0.2798 | 0.2792 | 0.2771 |
| **1.8** | 0.2565 | 0.2691 | 0.2762 | 0.2790 | 0.2802 | 0.2787 | 0.2761 |
| **2.1** | 0.2550 | 0.2695 | 0.2762 | 0.2793 | 0.2801 | 0.2786 | 0.2753 |

### en

| k1 \ b | 0.0 | 0.2 | 0.4 | 0.6 | 0.75 | 0.9 | 1.0 |
|---|---:|---:|---:|---:|---:|---:|---:|
| **0.6** | 0.3015 | 0.3065 | 0.3104 | 0.3131 | 0.3145 | 0.3154 | 0.3160 |
| **0.9** | 0.3063 | 0.3124 | 0.3172 | 0.3209 | 0.3231 | 0.3242 | 0.3247 |
| **1.2** | 0.3083 | 0.3148 | 0.3211 | 0.3257 | 0.3274 | 0.3287 | 0.3291 |
| **1.5** | 0.3099 | 0.3171 | 0.3236 | 0.3284 | 0.3303 | 0.3313 | 0.3321 |
| **1.8** | 0.3102 | 0.3177 | 0.3239 | 0.3298 | 0.3324 | 0.3332 | 0.3341 |
| **2.1** | 0.3099 | 0.3182 | 0.3254 | 0.3306 | 0.3334 | 0.3349 | 0.3356 |

## Test split, scored once

Selected parameters against the library defaults used in experiments 01 and 05.

| language | setting | k1 | b | nDCG@10 (95% CI) | P@10 | R@10 | MRR |
|---|---|---:|---:|---:|---:|---:|---:|
| pt | tuned | 1.8 | 0.75 | 0.2658 [0.2496, 0.2806] | 0.204 | 0.108 | 0.519 |
| pt | default | 1.5 | 0.75 | 0.2658 [0.2500, 0.2806] | 0.203 | 0.107 | 0.524 |
| en | tuned | 2.1 | 1.0 | 0.3273 [0.3097, 0.3435] | 0.252 | 0.134 | 0.614 |
| en | default | 1.5 | 0.75 | 0.3252 [0.3084, 0.3416] | 0.250 | 0.134 | 0.611 |

| language | gain from tuning |
|---|---:|
| pt | -0.0% |
| en | +0.7% |

English advantage: +22.3% at defaults, +23.2% tuned (+0.8 pp).
