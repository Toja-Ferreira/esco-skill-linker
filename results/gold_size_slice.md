# Retrieval quality by gold set size

BM25, `labels_desc`, stemmed, test split. Occupations are split into quartiles by number of essential skills. Computed from the per-query results recorded by `experiments/01_bm25.py`; no retrieval is re-run.
Intervals are 95% percentile bootstrap over queries within each bucket.

## Buckets

| bucket | queries | essential skills | median | max recall@10 |
|---|---:|---|---:|---:|
| Q1 smallest | 159 | 6–14 | 12 | 0.861 |
| Q2 | 163 | 15–20 | 18 | 0.577 |
| Q3 | 139 | 21–27 | 24 | 0.419 |
| Q4 largest | 147 | 28–74 | 34 | 0.279 |

Recall ceilings differ sharply between buckets, so recall is not comparable across them. nDCG normalises by the ideal ranking and is.

## ndcg@10

| bucket | pt | en | en advantage |
|---|---|---|---:|
| Q1 smallest | 0.237 [0.210, 0.265] | 0.308 [0.277, 0.339] | +29.7% |
| Q2 | 0.247 [0.215, 0.278] | 0.310 [0.275, 0.344] | +25.4% |
| Q3 | 0.224 [0.196, 0.254] | 0.289 [0.261, 0.318] | +28.9% |
| Q4 largest | 0.281 [0.250, 0.314] | 0.330 [0.296, 0.364] | +17.2% |

## recall@10

| bucket | pt | en | en advantage |
|---|---|---|---:|
| Q1 smallest | 0.146 [0.125, 0.166] | 0.188 [0.165, 0.211] | +28.9% |
| Q2 | 0.107 [0.092, 0.121] | 0.139 [0.122, 0.156] | +30.4% |
| Q3 | 0.073 [0.063, 0.083] | 0.093 [0.083, 0.103] | +27.7% |
| Q4 largest | 0.065 [0.057, 0.074] | 0.076 [0.067, 0.085] | +17.2% |

## precision@10

| bucket | pt | en | en advantage |
|---|---|---|---:|
| Q1 smallest | 0.160 [0.138, 0.182] | 0.208 [0.184, 0.232] | +29.4% |
| Q2 | 0.185 [0.160, 0.209] | 0.240 [0.210, 0.269] | +29.5% |
| Q3 | 0.174 [0.152, 0.199] | 0.222 [0.198, 0.246] | +27.3% |
| Q4 largest | 0.228 [0.200, 0.256] | 0.271 [0.241, 0.300] | +18.8% |

## mrr

| bucket | pt | en | en advantage |
|---|---|---|---:|
| Q1 smallest | 0.514 [0.451, 0.578] | 0.601 [0.539, 0.665] | +16.9% |
| Q2 | 0.490 [0.426, 0.554] | 0.590 [0.525, 0.653] | +20.4% |
| Q3 | 0.478 [0.419, 0.539] | 0.615 [0.549, 0.680] | +28.5% |
| Q4 largest | 0.542 [0.478, 0.606] | 0.590 [0.527, 0.654] | +8.9% |

## Separability within buckets

Each bucket holds roughly a quarter of the split, so intervals are wider than the pooled comparison and individual buckets may not separate. What matters is whether the direction and magnitude are consistent across buckets.

| bucket | queries | pt nDCG@10 | en nDCG@10 | separable at this n |
|---|---:|---|---|---|
| Q1 smallest | 159 | 0.237 [0.210, 0.265] | 0.308 [0.277, 0.339] | yes |
| Q2 | 163 | 0.247 [0.215, 0.278] | 0.310 [0.275, 0.344] | no |
| Q3 | 139 | 0.224 [0.196, 0.254] | 0.289 [0.261, 0.318] | yes |
| Q4 largest | 147 | 0.281 [0.250, 0.314] | 0.330 [0.296, 0.364] | no |

English leads in 4 of 4 buckets, by +17.2% to +29.7%. Consistent direction across independent buckets is the evidence here; no single bucket is individually decisive.
