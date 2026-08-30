# esco-skill-linker

Mapping free-text learning outcomes and course descriptions to concepts in the
[ESCO](https://esco.ec.europa.eu/) skills pillar, with a reproducible benchmark for measuring
how well different retrieval approaches do it.

Portuguese-focused, evaluated against English as the comparison language.

> **Status:** the benchmark is under construction. No retrieval code yet. This README describes
> the design and the dataset it will run against.

## The problem

Course units are described in prose — learning outcomes, syllabus text, competence statements.
Labour market systems speak ESCO. Linking the two makes course content legible to employers,
comparable across institutions, and usable for guidance and matching.

The retrieval task: given a short free-text learning outcome, return the ESCO skill and
knowledge concepts it corresponds to, from a candidate space of 13,939 concepts.

## The central question

ESCO's **descriptions are complete in both languages** — 100% of skills and occupations carry
one in Portuguese and in English. ESCO's **alternative labels are not**: English skills carry
86,454 alt-labels, Portuguese skills carry 3,632. A **23.8× gap**.

Lexical retrieval therefore starts from a heavily unequal footing across the two languages,
while dense retrieval over descriptions does not. Hence:

> **Can multilingual dense retrieval compensate for a 24× deficit in lexical surface forms?**

If it can, that is a concrete argument for dense methods in lower-resource European languages.
If it cannot, the finding is that ESCO's label coverage — not the model — is the binding
constraint for Portuguese, which is actionable for anyone deploying this.

## Prior art

**This is not an unsolved problem, and this project does not claim to be novel in framing.**
The European Commission has run a three-phase pilot on exactly this task since 2019:
*Linking learning outcomes of qualifications with ESCO skills*.

| | Phase 2 (2020–21) | Phase 3 (2022–23) |
|---|---|---|
| Qualifications | 367, 9 languages | 443 mapped of 1038, 12 languages |
| Selected concept ranked 1st | 30% | 44.65% |
| In top 3 | 48% | 63.98% |
| In top 5 | 56% | 70.35% |
| In top 10 | 66% | not reported |

Phase 3 covered DE, EL, ES, EN, FR, IT, LV, NL, PL, **PT**, SE and SI, produced 8,499 mapped
learning outcomes generating 29,894 links, and compared three matching algorithms: a
word2vec-based model, a multilingual Sentence-BERT model operating in the native language,
and an English-only embedding model behind a translation step.

Sources:
[phase 1 note](https://esco.ec.europa.eu/system/files/2021-07/6a848118-4ea7-4577-8047-1e5ca0b01c98ESCO_MSWG_11-3_Initial_results_from_the_pilot_linking_Learning_Outcomes_of_qualifications_with_ESCO_skills.pdf) ·
[phase 2 report](https://esco.ec.europa.eu/system/files/2021-07/MSWG%2014-03%20Results%20of%20the%20second%20phase%20of%20the%20pilot%20project%20for%20linking%20learning%20outcomes%20of%20qualifications%20with%20ESCO%20skills%20and%20next%20steps.pdf) ·
[phase 3 report](https://esco.ec.europa.eu/system/files/2023-04/ESCO%20MSWG15032023_Results%20for%20the%20third%20phase%20of%20the%20pilot%20project%20for%20linking%20learning%20outcomes%20.pdf) ·
[ESCOpedia overview](https://esco.ec.europa.eu/en/about-esco/escopedia/escopedia/linking-learning-outcomes-qualifications-esco-skills)

### What this project adds

Two gaps in the published record:

1. **No per-language results were published.** Testing algorithm performance across EU
   languages was an explicit objective of phase 3, but the published note reports only pooled
   figures across all 12 languages, and does not state which of the three candidate algorithms
   performed best. Portuguese qualifications were mapped — PT is in the language list and the
   University of Lusófona was among the seven participating training providers — but no
   Portuguese number was released.

2. **The gold labels are conditioned on the system being evaluated.** The reported metric is
   how often a concept *selected by a human reviewer* appeared in the tool's top-k
   suggestions. Reviewers selected from the tool's own ranked list, so the ranking partly
   caused the labels it is scored against. This inflates the figures by an unknown amount and
   makes cross-system comparison difficult.

This project is an independent, reproducible, Portuguese-focused study: gold labels derived
from ESCO's own curated relations rather than from any system's output, a frozen test split,
and per-language numbers reported separately.

### Findings from the pilot reports that constrain the design

- Learning outcomes average **10–15 words**. Short queries, not documents.
- Both phases converged on **1–3 ESCO concepts per learning outcome** as the expected mapping
  density.
- Only ~26% of phase 3 links were exact matches; *close match* dominated, meaning the chosen
  concept typically does not fully cover the learning outcome's scope. Multi-label by nature.
- Linking worked **better for VET than for higher education**, and ESCO was judged granular
  enough that some level of abstraction is needed at EQF 5–7. University course units are the
  harder case.
- Linking performed best in the native language, rather than via translation into English.
- Language-proficiency skills were called out as a weak spot, which is why ESCO's
  language-skill concepts are treated as their own slice.

## Scope

**In:** the ESCO skills pillar, including knowledge concepts. A course unit teaches a body of
knowledge at least as often as an applied competence, so excluding knowledge concepts would
misrepresent the task.

**Preferred input granularity:** individual learning outcome statements rather than whole
course descriptions. Cleaner retrieval problem, matches the European Learning Model structure,
and matches how the Commission's pilot framed it.

**Languages:** Portuguese and English. The loader takes a language list as a parameter, so
adding a third is configuration rather than a rewrite.

**Out:** the qualifications pillar. Three reasons:

1. ESCO is structured as **two** pillars — occupations and skills. Qualifications data lives
   in Europass. The portal's classification search offers only occupations and
   skills/competences.
2. Portugal's *Catálogo Nacional de Qualificações* is explicitly **non-tertiary** (levels 2, 4,
   5). It does not cover university degrees, which is the use case here.
3. ESCO's qualifications page states in the future tense that Europass *should* eventually
   display ESCO skills for qualifications. The per-learning-outcome skill links are therefore
   not publicly harvestable at scale today.

Worth revisiting if Europass exposes those links. The Portuguese CNQ revision completing in
March 2026 reorganises the catalogue around learning outcomes, which would be the right shape
if the ESCO links become available.

## Dataset

ESCO v1.2.1, classification release, CSV distribution, `pt` and `en`. All figures below are
measured by `src/ingest/build.py` and recorded in
[`results/dataset_profile.md`](results/dataset_profile.md).

### Concepts

| | Count |
|---|---|
| Skills (all `KnowledgeSkillCompetence`, all `released`) | 13,939 |
| — skill/competence | 10,715 |
| — knowledge | 3,219 |
| — unlabelled | 5 |
| Occupations (all `released`) | 3,039 |

Reusability level: sector-specific 6,655 · cross-sector 3,783 · occupation-specific 3,044 ·
transversal 452 · blank 5.

The 5 concepts with no `skillType` or `reuseLevel` are the DigComp competence areas
(*segurança TIC*, *criação de conteúdos digitais*, and three others) — container concepts from
a framework layered onto ESCO. They are real concepts, kept in the index, and are not expected
to appear as gold.

### Text availability

| Field | PT skills | EN skills |
|---|---|---|
| `description` | 13,939 (100%) | 13,939 (100%) |
| `altLabels` — concepts covered | 1,124 (8.1%) | 13,921 (99.9%) |
| `altLabels` — total labels | 3,632 | **86,454** |
| `definition` | 0 | 0 |
| `scopeNote` | 0 | 0 |

`definition` and `scopeNote` are empty throughout and are dropped.

**The asymmetry is concentrated on the corpus side.** Occupations — which supply the queries —
carry 8,924 Portuguese alt-labels against 30,387 English, a 3.4× gap, much of it gendered pairs
(*Diretor técnico / Diretora técnica*). Skills — the retrieval corpus — differ by 23.8×. So
Portuguese queries are only mildly disadvantaged while the documents being searched are
severely so, which is precisely where a lexical method needs surface forms to match against.

Every concept carries a preferred label in both languages — 13,939 skills and 3,039
occupations, with no gaps on either side. Any PT–EN performance gap is therefore a genuine
effect, not an artefact of missing labels.

### Ground truth

126,051 occupation→skill relations, identical across both language distributions. These
correspond to the ESCO model properties `relatedEssentialSkill` and `relatedOptionalSkill`.

| | Count |
|---|---|
| `essential` | 67,600 |
| `optional` | 58,451 |
| Occupations with ≥1 essential skill | 3,039 of 3,039 (100%) |
| Distinct skills appearing as gold | 11,378 of 13,939 (81.6%) |
| Skills never appearing as gold | 2,561 |

Essential skills per occupation: mean 22.2, median 19, min 3, max 99.

All 13,939 skills stay in the retrieval index. The 2,561 that never appear as gold serve as
distractors, which is the realistic setting — and a stricter one than indexing only
gold-eligible concepts.

### Known defects in the release

**Concepts are exported more than once.** 21 skills and 4 occupations appear as two rows each,
differing only in `modifiedDate`; all other fields are identical. A loader that does not
deduplicate will carry 13,960 skill rows for 13,939 concepts and double-count the affected
queries. `src/ingest/build.py` collapses them and raises if a URI ever appears twice with
genuinely conflicting attributes.

**`occupationSkillRelations_<lang>.csv` carries English labels regardless of language.** The
`occupationLabel` and `skillLabel` columns hold English strings even in the `pt` distribution,
though the data dictionary declares both as `skos:prefLabel`. Only the URI columns are
language-correct. Joins must go through URIs and take labels from the concept files; using the
relation-file labels would silently produce an English benchmark labelled as Portuguese.

### Files used

Three per language: `skills_<lang>.csv`, `occupations_<lang>.csv`,
`occupationSkillRelations_<lang>.csv`.

The distribution ships 17 files per language. The collection files
(`transversalSkillsCollection`, `greenSkillsCollection`, `digitalSkillsCollection` and
similar) are redundant here because `reuseLevel` and `inScheme` on `skills` already encode
that membership. `broaderRelationsSkillPillar`, `skillGroups` and `skillsHierarchy` become
relevant only for the abstraction experiment; `skillSkillRelations` only for query expansion.

## Benchmark design

**Queries:** ESCO occupation descriptions.
**Relevant items:** the skills ESCO relates to that occupation.
**Splits:** at the occupation level. The test set is frozen and scored once per approach.

Gold labels come from ESCO's own curated relations, so they are independent of any retrieval
system's output.

### Graded relevance

An optional skill is genuinely related to the occupation, so scoring its retrieval as an error
would be wrong. The essential/optional distinction is kept as a grade:

| Relation | Grade |
|---|---|
| `essential` | 2 |
| `optional` | 1 |
| none | 0 |

nDCG@k uses the graded scale directly. precision@k, recall@k and MRR are reported on
**essential-only** as a binary set. Both readings come from a single run, and reporting them
side by side shows whether a method's advantage is real or comes from surfacing optional
skills.

### Metrics

precision@k, recall@k, MRR, nDCG@k.

Also reported: **top-k accuracy in the Commission's form** — the share of gold concepts
appearing in the top k, at k = 1, 3, 5, 10. The comparison is not like-for-like (different
task, different corpus, different label provenance), but without it these results cannot be set
beside the only published numbers in this space at all.

### Slices

- **Language:** Portuguese against English, the primary comparison.
- **Lexical field:** BM25 scored twice, over labels only and over labels plus description. The
  PT–EN asymmetry lives entirely in the labels, so splitting them isolates it rather than
  confounding it.
- **Transversal:** with and without the 452 transversal skills, which flood similarity-based
  rankings.
- **Concept type:** knowledge against skill/competence.
- **Sector:** via `iscoGroup` and `naceCode`, both fully populated on occupations.
- **Language skills:** reported separately, following the Commission's finding that proficiency
  levels are a known failure case.

### Cross-lingual evaluation

ESCO assigns a stable URI per concept across all languages. The same occupation queried in
Portuguese and in English has an identical gold set, so the per-language delta is measurable
directly, with no translation step and no annotation cost.

## Approaches compared

Each scored on the same frozen split, with latency and cost recorded alongside quality.

1. **BM25** over labels and descriptions — the floor any semantic method must clear
2. **Bi-encoder**, several multilingual checkpoints
3. **Cross-encoder reranking** over the bi-encoder shortlist
4. **Hybrid** lexical + dense score fusion
5. **LLM reranking**, judged against the cheaper alternatives on quality, latency and cost

## Limitations

- **Occupation→skill links describe work, not teaching.** Performance on this benchmark is a
  proxy for the course-documentation use case, not a measurement of it.
- **Query shape differs from the target use case by an order of magnitude.** Benchmark queries
  are occupation descriptions with a mean of 22.2 gold skills each. Real learning outcomes run
  10–15 words with 1–3 concepts. These reward different systems. Mitigated by also scoring
  per-sentence, and by the hand-labelled set below.
- **Any lexical PT–EN gap is partly a corpus artefact.** With 23.8× fewer alternative labels on
  the skills being retrieved, a BM25 gap measures ESCO's label coverage as much as the method.
- **Reality check set:** 150–250 hand-labelled Portuguese course units. Annotation uses pooling
  — run every approach, pool the top-k from each, judge only pooled candidates — so recall is
  *recall within pool*, not true recall. A large gap between benchmark and hand-labelled
  performance is itself a finding.

## Repository layout

```
src/ingest/      load and normalise the ESCO release
src/eval/        benchmark construction and metrics
src/retrieval/   one module per approach
experiments/     scripts producing rows in the results table
results/         committed output of every run
data/raw/        source release files (gitignored)
data/processed/  derived tables
```

Files under `results/` are version-controlled deliberately, so claims about improvement stay
checkable against the run that produced them.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Getting the data

The ESCO download portal requires registration, so ingest cannot run end-to-end from a clean
clone. The release is pinned and verifiable instead:

1. Register at the [ESCO download page](https://esco.ec.europa.eu/en/use-esco/download).
2. Select version **v1.2.1**, content **Classification**, format **csv**, and download once per
   language (`pt`, `en`).
3. Extract into `data/raw/pt/` and `data/raw/en/`.
4. Verify: `sha256sum -c data/checksums.txt`

`data/checksums.txt` and `data/README.md` record the version, download date, and hash of every
source file.

## Design notes

- **Eval infrastructure comes before pipeline code.** Building the pipeline first invites weeks
  of tuning by intuition followed by a rewrite.
- **Every result is committed alongside the run that produced it**, so improvement claims stay
  checkable.
- **Metrics are reported per slice rather than pooled**, because a pooled average across
  languages is exactly what makes the existing published numbers hard to build on.

## Related work by the author

A 2024 version of this system was built as master's thesis work:
[esco-skills-matcher-api](https://github.com/Toja-Ferreira/esco-skills-matcher-api). KeyBERT
keywords plus Sentence-Transformers embeddings with optional KMeans clustering, merged into a
shortlist, reranked by an LLM, validated against ESCO. It was evaluated by asking academic
staff to rate outputs from three candidate pipelines — informative, but not reproducible.

This repository is a clean rebuild against public data with an automatic benchmark. No code
carried over, no university data used.

## Licence

ESCO is published by the European Commission under its own terms of use; see the
[ESCO portal](https://esco.ec.europa.eu/) for details. Check those terms before redistributing
derived data.erived data.
