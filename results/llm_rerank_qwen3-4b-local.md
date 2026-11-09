# Listwise LLM reranking

`Qwen/Qwen3-4B-Instruct-2507` (local) reranking the hybrid weighted fusion first stage. The whole shortlist goes into one prompt, so the model can compare candidates against each other, which a pointwise cross-encoder cannot.
Depth selected on a dev subsample, applied once to test. Intervals are 95% percentile bootstrap over queries.

## Test results

| language | stage | depth | nDCG@10 (95% CI) | P@10 | R@10 | MRR |
|---|---|---:|---:|---:|---:|---:|
| pt | first stage |  | 0.3439 [0.3279, 0.3603] | 0.262 | 0.138 | 0.654 |
| pt | llm reranked | 20 | 0.3788 [0.3631, 0.3958] | 0.287 | 0.150 | 0.717 |
| en | first stage |  | 0.3794 [0.3629, 0.3960] | 0.292 | 0.155 | 0.700 |
| en | llm reranked | 20 | 0.4149 [0.3991, 0.4317] | 0.318 | 0.169 | 0.748 |

## Paired change against the first stage

| language | first stage | llm | gain | paired difference (95% CI) | won |
|---|---:|---:|---:|---|---:|
| pt | 0.3439 | 0.3788 | +10.1% | +0.0349 [+0.0266, +0.0440] | 59% |
| en | 0.3794 | 0.4149 | +9.4% | +0.0355 [+0.0274, +0.0448] | 61% |

## Against the other rerankers and the ceiling

The oracle is taken at the same depth as the LLM, since a reranker cannot recover a skill it was never shown.

| language | depth | first stage | bge cross-encoder | this LLM | oracle | headroom captured |
|---|---:|---:|---:|---:|---:|---:|
| pt | 20 | 0.3439 | 0.3482 | 0.3788 | 0.5540 | 17% |
| en | 20 | 0.3794 | 0.3793 | 0.4149 | 0.5932 | 17% |

## Output reliability

Listwise output is a list of candidate numbers, so a malformed response is an out-of-range index, a repeat, or an omission. Each is counted rather than quietly repaired: a method that mangles a tenth of its queries is not usable whatever its mean looks like. Omitted candidates keep their first-stage order beneath the ranked block, and an unparsable response leaves the query untouched.

| language | unparsable | invalid/query | duplicates/query | omitted/query |
|---|---:|---:|---:|---:|
| pt | 0.0% | 0.00 | 0.01 | 0.01 |
| en | 0.0% | 0.00 | 0.00 | 0.00 |

## Cost

| language | depth | s/query | prompt tokens | completion tokens |
|---|---:|---:|---:|---:|
| pt | 20 | 1.63 | 827,512 | 21,545 |
| en | 20 | 1.23 | 519,413 | 21,466 |

## Depth sweep on dev

| depth | en | pt |
|---|---:|---:|
| 0 (none) | 0.3933 | 0.3551 |
| 10 | 0.4074 | 0.3757 |
| 20 | 0.4202 | 0.3928 |
