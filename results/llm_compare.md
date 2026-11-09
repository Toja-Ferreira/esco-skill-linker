# Local against API reranking

Both models rerank the same first stage at depth 20 on the same 608 test queries, so every comparison here is paired by query. Intervals are 95% percentile bootstrap over queries.

## Model against model

| language | DeepSeek minus Qwen3-4B, nDCG@10 (95% CI) | DeepSeek better | Qwen better |
|---|---|---:|---:|
| pt | +0.0331 [+0.0266, +0.0393] | 61% | 30% |
| en | +0.0311 [+0.0250, +0.0375] | 65% | 31% |

## Language gap

English minus Portuguese for the same occupation. Relative is the mean gap over the Portuguese mean.

| system | gap, nDCG@10 (95% CI) | relative |
|---|---|---:|
| first stage | +0.0355 [+0.0257, +0.0448] | +10.3% |
| Qwen3-4B (local) | +0.0361 [+0.0261, +0.0454] | +9.5% |
| DeepSeek (API) | +0.0341 [+0.0238, +0.0445] | +8.3% |

## Change in the gap

A negative value means the second system has a smaller English lead than the first. An interval that crosses zero means the change is not distinguishable from noise at this sample size.

| comparison | change (95% CI) |
|---|---|
| Qwen3-4B (local) minus first stage | +0.0006 [-0.0094, +0.0107] |
| DeepSeek (API) minus first stage | -0.0014 [-0.0118, +0.0089] |
| DeepSeek (API) minus Qwen3-4B (local) | -0.0020 [-0.0103, +0.0068] |

## Cost on the test split

Seconds per query are wall time divided by queries: batched on the local GPU, eight concurrent requests for the API. Token counts come from different tokenisers, so compare them within a model, not across.

| system | language | s/query | prompt tokens | completion tokens |
|---|---|---:|---:|---:|
| Qwen3-4B (local) | pt | 1.63 | 827,512 | 21,545 |
| Qwen3-4B (local) | en | 1.23 | 519,413 | 21,466 |
| DeepSeek (API) | pt | 0.11 | 784,547 | 18,240 |
| DeepSeek (API) | en | 0.11 | 504,227 | 18,240 |
