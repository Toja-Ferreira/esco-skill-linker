# BM25 with and without stopword removal

Split `dev`, 2,431 occupation-description queries against all 13,939 skills. Stopword lists are NLTK's, which derive from Snowball and pair with the stemmers in use. Removal happens before stemming, since the lists are of surface forms.
Intervals are 95% percentile bootstrap over queries.

## Effect of removing stopwords

nDCG@10, and the relative change from keeping them.

| lang | documents | stemming | kept | removed | change |
|---|---|---|---:|---:|---:|
| pt | preferred | raw | 0.1662 | 0.2269 | +36.5% |
| pt | preferred | stemmed | 0.1929 | 0.2476 | +28.4% |
| pt | labels | raw | 0.1661 | 0.2310 | +39.1% |
| pt | labels | stemmed | 0.1901 | 0.2501 | +31.6% |
| pt | labels_desc | raw | 0.2361 | 0.2613 | +10.7% |
| pt | labels_desc | stemmed | 0.2579 | 0.2798 | +8.5% |
| pt | description | raw | 0.1942 | 0.2163 | +11.4% |
| pt | description | stemmed | 0.2155 | 0.2374 | +10.1% |
| en | preferred | raw | 0.1999 | 0.2687 | +34.4% |
| en | preferred | stemmed | 0.2334 | 0.2938 | +25.9% |
| en | labels | raw | 0.2350 | 0.2802 | +19.3% |
| en | labels | stemmed | 0.2569 | 0.2979 | +16.0% |
| en | labels_desc | raw | 0.3001 | 0.3187 | +6.2% |
| en | labels_desc | stemmed | 0.3139 | 0.3303 | +5.2% |
| en | description | raw | 0.2343 | 0.2478 | +5.8% |
| en | description | stemmed | 0.2559 | 0.2679 | +4.7% |

## Does the Portuguese gap narrow?

English advantage in nDCG@10, before and after removal. The prediction under test is that removal helps Portuguese more, so the advantage shrinks.

| documents | stemming | gap, stops kept | gap, stops removed | change |
|---|---|---:|---:|---:|
| preferred | raw | +20.3% | +18.4% | -1.8 pp |
| preferred | stemmed | +21.0% | +18.6% | -2.4 pp |
| labels | raw | +41.4% | +21.3% | -20.1 pp |
| labels | stemmed | +35.1% | +19.1% | -16.0 pp |
| labels_desc | raw | +27.1% | +22.0% | -5.2 pp |
| labels_desc | stemmed | +21.7% | +18.0% | -3.7 pp |
| description | raw | +20.6% | +14.6% | -6.1 pp |
| description | stemmed | +18.7% | +12.9% | -5.9 pp |

## Full results

| lang | documents | stemming | stopwords | P@10 | R@10 | MRR | nDCG@10 (95% CI) | tok/doc |
|---|---|---|---|---:|---:|---:|---:|---:|
| pt | preferred | raw | kept | 0.122 | 0.064 | 0.384 | 0.166 [0.160, 0.173] | 4.9 |
| pt | labels | raw | kept | 0.120 | 0.063 | 0.392 | 0.166 [0.160, 0.173] | 6.1 |
| pt | labels_desc | raw | kept | 0.174 | 0.091 | 0.511 | 0.236 [0.229, 0.244] | 31.3 |
| pt | description | raw | kept | 0.141 | 0.074 | 0.439 | 0.194 [0.187, 0.201] | 25.2 |
| pt | preferred | stemmed | kept | 0.142 | 0.075 | 0.434 | 0.193 [0.186, 0.200] | 4.9 |
| pt | labels | stemmed | kept | 0.139 | 0.073 | 0.432 | 0.190 [0.183, 0.197] | 6.1 |
| pt | labels_desc | stemmed | kept | 0.190 | 0.100 | 0.540 | 0.258 [0.251, 0.265] | 31.3 |
| pt | description | stemmed | kept | 0.158 | 0.084 | 0.467 | 0.216 [0.209, 0.222] | 25.2 |
| pt | preferred | raw | removed | 0.169 | 0.088 | 0.493 | 0.227 [0.219, 0.235] | 3.4 |
| pt | labels | raw | removed | 0.172 | 0.090 | 0.498 | 0.231 [0.224, 0.239] | 4.3 |
| pt | labels_desc | raw | removed | 0.195 | 0.103 | 0.544 | 0.261 [0.254, 0.269] | 19.1 |
| pt | description | raw | removed | 0.160 | 0.084 | 0.469 | 0.216 [0.209, 0.224] | 14.8 |
| pt | preferred | stemmed | removed | 0.184 | 0.097 | 0.527 | 0.248 [0.240, 0.255] | 3.4 |
| pt | labels | stemmed | removed | 0.187 | 0.099 | 0.522 | 0.250 [0.243, 0.258] | 4.3 |
| pt | labels_desc | stemmed | removed | 0.211 | 0.112 | 0.563 | 0.280 [0.272, 0.287] | 19.1 |
| pt | description | stemmed | removed | 0.177 | 0.094 | 0.494 | 0.237 [0.230, 0.245] | 14.8 |
| en | preferred | raw | kept | 0.144 | 0.076 | 0.454 | 0.200 [0.192, 0.207] | 3.6 |
| en | labels | raw | kept | 0.175 | 0.092 | 0.498 | 0.235 [0.228, 0.243] | 29.3 |
| en | labels_desc | raw | kept | 0.223 | 0.118 | 0.601 | 0.300 [0.293, 0.308] | 51.5 |
| en | description | raw | kept | 0.172 | 0.091 | 0.504 | 0.234 [0.227, 0.241] | 22.2 |
| en | preferred | stemmed | kept | 0.172 | 0.092 | 0.504 | 0.233 [0.226, 0.241] | 3.6 |
| en | labels | stemmed | kept | 0.192 | 0.101 | 0.532 | 0.257 [0.249, 0.265] | 29.3 |
| en | labels_desc | stemmed | kept | 0.234 | 0.124 | 0.620 | 0.314 [0.306, 0.322] | 51.5 |
| en | description | stemmed | kept | 0.190 | 0.102 | 0.530 | 0.256 [0.249, 0.263] | 22.2 |
| en | preferred | raw | removed | 0.200 | 0.106 | 0.560 | 0.269 [0.261, 0.277] | 3.2 |
| en | labels | raw | removed | 0.213 | 0.111 | 0.560 | 0.280 [0.273, 0.288] | 24.8 |
| en | labels_desc | raw | removed | 0.239 | 0.127 | 0.625 | 0.319 [0.311, 0.327] | 38.7 |
| en | description | raw | removed | 0.183 | 0.098 | 0.517 | 0.248 [0.241, 0.255] | 13.9 |
| en | preferred | stemmed | removed | 0.221 | 0.117 | 0.594 | 0.294 [0.286, 0.301] | 3.2 |
| en | labels | stemmed | removed | 0.226 | 0.119 | 0.586 | 0.298 [0.290, 0.306] | 24.8 |
| en | labels_desc | stemmed | removed | 0.250 | 0.134 | 0.630 | 0.330 [0.322, 0.338] | 38.7 |
| en | description | stemmed | removed | 0.200 | 0.108 | 0.543 | 0.268 [0.260, 0.275] | 13.9 |
