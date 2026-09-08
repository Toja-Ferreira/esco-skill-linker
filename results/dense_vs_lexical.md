# Dense against lexical: where does the gain come from?

Per-query `ndcg@10` over the 608 test occupations, comparing BM25 at its best configuration against each bi-encoder. No retrieval is re-run.

Experiment 10 recorded a prediction before running: because the Portuguese lexical gap comes from a tail of queries where the two records use different words for the same concept, dense retrieval should compress that tail rather than lift the median.

## Distribution of per-query scores

A query below 0.10 has essentially failed.

### pt

| method | mean | p10 | p25 | p50 | p75 | p90 | failed |
|---|---:|---:|---:|---:|---:|---:|---:|
| bm25 | 0.2658 | 0.0000 | 0.0991 | 0.2413 | 0.4004 | 0.5549 | 25.2% |
| e5-base | 0.2630 | 0.0000 | 0.0953 | 0.2424 | 0.3882 | 0.5225 | 25.2% |
| embeddinggemma | 0.3284 | 0.0694 | 0.1748 | 0.3223 | 0.4660 | 0.5947 | 15.3% |
| qwen3-4b | 0.3026 | 0.0256 | 0.1269 | 0.2935 | 0.4459 | 0.5951 | 21.5% |

### en

| method | mean | p10 | p25 | p50 | p75 | p90 | failed |
|---|---:|---:|---:|---:|---:|---:|---:|
| bm25 | 0.3252 | 0.0367 | 0.1682 | 0.3188 | 0.4711 | 0.6124 | 18.8% |
| e5-base | 0.3145 | 0.0650 | 0.1521 | 0.2985 | 0.4539 | 0.5825 | 16.9% |
| embeddinggemma | 0.3576 | 0.0831 | 0.2122 | 0.3536 | 0.4903 | 0.6180 | 12.3% |
| qwen3-4b | 0.3203 | 0.0634 | 0.1642 | 0.3268 | 0.4630 | 0.5896 | 16.0% |

## Change from BM25, by how well BM25 did

Queries are split into quartiles by their BM25 score, then compared against themselves under the dense model. If the prediction holds, the gain concentrates in Q1, where BM25 failed.

### e5-base

| lang | BM25 quartile | BM25 | dense | change | 95% CI | improved |
|---|---|---:|---:|---:|---|---:|
| pt | Q1 worst | 0.0320 | 0.1379 | +0.1058 | [+0.0828, +0.1309] | 60% |
| pt | Q2 | 0.1743 | 0.1994 | +0.0251 | [+0.0017, +0.0489] | 53% |
| pt | Q3 | 0.3226 | 0.2888 | -0.0338 | [-0.0596, -0.0073] | 43% |
| pt | Q4 best | 0.5344 | 0.4258 | -0.1086 | [-0.1353, -0.0817] | 26% |
| en | Q1 worst | 0.0618 | 0.1495 | +0.0877 | [+0.0677, +0.1092] | 69% |
| en | Q2 | 0.2434 | 0.2584 | +0.0150 | [-0.0097, +0.0410] | 51% |
| en | Q3 | 0.3946 | 0.3454 | -0.0492 | [-0.0723, -0.0263] | 34% |
| en | Q4 best | 0.6008 | 0.5049 | -0.0960 | [-0.1232, -0.0710] | 26% |

### embeddinggemma

| lang | BM25 quartile | BM25 | dense | change | 95% CI | improved |
|---|---|---:|---:|---:|---|---:|
| pt | Q1 worst | 0.0320 | 0.1830 | +0.1510 | [+0.1253, +0.1789] | 80% |
| pt | Q2 | 0.1743 | 0.2634 | +0.0891 | [+0.0627, +0.1159] | 68% |
| pt | Q3 | 0.3226 | 0.3668 | +0.0442 | [+0.0185, +0.0700] | 59% |
| pt | Q4 best | 0.5344 | 0.5005 | -0.0339 | [-0.0592, -0.0087] | 44% |
| en | Q1 worst | 0.0618 | 0.1831 | +0.1213 | [+0.0986, +0.1461] | 75% |
| en | Q2 | 0.2434 | 0.2954 | +0.0520 | [+0.0300, +0.0744] | 62% |
| en | Q3 | 0.3946 | 0.4036 | +0.0090 | [-0.0108, +0.0317] | 48% |
| en | Q4 best | 0.6008 | 0.5481 | -0.0528 | [-0.0796, -0.0264] | 35% |

### qwen3-4b

| lang | BM25 quartile | BM25 | dense | change | 95% CI | improved |
|---|---|---:|---:|---:|---|---:|
| pt | Q1 worst | 0.0320 | 0.1796 | +0.1475 | [+0.1220, +0.1760] | 78% |
| pt | Q2 | 0.1743 | 0.2665 | +0.0922 | [+0.0652, +0.1186] | 66% |
| pt | Q3 | 0.3226 | 0.3410 | +0.0184 | [-0.0118, +0.0508] | 53% |
| pt | Q4 best | 0.5344 | 0.4233 | -0.1111 | [-0.1446, -0.0772] | 38% |
| en | Q1 worst | 0.0618 | 0.2025 | +0.1407 | [+0.1149, +0.1660] | 76% |
| en | Q2 | 0.2434 | 0.2741 | +0.0307 | [+0.0028, +0.0558] | 53% |
| en | Q3 | 0.3946 | 0.3546 | -0.0400 | [-0.0678, -0.0142] | 41% |
| en | Q4 best | 0.6008 | 0.4502 | -0.1506 | [-0.1881, -0.1162] | 26% |

## Reading this

If the prediction holds, two things follow. The failure rate should fall further in Portuguese than in English, and the paired gain should be largest in the bottom BM25 quartile. If instead the gain is flat across quartiles, dense retrieval is doing something other than bridging vocabulary mismatch, and the diagnosis in experiments 07 to 09 does not explain why it helps.

### A caveat on the quartile table

Quartiles are defined on BM25 scores, so the comparison is subject to regression to the mean. Any second method, including a worse one, would tend to score higher than BM25 in BM25's worst quartile and lower in its best, simply because those groups were selected on BM25's own noise. The monotonic pattern alone is therefore not evidence.

What is not explained by regression is the asymmetry between languages. Portuguese and English Q1 groups start at similar levels, 0.032 and 0.062, yet Portuguese gains more from every model. And the failure rate falls further in Portuguese than in English for all three checkpoints, which is a threshold count over the whole distribution rather than a quartile comparison, so regression does not apply to it.
