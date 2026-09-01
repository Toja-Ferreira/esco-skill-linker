# Weighted lexical overlap

Split `test`. Experiment 03 measured how many gold tokens the query reaches. This measures how much those tokens are worth.
No retrieval is run. IDF is computed over each language's skill corpus using the same smoothed form BM25 Okapi applies.
Intervals are 95% percentile bootstrap over queries.

## Three measures of the same overlap

### Type coverage

Share of gold tokens present in the query. Every token counts once. Reproduces experiment 03.

| field | stemming | pt | en | en advantage |
|---|---|---|---|---:|
| labels | raw | 0.1654 [0.1597, 0.1710] | 0.0912 [0.0880, 0.0945] | -44.8% |
| labels | stemmed | 0.2146 [0.2071, 0.2218] | 0.1245 [0.1200, 0.1289] | -42.0% |
| description | raw | 0.0798 [0.0770, 0.0830] | 0.0789 [0.0758, 0.0822] | -1.2% |
| description | stemmed | 0.1051 [0.1015, 0.1090] | 0.0982 [0.0946, 0.1021] | -6.6% |

### IDF-weighted coverage

The same ratio with each token weighted by its IDF, so common terms contribute little. Closer to what BM25 acts on.

| field | stemming | pt | en | en advantage |
|---|---|---|---|---:|
| labels | raw | 0.1241 [0.1190, 0.1290] | 0.0710 [0.0682, 0.0738] | -42.8% |
| labels | stemmed | 0.1700 [0.1635, 0.1765] | 0.0998 [0.0958, 0.1038] | -41.3% |
| description | raw | 0.0481 [0.0461, 0.0503] | 0.0534 [0.0511, 0.0561] | +11.1% |
| description | stemmed | 0.0687 [0.0660, 0.0716] | 0.0702 [0.0672, 0.0734] | +2.1% |

### Content-only coverage

Type coverage after removing each corpus's 50 most frequent terms, standing in for a stopword list.

| field | stemming | pt | en | en advantage |
|---|---|---|---|---:|
| labels | raw | 0.0968 [0.0917, 0.1017] | 0.0623 [0.0596, 0.0649] | -35.6% |
| labels | stemmed | 0.1335 [0.1271, 0.1399] | 0.0860 [0.0820, 0.0897] | -35.6% |
| description | raw | 0.0424 [0.0404, 0.0443] | 0.0506 [0.0483, 0.0530] | +19.3% |
| description | stemmed | 0.0616 [0.0591, 0.0642] | 0.0636 [0.0607, 0.0666] | +3.2% |

## Most frequent corpus terms

The terms the weighting discounts. If the Portuguese list is dominated by function words while the English list carries content words, that is the mechanism.

**pt, stemmed, description corpus**  
`de(11485)` `e(11270)` `a(8071)` `com(5682)` `par(5267)` `o(5057)` `os(4898)` `as(4264)` `em(3952)` `ou(3469)` `que(3099)` `da(3038)` `do(2834)` `utiliz(2591)` `dos(2362)`

**en, stemmed, description corpus**  
`and(11250)` `the(9085)` `of(7593)` `to(6945)` `in(4970)` `or(3493)` `a(3441)` `as(3075)` `for(2941)` `use(2691)` `such(2514)` `with(2254)` `on(1955)` `that(1788)` `by(1540)`

## Vocabulary size

| field | stemming | pt | en |
|---|---|---:|---:|
| labels | raw | 7,694 | 12,369 |
| labels | stemmed | 5,336 | 7,609 |
| description | raw | 17,315 | 15,349 |
| description | stemmed | 9,517 | 8,930 |
