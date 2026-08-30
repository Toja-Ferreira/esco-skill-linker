"""Build the frozen evaluation split.

Partitions occupations into dev and test. Only the queries are split; every
query searches the full skill index in both halves.

Writes data/benchmark/splits.csv, which is committed to git so that any result
can be checked against the exact test set that produced it. Re-running with the
same seed reproduces the file byte for byte; if it would change an existing
file, the script refuses unless --overwrite is passed.

Usage:
    python -m src.eval.build_benchmark
    python -m src.eval.build_benchmark --test-size 0.3 --seed 7 --overwrite
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
PROCESSED = REPO_ROOT / "data" / "processed"
BENCHMARK = REPO_ROOT / "data" / "benchmark"
SPLITS_CSV = BENCHMARK / "splits.csv"

DEFAULT_SEED = 42
DEFAULT_TEST_SIZE = 0.2

# Relevance grades. ESCO's own distinction between the two relation types.
GRADES = {"essential": 2, "optional": 1}


def load() -> tuple[pd.DataFrame, pd.DataFrame]:
    occ = pd.read_parquet(PROCESSED / "occupations.parquet")
    rel = pd.read_parquet(PROCESSED / "occupation_skill_relations.parquet")
    return occ, rel


def scoreable(occ: pd.DataFrame, rel: pd.DataFrame) -> pd.DataFrame:
    """Occupations that can be scored: at least one essential skill.

    Essential-only metrics are undefined without one, so these are excluded
    from the benchmark rather than counted as failures.
    """
    with_essential = set(rel.loc[rel["relationType"] == "essential", "occupationUri"])
    keep = occ[occ["conceptUri"].isin(with_essential)].copy()
    dropped = len(occ) - len(keep)
    if dropped:
        print(f"  excluded {dropped} occupation(s) with no essential skill")
    return keep


def stratified_split(occ: pd.DataFrame, test_size: float, seed: int) -> pd.DataFrame:
    """Assign dev/test within each ISCO major group.

    Stratifying keeps the sector mix of the test set close to the whole, so the
    per-sector slice stays usable and test isn't accidentally skewed toward one
    part of the labour market.
    """
    out = []
    for major, group in occ.groupby("iscoMajor", sort=True):
        shuffled = group.sample(frac=1.0, random_state=seed).reset_index(drop=True)
        n_test = round(len(shuffled) * test_size)
        assignment = ["test"] * n_test + ["dev"] * (len(shuffled) - n_test)
        shuffled["split"] = assignment
        out.append(shuffled)

    df = pd.concat(out, ignore_index=True)
    # Sort by URI so the file is deterministic regardless of group ordering.
    return df.sort_values("conceptUri").reset_index(drop=True)


def gold_stats(rel: pd.DataFrame, splits: pd.DataFrame) -> pd.DataFrame:
    """Per-split gold set sizes, for the report."""
    rel = rel[rel["occupationUri"].isin(splits["conceptUri"])].copy()
    rel["grade"] = rel["relationType"].map(GRADES)
    merged = rel.merge(
        splits[["conceptUri", "split"]],
        left_on="occupationUri", right_on="conceptUri", how="left",
    )
    rows = []
    for split in ("dev", "test"):
        sub = merged[merged["split"] == split]
        ess = sub[sub["relationType"] == "essential"].groupby("occupationUri").size()
        allr = sub.groupby("occupationUri").size()
        rows.append({
            "split": split,
            "queries": sub["occupationUri"].nunique(),
            "essential": int((sub["relationType"] == "essential").sum()),
            "optional": int((sub["relationType"] == "optional").sum()),
            "essential_mean": round(ess.mean(), 1),
            "essential_median": int(ess.median()),
            "essential_min": int(ess.min()),
            "essential_max": int(ess.max()),
            "graded_mean": round(allr.mean(), 1),
        })
    return pd.DataFrame(rows)


def report(splits: pd.DataFrame, stats: pd.DataFrame, n_skills: int,
           seed: int, test_size: float) -> str:
    out: list[str] = []
    w = out.append

    w("# Evaluation split\n")
    w(f"Seed {seed}, test fraction {test_size:.0%}, stratified by ISCO major group.")
    w("Only queries are partitioned. Both splits search the same index of "
      f"{n_skills:,} skills.\n")

    w("## Sizes\n")
    w("| split | queries | essential | optional | essential/query (mean) |")
    w("|---|---:|---:|---:|---:|")
    for _, r in stats.iterrows():
        w(f"| {r['split']} | {r['queries']:,} | {r['essential']:,} | "
          f"{r['optional']:,} | {r['essential_mean']} |")
    w("")

    w("Essential skills per query — "
      + "; ".join(
          f"{r['split']}: median {r['essential_median']}, "
          f"range {r['essential_min']}–{r['essential_max']}"
          for _, r in stats.iterrows()
      ) + "\n")

    w("## Stratification\n")
    w("| ISCO major | dev | test | test share |")
    w("|---|---:|---:|---:|")
    pivot = splits.pivot_table(
        index="iscoMajor", columns="split", values="conceptUri", aggfunc="count"
    ).fillna(0).astype(int)
    for major, row in pivot.iterrows():
        total = row.get("dev", 0) + row.get("test", 0)
        share = row.get("test", 0) / total if total else 0
        w(f"| {major} | {row.get('dev', 0):,} | {row.get('test', 0):,} | {share:.1%} |")
    total_dev, total_test = pivot.get("dev", 0).sum(), pivot.get("test", 0).sum()
    w(f"| **all** | **{total_dev:,}** | **{total_test:,}** | "
      f"**{total_test/(total_dev+total_test):.1%}** |\n")

    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--test-size", type=float, default=DEFAULT_TEST_SIZE)
    ap.add_argument("--overwrite", action="store_true",
                    help="replace an existing splits.csv that differs")
    args = ap.parse_args()

    occ, rel = load()
    n_skills = len(pd.read_parquet(PROCESSED / "skills.parquet"))

    occ = scoreable(occ, rel)
    splits = stratified_split(occ, args.test_size, args.seed)[
        ["conceptUri", "iscoGroup", "iscoMajor", "split"]
    ]

    BENCHMARK.mkdir(parents=True, exist_ok=True)
    new_csv = splits.to_csv(index=False)

    if SPLITS_CSV.exists():
        old = SPLITS_CSV.read_text(encoding="utf-8")
        if old == new_csv:
            print(f"  {SPLITS_CSV.relative_to(REPO_ROOT)} unchanged")
        elif not args.overwrite:
            raise SystemExit(
                f"\nRefusing to change {SPLITS_CSV.relative_to(REPO_ROOT)}.\n"
                f"  existing sha256: {hashlib.sha256(old.encode()).hexdigest()[:16]}\n"
                f"  would write:     {hashlib.sha256(new_csv.encode()).hexdigest()[:16]}\n"
                f"Any results already recorded were scored against the existing "
                f"split. Pass --overwrite only if you intend to invalidate them."
            )
        else:
            SPLITS_CSV.write_text(new_csv, encoding="utf-8")
            print(f"  OVERWROTE {SPLITS_CSV.relative_to(REPO_ROOT)}")
    else:
        SPLITS_CSV.write_text(new_csv, encoding="utf-8")
        print(f"  wrote {SPLITS_CSV.relative_to(REPO_ROOT)} ({len(splits):,} rows)")

    stats = gold_stats(rel, splits)
    text = report(splits, stats, n_skills, args.seed, args.test_size)
    out = REPO_ROOT / "results" / "split_profile.md"
    out.write_text(text, encoding="utf-8")
    print(f"  wrote {out.relative_to(REPO_ROOT)}\n")
    print(text)


if __name__ == "__main__":
    main()