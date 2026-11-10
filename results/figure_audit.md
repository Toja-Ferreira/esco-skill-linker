# Figure audit

Inventory of every number in `README.md`, `results/README.md` and `data/README.md`, done
before any README is generated from templates. Nothing in the READMEs or results was changed.

Every result figure was recomputed at full precision from the committed files by a scratch
script (762 checks, one per table cell or prose figure) and formatted the way the README formats
it. A figure passes when the recomputed string equals the README string.

Classes:

- **D**, direct: one cell of a committed file. Given as `file [filter] column`.
- **F**, derived: a formula over direct figures, computed at full precision.
- **C**, constant: a fact about the data, the setup or an external source.
- **U**, untraceable: no committed file contains it.
- **J**, judgement: an approximate reading of other figures ("about a third", "roughly 90%").

Line numbers refer to the files as of commit `a6365a0`.

---

## 1. Decisions needed

### 1.1 Untraceable figures

| id | where | text | finding |
|---|---|---|---|
| U1 | results 534 to 535 | "MRR ... 0.524 against 0.611" | **Traceable after all.** It is BM25, `labels_desc`, stemmed, stopwords removed: `bm25_stopwords_summary.csv [pt/en, labels_desc, stemmed, removed] mrr` = 0.5237 / 0.6107 (same values in `bm25_tuned_test.csv [setting=default]`). For that system MRR is indeed the closest metric (+16.6% against nDCG@10 +22.3%, recall@10 +25.0%, P@10 +23.2%). The prose does not name the system. Proposal: add "for the corrected BM25 baseline" and make both placeholders. |
| U2 | README 72 / results 1251, 1253, 1314 | "$0.37" | No committed file records cost. Comes from the provider's billing. |
| U3 | README 75, 448 / results 1233 to 1234 | "0.4120 and 0.4119", "0.4445 and 0.4460", "up to 0.0015" | 0.4119 and 0.4460 are the committed run. 0.4120, 0.4445 are a second run that was not committed, so 0.0015 is untraceable too. |
| U4 | results 1230 | "from 0.3757 to 0.3756" | 0.3757 is `llm_rerank_dev_qwen3-4b-local.csv [pt, depth 10]`. 0.3756 came from a run at another batch size, not committed. |
| U5 | results 1241 to 1244 | 0.92 s/query, "over 6", 12.19, batch 8 and 4, 11.7 of 12.2 GB, 43 W of 140 W | Observations of a failed run and `nvidia-smi`. Nothing committed. |
| U6 | results 1255 | "0.94 and 1.63 s/query" | 1.63 is `llm_rerank_test_qwen3-4b-local.csv [pt] s_per_query`. 0.94 is an earlier run. |
| U7 | results 1251 | DeepSeek "0.11 to 0.12" s/query | Committed test rows are 0.11 in both languages. Dev rows are 0.10 and 0.11. 0.12 appears nowhere. |
| U8 | results 1071 to 1073 | "370-fold margin", "P(yes) = 0.037", "96% confidence" | Qwen3-Reranker sanity check output. Printed at run time, not committed. |
| U9 | results 1068 to 1069 | "100-word occupation description", "around 25 tokens" | Query length is recorded nowhere. Skill document length is: `bm25_summary.csv mean_doc_tokens` gives 25.2 / 22.2 for `description` and 31.3 / 51.5 for `labels_desc`. |
| U10 | README 258 / results 116 | "1,124 (8.1%)", "13,921 (99.9%)", "only 8% of Portuguese skills" | Not in `dataset_profile.md`. The local, gitignored `data/processed/labels.parquet` gives **1,126** Portuguese and 13,921 English skills with an alt label, so 1,124 also disagrees with the data. |
| U11 | README 260 to 261 / data README 86 | `definition` 0, `scopeNote` 0, "empty for all 13,960 skills and all 3,043 occupations" | Raw-file facts. Not in any committed file. |
| U12 | README 296 to 298 | "21 skills and 4 occupations", "13,960 skill rows" | Duplicate counts from the raw release. Not committed (consistent with 13,939 + 21 and 3,039 + 4). |
| U13 | README 313 / data README 35 | "17 files per language" | Raw-release fact. |
| U14 | README 64 | "against under one" (ms per query, first stage) | The hybrid's latency is not recorded. `bm25_summary.csv ms_per_query` puts BM25 at 26 to 47 ms per query, which contradicts both this and `rerank.md`'s "BM25 and the bi-encoder both answer in well under a millisecond". |
| U15 | results 703 to 705 | bi-encoder ms/query 0.08, 0.07, 0.09 | Matches only `bi_encoder_dev.csv`, first row per model (`en`, `description`), which is neither the split nor the variant reported. `bi_encoder_test.csv ms_per_query` gives 0.14/0.10, 0.11/0.10, 0.12/0.10 (en/pt). |

Options for U2 to U13: (a) move them into the registry as named constants whose source says
where they come from ("provider billing, 9 November 2026", "rerun, not committed", "raw release,
`src/ingest/build.py` dedup"), so `figure_sources.md` shows them as not reproducible from
`results/`; (b) commit the missing records (cost, rerun scores, raw counts) as small result files,
which for U10 to U13 means regenerating `dataset_profile.md` by running the ingest build;
(c) remove them from the prose. My suggestion is (a), with U10 corrected to 1,126 if you agree
the local data is authoritative.

### 1.2 Figures that do not match their source

Recomputed at full precision and rounded the README's way.

| id | where | README says | recomputed | cause |
|---|---|---|---|---|
| M1 | README 43 | hybrid gap **0.036** | **0.035** (0.03547) | rounded from rounded scores (0.379 - 0.344, or 0.0355 rounded again) |
| M2 | README 52 / results 664 | pooled improvement "a modest **10%**" | pooled over both languages: **16%** (0.6860 / 0.5910) | 10.0% is the English figure alone. Either say "in English" or quote 16%. |
| M3 | README 54 | fusion "adds another **6%**" | en +6.1%, **pt +4.7%** | language not stated |
| M4 | results 131 | PT preferred labels "score **16%** lower" | PT is **14%** lower (EN is 15.8% higher) | wrong base for the relative change |
| M5 | results 132 | PT descriptions "score **24%** lower" | PT is **20%** lower, stemmed (EN is 24.3% higher; raw it is 18%/22.4%) | wrong base, as M4 |
| M6 | results 198 | "index build under **7 s**" | max **7.1 s** (`en labels_desc stemmed`) | |
| M7 | results 198 | "**26 to 50** ms per query" | **26 to 47** | upper bound loose |
| M8 | results 290 | Portuguese coverage gain **31.7%** | **31.6%** (0.10510 / 0.07985) | rounded from rounded (0.1051 / 0.0798) |
| M9 | results 384 | labels_desc stemmed **−2.7 pp** | **−2.6 pp** | difference of rounded percentages. Generated `bm25_stopwords.md` already shows −2.6. |
| M10 | results 386, 389 | description stemmed **−6.1 pp**, "**6.1** points of 24.3" | **−6.2 pp**, 6.2 | as M9. `bm25_stopwords.md` shows −6.2. |
| M11 | results 896 | RRF all four wins "on **exactly 50%**" | **49.7%** | |
| M12 | results 968 | hybrid PT "**29.3%** above" BM25 PT | **29.4%** (0.34393 / 0.26582) | |
| M13 | results 1203 | Qwen dev gain EN **+6.8%** | **+6.9%** (0.42024 / 0.39326) | |
| M14 | results 1204 | DeepSeek dev gain EN **+15.5%** | **+15.6%** (0.45442 / 0.39326) | |
| M15 | results 1110 to 1111 | "**both** rerankers lowered [MRR] further" | bge-m3 **raised** it: pt 0.6539 → 0.6544, en 0.6998 → 0.6999. Only Qwen3 lowered it. | wording |
| M16 | results 92 | "The best English run has P@10 of 0.270 ... MRR of 0.678" | those are EmbeddingGemma's. The best English run (DeepSeek) has P@10 **0.345**, MRR **0.768** | label went stale when better systems were added |
| M17 | results 1095 to 1098 | "over a top-100 shortlist ... Share of that headroom captured" | the shares (+2.0%, −0.1%, −10.1%, −5.6%) are against the oracle at each reranker's own depth (20 or 10), not at 100. Numbers are right, the label is not. | wording |
| M18 | README 64 / results 1160 | "20 to **140** ms" | 20 to **142** (141.8) | |
| M19 | results 811 | gap "two to three times larger at every percentile" | 1.8x at p25 (2.5 to 2.9x elsewhere) | |
| M20 | results 1258 | "**55% to 60%** longer" | **56%** (DeepSeek) to **59%** (Qwen) | range loose |
| M21 | README 36 (alt text), 390 | "about **0.80**" | pt 0.797, en 0.821, mean **0.81** | |
| M22 | README 36 (alt text) | DeepSeek "adds about **19%**" | pt +19.8%, en +17.6% (prose elsewhere says 18% to 20%) | |
| M23 | README 60 / results 40, 1109 | "roughly **91%** of queries" | pt 91.2%, **en 92.6%** | language not stated (the 0.912/0.926 pair is quoted at results 1107) |
| M24 | results 64 | "the hybrid's 0.155 is 29%" | English only (pt is 0.138, 25%) | language not stated, known issue |
| M25 | results 78 | "A recall@10 of 0.145 is 27%" | unnamed. Only match is EmbeddingGemma EN (0.1446) | system not stated |
| M26 | README 419 | "mean of 22.2 gold skills each" for "benchmark queries" | 22.2 is all 3,039 occupations (`dataset_profile.md`). The 608 test queries average **22.5** (`split_profile.md`) | population |
| M27 | results 689 to 690 | Qwen3 "0.2973 ... against 0.2600" | correct, but these are **dev, Portuguese** (`bi_encoder_dev.csv`), and neither is stated | split and language not stated |
| M28 | results 1223 to 1224 | Qwen repeated or dropped a candidate "never in English" | `duplicates_per_query` en = 0.0049, i.e. **3 of 608** queries | wording |

M8 to M10, M12 and probably M1, M13, M14 are the "rounded from rounded" kind the task
describes. The generator would fix all of M1 and M6 to M14 mechanically, since they are
placeholders with a format. M2 to M5, M15 to M17 and M23 to M27 also need a word changed.

### 1.3 Source conflict

| id | figure | finding |
|---|---|---|
| S1 | BM25 PT nDCG@10 | Two committed files disagree in the fifth decimal: `bm25_stopwords_summary.csv`, `bm25_tuned_test.csv [default]`, `dense_vs_lexical.csv` and `residual_gap.csv` give 0.265817; `fusion_test.csv [bm25 pt]` gives 0.265888 (shown as 0.2659 in `fusion.md`). The READMEs use 0.2658. Proposal: the registry reads `bm25_stopwords_summary.csv` for every BM25 figure. No README figure changes either way. |

### 1.4 Approximations and judgements that contain digits

These are readings, not lookups, but they contain digits so `--check` would flag them. For each
I propose either a placeholder (the rendered value is given) or an allowlist entry.

| where | text | proposal |
|---|---|---|
| README 18 / results 532 | "worst 5 to 10%", "Roughly 90%" | allowlist: a reading of the percentile table (the distributions separate between the 90th and 95th percentile) |
| results 230 | "around 150 queries" | placeholder from bucket sizes (139 to 163), or allowlist |
| results 502 | "roughly 13,000 non-gold" | allowlist |
| README 72 | "about 2,000 reranked descriptions" | placeholder for 2,016 prompts (2 × 2 × 200 dev + 2 × 608 test), rendered "about 2,000" via a rounding format, or allowlist |
| README 77, alt 86 | "about 0.035", "near 0.035" | placeholder, :.3f of the first-stage gap renders 0.035 |
| README 68, 69 / results 1370 | "about 10%", "18% to 20%" | placeholders, render unchanged |
| README 431 / results 76, 205 | "around 22", "a mean of 22" | placeholder, :.0f of 22.5 renders 22 |
| results 460 / README 70, 449 / results 1312 | "roughly 0.06", "about 0.03", "0.03 lead" | placeholders, render unchanged |
| results 459 | "under 0.005" | allowlist, or "at most 0.0041" from the span |

---

## 2. Inventory: README.md

| lines | figures | class | source or formula | status |
|---|---|---|---|---|
| 9 | "sixteen experiments" | C | count of `experiments/NN_*.py` | ok (word) |
| 18 | 22% | F | `gap.rel.bm25` = bm25.en / bm25.pt − 1, 22.33% | ok |
| 18 | 5 to 10% | J | percentile table, results 522 to 530 | see 1.4 |
| 21 to 22 | rank 478, rank 2 | D | `score_distribution_per_query.csv [occupationUri=…fd2dd3e9…, pt/en] n_outranking` + 1; also `failure_cases.md` | ok |
| 28 | 25.2%, 15.3% | D | `dense_vs_lexical.csv [bm25 / embeddinggemma, pt] failure_rate` | ok |
| 32 | 608, 13,939 | C | `split_profile.md` test queries, `dataset_profile.md` skills | ok |
| 36 (alt) | about 10%, about 19%, about 0.80 | F/J | mean of pt/en gains; mean of oracle@100 | M21, M22 |
| 41 to 45 | 15 scores, 5 gaps, 5 relative gaps | D, F | scores: BM25 `bm25_stopwords_summary.csv [labels_desc, stemmed, removed] ndcg@10`; bi-encoder `bi_encoder_test.csv [embeddinggemma]`; hybrid `rerank_test.csv [first stage]` (= `fusion_test.csv [hybrid, wsf]`); rerankers `llm_rerank_test_{qwen3-4b-local,deepseek}.csv [llm reranked]`. gap = en − pt, relative = en / pt − 1 | all ok except M1 |
| 50 to 51 | 51%, 60%, 23.5%, 10.0% | F | 1 − gap.abs.bi / gap.abs.bm25; 1 − gap.rel.bi / gap.rel.bm25; bi / bm25 − 1 per language | ok |
| 52 | 10% | F | stated as pooled | M2 |
| 54 | 6% | F | hybrid.en / bi.en − 1 | M3 |
| 59 to 60 | 0.797, 0.821, more than double, 91% | D, F | `rerank_test.csv [oracle, depth 100] ndcg@10`; ratio to hybrid; `[oracle, depth 10] mrr` | M23 |
| 63 to 64 | 82% to 103%, 20 to 140 ms, under one | F, D, U | recovered = (reranked − random) / (first stage − random) from `rerank_diagnostics*.csv`; `rerank_test*.csv [reranked] ms_per_query` | M18, U14 |
| 68 to 76 | about 10%, 18% to 20%, 0.03, a third, a sixth, about 2,000, $0.37, ten times, 0.0015 | F, U | llm / hybrid − 1; `llm_compare.csv [DeepSeek minus Qwen] mean`; headroom captured = (llm − hybrid) / (oracle@20 − hybrid) = 32%/31% and 17%/17%; s_per_query ratio 11x | U2, U3 |
| 77 to 81 | about 0.035, a third | F | gaps of hybrid, Qwen, DeepSeek (0.0355, 0.0361, 0.0341); 1 − gap.oracle100 / gap.hybrid = 31% | ok |
| 86 (alt) | 0.035, 0.024 | F | gap.abs.oracle100 = 0.0244 | ok |
| 89 to 95 | 308M, 4B, four of five, all five, a quarter | C, F | model cards; count of `fusion_paired.csv` rows with delta_lo > 0 per fusion; 6.2 / 24.3 pp | ok (but "a quarter" uses M10) |
| 106 | 13,939 | C | `dataset_profile.md` | ok |
| 111 to 113 | 100%, 86,454, 3,632, 23.8x | C, F | `dataset_profile.md` text availability; 86,454 / 3,632 = 23.80 | ok |
| 116 | a fifth | F | `bm25_summary.csv` en labels/preferred raw − 1 = 20.1% | ok |
| 127 to 130 | 10, 11, 27 of 28 languages | C | ESCO | ok |
| 143 to 154 | 2019, 367, 9, 443 of 1038, 12, 30%, 44.65%, 48%, 63.98%, 56%, 70.35%, 66%, 8,499, 29,894 | C | European Commission pilot reports, linked at 157 to 160 | external |
| 168 to 170 | 12, seven | C | phase 3 report | external |
| 185 to 191 | 10 to 15 words, 1 to 3, 26%, EQF 5 to 7 | C | pilot reports | external |
| 220, 226 | levels 2, 4 and 5; March 2026 | C | CNQ | external |
| 231 | v1.2.1 | C | `data/README.md` | ok |
| 239 to 246 | 13,939; 10,715; 3,219; 5; 3,039; 6,655; 3,783; 3,044; 452; 5 | C | `dataset_profile.md` | ok |
| 248 | 5 concepts | C | `dataset_profile.md` blank-type table | ok |
| 257 to 261 | 13,939 (100%) ×2, 1,124 (8.1%), 13,921 (99.9%), 3,632, 86,454, 0 ×4 | C, U | `dataset_profile.md` for descriptions and totals | U10, U11 |
| 266 to 267 | 8,924, 30,387, 3.4x, 23.8x | C, F | `dataset_profile.md` occupations; 30,387 / 8,924 = 3.41 | ok |
| 271 | 13,939, 3,039 | C | `dataset_profile.md` | ok |
| 277 to 290 | 126,051; 67,600; 58,451; 3,039 of 3,039 (100%); 11,378 of 13,939 (81.6%); 2,561; mean 22.2, median 19, min 3, max 99 | C | `dataset_profile.md` | ok |
| 296 to 298 | 21, 4, 13,960, 13,939 | U | raw release | U12 |
| 313 | 17 files | U | raw release | U13 |
| 336 to 338 | grades 2, 1, 0 | C | benchmark definition (`src/eval`) | allowlist |
| 349 | k = 1, 3, 5, 10 | C | metric definition | allowlist |
| 362 | 452 | C | `dataset_profile.md` transversal | ok |
| 369 to 370 | experiment 02 | C | | allowlist |
| 390 | about 0.80 | F | oracle@100 | M21 |
| 404 to 408 | 15.3%, 12.3%, 9.0%, 6.2%, 3.3%, 0.825 | D | `residual_gap.csv [embeddinggemma] pt_fails, en_fails, both_fail, pt_only_fails, en_only_fails, correlation` | ok |
| 419 to 423 | 22.2, 10 to 15, 1 to 3, median 12 | C, D | `dataset_profile.md`; pilot; `gold_size_slice.csv [Q1] gold_median` | M26 |
| 425 to 428 | 23.8x, a fifth | F | as above | ok |
| 431 to 432 | around 22, 0.543 | D, F | ceiling = mean over test queries of min(10, n) / n. Recomputable exactly from committed per-query files (all 608 gold counts recover, summing to 13,682 as in `split_profile.md`): 0.54307. Also `bm25.md` at 3 dp | ok |
| 437 | a quarter | F | 6.2 / 24.3 pp | ok |
| 447 to 449 | 9 November 2026, 0.0015, 0.03 | D, U, F | `llm_rerank_test_deepseek.csv run_date`; rerun; llm_compare | U3 |
| 470 | 3.12, 12 GB, RTX 5070, WSL2 | C | setup | allowlist |
| 485 to 486 | 15, 20, 12 GB, 4 | C | setup | allowlist |
| 489 | CUDA 13.2 | C | setup | allowlist |
| 498 to 501 | v1.2.1, sha256 | C | | allowlist |
| 514 to 534 | demo command and output ranks 1 to 10 | C | example output of `src/linker.py` | allowlist (code blocks) |
| 545 | 13,939 | C | `dataset_profile.md` | ok |
| 562 | 2024 | C | | allowlist |

## 3. Inventory: results/README.md

| lines | figures | class | source or formula | status |
|---|---|---|---|---|
| 7 to 24 | experiment numbers 01 to 16 | C | | allowlist |
| 35 | 608, 13,939 | C | profiles | ok |
| 38 to 40 | 0.797, 0.821, 91% | D | `rerank_test.csv [oracle]` | M23 |
| 49 to 53 | 10 scores, 5 gaps, 5 relative gaps (4 dp) | D, F | as README 41 to 45 | ok |
| 56 to 58 | $0.0002, about half | F, U | 0.37 / 2,016 = 0.00018; Qwen gain / DeepSeek gain = 0.51 pt, 0.53 en | U2 |
| 60 to 62 | 0.3817, +0.0023 [−0.0010, +0.0056] | D | `fusion_head_to_head.csv [all four (wsf) vs hybrid en (wsf)] a_score, mean_delta, delta_lo, delta_hi` | ok |
| 64 to 65 | 0.543, 0.155, 29% | D, F | ceiling as README 432; `rerank_test.csv [en, first stage] recall@10`; ratio 28.6% | M24 |
| 76 to 79 | 22, 10, 0.543, 0.145, 27% | D, F | | M25 |
| 81 to 83 | max recall@k at 1, 3, 5, 10, 20, 50 | F | exact from per-query gold counts (0.05565, 0.16696, 0.27826, 0.54307, 0.85629, 0.99258); `bm25.md` | ok |
| 91 to 93 | 0.270, 0.678, 13,939 | D | `bi_encoder_test.csv [embeddinggemma, en]` | M16 |
| 101 | 608, 16, 2, 4 | C | `bm25_summary.csv` has 16 rows | ok |
| 112 to 113 | 0.163, 0.162, −0.5%, 0.189, 0.227, +20.1%, tokens 4.9 to 6.1, 3.6 to 29.3 | D, F | `bm25_summary.csv [lang, preferred/labels, raw] ndcg@10, mean_doc_tokens` | ok |
| 115 to 118 | eightfold, one token, 8%, 23.8x, a fifth | F, U | 29.3 / 3.6 = 8.1; 6.1 − 4.9; | 8%: U10 |
| 127 to 129 | tokens, nDCG@10, en advantage | D, F | `bm25_summary.csv`; en / pt − 1 | ok |
| 131 to 132 | 36% longer, 16% lower, 14% longer, 24% lower | F | token ratios (from values stored at 1 dp only); score ratios | M4, M5 |
| 143 to 146 | 8 stemming gains | F | `bm25_summary.csv` stemmed / raw − 1 | ok |
| 150 | roughly half | F | 13.5 / 23.3 | ok |
| 171 to 172 | 1.5 / 0.75 / 0.25, 13,939 | C | `rank_bm25` defaults (k1, b also in `bm25_tuned_test.csv [default]`) | allowlist |
| 187 to 188 | 29.3, 6.1 | D | `bm25_summary.csv [labels, raw] mean_doc_tokens` | ok |
| 189 | 0.25, half | C | | allowlist |
| 198 | 26 to 50 ms, under 7 s | D | min/max of `bm25_summary.csv ms_per_query`, max `build_s` | M6, M7 |
| 205 to 206 | 22, 1 to 3 | C | | M26 |
| 213 to 216 | queries, gold ranges, medians, ceilings | D | `gold_size_slice.csv [bucket, pt]` | ok |
| 224 to 227 | nDCG@10 with CI, en advantage | D, F | `gold_size_slice.csv` | ok |
| 229 to 233 | 17% and 30%, 150, 608 | F, J | min/max of bucket advantages | see 1.4 |
| 237 to 243 | 0.289 to 0.330, 6, 74, 0.188 to 0.076, 0.208 to 0.271, 0.861 to 0.279 | D | `gold_size_slice.csv [en]` | ok |
| 248 to 250 | 12, 0.308, 0.309, 0.237, 0.248 | D | `gold_size_slice.csv [Q1]`; `bm25_summary.csv [labels_desc, stemmed]` | ok |
| 267 to 270 | 8 coverages with CI | D | `lexical_overlap.csv gold_coverage, _lo, _hi` | ok |
| 272 to 273 | 271, 257 | D | `lexical_overlap.csv [raw, description] mean_gold_vocab` | ok |
| 277 | more than twice | F | 159.5 / 73.3 = 2.18 | ok |
| 290 to 291 | 31.7%, 24.5%, 12.5%, 11.7% | F | stemmed / raw coverage; 1 − stemmed / raw mean_gold_vocab | M8 |
| 309 to 311 | 12 coverages | D | `weighted_overlap.csv [description] type_, idf_, content_coverage` | ok |
| 316 to 318 | 50, 47%, 36% | C, F | top-N parameter of experiment 04; 1 − content / type coverage | ok |
| 334 | 2,591, 2,691 | D | `weighted_overlap.md` term lists (not in any CSV) | ok |
| 361 to 368 | 16 stopword gains | F | `bm25_stopwords_summary.csv` removed / kept − 1 | ok |
| 379 to 386 | 16 gaps, 8 pp changes | F | en / pt − 1 per stopword setting; pp = difference at full precision | M9, M10 |
| 389 to 390 | 6.1, 24.3, 18.2% | F | | M10 |
| 398 to 401 | 8 shares of tokens removed | F | 1 − removed / kept `mean_doc_tokens`. Source stored at 1 dp only, so the 0.1% precision shown is not supported (11.1% is 3.2 / 3.6, ±1.5 points) | ok, precision caveat |
| 404 to 405 | a third, a ninth | F | 30.6%, 11.1% | ok |
| 412, 415 | a quarter, 18.2% | F | | ok |
| 435 | 42, 2,431 | F, C | rows of `bm25_sweep_dev.csv` per language; `split_profile.md` | ok |
| 442 to 443 | selected k1/b, dev, tuned, default, gain | D, F | argmax of `bm25_sweep_dev.csv`; `bm25_tuned_test.csv` | ok |
| 457 to 460 | 0.75, 0.9, 1.0, 0.2787, 0.2761, 0.3349, 0.3334, 0.005, 0.06 | D, F | `bm25_sweep_dev.csv [k1 = selected]` | ok (0.005 see 1.4) |
| 478 to 481 | 8 vocabulary sizes | D | `weighted_overlap.csv corpus_vocab` | ok |
| 483 to 484 | 13%, 7% | F | pt / en − 1 | ok |
| 502 | 13,000 | J | | see 1.4 |
| 511 to 512 | separation, mean, median, flatness | D | `score_distribution.csv` | ok |
| 514 | 20.5% | F | separation en / pt − 1 | ok |
| 518 to 519 | factor of two, rank 2 | F | 14.1 / 6.9 = 2.04; median n_outranking + 1 | ok |
| 524 to 530 | percentiles 50 to 99, max | F | `np.percentile` of `score_distribution_per_query.csv n_outranking` per language | ok |
| 531 to 532 | 90%, 5 to 10% | J | | see 1.4 |
| 534 to 535 | 0.524, 0.611 | D | | U1 |
| 540 to 543 | 0.321, 1,162, 0.737 | F, D | Pearson of `n_outranking` pt vs en; `residual_gap.csv [bm25] correlation` | ok |
| 563 to 566 | rank 2, 67.99, rank 478 | D | `failure_cases.md`; ranks also from `score_distribution_per_query.csv` | ok |
| 574 | eight | C | `failure_cases.md` | ok |
| 587 to 590 | coverages with CI, gold term counts | D | `idf_band_overlap.csv coverage, _lo, _hi, mean_gold_terms` | ok |
| 623 to 625 | 500M, 4B, 6th | C | leaderboards | external |
| 635 to 640 | nDCG@10, CI, MRR, vs BM25 | D, F | `bi_encoder_test.csv`; / bm25 − 1 | ok |
| 646 to 649 | 12 figures | D, F | as above | ok |
| 652 to 654 | 51%, 0.059, 0.029, 60%, 22.3%, 8.9%, 23.5%, 10.0% | F | as README 50 | ok |
| 656 to 659 | 5.9%, 74%, 0.3203, 0.3576, 0.3026, 0.3284 | D, F | 1 − gap.rel.qwen / gap.rel.bm25 | ok |
| 664 | 10% | F | | M2 |
| 669 to 671 | 11.6%, 8.5%, thirteenth, third, 768, 2560 | F, C | gemma / qwen − 1; `bi_encoder_test.csv index_mb, dim` | ok |
| 689 to 690 | 0.2973, 0.2600 | D | `bi_encoder_dev.csv [qwen3-4b, pt, preferred / labels_desc]` | M27 |
| 694 to 695 | 0.567, 0.640, 8.5% | D | `bi_encoder_test.csv [pt] mrr` | ok |
| 703 to 705 | dims, index MB, ms/query | D | | U15 |
| 719 | 608 | C | | ok |
| 728 to 731 | p10, p50, p90, failed | D | `dense_vs_lexical.csv` | ok |
| 733 to 734 | 39%, 34%, 0.069, a tenth | F | 1 − gemma / bm25 failure_rate | ok |
| 738 | 0.5549 to 0.5947, 0.6124 to 0.6180 | D | `dense_vs_lexical.csv p90` | ok |
| 748 to 755 | 32 cells | D | `dense_vs_lexical_paired.csv [embeddinggemma]` | ok |
| 759 | +0.106 | D | `dense_vs_lexical_paired.csv [e5-base, pt, Q1 worst] delta` | ok |
| 774 | 0.032, 0.062 | D | `[Q1 worst] bm25_mean` | ok |
| 783 | 80%, 56% | F | improved; 1 − improved for Q4 | ok |
| 792 | 8.9% | F | | ok |
| 804 to 807 | 20 percentile gaps, 4 relative gaps | D | `residual_gap.csv gap_p10..gap_p90, gap_relative` | ok |
| 810 to 812 | 0.014, 0.037, two to three times, 0.0000 | F | min/max of gemma gaps; bm25 / gemma ratios | M19 |
| 826 to 832 | 0.321, 0, 1,162, 0.737, 0.825 | D, F | | ok |
| 839 to 842 | 20 shares | D | `residual_gap.csv *_fails` | ok |
| 844 | 0.10 | C | failure threshold, experiment 11 | allowlist |
| 846 to 848 | 6.2%, 3.3%, about 6% | D | | ok |
| 867, 870 | 6.2%, 200 | D, C | run depth | ok |
| 883 to 892 | fused, gain, paired difference with CI | D, F | `fusion_paired.csv`; fused / baseline − 1 | ok |
| 894 to 896 | one of five, +1.7%, 50%, all five | F, D | `fusion_paired.csv share_positive` | M11 |
| 911 to 914 | 16 cells | D | `fusion_head_to_head.csv` rows 0, 1, 4, 5 | ok |
| 916 to 917 | 42% | D | | ok |
| 926 to 927 | 6.8%, 59%, 47% | D, F | `fusion_paired.csv` | ok |
| 930 | 6.2% | D | | ok |
| 938 to 945 | 36 dev surface cells, axis weights | D | `fusion_dev.csv [all four] weight, beta, ndcg@10` | ok |
| 947 to 951 | 0.4, 0.2 | D | argmax of the surface | ok |
| 958 to 960 | 9 cells | D, F | | ok |
| 962 to 963 | +6.1%, +4.7% | F | hybrid / gemma − 1 | ok |
| 968 | 0.3439, 29.3% | D, F | | M12 |
| 985 to 988 | 568M, 0.6B, 2.0, v3.5, 4.0 | C | model cards | allowlist |
| 996 | dev subsample | C | | ok |
| 1003 to 1006 | 28 cells | D, F | `rerank_test*.csv [first stage, reranked]` | ok |
| 1018 to 1022 | 20 dev cells | D | `rerank_dev*.csv` | ok |
| 1025 to 1026 | 10, 20 | D | selected depths | ok |
| 1045 to 1048 | random, reranked, first, recovered, AUC | D, F | `rerank_diagnostics*.csv` | ok |
| 1056 | 82%, 103% | F | | ok |
| 1068 to 1073 | 100-word, 25 tokens, 370-fold, 0.037, 96% | U | | U8, U9 |
| 1089 to 1090 | 10 cells | D | `rerank_test.csv [oracle]` | ok |
| 1092 | 132%, 116% | F | oracle@100 / first stage − 1 | ok |
| 1097 to 1098 | 4 captured shares | F | (reranked − first) / (oracle@depth − first) | M17 |
| 1107 to 1111 | 0.912, 0.926, 91%, 0.654, 0.700, 0.628, 0.683 | D | `rerank_test*.csv mrr` | M15, M23 |
| 1120 to 1124 | 25 cells | D, F | gaps; share removed = 1 − gap / first-stage gap | ok |
| 1127 to 1130 | 0.361, 0.388, 7.5%, 0.0355, 0.0244, 31% | F | mean of `rerank_ceiling.csv` column 100 per language | ok |
| 1132 to 1137 | 10.3%, 3.1%, 50, 20 | F, C | | ok |
| 1144 to 1147 | depth, pairs, ms | D | `rerank_test*.csv [reranked]` | ok |
| 1149 | 6,080, 4.7 | F | 95.1 / 20.4 | ok |
| 1158 to 1160 | 82% to 103%, 20 to 140 ms | F | | M18 |
| 1173 | 10 | C | | allowlist |
| 1181 to 1184 | 4B, 12 GB, 2024, 9 November 2026 | C, D | `llm_rerank_test_deepseek.csv run_date` | ok |
| 1186 to 1187 | 200, 10, 20, 50, 2 | C | `rerank_dev.csv queries`; setup | allowlist |
| 1193 to 1194 | 8 cells with gains | D, F | | ok |
| 1196 to 1200 | 608, 20, Qwen paired differences | D | `llm_rerank_test_qwen3-4b-local.csv mean_delta, delta_lo, delta_hi` | ok |
| 1202 to 1204 | 8 dev and test gains | F | `llm_rerank_dev_*.csv` depth 20 / depth 0 − 1; test as above | M13, M14 |
| 1207 | 20 | C | | ok |
| 1213 | 20, 0.5540, 0.5932 | D | | ok |
| 1217 to 1218 | 17%, 17%, 32%, 31% | F | headroom captured at depth 20 | ok |
| 1223 | one in a hundred | D | `llm_rerank_test_qwen3-4b-local.csv duplicates_per_query` 0.0115 pt (7 of 608) | M28 |
| 1229 to 1235 | 0.3757, 0.3756, 0.4120, 0.4119, 0.4445, 0.4460, a twentieth | D, U | | U3, U4 |
| 1239 to 1244 | 8, 12 GB, 0.92, 6, 12.19, 11.7, 12.2, 43 W, 140 W, 4 | U | | U5 |
| 1250 to 1251 | 5070, 1.2 to 1.6, 8, 0.11 to 0.12, $0.37 | D, U | `llm_rerank_test_*.csv s_per_query` | U2, U7 |
| 1253 to 1256 | $0.37, 2,016, $0.0002, 0.94, 1.63 | F, U | 2 × 2 × 200 + 2 × 608 | U2, U6 |
| 1258 to 1259 | 55% to 60%, 784,547, 504,227 | D, F | `llm_rerank_test_*.csv prompt_tokens` | M20 |
| 1268 | 608 | C | | ok |
| 1273 to 1274 | 2 differences with CI | D | `llm_compare.csv [DeepSeek minus Qwen]` | ok |
| 1292 to 1294 | 3 gaps with CI, relative | D | `llm_compare.csv [language gap, *]` | ok |
| 1298 to 1300 | 3 changes with CI | D | `llm_compare.csv [gap change, *]` | ok |
| 1302 | 10.3%, 8.3% | D | `llm_compare.csv relative` | ok |
| 1307 | 20 | C | | ok |
| 1312 to 1314 | 0.03, roughly double, ten times, $0.37 | F, U | DeepSeek gain / Qwen gain = 1.95 pt, 1.87 en; speed 11x | U2 |
| 1325 | 23.8x | F | | ok |
| 1329 to 1331 | a fifth | F | | ok |
| 1338 to 1345 | experiment numbers, a quarter | C, F | | ok |
| 1348 to 1350 | 22.3%, 8.9%, 0.059, 0.029, 25.2%, 15.3% | F, D | | ok |
| 1355 to 1356 | 0.3794, 0.3439, 10.3% | D, F | | ok |
| 1361 to 1366 | 12, 14, 0.361, 0.388, 100, 31% | F | | ok |
| 1369 to 1371 | 10%, 4B, 18% to 20% | F | | ok |

## 4. Inventory: data/README.md

| lines | figures | class | source | status |
|---|---|---|---|---|
| 11 | v1.2.1 | C | release | allowlist |
| 16 to 17 | 2026-08-28, 2025-12-10 | C | download log, release notes | allowlist (dates) |
| 35 | 17 files | U | raw release | U13 |
| 43, 53 | sha256 commands | C | | allowlist |
| 86 | 13,960 skills, 3,043 occupations | U | raw release (13,939 + 21, 3,039 + 4) | U11, U12 |

## 5. Notes for phase 2

- The recall ceiling can be computed exactly from committed files, so 29% and 27% need not be
  derived from the 3 dp value in `bm25.md`.
- Two README figures come only from generated `.md` files, not CSVs: the term counts 2,591 and
  2,691 (`weighted_overlap.md`) and the punch-press score 67.99 (`failure_cases.md`). The registry
  can read those with a regex, or they can be treated as constants citing the file.
- Token means in `bm25*_summary.csv` are stored at one decimal, which limits every ratio built
  on them (results 131, 132, 398 to 401).
- `experiments/check_figures.py` covers about 40 of the derived figures above. Everything it
  prints is reproduced by the registry, so it can be removed once the registry exists.
