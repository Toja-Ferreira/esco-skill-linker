"""Load the ESCO CSV distribution into normalised tables.

Reads data/raw/<lang>/ for each configured language and writes parquet tables to
data/processed/. Verifies that the concept space and the occupation-skill
relations are identical across languages, since the cross-lingual evaluation
depends on that.

Usage:
    python -m src.ingest.build
    python -m src.ingest.build --languages pt en de
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW = REPO_ROOT / "data" / "raw"
PROCESSED = REPO_ROOT / "data" / "processed"

DEFAULT_LANGUAGES = ["pt", "en"]

# ESCO packs multiple alternative labels into a single field, newline-separated.
LABEL_SEP = "\n"

# Language-independent attributes. Taken from the first language and checked
# against the others.
SKILL_ATTRS = ["conceptUri", "skillType", "reuseLevel", "status", "inScheme"]
OCCUPATION_ATTRS = ["conceptUri", "iscoGroup", "status", "code", "naceCode"]
RELATION_COLS = ["occupationUri", "relationType", "skillType", "skillUri"]


def read_raw(lang: str, stem: str) -> pd.DataFrame:
    path = RAW / lang / f"{stem}_{lang}.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {path}\n"
            f"Expected the ESCO CSV distribution for '{lang}' extracted into "
            f"data/raw/{lang}/. See data/README.md."
        )
    return pd.read_csv(path, encoding="utf-8", dtype=str, keep_default_na=False)


def build_concepts(languages: list[str], stem: str, attrs: list[str]) -> pd.DataFrame:
    """One row per concept, carrying only language-independent attributes.

    The release contains a handful of concepts exported twice, differing only
    in `modifiedDate` (four occupations in v1.2.1). Since `modifiedDate` is not
    among the retained attributes, those rows are exact duplicates here and are
    collapsed. A URI appearing twice with genuinely conflicting attributes is a
    different problem and raises.
    """
    ref_lang = languages[0]
    ref = read_raw(ref_lang, stem)[attrs].sort_values("conceptUri").reset_index(drop=True)

    n_before = len(ref)
    ref = ref.drop_duplicates().reset_index(drop=True)
    if len(ref) < n_before:
        print(f"  {stem}: collapsed {n_before - len(ref)} duplicate row(s)")

    conflicting = ref.loc[ref["conceptUri"].duplicated(keep=False), "conceptUri"].unique()
    if len(conflicting):
        raise ValueError(
            f"{stem}: {len(conflicting)} concept URI(s) appear more than once with "
            f"differing attributes, e.g. {conflicting[0]}. Resolve before building."
        )

    for lang in languages[1:]:
        other = read_raw(lang, stem)[attrs].sort_values("conceptUri").reset_index(drop=True)
        other = other.drop_duplicates().reset_index(drop=True)
        if not ref["conceptUri"].equals(other["conceptUri"]):
            raise ValueError(
                f"{stem}: concept URIs differ between '{ref_lang}' and '{lang}'. "
                f"The benchmark assumes one shared concept space across languages."
            )
        for col in attrs:
            if col == "conceptUri" or ref[col].equals(other[col]):
                continue
            n = int((ref[col] != other[col]).sum())
            print(f"  ! {stem}.{col}: {n} values differ ({ref_lang} vs {lang}); keeping {ref_lang}")

    return ref


def build_relations(languages: list[str]) -> pd.DataFrame:
    """Occupation-to-skill relations, verified identical across languages.

    Note: the relation files' label columns hold English strings regardless of
    the distribution language, so they are dropped. Labels come from the
    concept files via URI joins.
    """
    ref_lang = languages[0]
    ref = (
        read_raw(ref_lang, "occupationSkillRelations")[RELATION_COLS]
        .sort_values(["occupationUri", "skillUri"])
        .reset_index(drop=True)
    )

    for lang in languages[1:]:
        other = (
            read_raw(lang, "occupationSkillRelations")[RELATION_COLS]
            .sort_values(["occupationUri", "skillUri"])
            .reset_index(drop=True)
        )
        if not ref.equals(other):
            raise ValueError(
                f"Relations differ between '{ref_lang}' and '{lang}'. "
                f"Ground truth must be identical across languages."
            )
    print(f"  relations verified identical across: {', '.join(languages)}")
    return ref


def build_labels(languages: list[str]) -> pd.DataFrame:
    """Long format: one row per concept x language x label type x label."""
    parts = []
    for stem in ("skills", "occupations"):
        for lang in languages:
            df = read_raw(lang, stem)
            for kind, col in (("preferred", "preferredLabel"),
                              ("alt", "altLabels"),
                              ("hidden", "hiddenLabels")):
                sub = df[["conceptUri", col]].copy()
                sub[col] = sub[col].str.split(LABEL_SEP)
                sub = sub.explode(col)
                sub[col] = sub[col].str.strip()
                sub = sub[sub[col] != ""]
                parts.append(pd.DataFrame({
                    "conceptUri": sub["conceptUri"].to_numpy(),
                    "language": lang,
                    "labelType": kind,
                    "label": sub[col].to_numpy(),
                }))
    return pd.concat(parts, ignore_index=True).drop_duplicates().reset_index(drop=True)


def build_texts(languages: list[str]) -> pd.DataFrame:
    """Descriptions, plus the preferred label alongside for convenience.

    `definition` and `scopeNote` are empty throughout this release and dropped.
    """
    parts = []
    for stem in ("skills", "occupations"):
        for lang in languages:
            df = read_raw(lang, stem)
            sub = df[["conceptUri", "preferredLabel", "description"]].copy()
            sub["language"] = lang
            sub["conceptKind"] = "skill" if stem == "skills" else "occupation"
            parts.append(sub[["conceptUri", "conceptKind", "language",
                              "preferredLabel", "description"]])
    texts = pd.concat(parts, ignore_index=True).drop_duplicates().reset_index(drop=True)

    dupes = texts.duplicated(subset=["conceptUri", "language"], keep=False)
    if dupes.any():
        raise ValueError(
            f"texts: {texts.loc[dupes, 'conceptUri'].nunique()} concept(s) have more "
            f"than one distinct text row per language. Resolve before building."
        )
    return texts


def profile(skills, occupations, relations, labels, texts, languages) -> str:
    """Build a human-readable dataset profile. Returned as markdown so it can
    be committed to results/ alongside the numbers quoted in the README."""
    out: list[str] = []
    w = out.append

    w("# ESCO v1.2.1 — dataset profile\n")
    w(f"Languages: {', '.join(languages)}\n")

    w("## Concepts\n")
    w(f"- Skills: {len(skills):,}")
    w(f"- Occupations: {len(occupations):,}")
    w(f"- Occupation-skill relations: {len(relations):,}\n")

    w("### Skill type\n")
    w("| skillType | n | share |")
    w("|---|---:|---:|")
    for v, n in skills["skillType"].value_counts(dropna=False).items():
        w(f"| {v or '(blank)'} | {n:,} | {n/len(skills):.1%} |")
    w("")

    w("### Reusability level\n")
    w("| reuseLevel | n | share |")
    w("|---|---:|---:|")
    for v, n in skills["reuseLevel"].value_counts(dropna=False).items():
        w(f"| {v or '(blank)'} | {n:,} | {n/len(skills):.1%} |")
    w("")

    w("## Ground truth\n")
    w("| relationType | n | share |")
    w("|---|---:|---:|")
    for v, n in relations["relationType"].value_counts(dropna=False).items():
        w(f"| {v or '(blank)'} | {n:,} | {n/len(relations):.1%} |")
    w("")

    ess = relations[relations["relationType"] == "essential"]
    per_occ = ess.groupby("occupationUri").size()
    w(f"- Occupations with >=1 essential skill: {per_occ.size:,} of {len(occupations):,} "
      f"({per_occ.size/len(occupations):.1%})")
    w(f"- Essential per occupation: mean {per_occ.mean():.1f}, median {per_occ.median():.0f}, "
      f"min {per_occ.min()}, max {per_occ.max()}")
    w(f"- Distinct skills used as gold: {ess['skillUri'].nunique():,} of {len(skills):,} "
      f"({ess['skillUri'].nunique()/len(skills):.1%})")
    w(f"- Skills never gold (index distractors): {len(skills) - ess['skillUri'].nunique():,}\n")

    w("## Text availability, skills\n")
    w("| language | preferred | alt | hidden | descriptions |")
    w("|---|---:|---:|---:|---:|")
    skill_uris = set(skills["conceptUri"])
    sl = labels[labels["conceptUri"].isin(skill_uris)]
    st = texts[(texts["conceptKind"] == "skill") & (texts["description"] != "")]
    for lang in languages:
        c = sl[sl["language"] == lang]["labelType"].value_counts()
        w(f"| {lang} | {c.get('preferred', 0):,} | {c.get('alt', 0):,} | "
          f"{c.get('hidden', 0):,} | {(st['language'] == lang).sum():,} |")
    w("")

    w("## Text availability, occupations\n")
    w("| language | preferred | alt | hidden | descriptions |")
    w("|---|---:|---:|---:|---:|")
    ol = labels[~labels["conceptUri"].isin(skill_uris)]
    ot = texts[(texts["conceptKind"] == "occupation") & (texts["description"] != "")]
    for lang in languages:
        c = ol[ol["language"] == lang]["labelType"].value_counts()
        w(f"| {lang} | {c.get('preferred', 0):,} | {c.get('alt', 0):,} | "
          f"{c.get('hidden', 0):,} | {(ot['language'] == lang).sum():,} |")
    w("")

    # Anything with a blank language-independent attribute is worth a look
    # rather than a silent filter.
    odd = skills[(skills["skillType"] == "") | (skills["reuseLevel"] == "")]
    if len(odd):
        w(f"## Skills with blank skillType or reuseLevel ({len(odd)})\n")
        pref = texts[(texts["language"] == languages[0])].set_index("conceptUri")["preferredLabel"]
        w("| conceptUri | preferredLabel | skillType | reuseLevel |")
        w("|---|---|---|---|")
        for _, r in odd.iterrows():
            label = pref.get(r["conceptUri"], "")
            w(f"| `{r['conceptUri'].rsplit('/', 1)[-1]}` | {label} | "
              f"{r['skillType'] or '—'} | {r['reuseLevel'] or '—'} |")
        w("")

    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--languages", nargs="+", default=DEFAULT_LANGUAGES)
    args = ap.parse_args()
    languages = args.languages

    PROCESSED.mkdir(parents=True, exist_ok=True)
    (REPO_ROOT / "results").mkdir(exist_ok=True)
    print(f"Reading {RAW} for: {', '.join(languages)}")

    skills = build_concepts(languages, "skills", SKILL_ATTRS)
    occupations = build_concepts(languages, "occupations", OCCUPATION_ATTRS)
    relations = build_relations(languages)
    labels = build_labels(languages)
    texts = build_texts(languages)

    # ISCO major group: the leading digit, used to stratify the split.
    occupations["iscoMajor"] = occupations["iscoGroup"].str[:1]

    tables = {
        "skills": skills,
        "occupations": occupations,
        "occupation_skill_relations": relations,
        "labels": labels,
        "texts": texts,
    }
    for name, df in tables.items():
        path = PROCESSED / f"{name}.parquet"
        df.to_parquet(path, index=False)
        print(f"  wrote {path.relative_to(REPO_ROOT)} ({len(df):,} rows)")

    report = profile(skills, occupations, relations, labels, texts, languages)
    out = REPO_ROOT / "results" / "dataset_profile.md"
    out.write_text(report, encoding="utf-8")
    print(f"  wrote {out.relative_to(REPO_ROOT)}\n")
    print(report)


if __name__ == "__main__":
    main()