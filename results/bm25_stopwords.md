# BM25 with and without stopword removal

Split `test`, 608 occupation-description queries against all 13,939 skills. Stopword lists are NLTK's, which derive from Snowball and pair with the stemmers in use. Removal happens before stemming, since the lists are of surface forms.
Intervals are 95% percentile bootstrap over queries.

## Effect of removing stopwords

nDCG@10, and the relative change from keeping them.

| lang | documents | stemming | kept | removed | change |
|---|---|---|---:|---:|---:|
| pt | preferred | raw | 0.1630 | 0.2200 | +35.0% |
| pt | preferred | stemmed | 0.1851 | 0.2345 | +26.7% |
| pt | labels | raw | 0.1622 | 0.2211 | +36.4% |
| pt | labels | stemmed | 0.1840 | 0.2375 | +29.1% |
| pt | labels_desc | raw | 0.2317 | 0.2523 | +8.9% |
| pt | labels_desc | stemmed | 0.2476 | 0.2658 | +7.4% |
| pt | description | raw | 0.1878 | 0.2129 | +13.4% |
| pt | description | stemmed | 0.2076 | 0.2289 | +10.2% |
| en | preferred | raw | 0.1887 | 0.2521 | +33.6% |
| en | preferred | stemmed | 0.2328 | 0.2893 | +24.3% |
| en | labels | raw | 0.2267 | 0.2730 | +20.4% |
| en | labels | stemmed | 0.2530 | 0.2891 | +14.2% |
| en | labels_desc | raw | 0.2928 | 0.3110 | +6.2% |
| en | labels_desc | stemmed | 0.3094 | 0.3252 | +5.1% |
| en | description | raw | 0.2299 | 0.2471 | +7.5% |
| en | description | stemmed | 0.2582 | 0.2704 | +4.7% |

## Does the Portuguese gap narrow?

English advantage in nDCG@10, before and after removal. The prediction under test is that removal helps Portuguese more, so the advantage shrinks.

| documents | stemming | gap, stops kept | gap, stops removed | change |
|---|---|---:|---:|---:|
| preferred | raw | +15.8% | +14.6% | -1.2 pp |
| preferred | stemmed | +25.8% | +23.4% | -2.4 pp |
| labels | raw | +39.8% | +23.4% | -16.4 pp |
| labels | stemmed | +37.5% | +21.7% | -15.8 pp |
| labels_desc | raw | +26.4% | +23.3% | -3.1 pp |
| labels_desc | stemmed | +25.0% | +22.3% | -2.6 pp |
| description | raw | +22.4% | +16.0% | -6.4 pp |
| description | stemmed | +24.3% | +18.2% | -6.2 pp |

## Full results

| lang | documents | stemming | stopwords | P@10 | R@10 | MRR | nDCG@10 (95% CI) | tok/doc |
|---|---|---|---|---:|---:|---:|---:|---:|
| pt | preferred | raw | kept | 0.121 | 0.064 | 0.365 | 0.163 [0.148, 0.177] | 4.9 |
| pt | labels | raw | kept | 0.120 | 0.063 | 0.365 | 0.162 [0.147, 0.177] | 6.1 |
| pt | labels_desc | raw | kept | 0.174 | 0.091 | 0.480 | 0.232 [0.215, 0.247] | 31.3 |
| pt | description | raw | kept | 0.137 | 0.072 | 0.416 | 0.188 [0.174, 0.202] | 25.2 |
| pt | preferred | stemmed | kept | 0.136 | 0.072 | 0.409 | 0.185 [0.170, 0.200] | 4.9 |
| pt | labels | stemmed | kept | 0.142 | 0.075 | 0.397 | 0.184 [0.169, 0.199] | 6.1 |
| pt | labels_desc | stemmed | kept | 0.187 | 0.099 | 0.506 | 0.248 [0.232, 0.262] | 31.3 |
| pt | description | stemmed | kept | 0.155 | 0.082 | 0.447 | 0.208 [0.193, 0.221] | 25.2 |
| pt | preferred | raw | removed | 0.167 | 0.088 | 0.454 | 0.220 [0.204, 0.235] | 3.4 |
| pt | labels | raw | removed | 0.168 | 0.088 | 0.451 | 0.221 [0.205, 0.237] | 4.3 |
| pt | labels_desc | raw | removed | 0.193 | 0.101 | 0.506 | 0.252 [0.237, 0.267] | 19.1 |
| pt | description | raw | removed | 0.160 | 0.084 | 0.453 | 0.213 [0.199, 0.227] | 14.8 |
| pt | preferred | stemmed | removed | 0.179 | 0.093 | 0.492 | 0.234 [0.219, 0.250] | 3.4 |
| pt | labels | stemmed | removed | 0.181 | 0.094 | 0.489 | 0.238 [0.221, 0.253] | 4.3 |
| pt | labels_desc | stemmed | removed | 0.203 | 0.107 | 0.524 | 0.266 [0.250, 0.281] | 19.1 |
| pt | description | stemmed | removed | 0.173 | 0.092 | 0.480 | 0.229 [0.214, 0.242] | 14.8 |
| en | preferred | raw | kept | 0.138 | 0.073 | 0.412 | 0.189 [0.174, 0.204] | 3.6 |
| en | labels | raw | kept | 0.171 | 0.092 | 0.473 | 0.227 [0.211, 0.243] | 29.3 |
| en | labels_desc | raw | kept | 0.219 | 0.117 | 0.582 | 0.293 [0.276, 0.308] | 51.5 |
| en | description | raw | kept | 0.168 | 0.090 | 0.509 | 0.230 [0.215, 0.244] | 22.2 |
| en | preferred | stemmed | kept | 0.175 | 0.094 | 0.499 | 0.233 [0.218, 0.249] | 3.6 |
| en | labels | stemmed | kept | 0.195 | 0.104 | 0.510 | 0.253 [0.237, 0.269] | 29.3 |
| en | labels_desc | stemmed | kept | 0.235 | 0.126 | 0.599 | 0.309 [0.293, 0.325] | 51.5 |
| en | description | stemmed | kept | 0.194 | 0.106 | 0.536 | 0.258 [0.243, 0.273] | 22.2 |
| en | preferred | raw | removed | 0.187 | 0.099 | 0.519 | 0.252 [0.236, 0.268] | 3.2 |
| en | labels | raw | removed | 0.211 | 0.112 | 0.534 | 0.273 [0.257, 0.289] | 24.8 |
| en | labels_desc | raw | removed | 0.235 | 0.124 | 0.606 | 0.311 [0.294, 0.327] | 38.7 |
| en | description | raw | removed | 0.185 | 0.099 | 0.522 | 0.247 [0.232, 0.261] | 13.9 |
| en | preferred | stemmed | removed | 0.217 | 0.115 | 0.588 | 0.289 [0.274, 0.305] | 3.2 |
| en | labels | stemmed | removed | 0.225 | 0.119 | 0.558 | 0.289 [0.273, 0.305] | 24.8 |
| en | labels_desc | stemmed | removed | 0.250 | 0.134 | 0.611 | 0.325 [0.308, 0.342] | 38.7 |
| en | description | stemmed | removed | 0.208 | 0.113 | 0.539 | 0.270 [0.255, 0.285] | 13.9 |
