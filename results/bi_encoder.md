# Bi-encoder retrieval

Three multilingual checkpoints. Checkpoint and document variant selected on the dev split, then scored once per language on test.
Prompts are per-model: E5 takes `query:` and `passage:` prefixes, Qwen3 an instruction on the query side only, EmbeddingGemma its own task strings.
Intervals are 95% percentile bootstrap over queries.

## Test results

| model | lang | documents | nDCG@10 (95% CI) | P@10 | R@10 | MRR | vs BM25 |
|---|---|---|---:|---:|---:|---:|---:|
| embeddinggemma | en | labels_desc | 0.3576 [0.3419, 0.3744] | 0.270 | 0.145 | 0.678 | +10.0% |
| qwen3-4b | en | preferred | 0.3203 [0.3038, 0.3361] | 0.254 | 0.132 | 0.604 | -1.5% |
| e5-base | en | labels_desc | 0.3145 [0.2987, 0.3307] | 0.238 | 0.127 | 0.634 | -3.3% |
| embeddinggemma | pt | labels_desc | 0.3284 [0.3122, 0.3448] | 0.248 | 0.130 | 0.640 | +23.5% |
| qwen3-4b | pt | preferred | 0.3026 [0.2862, 0.3185] | 0.243 | 0.124 | 0.567 | +13.8% |
| e5-base | pt | labels_desc | 0.2630 [0.2466, 0.2784] | 0.197 | 0.105 | 0.551 | -1.1% |

BM25 reference, best configuration on the same split: pt 0.2658, en 0.3252.

## Language gap

| model | pt | en | en advantage |
|---|---:|---:|---:|
| e5-base | 0.2630 | 0.3145 | +19.6% |
| embeddinggemma | 0.3284 | 0.3576 | +8.9% |
| qwen3-4b | 0.3026 | 0.3203 | +5.9% |
| *BM25* | 0.2658 | 0.3252 | +22.3% |

A smaller language gap is not automatically better. It can be reached by degrading the stronger language rather than improving the weaker one, so this table should be read alongside the absolute scores above.

## Dev sweep

Used for selection only. Test numbers above come from the best row per model and language.

| model | lang | documents | nDCG@10 | R@10 | MRR |
|---|---|---|---:|---:|---:|
| e5-base | en | description | 0.2798 | 0.111 | 0.591 |
| e5-base | en | labels_desc | 0.3175 | 0.128 | 0.638 |
| e5-base | en | preferred | 0.3074 | 0.124 | 0.621 |
| e5-base | pt | description | 0.2242 | 0.088 | 0.485 |
| e5-base | pt | labels_desc | 0.2612 | 0.101 | 0.555 |
| e5-base | pt | preferred | 0.2348 | 0.092 | 0.508 |
| embeddinggemma | en | description | 0.3324 | 0.132 | 0.652 |
| embeddinggemma | en | labels_desc | 0.3616 | 0.145 | 0.693 |
| embeddinggemma | en | preferred | 0.3386 | 0.135 | 0.666 |
| embeddinggemma | pt | description | 0.2999 | 0.117 | 0.603 |
| embeddinggemma | pt | labels_desc | 0.3210 | 0.126 | 0.640 |
| embeddinggemma | pt | preferred | 0.2939 | 0.118 | 0.579 |
| qwen3-4b | en | description | 0.3047 | 0.124 | 0.603 |
| qwen3-4b | en | labels_desc | 0.2999 | 0.121 | 0.598 |
| qwen3-4b | en | preferred | 0.3153 | 0.128 | 0.617 |
| qwen3-4b | pt | description | 0.2641 | 0.105 | 0.545 |
| qwen3-4b | pt | labels_desc | 0.2600 | 0.102 | 0.542 |
| qwen3-4b | pt | preferred | 0.2973 | 0.121 | 0.568 |

## Cost

Index size is the corpus embedding matrix held in memory. Encoding is one-off; only the query is encoded per request.

| model | dims | index MB | ms/query |
|---|---:|---:|---:|
| e5-base | 768 | 42.8 | 0.08 |
| embeddinggemma | 768 | 42.8 | 0.07 |
| qwen3-4b | 2560 | 142.7 | 0.09 |
