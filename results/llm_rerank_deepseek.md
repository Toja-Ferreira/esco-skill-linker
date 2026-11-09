# Listwise LLM reranking

`deepseek-chat` (api) reranking the hybrid weighted fusion first stage. The whole shortlist goes into one prompt, so the model can compare candidates against each other, which a pointwise cross-encoder cannot.
Depth selected on a dev subsample, applied once to test. Intervals are 95% percentile bootstrap over queries.

## Test results

| language | stage | depth | nDCG@10 (95% CI) | P@10 | R@10 | MRR |
|---|---|---:|---:|---:|---:|---:|
| pt | first stage |  | 0.3439 [0.3279, 0.3603] | 0.262 | 0.138 | 0.654 |
| pt | llm reranked | 20 | 0.4119 [0.3953, 0.4287] | 0.315 | 0.164 | 0.739 |
| en | first stage |  | 0.3794 [0.3629, 0.3960] | 0.292 | 0.155 | 0.700 |
| en | llm reranked | 20 | 0.4460 [0.4298, 0.4629] | 0.345 | 0.183 | 0.768 |

## Paired change against the first stage

| language | first stage | llm | gain | paired difference (95% CI) | won |
|---|---:|---:|---:|---|---:|
| pt | 0.3439 | 0.4119 | +19.8% | +0.0680 [+0.0594, +0.0775] | 70% |
| en | 0.3794 | 0.4460 | +17.6% | +0.0666 [+0.0580, +0.0765] | 68% |

## Against the other rerankers and the ceiling

The oracle is taken at the same depth as the LLM, since a reranker cannot recover a skill it was never shown.

| language | depth | first stage | bge cross-encoder | this LLM | oracle | headroom captured |
|---|---:|---:|---:|---:|---:|---:|
| pt | 20 | 0.3439 | 0.3482 | 0.4119 | 0.5540 | 32% |
| en | 20 | 0.3794 | 0.3793 | 0.4460 | 0.5932 | 31% |

## Output reliability

Listwise output is a list of candidate numbers, so a malformed response is an out-of-range index, a repeat, or an omission. Each is counted rather than quietly repaired: a method that mangles a tenth of its queries is not usable whatever its mean looks like. Omitted candidates keep their first-stage order beneath the ranked block, and an unparsable response leaves the query untouched.

| language | unparsable | invalid/query | duplicates/query | omitted/query |
|---|---:|---:|---:|---:|
| pt | 0.0% | 0.00 | 0.00 | 0.00 |
| en | 0.0% | 0.00 | 0.00 | 0.00 |

## Cost

| language | depth | s/query | prompt tokens | completion tokens |
|---|---:|---:|---:|---:|
| pt | 20 | 0.11 | 784,547 | 18,240 |
| en | 20 | 0.11 | 504,227 | 18,240 |

## Depth sweep on dev

| depth | en | pt |
|---|---:|---:|
| 0 (none) | 0.3933 | 0.3551 |
| 10 | 0.4172 | 0.3861 |
| 20 | 0.4544 | 0.4299 |
