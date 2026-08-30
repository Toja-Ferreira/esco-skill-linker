# Evaluation split

Seed 42, test fraction 20%, stratified by ISCO major group.
Only queries are partitioned. Both splits search the same index of 13,939 skills.

## Sizes

| split | queries | essential | optional | essential/query (mean) |
|---|---:|---:|---:|---:|
| dev | 2,431 | 53,918 | 46,639 | 22.2 |
| test | 608 | 13,682 | 11,812 | 22.5 |

Essential skills per query — dev: median 19, range 3–99; test: median 20, range 6–74

## Stratification

| ISCO major | dev | test | test share |
|---|---:|---:|---:|
| 0 | 17 | 4 | 19.0% |
| 1 | 280 | 70 | 20.0% |
| 2 | 694 | 174 | 20.0% |
| 3 | 517 | 129 | 20.0% |
| 4 | 71 | 18 | 20.2% |
| 5 | 163 | 41 | 20.1% |
| 6 | 35 | 9 | 20.5% |
| 7 | 315 | 79 | 20.1% |
| 8 | 278 | 69 | 19.9% |
| 9 | 61 | 15 | 19.7% |
| **all** | **2,431** | **608** | **20.0%** |
