# Lexical overlap between queries and their gold skills

Split `test`. For each occupation, the share of its gold skills' vocabulary that also appears in the occupation description. This is the quantity BM25 depends on: a token present in a gold skill but absent from the query contributes nothing to that skill's score.
No retrieval is run, so nothing here depends on BM25 parameters.
Intervals are 95% percentile bootstrap over queries.

## Gold vocabulary covered by the query

| field | stemming | pt | en | en advantage |
|---|---|---|---|---:|
| labels | raw | 0.1654 [0.1597, 0.1710] | 0.0912 [0.0880, 0.0945] | -44.8% |
| labels | stemmed | 0.2146 [0.2071, 0.2218] | 0.1245 [0.1200, 0.1289] | -42.0% |
| description | raw | 0.0798 [0.0770, 0.0830] | 0.0789 [0.0758, 0.0822] | -1.2% |
| description | stemmed | 0.1051 [0.1015, 0.1090] | 0.0982 [0.0946, 0.1021] | -6.6% |

## What stemming recovers

Relative gain in coverage from stemming, within each language. A language whose stemmer conflates more aggressively gains more.

| field | pt | en |
|---|---:|---:|
| labels | +29.8% | +36.4% |
| description | +31.6% | +24.5% |

## Gold vocabulary size

Mean distinct tokens across an occupation's gold skills. Sets the denominator above, and shows how much larger the English label vocabulary is.

| field | stemming | pt | en |
|---|---|---:|---:|
| labels | raw | 73 | 159 |
| labels | stemmed | 68 | 128 |
| description | raw | 271 | 257 |
| description | stemmed | 237 | 227 |

## Reading this

On `description`, both languages have complete coverage of the field, so a gap there is about word choice rather than about how much text exists. If the gap persists under stemming, it is vocabulary drift between independently translated records. If stemming closes it, the gap was morphological and the retrieval difference is a stemmer question.

On `labels`, the English vocabulary is far larger because of alternative label coverage, so coverage figures there are not directly comparable between languages: the denominators differ.
