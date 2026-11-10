# ESCO v1.2.1 — dataset profile

Languages: pt, en

## Concepts

- Skills: 13,939
- Occupations: 3,039
- Occupation-skill relations: 126,051

### Skill type

| skillType | n | share |
|---|---:|---:|
| skill/competence | 10,715 | 76.9% |
| knowledge | 3,219 | 23.1% |
| (blank) | 5 | 0.0% |

### Reusability level

| reuseLevel | n | share |
|---|---:|---:|
| sector-specific | 6,655 | 47.7% |
| cross-sector | 3,783 | 27.1% |
| occupation-specific | 3,044 | 21.8% |
| transversal | 452 | 3.2% |
| (blank) | 5 | 0.0% |

## Ground truth

| relationType | n | share |
|---|---:|---:|
| essential | 67,600 | 53.6% |
| optional | 58,451 | 46.4% |

- Occupations with >=1 essential skill: 3,039 of 3,039 (100.0%)
- Essential per occupation: mean 22.2, median 19, min 3, max 99
- Distinct skills used as gold: 11,378 of 13,939 (81.6%)
- Skills never gold (index distractors): 2,561

## Text availability, skills

| language | preferred | alt | hidden | descriptions |
|---|---:|---:|---:|---:|
| pt | 13,939 | 3,632 | 569 | 13,939 |
| en | 13,939 | 86,454 | 1,095 | 13,939 |

## Text availability, occupations

| language | preferred | alt | hidden | descriptions |
|---|---:|---:|---:|---:|
| pt | 3,039 | 8,924 | 109 | 3,039 |
| en | 3,039 | 30,387 | 92 | 3,039 |

## Skills with blank skillType or reuseLevel (5)

| conceptUri | preferredLabel | skillType | reuseLevel |
|---|---|---|---|
| `426ceaba-6867-481c-bb6b-aee3933da7d2` | segurança TIC | — | — |
| `574257ea-7b64-4100-b7b6-e27c233fe143` | comunicação e colaboração digitais | — | — |
| `629685b8-5f9e-4522-8cff-b3e2c4ec625a` | tratamento de dados digitais | — | — |
| `7e5147d1-60b1-4a68-804b-1f5cb0396b91` | resolução de problemas com a ajuda de ferramentas e equipamentos TIC | — | — |
| `f5369f2f-e52b-43d8-8d31-79a6c11188d8` | criação de conteúdos digitais | — | — |

## Raw release

Counted on the CSV files as downloaded, before duplicate rows are collapsed.

| language | CSV files | skill rows | skill URIs | occupation rows | occupation URIs |
|---|---:|---:|---:|---:|---:|
| pt | 18 | 13,960 | 13,939 | 3,043 | 3,039 |
| en | 19 | 13,960 | 13,939 | 3,043 | 3,039 |

### Concepts with at least one alternative label

| language | skills | occupations |
|---|---:|---:|
| pt | 1,126 | 2,588 |
| en | 13,921 | 3,039 |

### Concepts with a non-empty `definition` or `scopeNote`

Both fields are dropped by the build; `description` is the text used.

| language | concept type | definition | scopeNote |
|---|---|---:|---:|
| pt | skills | 0 | 0 |
| pt | occupations | 0 | 0 |
| en | skills | 2 | 235 |
| en | occupations | 8 | 309 |
