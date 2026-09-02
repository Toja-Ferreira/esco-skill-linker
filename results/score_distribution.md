# Score distribution: does gold separate from the field?

Split `test`, labels_desc, stemmed, stopwords removed, BM25 defaults. Each query produces a score over all 13,939 skills; these measure where the gold skills sit within it.
Intervals are 95% percentile bootstrap over queries.

## Separation

Mean gold score minus mean non-gold score, in units of the non-gold standard deviation. Higher means gold stands further above the field, which is what a ranking metric rewards.

| language | separation | 95% CI |
|---|---:|---|
| pt | 3.1672 | [3.0225, 3.3129] |
| en | 3.8174 | [3.6321, 4.0030] |

English separation is +20.5% relative to Portuguese.

## How much competition sits above the best gold skill

| language | non-gold outranking best gold | median | best gold percentile |
|---|---:|---:|---:|
| pt | 14.1 | 1 | 99.891 |
| en | 6.9 | 1 | 99.943 |

## Flatness at the top

Score at rank 10 minus score at rank 100, divided by the score at rank 1. A flatter top means many candidates are nearly tied, so small differences decide the ordering.

| language | flatness | 95% CI |
|---|---:|---|
| pt | 0.2707 | [0.2641, 0.2771] |
| en | 0.2763 | [0.2690, 0.2836] |

## Raw score levels

Included so the normalised measures above can be checked. Absolute BM25 scores are not comparable across corpora; the ratios are what matter.

| language | rank-1 score | mean gold | mean non-gold | non-gold sd |
|---|---:|---:|---:|---:|
| pt | 49.96 | 14.11 | 2.23 | 3.71 |
| en | 67.79 | 20.04 | 2.73 | 4.60 |

## Reading this

If Portuguese separation is materially lower, the residual gap is a signal to noise problem: gold scores as well as it does in English but the field scores well too, so ordering degrades. That would be the mechanism the earlier overlap experiments could not see, since they measured only the query to gold relationship.

If separation is comparable while the retrieval metrics still differ, the cause is not capturable by any aggregate of the score distribution, and lexical analysis has been exhausted.
