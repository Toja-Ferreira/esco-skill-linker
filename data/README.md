# Data provenance

Source data for this project is **not** committed. This file records exactly which release was
used, so results stay reproducible against a verifiable input.

## Release

| | |
|---|---|
| Classification | ESCO |
| Version | **v1.2.1** |
| Content | Classification |
| Format | csv |
| Languages | `pt`, `en` |
| Portal | https://esco.ec.europa.eu/en/use-esco/download |
| Downloaded | 2026-08-28 |
| Release date | 2025-12-10 |

The portal requires registration, so this step cannot be automated. The checksums below make
the manual step auditable: anyone can download the same release and confirm they hold identical
bytes.

## Layout

```
data/
├── README.md          this file
├── checksums.txt      SHA-256 of every source file
├── raw/               gitignored
│   ├── pt/            skills_pt.csv, occupations_pt.csv, ...
│   └── en/            skills_en.csv, occupations_en.csv, ...
└── processed/         gitignored; derived tables written by src/ingest
```

Each language folder holds the full distribution as downloaded (17 files). The extra files are
kept unmodified rather than pruned, so the folder matches what the portal serves.

## Verification

The paths in `checksums.txt` are relative to `data/`, so run the check from there:

```bash
(cd data && sha256sum -c checksums.txt)
```

Every line must report `OK`. A mismatch means a different release, a partial download, or a
modified file. Investigate before running anything, since every number in the main README was
measured against these exact bytes.

Checksums were generated from inside `data/`:

```bash
(cd data && sha256sum raw/pt/*.csv raw/en/*.csv > checksums.txt)
```

## Files used

Only three per language are read by `src/ingest`:

| File | Role |
|---|---|
| `skills_<lang>.csv` | retrieval corpus: labels, descriptions, `skillType`, `reuseLevel`, `inScheme` |
| `occupations_<lang>.csv` | queries: descriptions, `iscoGroup`, `naceCode` |
| `occupationSkillRelations_<lang>.csv` | ground truth: occupation↔skill URI pairs with essential/optional |

The remaining files are retained for later work: `broaderRelationsSkillPillar`, `skillGroups`
and `skillsHierarchy` for the abstraction experiment, `skillSkillRelations` for query expansion.
`dictionary_<lang>.csv` documents every column in the distribution and its corresponding RDF
property; it is a reference, not an input.

The collection files (`transversalSkillsCollection`, `greenSkillsCollection`,
`digitalSkillsCollection`, `digCompSkillsCollection`, `researchSkillsCollection`,
`researchOccupationsCollection`, `languageSkillsCollection`) duplicate information already
present as the `reuseLevel` and `inScheme` columns on `skills_<lang>.csv`, so they are not read.

## Notes on the release

Two things to know before working with these files.

**`occupationSkillRelations_<lang>.csv` carries English labels regardless of language.** The
`occupationLabel` and `skillLabel` columns hold English strings even in the `pt` distribution,
though the data dictionary declares both as `skos:prefLabel`. Only `occupationUri` and
`skillUri` are language-correct. All joins go through URIs, and labels are taken from the
concept files.

**`definition` and `scopeNote` are empty for all 13,960 skills and all 3,043 occupations**, in
both languages. `description` is the only long-form text field with content.

## Other distributions

Only the CSV distribution is required. The portal also offers ttl, rdf, json-ld, xml and ods for
the same content; these carry the same classification and are not used here.

## Licence

ESCO is published by the European Commission under its own terms of use; see
https://esco.ec.europa.eu/. Those terms govern redistribution, which is why source files and
derived tables are gitignored rather than committed.