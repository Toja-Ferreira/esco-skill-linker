# esco-skill-linker

Mapping free-text learning outcomes and course descriptions to concepts in the
[ESCO](https://esco.ec.europa.eu/) skills pillar, with a reproducible benchmark for measuring
how well different retrieval approaches do it.

Portuguese-focused, evaluated against English as the comparison language.

> **Status:** method comparison complete. Benchmark frozen; lexical, dense, fusion,
> cross-encoder and LLM reranking scored across sixteen experiments. Four planned slices are
> not yet run; see [Future work](#future-work). Full findings in
> [`results/README.md`](results/README.md).

## Results so far

Portuguese retrieves worse than English, and the reason is not what the averages suggest.

Under lexical retrieval the two languages place a correct skill at the same median rank. The
{{gap.rel.bm25:.0%}} aggregate gap is produced by the worst 5 to 10% of queries, where the occupation
description and its gold skills use different Portuguese words for the same thing. A punch
press is a *puncionadora* in one record and a *prensa biela-manivela* in the other, so they
share no tokens at all and the best gold skill falls to rank {{failure.punch.pt.rank:.0f}}. English says "punch press" on
both sides and retrieves it at rank {{failure.punch.en.rank:.0f}}. The effect is severe where it occurs and rare enough to
leave no trace in aggregate vocabulary overlap, which is why several averaged measurements
found nothing.

That diagnosis made a prediction, recorded before the dense retrieval runs: embeddings do not
need *cabedal* and *couro* to be the same string, so they should compress the Portuguese tail
rather than lift the median. They did. The Portuguese failure rate falls from {{perquery.bm25.pt.failure_rate:.1%}} to {{perquery.embeddinggemma.pt.failure_rate:.1%}},
the top of the distribution barely moves, and per-query gains concentrate in exactly the
queries where lexical matching failed.

{{split.test.queries:.0f}} held-out occupation descriptions against all {{data.skills:,.0f}} skills:

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="results/figures/systems_dark.svg">
  <img alt="nDCG@10 per system and language. Scores rise from BM25 through dense retrieval and fusion; the cross-encoder adds nothing, Qwen3-4B adds about {{qwen.gain.mean:.0%}} and DeepSeek {{deepseek.gain.en:.0%}} to {{deepseek.gain.pt:.0%}}. Perfect ordering of the same shortlist would reach about {{oracle100.mean:.2f}}." src="results/figures/systems_light.svg">
</picture>

| method | English | Portuguese | gap | gap, relative |
|---|---:|---:|---:|---:|
| BM25, stemmed, stopwords removed | {{bm25.test.en.ndcg10:.3f}} | {{bm25.test.pt.ndcg10:.3f}} | {{gap.abs.bm25:.3f}} | {{gap.rel.bm25:+.1%}} |
| Bi-encoder, EmbeddingGemma-300M | {{bi.embeddinggemma.test.en.ndcg10:.3f}} | {{bi.embeddinggemma.test.pt.ndcg10:.3f}} | {{gap.abs.bi:.3f}} | {{gap.rel.bi:+.1%}} |
| Hybrid, weighted score fusion | {{hybrid.test.en.ndcg10:.3f}} | {{hybrid.test.pt.ndcg10:.3f}} | {{gap.abs.hybrid:.3f}} | {{gap.rel.hybrid:+.1%}} |
| Hybrid, reranked by Qwen3-4B (local) | {{qwen.test.en.ndcg10:.3f}} | {{qwen.test.pt.ndcg10:.3f}} | {{gap.abs.qwen:.3f}} | {{gap.rel.qwen:+.1%}} |
| **Hybrid, reranked by DeepSeek (API)** | **{{deepseek.test.en.ndcg10:.3f}}** | **{{deepseek.test.pt.ndcg10:.3f}}** | {{gap.abs.deepseek:.3f}} | {{gap.rel.deepseek:+.1%}} |

nDCG@10. The gap is English minus Portuguese. Both columns matter: a relative gap shrinks
whenever both languages improve, even if the distance between them stays the same.

Dense retrieval removes about half of the language gap ({{dense.gap_removed.abs:.0%}} in absolute terms, {{dense.gap_removed.rel:.0%}} as a
relative gap), and does so asymmetrically: Portuguese gains {{dense.gain.pt:.1%}} where English gains {{dense.gain.en:.1%}}. A study reporting only the English figure
would have called that a modest {{dense.gain.en:.0%}} improvement and missed what it was doing.

Combining lexical with dense retrieval adds another {{hybrid.gain_over_bi.en:.0%}} in English and {{hybrid.gain_over_bi.pt:.0%}} in Portuguese on top.
Read off the means, that widens the language gap again, from {{gap.abs.bi:.3f}} to {{gap.abs.hybrid:.3f}}, and an earlier
version of this README concluded that the best-performing system is not the most
language-equitable one. Paired on occupation, the change is {{gap.change.fusion.mean:+.3f}} [{{gap.change.fusion.lo:+.3f}}, {{gap.change.fusion.hi:+.3f}}],
not distinguishable from zero, so that conclusion rested on point estimates. No stage after
dense retrieval measurably moves the gap in either direction.

After fusion the bottleneck moved to ordering. A flawless reranker over the same top-100
candidates would reach {{oracle100.test.pt.ndcg10:.3f}} in Portuguese and {{oracle100.test.en.ndcg10:.3f}} in English, more than double the best
first stage, and a correct skill already sits in the top 10 for roughly {{oracle10.test.pt.mrr:.0%}} of Portuguese queries and {{oracle10.test.en.mrr:.0%}} of English ones. Two
off-the-shelf multilingual cross-encoders captured none of that headroom. Both separate correct
from incorrect candidates well above chance and reproduce {{ce.recovered.min:.0%}} to {{ce.recovered.max:.0%}} of the first stage's
ordering quality, so they work, but they never improve on it, while adding {{ce.ms.min:.0f}} to {{ce.ms.max:.0f}} ms per
query on top of the first stage.

Listwise LLM reranking does improve on it. The model sees the description and all 20 top
candidates in one prompt and picks the best 10, so it can compare candidates against each
other, which a cross-encoder scoring one pair at a time cannot. Whether that is why it helps is
not yet tested: the LLMs are also larger than the cross-encoders and from different model
families, and the same-size pointwise control has not been run. A local Qwen3-4B adds about {{qwen.gain.mean:.0%}}
in both languages. DeepSeek's API model (`deepseek-flash`) adds {{deepseek.gain.en:.0%}} to {{deepseek.gain.pt:.0%}}, beats the local
model on the same queries by about {{llm.ds_minus_qwen.pt.mean:.2f}} nDCG@10 in both languages, and captures about a third
of the headroom available at that depth against the local model's sixth. The whole experiment,
about {{llm.prompts.thousands:,.0f}} reranked descriptions, cost ${{deepseek.cost_usd:.2f}} and ran more than ten times faster than the local
model on a laptop GPU. Paying bought quality as well as speed. What the local model offers in
return is reproducibility: it gave identical scores on a rerun, where the API moved by up to
{{deepseek.rerun.max_drift:.4f}}.

No reranker narrowed the language gap. English leads by about {{gap.abs.hybrid:.3f}} nDCG@10 before reranking
and after either model, and the paired intervals on the change all include zero. The oracle
predicts this: at a depth of 20 even perfect ordering would leave the gap as it is. Perfect
ordering of the full top 100 may remove up to about half of it, but that effect is not
distinguishable from zero on this split ({{gap.removed.oracle100.mean:.0%}}, [{{gap.removed.oracle100.lo:.0%}}, {{gap.removed.oracle100.hi:.0%}}]). An earlier version
of this README said most of the remaining gap was an ordering problem. That came from comparing
relative gaps at very different score levels, and the absolute figures do not support it.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="results/figures/language_gap_dark.svg">
  <img alt="English minus Portuguese nDCG@10 per system. The gap halves from BM25 to dense retrieval, then stays near {{gap.abs.hybrid:.3f}} through fusion and both rerankers, with overlapping intervals. Perfect ordering of the top 20 would not shrink it; of the top 100, it would fall to {{gap.abs.oracle100:.3f}}, a reduction not distinguishable from zero." src="results/figures/language_gap_light.svg">
</picture>

Three results worth noting alongside. A {{model.embeddinggemma.params_m:.0f}}M model beat a {{model.qwen3emb.params_b:.0f}}B one in both languages, and
`multilingual-e5-base` lost to BM25 in both, so the checkpoint matters more than the
architecture. Absent stopword handling turned out to cost Portuguese about a quarter of the
lexical gap, which was a flaw in this repository rather than in the data. And reciprocal rank
fusion, usually presented as the safe parameter-free default, failed to beat its own inputs in
{{fusion.rrf.failed:w}} of {{fusion.rrf.combinations:w}} combinations at its conventional constant, while weighted fusion with a dev-tuned weight
succeeded in all {{fusion.wsf.cleared:w}}. That comparison was tuned against untuned. Given the same dev tuning, RRF
beats its inputs in {{fusion.rrft.cleared:w}} of {{fusion.rrf.combinations:w}}, so the default failed rather than the method, though weighted
fusion still scores significantly higher for the hybrid used here.

Full analysis in [`results/README.md`](results/README.md).

## The problem

Course units are described in prose: learning outcomes, syllabus text, competence statements.
Labour market systems speak ESCO. Linking the two makes course content legible to employers,
comparable across institutions, and usable for guidance and matching.

The retrieval task: given a short free-text learning outcome, return the ESCO skill and
knowledge concepts it corresponds to, from a candidate space of {{data.skills:,.0f}} concepts.

## The central question

The project started from an asymmetry in the data. ESCO's **descriptions are complete in both
languages**: {{data.desc_share.pt.skills:.0%}} of skills and occupations carry one in Portuguese and in English. ESCO's
**alternative labels are not**: English skills carry {{data.skill_labels.en.alt:,.0f}} alt-labels, Portuguese skills carry
{{data.skill_labels.pt.alt:,.0f}}, a **{{data.alt_ratio.skills:.1f}}x gap**. The original question was whether dense retrieval could compensate for
that deficit in lexical surface forms.

Measurement narrowed it. The label deficit is worth about a fifth of English's lexical quality
when retrieval runs over labels alone, and Portuguese cannot access any of it. But on
description-only retrieval, where both languages have complete and comparable coverage,
English still leads. That residual is not caused by missing text, and it survives stopword
correction and parameter tuning. It comes from a minority of queries where the two records use
different words for the same concept, which a string-matching method cannot bridge.

So the question became:

> **How much of a vocabulary mismatch penalty does multilingual dense retrieval remove?**

Answered in [experiments 10 and 11](results/README.md): about half of it, and by compressing
the tail of failing queries rather than by improving retrieval generally. That is a concrete
argument for dense methods wherever a classification has been translated rather than authored
in the target language, which is the situation for 27 of ESCO's 28 languages. The rest of the
gap survives every later method, including both LLM rerankers, and remains unexplained.

A second question follows from the deployment setting. Because course documentation exists in
both languages, the practical question is not which language is better but whether using both
beats using either.

## Prior art

**This is not an unsolved problem, and this project does not claim to be novel in framing.**
The European Commission has run a three-phase pilot on exactly this task since 2019:
*Linking learning outcomes of qualifications with ESCO skills*.

| | Phase 2 (2020 to 2021) | Phase 3 (2022 to 2023) |
|---|---|---|
| Qualifications | {{pilot.p2.qualifications:.0f}}, {{pilot.p2.languages:.0f}} languages | {{pilot.p3.mapped:.0f}} mapped of {{pilot.p3.qualifications:.0f}}, {{pilot.p3.languages:.0f}} languages |
| Selected concept ranked 1st | {{pilot.p2.top1:.0%}} | {{pilot.p3.top1:.2%}} |
| In top 3 | {{pilot.p2.top3:.0%}} | {{pilot.p3.top3:.2%}} |
| In top 5 | {{pilot.p2.top5:.0%}} | {{pilot.p3.top5:.2%}} |
| In top 10 | {{pilot.p2.top10:.0%}} | not reported |

Phase 3 covered DE, EL, ES, EN, FR, IT, LV, NL, PL, **PT**, SE and SI, produced {{pilot.p3.outcomes:,.0f}} mapped
learning outcomes generating {{pilot.p3.links:,.0f}} links, and compared three matching algorithms: a
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
   performed best. Portuguese qualifications were mapped, since PT is in the language list and
   the University of Lusófona was among the seven participating training providers, yet no
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

- Learning outcomes average **10 to 15 words**, so queries are short rather than document-length.
- Both phases converged on **1 to 3 ESCO concepts per learning outcome** as the expected
  mapping density.
- Only around {{pilot.p3.exact_share:.0%}} of phase 3 links were exact matches; *close match* dominated, meaning the
  chosen concept typically does not fully cover the learning outcome's scope.
- Linking worked **better for VET than for higher education**, and ESCO was judged granular
  enough that some level of abstraction is needed at EQF 5 to 7. University course units are
  the harder case.
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

Course documentation at the target institution is authored in both languages, including the
learning outcomes themselves. A deployed system therefore has both texts for every course unit,
which is why the language comparison is treated as a design choice rather than as a constraint,
and why bilingual fusion is one of the approaches compared.

**Out:** the qualifications pillar. Three reasons:

1. ESCO is structured as **two** pillars, occupations and skills. Qualifications data lives
   in Europass. The portal's classification search offers only occupations and
   skills/competences.
2. Portugal's *Catálogo Nacional de Qualificações* is explicitly **non-tertiary** (levels 2, 4 and 5). It does not cover university degrees, which is the use case here.
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
| Skills (all `KnowledgeSkillCompetence`, all `released`) | {{data.skills:,.0f}} |
| of which skill/competence | {{data.skilltype.skill/competence:,.0f}} |
| of which knowledge | {{data.skilltype.knowledge:,.0f}} |
| of which unlabelled | {{data.skilltype.blank:,.0f}} |
| Occupations (all `released`) | {{data.occupations:,.0f}} |

Reusability level: sector-specific {{data.reuse.sector-specific:,.0f}} · cross-sector {{data.reuse.cross-sector:,.0f}} · occupation-specific {{data.reuse.occupation-specific:,.0f}} ·
transversal {{data.reuse.transversal:,.0f}} · blank {{data.reuse.blank:,.0f}}.

The {{data.skilltype.blank:,.0f}} concepts with no `skillType` or `reuseLevel` are the DigComp competence areas
(*segurança TIC*, *criação de conteúdos digitais*, and three others), container concepts from a
framework layered onto ESCO. They are real concepts, kept in the index, and are not expected to
appear as gold.

### Text availability

| Field | PT skills | EN skills |
|---|---|---|
| `description` | {{data.skill_labels.pt.descriptions:,.0f}} ({{data.desc_share.pt.skills:.0%}}) | {{data.skill_labels.en.descriptions:,.0f}} ({{data.desc_share.en.skills:.0%}}) |
| `altLabels`, concepts covered | {{data.alt_covered.pt.skills:,.0f}} ({{data.alt_share.pt.skills:.1%}}) | {{data.alt_covered.en.skills:,.0f}} ({{data.alt_share.en.skills:.1%}}) |
| `altLabels`, total labels | {{data.skill_labels.pt.alt:,.0f}} | **{{data.skill_labels.en.alt:,.0f}}** |
| `definition` | {{data.nonempty.pt.skills.definition:.0f}} | {{data.nonempty.en.skills.definition:.0f}} |
| `scopeNote` | {{data.nonempty.pt.skills.scopeNote:.0f}} | {{data.nonempty.en.skills.scopeNote:,.0f}} |

`definition` and `scopeNote` are not used. Only English has them, so including them would add
another English-only advantage.

**The asymmetry is concentrated on the corpus side.** Occupations, which supply the queries,
carry {{data.occ_labels.pt.alt:,.0f}} Portuguese alt-labels against {{data.occ_labels.en.alt:,.0f}} English, a {{data.alt_ratio.occupations:.1f}}x gap, much of it gendered pairs
(*Diretor técnico / Diretora técnica*). Skills, the retrieval corpus, differ by {{data.alt_ratio.skills:.1f}}x.
Portuguese queries are therefore only mildly disadvantaged while the documents being searched
are severely so, which is where a lexical method needs surface forms to match against.

Every concept carries a preferred label in both languages: {{data.skills:,.0f}} skills and {{data.occupations:,.0f}}
occupations, with no gaps on either side. Any Portuguese to English performance gap is
therefore a genuine effect rather than an artefact of missing labels.

### Ground truth

{{data.relations:,.0f}} occupation to skill relations, identical across both language distributions. These
correspond to the ESCO model properties `relatedEssentialSkill` and `relatedOptionalSkill`.

| | Count |
|---|---|
| `essential` | {{data.relations.essential:,.0f}} |
| `optional` | {{data.relations.optional:,.0f}} |
| Occupations with ≥1 essential skill | {{data.occ_with_essential:,.0f}} of {{data.occupations:,.0f}} ({{data.occ_with_essential.share:.0%}}) |
| Distinct skills appearing as gold | {{data.gold_skills:,.0f}} of {{data.skills:,.0f}} ({{data.gold_skills.share:.1%}}) |
| Skills never appearing as gold | {{data.never_gold:,.0f}} |

Essential skills per occupation: mean {{data.essential_per_occ.mean:.1f}}, median {{data.essential_per_occ.median:.0f}}, min {{data.essential_per_occ.min:.0f}}, max {{data.essential_per_occ.max:.0f}}.

All {{data.skills:,.0f}} skills stay in the retrieval index. The {{data.never_gold:,.0f}} that never appear as gold serve as
distractors, which is the realistic setting and a stricter one than indexing only
gold-eligible concepts.

### Known defects in the release

**Concepts are exported more than once.** {{data.raw.skill_dupes:.0f}} skills and {{data.raw.occ_dupes:.0f}} occupations appear as two rows each,
differing only in `modifiedDate`; all other fields are identical. A loader that does not
deduplicate will carry {{data.raw.pt.skill_rows:,.0f}} skill rows for {{data.skills:,.0f}} concepts and double-count the affected
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

The distribution ships {{data.raw.pt.files:.0f}} files in Portuguese and {{data.raw.en.files:.0f}} in English. The collection files
(`transversalSkillsCollection`, `greenSkillsCollection`, `digitalSkillsCollection` and
similar) are redundant here because `reuseLevel` and `inScheme` on `skills` already encode
that membership. `broaderRelationsSkillPillar`, `skillGroups` and `skillsHierarchy` become
relevant only for the abstraction experiment, and `skillSkillRelations` only for query
expansion.

## Benchmark design

**Queries:** ESCO occupation descriptions.
**Relevant items:** the skills ESCO relates to that occupation.
**Splits:** at the occupation level. The test set is frozen and scored once per approach.

Gold labels come from ESCO's own curated relations, so they are independent of any retrieval
system's output.

### Graded relevance

An optional skill is genuinely related to the occupation, so scoring its retrieval as an error
would be wrong. The essential and optional distinction is kept as a grade:

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

The Commission's pilot reports top-k accuracy, the share of reviewer-selected concepts
appearing in the tool's top k. It is not reported here. A pilot learning outcome carries 1 to
3 concepts; an occupation here carries around {{data.essential_per_occ.mean:.0f}}, so the same share is capped far below
1 at small k (see the recall ceilings in [`results/README.md`](results/README.md)) and would
not be comparable with the pilot's figures even as a rough reference.

### Slices

- **Language:** Portuguese against English, the primary comparison.
- **Text field:** labels alone against labels plus description. The alternative-label
  asymmetry is confined to the labels, so splitting the fields separates the part of the gap
  caused by missing text from the part that is not.
- **Gold set size:** quartiles by number of essential skills, since the benchmark's query shape
  differs from the target application's.

The language slice is reported in every experiment, the text-field slice in experiments 01, 05
and 10, and gold set size in experiment 02, for BM25 only. Further slices were planned and
are listed under [Future work](#future-work).

### Cross-lingual evaluation

ESCO assigns a stable URI per concept across all languages. The same occupation queried in
Portuguese and in English has an identical gold set, so the per-language delta is measurable
directly, with no translation step and no annotation cost.

## Approaches compared

Each scored on the same frozen split, with latency and cost recorded alongside quality.

1. **BM25** over labels and descriptions, the floor any semantic method must clear
2. **Bi-encoder**, several multilingual checkpoints
3. **Hybrid** lexical and dense score fusion
4. **Bilingual fusion**, combining the Portuguese and English ranked lists for the same course unit
5. **Cross-encoder reranking** over a shortlist from the best first-stage method
6. **Listwise LLM reranking**, a local model against a paid API, on quality, latency and cost

Late interaction (ColBERT-style, one vector per token) was planned and dropped. The oracle in
experiment 14 shows the existing shortlist already supports nDCG@10 of about {{oracle100.mean:.2f}}, so the
bottleneck is ordering, and a different retriever would not address it.

### Why bilingual fusion

Course documentation at the target institution is written in both Portuguese and English, so a
deployed system has both texts for the same course unit. That makes the language comparison a
design question rather than a constraint: which language should the system retrieve in, given
both exist?

ESCO assigns a stable URI per concept, so retrieval language and display language are
independent: a system can retrieve using the English text and present the Portuguese label for
the same concept.

The headroom is measured rather than assumed. Under the best bi-encoder, Portuguese fails on
{{residual.embeddinggemma.pt_fails:.1%}} of queries and English on {{residual.embeddinggemma.en_fails:.1%}}, but only {{residual.embeddinggemma.both_fail:.1%}} fail in both. So {{residual.embeddinggemma.pt_only_fails:.1%}} of occupations are
Portuguese-only failures that the English text could recover, and {{residual.embeddinggemma.en_only_fails:.1%}} the reverse. Per-query
scores correlate {{residual.embeddinggemma.correlation:.3f}} between the languages, so most failures are shared and fusion's ceiling
is modest. It is worth measuring because that ceiling is real, not because the languages are
independent.

Because per-query results are recorded per language against the same occupation URIs, fusion is
an analysis over existing runs rather than a separate retrieval pipeline.

## Limitations

- **Occupation to skill links describe work, not teaching.** Performance on this benchmark is
  a proxy for the course-documentation use case rather than a measurement of it.
- **Query shape differs from the target use case.** Test queries are occupation descriptions
  with a mean of {{split.test.essential_mean:.1f}} essential skills each ({{data.essential_per_occ.mean:.1f}} across all occupations). Real learning
  outcomes run 10 to 15 words with 1 to 3 concepts. [Experiment 02](results/README.md) tests
  how far this matters by slicing results into gold-set-size quartiles, but only for one
  configuration: BM25 over labels and descriptions, stemmed, without stopword removal. For
  that configuration the Portuguese deficit holds in every quartile, and performance on the
  smallest bucket (median {{goldsize.q1.gold_median:.0f}} essential skills) matches the pooled figures. Whether dense
  retrieval, fusion and reranking behave the same way on small gold sets is untested, and so
  is query *length*, since every query here is a full occupation description.
- **Any lexical PT to EN gap is partly a corpus artefact.** With {{data.alt_ratio.skills:.1f}}x fewer alternative labels
  on the skills being retrieved, a BM25 gap over labels measures ESCO's label coverage as well
  as the method. [Experiment 01](results/README.md) separates the two: adding alternative
  labels is worth about a fifth of English's quality and nothing measurable in Portuguese,
  while the gap on description-only retrieval, where coverage is equal, has a different cause
  entirely.
- **Recall is bounded well below 1.** With around {{split.test.essential_mean:.0f}} gold skills per query, recall@10 cannot
  exceed {{ceiling.recall10:.3f}} on this split. Absolute recall figures should be read against the ceilings
  reported alongside them.
- **Cross-language comparisons are partly confounded with preprocessing quality.** Both
  languages run through identical code and identical parameters, audited in
  [`results/README.md`](results/README.md), but identical treatment is not equal treatment.
  Absent stopword handling was found to cost Portuguese roughly a quarter of the measured gap
  and has been corrected. Snowball's two stemmers remain different algorithms, and the corpora
  differ enough in scale that BM25's length normalisation and negative-IDF floor may not behave
  equivalently. Neither has been ruled out.
- **The LLM rerankers may have seen the answers.** The gold labels are ESCO's own
  occupation-to-skill links, which are published on the web and likely in both models'
  training data. Part of the LLM gain could be recall of those links rather than judgement of
  relevance. Larger models memorise more, so this weighs more on DeepSeek's result than on
  Qwen's. The benchmark cannot separate the two.
- **The API model is a moving target.** `deepseek-chat` is an alias the provider repoints; the
  reported run was served by `deepseek-flash` on {{deepseek.run_date:date}}. The API is also not
  deterministic at temperature 0: two identical runs differed by up to {{deepseek.rerun.max_drift:.4f}} nDCG@10, small
  against its {{llm.ds_minus_qwen.en.mean:.2f}} lead over the local model, but enough that the figures cannot be reproduced
  exactly.

## Future work

Slices that are part of the benchmark design and not yet run:

- **Transversal:** with and without the {{data.reuse.transversal:,.0f}} transversal skills, which flood similarity-based
  rankings.
- **Concept type:** knowledge against skill/competence.
- **Sector:** via `iscoGroup` and `naceCode`, both fully populated on occupations.
- **Language skills:** reported separately, following the Commission's finding that proficiency
  levels are a known failure case.

One control is also outstanding: `Qwen3-Reranker-4B`, a pointwise reranker built on the same
base as the local listwise model, to separate listwise scoring from model size and family in
[experiment 15](results/README.md).

## Repository layout

```
src/ingest/      load and normalise the ESCO release
src/eval/        benchmark construction and metrics
src/retrieval/   one module per approach
src/linker.py    the selected pipeline, for one learning outcome at a time
experiments/     scripts producing rows in the results table
results/         committed output of every run
data/raw/        source release files (gitignored)
data/processed/  derived tables
```

Files under `results/` are version-controlled deliberately, so claims about improvement stay
checkable against the run that produced them.

## Setup

Python 3.12. Developed on a 12 GB RTX 5070 laptop GPU under WSL2.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -c "import nltk; nltk.download('stopwords')"
```

Two parts need access set up beforehand:

- **Dense retrieval (10 onwards) uses EmbeddingGemma, a gated model.** Accept the Gemma terms
  on the [model page](https://huggingface.co/google/embeddinggemma-300m), then log in with a
  Hugging Face token: `hf auth login`.
- **The API arm of experiment 15 needs a DeepSeek key** in `DEEPSEEK_API_KEY`. The local arm
  needs no key, but at a shortlist depth of 20 it needs about 12 GB of GPU memory at batch
  size 4.

`requirements.txt` installs the default PyPI build of torch. The results were produced with the
CUDA 13.2 build; to match it, install torch from [pytorch.org](https://pytorch.org/) before the
requirements.

## Getting the data

The ESCO download portal requires registration, so ingest cannot run end-to-end from a clean
clone. The release is pinned and verifiable instead:

1. Register at the [ESCO download page](https://esco.ec.europa.eu/en/use-esco/download).
2. Select version **v1.2.1**, content **Classification**, format **csv**, and download once per
   language (`pt`, `en`).
3. Extract into `data/raw/pt/` and `data/raw/en/`.
4. Verify: `(cd data && sha256sum -c checksums.txt)`
5. Build the derived tables: `python -m src.ingest.build`

`data/checksums.txt` and `data/README.md` record the version, download date, and hash of every
source file.

## Try it

`src/linker.py` runs the selected system on one learning outcome at a time: BM25 and
EmbeddingGemma fused with the dev-tuned weight, optionally followed by LLM reranking of the top
20. It needs the data from the previous section.

```bash
python -m src.linker --lang pt "Aplicar técnicas de aprendizagem automática a dados de sensores"
python -m src.linker --lang en --rerank qwen3-4b-local
python -m src.linker --lang pt --rerank deepseek
```

The first of those, without reranking:

```
  Competências / Skills
    1. utilizar aprendizagem por máquina / utilise machine learning
    4. aplicar técnicas de análise estatística / apply statistical analysis techniques
    5. efetuar redução de dimensionalidade / perform dimensionality reduction
    6. testar sensores / test sensors
   10. fazer modelo de simulação de sensores / model sensor

  Conhecimentos / Knowledge
    2. ciência dos dados / data science
    3. aprendizagem automática / machine learning
    7. análise de dados / data mining
    8. tecnologia de gémeos digitais / digital twin technology
    9. leitura de contador automático / automatic meter reading
```

ESCO types each concept as a *skill* (*competência*), something a person does, or *knowledge*
(*conhecimento*), something a person knows, which maps onto how learning outcomes are usually
written. Results are grouped by type, each label shown in both languages, and each keeps its rank in
the full list.

Without a learning outcome it starts an interactive prompt, so the indexes and models load once
and each further query costs only its own retrieval. Every result shows the skill's label in
both languages, since an ESCO concept keeps one URI across all of them. The first run in each
language embeds all {{data.skills:,.0f}} skills, which takes a minute or two on a GPU; later runs read the
cached embeddings.

## Design notes

- **Eval infrastructure comes before pipeline code.** Building the pipeline first invites weeks
  of tuning by intuition followed by a rewrite.
- **Every result is committed alongside the run that produced it**, so improvement claims stay
  checkable.
- **Metrics are reported per slice rather than pooled**, because a pooled average across
  languages is exactly what makes the existing published numbers hard to build on.
- **Language gaps are reported in absolute as well as relative terms.** A relative gap shrinks
  whenever both languages improve, so any claim that a method narrows the gap is checked against
  the absolute difference, per query, with a paired interval.
- **Numbers in the READMEs are generated.** The prose lives in `docs/templates/`, where every
  figure is a placeholder resolved by `experiments/figures.py` from the committed result files.
  [`results/figure_sources.md`](results/figure_sources.md) lists each figure's value and source.
  Regenerate with `python -m experiments.render_docs`; add `--check` to fail on a stale README or
  a hand-typed number in a template.

## Related work by the author

A 2024 version of this system was built as master's thesis work:
[esco-skills-matcher-api](https://github.com/Toja-Ferreira/esco-skills-matcher-api). KeyBERT
keywords plus Sentence-Transformers embeddings with optional KMeans clustering, merged into a
shortlist, reranked by an LLM, validated against ESCO. It was evaluated by asking academic
staff to rate outputs from three candidate pipelines, which was informative but not
reproducible.

That system reranked with DeepSeek. Experiment 15 measures that choice against a benchmark for
the first time: listwise LLM reranking is the only reranking method here that improves on the
first stage.

This repository is a clean rebuild against public data with an automatic benchmark. No code
carried over, no university data used.

## Licence

ESCO is published by the European Commission under its own terms of use; see the
[ESCO portal](https://esco.ec.europa.eu/) for details. Check those terms before redistributing
derived data.