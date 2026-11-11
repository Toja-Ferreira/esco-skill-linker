# Local against API reranking

Both models rerank the same first stage at depth 20 on the same 608 test queries, so every comparison here is paired by query. Intervals are 95% percentile bootstrap over queries. The first stage is hybrid weighted score fusion of BM25 and EmbeddingGemma (experiment 13); those two inputs are included so the language gap can be followed through every stage.

## Model against model

| language | DeepSeek minus Qwen3-4B, nDCG@10 (95% CI) | DeepSeek better | Qwen better |
|---|---|---:|---:|
| pt | +0.0331 [+0.0266, +0.0393] | 61% | 30% |
| en | +0.0311 [+0.0250, +0.0375] | 65% | 31% |
| pt | -0.0095 [-0.0172, -0.0018] | 42% | 52% |
| en | -0.0010 [-0.0079, +0.0059] | 50% | 45% |
| pt | +0.0342 [+0.0260, +0.0432] | 58% | 37% |
| en | +0.0393 [+0.0308, +0.0480] | 64% | 33% |

## Pointwise control

Qwen3-Reranker-4B scores one candidate at a time, on the same Qwen3 4B base as the listwise model, with experiment 15's depths, candidate text and dev sample. Decision rules are in `experiments/14_rerank.py`.

| comparison | language | difference, nDCG@10 (95% CI) | pointwise better |
|---|---|---|---:|
| Qwen3-Reranker-4B (pointwise) minus first stage | pt | +0.0254 [+0.0168, +0.0348] | 54% |
| Qwen3-Reranker-4B (pointwise) minus first stage | en | +0.0346 [+0.0254, +0.0440] | 60% |
| Qwen3-Reranker-4B (pointwise) minus Qwen3-4B (local) | pt | -0.0095 [-0.0172, -0.0018] | 42% |
| Qwen3-Reranker-4B (pointwise) minus Qwen3-4B (local) | en | -0.0010 [-0.0079, +0.0059] | 50% |
| Qwen3-Reranker-4B (pointwise) minus DeepSeek (API) | pt | -0.0426 [-0.0502, -0.0355] | 29% |
| Qwen3-Reranker-4B (pointwise) minus DeepSeek (API) | en | -0.0320 [-0.0399, -0.0249] | 33% |
| Qwen3-Reranker-4B (pointwise) minus Qwen3-Reranker-0.6B (pointwise) | pt | +0.0342 [+0.0260, +0.0432] | 58% |
| Qwen3-Reranker-4B (pointwise) minus Qwen3-Reranker-0.6B (pointwise) | en | +0.0393 [+0.0308, +0.0480] | 64% |

Whether the listwise format helps one language more: per occupation, (listwise minus pointwise) in Portuguese minus the same in English, +0.0085 [-0.0004, +0.0178]. The per-language comparisons above are not a test of a difference between languages; this is.

## Language gap

English minus Portuguese for the same occupation. Relative is the mean gap over the Portuguese mean.

| system | gap, nDCG@10 (95% CI) | relative |
|---|---|---:|
| BM25 | +0.0594 [+0.0479, +0.0709] | +22.3% |
| EmbeddingGemma | +0.0291 [+0.0194, +0.0383] | +8.9% |
| first stage | +0.0355 [+0.0257, +0.0448] | +10.3% |
| Qwen3-4B (local) | +0.0361 [+0.0261, +0.0454] | +9.5% |
| DeepSeek (API) | +0.0341 [+0.0238, +0.0445] | +8.3% |
| oracle@10 | +0.0341 [+0.0236, +0.0445] | +7.9% |
| oracle@20 | +0.0393 [+0.0288, +0.0501] | +7.1% |
| oracle@50 | +0.0276 [+0.0175, +0.0377] | +3.9% |
| oracle@100 | +0.0244 [+0.0156, +0.0334] | +3.1% |
| Qwen3-Reranker-4B (pointwise) | +0.0446 [+0.0350, +0.0543] | +12.1% |
| Qwen3-Reranker-0.6B (pointwise) | +0.0395 [+0.0293, +0.0498] | +11.8% |

## Change in the gap

A negative value means the second system has a smaller English lead than the first. An interval that crosses zero means the change is not distinguishable from noise at this sample size.

| comparison | change (95% CI) |
|---|---|
| EmbeddingGemma minus BM25 | -0.0302 [-0.0440, -0.0176] |
| first stage minus EmbeddingGemma | +0.0063 [-0.0011, +0.0140] |
| first stage minus BM25 | -0.0239 [-0.0349, -0.0135] |
| Qwen3-4B (local) minus first stage | +0.0006 [-0.0094, +0.0107] |
| DeepSeek (API) minus first stage | -0.0014 [-0.0118, +0.0089] |
| DeepSeek (API) minus Qwen3-4B (local) | -0.0020 [-0.0103, +0.0068] |
| Qwen3-Reranker-4B (pointwise) minus first stage | +0.0092 [-0.0009, +0.0192] |

## Gap removed by perfect ordering

The oracle sorts the first stage's top d candidates by true relevance (experiment 14). Share removed is one minus the oracle's mean gap over the first stage's, with both resampled on the same occupations.

| depth | share of the gap removed (95% CI) |
|---|---|
| 10 | 4% [-14%, 21%] |
| 20 | -11% [-46%, 16%] |
| 50 | 22% [-12%, 49%] |
| 100 | 31% [-3%, 56%] |

## Cost on the test split

Seconds per query are wall time divided by queries: batched on the local GPU, eight concurrent requests for the API. Token counts come from different tokenisers, so compare them within a model, not across.

| system | language | s/query | prompt tokens | completion tokens |
|---|---|---:|---:|---:|
| Qwen3-4B (local) | pt | 1.63 | 827,512 | 21,545 |
| Qwen3-4B (local) | en | 1.23 | 519,413 | 21,466 |
| DeepSeek (API) | pt | 0.11 | 784,547 | 18,240 |
| DeepSeek (API) | en | 0.11 | 504,227 | 18,240 |
