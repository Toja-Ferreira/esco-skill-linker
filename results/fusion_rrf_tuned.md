# Reciprocal rank fusion, tuned on dev

k swept over [1, 5, 10, 20, 40, 60, 100, 200] and run weights over the same grids as weighted score fusion, selected on 2,431 dev queries by ndcg@10, then scored once on 608 test queries. `rrf` is the untuned default (k = 60, equal weights) for reference. Paired differences are against the stronger single input and against weighted score fusion at its dev-selected weights, 95% percentile bootstrap over queries.

| combination | fusion | k | weight | pt weight | nDCG@10 | over better input (95% CI) | wins | minus weighted score fusion (95% CI) |
|---|---|---:|---:|---:|---:|---|---:|---|
| hybrid pt | rrf | 60 |  |  | 0.3271 | -0.0013 [-0.0103, +0.0080] | 49% | -0.0168 [-0.0224, -0.0110] |
| hybrid pt | rrf tuned | 5 | 0.4 |  | 0.3366 | +0.0082 [+0.0022, +0.0143] | 47% | -0.0074 [-0.0111, -0.0039] |
| hybrid en | rrf | 60 |  |  | 0.3684 | +0.0108 [+0.0020, +0.0196] | 56% | -0.0110 [-0.0154, -0.0064] |
| hybrid en | rrf tuned | 5 | 0.4 |  | 0.3731 | +0.0155 [+0.0098, +0.0213] | 55% | -0.0063 [-0.0101, -0.0029] |
| bilingual embeddinggemma | rrf | 60 |  |  | 0.3563 | -0.0013 [-0.0077, +0.0051] | 47% | -0.0084 [-0.0124, -0.0043] |
| bilingual embeddinggemma | rrf tuned | 1 | 0.2 |  | 0.3616 | +0.0041 [+0.0016, +0.0066] | 36% | -0.0031 [-0.0065, +0.0004] |
| bilingual bm25 | rrf | 60 |  |  | 0.3194 | -0.0058 [-0.0138, +0.0026] | 42% | -0.0101 [-0.0167, -0.0037] |
| bilingual bm25 | rrf tuned | 5 | 0.3 |  | 0.3276 | +0.0024 [-0.0014, +0.0065] | 41% | -0.0019 [-0.0047, +0.0008] |
| all four | rrf | 60 |  |  | 0.3637 | +0.0061 [-0.0033, +0.0158] | 50% | -0.0180 [-0.0243, -0.0116] |
| all four | rrf tuned | 10 | 0.4 | 0.2 | 0.3790 | +0.0214 [+0.0151, +0.0280] | 58% | -0.0027 [-0.0058, +0.0003] |
