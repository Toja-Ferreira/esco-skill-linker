# Cross-encoder reranking

`Qwen/Qwen3-Reranker-4B` (Apache-2.0) reranking the hybrid weighted score fusion first stage from experiment 13.
Shortlist depth selected on a random subsample of 200 dev queries, then applied once to the full test split. Scoring runs once at the deepest shortlist; shallower depths are truncations of it.
Intervals are 95% percentile bootstrap over queries.

## First-stage ceiling

Mean recall of essential skills within the shortlist. A reranker cannot promote what the first stage never retrieved, so these bound everything below.

| language | depth 10 | depth 20 | depth 50 | depth 100 | depth 200 |
|---|---:|---:|---:|---:|---:|
| pt | 0.1379 | 0.1951 | 0.2845 | 0.3608 | 0.4406 |
| en | 0.1554 | 0.2202 | 0.3110 | 0.3878 | 0.4670 |

## Depth sweep on dev

Depth 0 is the first stage without reranking.

| depth | en | pt |
|---|---:|---:|
| 0 (none) | 0.3933 | 0.3551 |
| 10 | 0.4029 | 0.3615 |
| 20 | 0.4229 | 0.3797 |

## Test results

| language | stage | depth | nDCG@10 (95% CI) | P@10 | R@10 | MRR |
|---|---|---:|---:|---:|---:|---:|
| pt | first stage |  | 0.3439 [0.3279, 0.3603] | 0.262 | 0.138 | 0.654 |
| pt | reranked | 20 | 0.3693 [0.3535, 0.3864] | 0.288 | 0.150 | 0.670 |
| pt | random | 20 | 0.2161 [0.2098, 0.2213] | nan | nan | nan |
| pt | oracle | 10 | 0.4307 [0.4145, 0.4467] | 0.262 | 0.138 | 0.912 |
| pt | oracle | 20 | 0.5540 [0.5356, 0.5729] | 0.379 | 0.194 | 0.944 |
| pt | oracle | 50 | 0.7066 [0.6887, 0.7250] | 0.548 | 0.276 | 0.975 |
| pt | oracle | 100 | 0.7968 [0.7808, 0.8132] | 0.664 | 0.336 | 0.988 |
| en | first stage |  | 0.3794 [0.3629, 0.3960] | 0.292 | 0.155 | 0.700 |
| en | reranked | 20 | 0.4140 [0.3985, 0.4301] | 0.325 | 0.173 | 0.729 |
| en | random | 20 | 0.2408 [0.2323, 0.2517] | nan | nan | nan |
| en | oracle | 10 | 0.4648 [0.4492, 0.4811] | 0.292 | 0.155 | 0.926 |
| en | oracle | 20 | 0.5932 [0.5756, 0.6107] | 0.418 | 0.219 | 0.963 |
| en | oracle | 50 | 0.7342 [0.7178, 0.7508] | 0.578 | 0.299 | 0.990 |
| en | oracle | 100 | 0.8212 [0.8064, 0.8358] | 0.695 | 0.358 | 0.997 |

## Is the result real, or an implementation error?

A reranker with weak but genuine signal should land between a random shuffle of the shortlist and the first stage. Landing at random means no signal at all. Landing **below** random would mean the ordering is inverted or misaligned, which would make this a bug rather than a finding.

AUC is the probability that a randomly chosen gold candidate outscores a randomly chosen non-gold one from the same shortlist. 0.5 is chance; it tests whether the model can separate them at all, independently of how the ranking is assembled. The bracketed range is the 2.5th to 97.5th percentile **across queries**, not uncertainty on the mean: a query with one or two gold items in its shortlist yields an AUC of 0 or 1 by construction, so the spread is wide even when the mean is well determined.

| language | random | reranked | first stage | recovered | gold-vs-rest AUC | per-query range | mean gold | mean other |
|---|---:|---:|---:|---:|---:|---|---:|---:|
| pt | 0.2161 | 0.3693 | 0.3439 | 120% | 0.761 | [0.39, 1.00] | 0.7834 | 0.4697 |
| en | 0.2408 | 0.4140 | 0.3794 | 125% | 0.779 | [0.44, 1.00] | 0.7280 | 0.3726 |

**Recovered** is where the reranker sits between a random shuffle and the first stage. Near 100% means it reproduces the first stage's ordering quality without exceeding it. Above 0% rules out an inverted or misaligned implementation.

## How much ordering headroom exists

The oracle sorts each shortlist by true relevance, so it is what a flawless reranker would reach over the same candidates. It involves no model and bounds every reranking attempt on this first stage.

The **reranked** column is filled only at the depth selected on dev, since that is the only depth scored on test. Blank cells are depths that were not run, not missing results.

| language | depth | first stage | reranked | oracle | headroom captured |
|---|---:|---:|---:|---:|---:|
| pt | 10 | 0.3439 |  | 0.4307 |  |
| pt | 20 | 0.3439 | 0.3693 | 0.5540 | 12% |
| pt | 50 | 0.3439 |  | 0.7066 |  |
| pt | 100 | 0.3439 |  | 0.7968 |  |
| en | 10 | 0.3794 |  | 0.4648 |  |
| en | 20 | 0.3794 | 0.4140 | 0.5932 | 16% |
| en | 50 | 0.3794 |  | 0.7342 |  |
| en | 100 | 0.3794 |  | 0.8212 |  |

A large gap between the first stage and the oracle means the ordering problem is real and unsolved, not that the shortlist is exhausted. Those are different conclusions and they point at different work.

## Paired change against the first stage

Both stages are scored on the identical queries, so the comparison is paired. **Won** is the share of queries where reranking improved the result.

| language | first stage | reranked | gain | paired difference (95% CI) | won |
|---|---:|---:|---:|---|---:|
| pt | 0.3439 | 0.3693 | +7.4% | +0.0254 [+0.0168, +0.0348] | 54% |
| en | 0.3794 | 0.4140 | +9.1% | +0.0346 [+0.0254, +0.0440] | 60% |

## Cost

A cross-encoder scores every pair individually, so nothing is precomputed and cost scales with shortlist depth. It comes on top of the first stage: the bi-encoder answers in well under a millisecond per query once indexed, and BM25 over the full index takes tens of milliseconds (experiment 01).

| language | pairs scored | total s | ms/query |
|---|---:|---:|---:|
| pt | 12,160 | 657.2 | 1081.0 |
| en | 12,160 | 516.8 | 849.9 |
