# The residual language gap under dense retrieval

Per-query `ndcg@10` on the test split, paired on occupation. The gold set for an occupation is identical in both languages, since ESCO assigns one URI per concept, so the pairing is exact.
No retrieval is re-run.

## Is the residual a tail or is it uniform?

Absolute gap between English and Portuguese at each percentile of the per-query score distribution. A tail effect shows a large gap at the bottom and a small one at the top. A uniform effect is flat.

| model | p10 | p25 | p50 | p75 | p90 | relative gap |
|---|---:|---:|---:|---:|---:|---:|
| bm25 | +0.0367 | +0.0691 | +0.0775 | +0.0707 | +0.0575 | +22.3% |
| e5-base | +0.0650 | +0.0568 | +0.0561 | +0.0657 | +0.0600 | +19.6% |
| embeddinggemma | +0.0137 | +0.0374 | +0.0314 | +0.0243 | +0.0233 | +8.9% |
| qwen3-4b | +0.0377 | +0.0373 | +0.0334 | +0.0171 | -0.0054 | +5.9% |

Portuguese and English distributions separately:

| model | lang | p10 | p25 | p50 | p75 | p90 |
|---|---|---:|---:|---:|---:|---:|
| bm25 | pt | 0.0000 | 0.0991 | 0.2413 | 0.4004 | 0.5549 |
| bm25 | en | 0.0367 | 0.1682 | 0.3188 | 0.4711 | 0.6124 |
| e5-base | pt | 0.0000 | 0.0953 | 0.2424 | 0.3882 | 0.5225 |
| e5-base | en | 0.0650 | 0.1521 | 0.2985 | 0.4539 | 0.5825 |
| embeddinggemma | pt | 0.0694 | 0.1748 | 0.3223 | 0.4660 | 0.5947 |
| embeddinggemma | en | 0.0831 | 0.2122 | 0.3536 | 0.4903 | 0.6180 |
| qwen3-4b | pt | 0.0256 | 0.1269 | 0.2935 | 0.4459 | 0.5951 |
| qwen3-4b | en | 0.0634 | 0.1642 | 0.3268 | 0.4630 | 0.5896 |

## Do the languages still fail on the same queries?

| model | Pearson r | Spearman | pt fails | en fails | both | pt only | en only |
|---|---:|---:|---:|---:|---:|---:|---:|
| bm25 | 0.737 | 0.729 | 25.2% | 18.8% | 13.5% | 11.7% | 5.3% |
| e5-base | 0.698 | 0.669 | 25.2% | 16.9% | 11.7% | 13.5% | 5.3% |
| embeddinggemma | 0.825 | 0.806 | 15.3% | 12.3% | 9.0% | 6.2% | 3.3% |
| qwen3-4b | 0.749 | 0.737 | 21.5% | 16.0% | 10.2% | 11.3% | 5.8% |

A query counts as failed below 0.10. The **pt only** column is the share of occupations where Portuguese fails and English does not, which is exactly what bilingual fusion could recover, since the deployment setting supplies both texts for every course unit.

## Mean paired difference

| model | pt | en | difference | 95% CI |
|---|---:|---:|---:|---|
| bm25 | 0.2658 | 0.3252 | +0.0594 | [+0.0479, +0.0709] |
| e5-base | 0.2630 | 0.3145 | +0.0516 | [+0.0391, +0.0635] |
| embeddinggemma | 0.3284 | 0.3576 | +0.0291 | [+0.0194, +0.0383] |
| qwen3-4b | 0.3026 | 0.3203 | +0.0178 | [+0.0060, +0.0286] |

## Reading this

If the percentile gaps under the dense models are flat, the residual is a uniform representation difference rather than the tail phenomenon that produced the lexical gap, and the explanation for one does not carry to the other.

A low correlation means the two languages still fail on different occupations, which is the precondition for bilingual fusion. A correlation that rises sharply under a dense model would mean the model has normalised the language-specific failures away, leaving shared task difficulty, and fusion would have less to recover.
