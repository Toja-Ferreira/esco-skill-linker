"""Hidden labels in the skill documents.

ESCO gives some skills hidden labels: search terms, misspellings and product
names that are meant to be matched but not shown. The skill documents so far
(`labels_desc`) leave them out. They are concentrated on a few software and ICT
skills (153 skills in English, 30 in Portuguese), and in English about half of
them repeat one of the skill's own alternative labels.

Three document variants, the same first stage otherwise:

    A  labels_desc, as deployed
    B  hidden labels appended in BM25 only; dense unchanged
    C  hidden labels appended in both. The dense cache variant is
       `labels_desc_hidden`: only skills whose document changes are re-embedded,
       the rest are copied from the `labels_desc` cache, which is never written.

Hidden labels are appended after the variant's own parts, for skills only, in
label order (`build_documents(..., hidden=...)`).

Each variant is scored as the hybrid at the deployed weights (BM25 weight 0.4
in English, 0.3 in Portuguese), and A and B also as BM25 alone. The weight dev
would select for B and C is reported and not adopted. Test is scored once.

Slices of the test queries, per language, tokenised as BM25 tokenises
(stemmed, stopwords removed):

    all
    affected               a gold skill has hidden labels
    triggered-gold-new     the query shares a token with a gold skill's hidden
                           labels that is not already in that skill's A document
    triggered-nongold-new  the same, for any non-gold skill

Gold is every essential and optional relation, as in the benchmark. Paired
differences B−A, C−A and C−B use experiment 16's bootstrap (2,000 resamples,
seed 42, 95% percentile intervals).

Course-text probe: `data/probe/hidden_label_probe.csv`, columns `sentence`,
`expected_skill_uris` (separated by |), `source_course`, and optionally
`language` (default `en`). For each sentence and variant, the rank of each
expected skill in the fused top 50 at the deployed weight. If the file is
missing the probe is skipped and rule 2 cannot be met. Rows with an empty
`expected_skill_uris` are sentences no ESCO skill fits: they are listed as
no-fit in the report and take no part in rule 2.

Decision rule, fixed before the run. English decides; Portuguese is reported.

1. Harm. B−A for the hybrid at the deployed weight, English: the lower bound
   of the nDCG@10 interval and of the P@10 interval are both above −0.005, in
   `all` and in `triggered-nongold-new`. Otherwise no switch.
2. Benefit, on the probe. A sentence counts as better under B if at least one
   expected skill ranks higher than under A and none ranks lower; worse if at
   least one ranks lower and none higher; otherwise unchanged. "Not in top 50"
   ranks below every position in it. Rule 2 holds if better sentences exceed
   worse ones by at least 3, and no expected skill that was in A's top 10
   falls out of B's top 10.
3. Switch to B only if 1 and 2 both hold. Prefer C over B only if, in
   addition, C−B in English over all queries has an interval above zero on
   both nDCG@10 and P@10.

The deployed configuration is not changed by this experiment whatever the
verdict; a switch would be a separate change.

Writes:
    results/hidden_labels_test.csv     aggregates per system, variant, slice
    results/hidden_labels_paired.csv   paired differences
    results/hidden_labels_dev.csv      dev weight sweep for A, B and C
    results/hidden_labels_sizes.csv    hidden labels, changed documents, slice sizes
    results/hidden_labels_decision.csv the verdict on each rule
    results/hidden_labels_probe.csv    probe ranks, when the probe exists
    results/hidden_labels_timing.csv   wall time per step
    results/hidden_labels.md

Usage:
    python -m experiments.17_hidden_labels
    python -m experiments.17_hidden_labels --probe path/to/probe.csv
"""

from __future__ import annotations

import argparse
import importlib
import time
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import pandas as pd

from src.retrieval.bm25 import BM25Index, build_documents, get_stemmer, get_stopwords, tokenize
from src.retrieval.dense import MODELS, DenseIndex, cache_path
from src.retrieval.fusion import weighted_score_fusion

exp13 = importlib.import_module("experiments.13_fusion")
exp16 = importlib.import_module("experiments.16_llm_compare")

REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS = REPO_ROOT / "results"
PROBE = REPO_ROOT / "data" / "probe" / "hidden_label_probe.csv"

LANGUAGES = ("en", "pt")
DENSE = exp13.DENSE_DEFAULT
BASE_VARIANT = "labels_desc"
HIDDEN_VARIANT = "labels_desc_hidden"
DEPLOYED = {"en": 0.4, "pt": 0.3}  # checked against results/fusion_dev.csv below
METRICS = ("ndcg@10", "precision@10", "recall@10", "mrr")
SLICES = ("all", "affected", "triggered-gold-new", "triggered-nongold-new")
HARM_FLOOR = -0.005
PROBE_MARGIN = 3
PROBE_DEPTH = 50
# Run names under data/runs/. A uses experiment 13's runs unchanged.
RUN_NAMES = {"bm25": {"A": "bm25", "B": "bm25-hidden", "C": "bm25-hidden"},
             "dense": {"A": DENSE, "B": DENSE, "C": f"{DENSE}-hidden"}}

TIMING: list[dict] = []


@contextmanager
def step(name: str):
    t0 = time.perf_counter()
    yield
    s = time.perf_counter() - t0
    TIMING.append({"step": name, "seconds": round(s, 2)})
    print(f"  [{s:7.1f}s] {name}")


def hidden_labels(labels: pd.DataFrame, lang: str, skills: set[str]) -> dict[str, list[str]]:
    h = labels[(labels["language"] == lang) & (labels["labelType"] == "hidden")
               & labels["conceptUri"].isin(skills)]
    out: dict[str, list[str]] = {}
    for u, label in zip(h["conceptUri"], h["label"]):
        out.setdefault(u, []).append(label)
    return out


def dense_hidden(index: DenseIndex, lang: str, uris: list[str], docs: list[str],
                 changed: list[int]) -> np.ndarray:
    """C's embeddings: the labels_desc cache with the changed rows re-encoded."""
    n = len(uris)
    base = cache_path(DENSE, lang, BASE_VARIANT, n)
    path = cache_path(DENSE, lang, HIDDEN_VARIANT, n)
    assert path != base
    if path.exists():
        return np.load(path)
    if not base.exists():
        raise SystemExit(f"{base.name} missing; run experiment 10 first")
    emb = np.load(base)
    if emb.shape[0] != n:
        raise SystemExit(f"{base.name}: {emb.shape[0]} rows, expected {n}")
    prefix = MODELS[DENSE].doc_prefix
    # The cache must hold what re-encoding the A documents would give, or the
    # unchanged rows would not be comparable with the re-encoded ones.
    keep = set(changed)
    probe = [i for i in range(n) if i not in keep][:32]
    drift = np.abs(index._encode([BASE_DOCS[lang][i] for i in probe], prefix) - emb[probe]).max()
    print(f"    cache check, {len(probe)} unchanged rows re-encoded: max |diff| {drift:.2e}")
    if drift > 1e-3:
        raise SystemExit("labels_desc cache does not match its documents")
    emb = emb.copy()
    emb[changed] = index._encode([docs[i] for i in changed], prefix)
    np.save(path, emb)
    return emb


BASE_DOCS: dict[str, list[str]] = {}


def dense_run(qvecs: np.ndarray, emb: np.ndarray, uri_arr, query_uris) -> dict:
    scores = qvecs @ emb.T
    return {q: exp13.top_n(scores[i], uri_arr, exp13.RUN_DEPTH) for i, q in enumerate(query_uris)}


def bm25_run(index: BM25Index, uri_arr, texts: list[str], query_uris) -> dict:
    return {q: exp13.top_n(index.bm25.get_scores(tokenize(t, index.stemmer, index.stopwords)),
                           uri_arr, exp13.RUN_DEPTH)
            for q, t in zip(query_uris, texts)}


def fuse(runs: dict, variant: str, w: float) -> dict:
    return weighted_score_fusion([runs[("bm25", variant)], runs[("dense", variant)]], [w, 1.0 - w])


def slices(test_q, gold, qtok, htok, hnew) -> dict[str, list[str]]:
    out = {s: [] for s in SLICES}
    for q in test_q:
        g = set(gold[q])
        out["all"].append(q)
        if g & set(htok):
            out["affected"].append(q)
        if any(qtok[q] & hnew[s] for s in g if s in hnew):
            out["triggered-gold-new"].append(q)
        if any(qtok[q] & new for s, new in hnew.items() if s not in g):
            out["triggered-nongold-new"].append(q)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", type=Path, default=PROBE)
    ap.add_argument("--device", default=None)
    ap.add_argument("--batch-size", type=int, default=64)
    args = ap.parse_args()

    from src.linker import fusion_weight
    for lang, w in DEPLOYED.items():
        if abs(fusion_weight(lang) - w) > 1e-12:
            raise SystemExit(f"deployed weight for {lang} is {fusion_weight(lang)}, not {w}")

    with step("load data"):
        splits, texts, labels, skills, gold = exp13.load()
        skill_set = set(skills["conceptUri"])
        query_uris = {s: splits.loc[splits["split"] == s, "conceptUri"].tolist()
                      for s in ("dev", "test")}
    probe = pd.read_csv(args.probe) if args.probe.exists() else None
    no_fit = None
    if probe is None:
        print(f"  probe file {args.probe} not found: probe skipped")
    else:
        empty = probe["expected_skill_uris"].fillna("").str.strip() == ""
        no_fit, probe = probe[empty], probe[~empty]

    agg_rows, paired_rows, dev_rows, probe_rows, size_rows = [], [], [], [], []
    for lang in LANGUAGES:
        print(f"\n{lang}")
        with step(f"{lang}: documents and slices"):
            skill_uris, preferred, alt, description, occ_desc = exp13.language_data(
                texts, labels, skills, lang)
            uri_arr = np.asarray(skill_uris)
            hidden = hidden_labels(labels, lang, skill_set)
            docs_a = build_documents(skill_uris, preferred, alt, description, BASE_VARIANT)
            docs_h = build_documents(skill_uris, preferred, alt, description, BASE_VARIANT,
                                     hidden=hidden)
            BASE_DOCS[lang] = docs_a
            changed = [i for i, (a, b) in enumerate(zip(docs_a, docs_h)) if a != b]
            stem, stops = get_stemmer(lang), get_stopwords(lang)
            doc_tok = {u: set(tokenize(d, stem, stops)) for u, d in zip(skill_uris, docs_a)}
            htok = {u: {t for h in hs for t in tokenize(h, stem, stops)} for u, hs in hidden.items()}
            hnew = {u: ts - doc_tok[u] for u, ts in htok.items()}
            hnew = {u: ts for u, ts in hnew.items() if ts}
            qtok = {q: set(tokenize(occ_desc[q], stem, stops)) for q in query_uris["test"]}
            sl = slices(query_uris["test"], gold, qtok, htok, hnew)
            size_rows.append({"language": lang, "hidden_labels": sum(map(len, hidden.values())),
                              "skills_with_hidden": len(hidden), "documents_changed": len(changed),
                              "skills_adding_new_tokens": len(hnew),
                              **{f"slice_{s}": len(v) for s, v in sl.items()}})

        runs = {}
        for split in ("dev", "test"):
            runs[split] = {("bm25", "A"): exp13.load_run(exp13.run_path("bm25", lang, split)),
                           ("dense", "A"): exp13.load_run(exp13.run_path(DENSE, lang, split))}

        bm25_b = None
        need_b = [s for s in ("dev", "test")
                  if not exp13.run_path(RUN_NAMES["bm25"]["B"], lang, s).exists()]
        if need_b or probe is not None:
            with step(f"{lang}: BM25 index, B"):
                bm25_b = BM25Index(skill_uris, docs_h, stem, stops)
        for split in need_b:
            with step(f"{lang}: BM25 run, B, {split}"):
                exp13.save_run(bm25_run(bm25_b, uri_arr, [occ_desc[q] for q in query_uris[split]],
                                        query_uris[split]),
                               exp13.run_path(RUN_NAMES["bm25"]["B"], lang, split))

        dense_idx = DenseIndex(MODELS[DENSE], device=args.device, batch_size=args.batch_size)
        need_c = [s for s in ("dev", "test")
                  if not exp13.run_path(RUN_NAMES["dense"]["C"], lang, s).exists()]
        emb_c = emb_a = None
        if need_c or probe is not None or not cache_path(DENSE, lang, HIDDEN_VARIANT,
                                                         len(skill_uris)).exists():
            with step(f"{lang}: re-embed {len(changed)} changed documents, C"):
                emb_c = dense_hidden(dense_idx, lang, skill_uris, docs_h, changed)
            emb_a = np.load(cache_path(DENSE, lang, BASE_VARIANT, len(skill_uris)))
        for split in need_c:
            with step(f"{lang}: encode {split} queries and dense run, C"):
                qv = dense_idx.encode_queries([occ_desc[q] for q in query_uris[split]])
                exp13.save_run(dense_run(qv, emb_c, uri_arr, query_uris[split]),
                               exp13.run_path(RUN_NAMES["dense"]["C"], lang, split))

        for split in ("dev", "test"):
            for kind in ("bm25", "dense"):
                for v in ("B", "C"):
                    runs[split][(kind, v)] = exp13.load_run(
                        exp13.run_path(RUN_NAMES[kind][v], lang, split))

        # Dev sweep, reported only.
        with step(f"{lang}: dev weight sweep"):
            for v in ("A", "B", "C"):
                for w in exp13.WEIGHT_GRID:
                    agg, _ = exp13.score(fuse(runs["dev"], v, w), query_uris["dev"], gold)
                    dev_rows.append({"language": lang, "variant": v, "weight": w,
                                     "ndcg@10": agg["ndcg@10"]})

        # Test, scored once.
        with step(f"{lang}: test scoring"):
            w = DEPLOYED[lang]
            pq = {("hybrid", v): exp13.score(fuse(runs["test"], v, w), query_uris["test"], gold)[1]
                  for v in ("A", "B", "C")}
            for v in ("A", "B"):
                pq[("bm25", v)] = exp13.score(runs["test"][("bm25", v)], query_uris["test"], gold)[1]
            ft = pd.read_csv(RESULTS / "fusion_test.csv")
            committed = ft.loc[(ft["combination"] == f"hybrid {lang}")
                               & (ft["fusion"] == "wsf"), "ndcg@10"].item()
            a_now = np.mean([m["ndcg@10"] for m in pq[("hybrid", "A")].values()])
            if abs(a_now - committed) > 1e-12:
                raise SystemExit(f"A hybrid {lang} {a_now} != committed {committed}")
            for (system, v), scores in pq.items():
                for s, qs in sl.items():
                    if not qs:
                        continue
                    agg_rows.append({"system": system, "variant": v, "language": lang,
                                     "slice": s, "queries": len(qs),
                                     "weight": w if system == "hybrid" else np.nan,
                                     **{m: float(np.mean([scores[q][m] for q in qs]))
                                        for m in METRICS}})

        with step(f"{lang}: paired bootstrap"):
            comps = [("hybrid", "B", "A"), ("hybrid", "C", "A"), ("hybrid", "C", "B"),
                     ("bm25", "B", "A")]
            for system, x, y in comps:
                for s, qs in sl.items():
                    if not qs:
                        continue
                    for m in METRICS:
                        d = np.array([pq[(system, x)][q][m] - pq[(system, y)][q][m] for q in qs])
                        paired_rows.append({"system": system, "comparison": f"{x}−{y}",
                                            "language": lang, "slice": s, "metric": m,
                                            **exp16.paired(d)})

        if probe is not None:
            with step(f"{lang}: probe"):
                langs = (probe["language"].fillna("en") if "language" in probe
                         else pd.Series("en", index=probe.index))
                rows = probe[langs == lang]
                if len(rows):
                    bm25_a = BM25Index(skill_uris, docs_a, stem, stops)
                    keys = [f"p{i}" for i in rows.index]
                    sents = rows["sentence"].tolist()
                    qv = dense_idx.encode_queries(sents)
                    pr = {("bm25", "A"): bm25_run(bm25_a, uri_arr, sents, keys),
                          ("bm25", "B"): bm25_run(bm25_b, uri_arr, sents, keys),
                          ("dense", "A"): dense_run(qv, emb_a, uri_arr, keys)}
                    pr[("bm25", "C")] = pr[("bm25", "B")]
                    pr[("dense", "B")] = pr[("dense", "A")]
                    pr[("dense", "C")] = dense_run(qv, emb_c, uri_arr, keys)
                    ranked = {v: fuse(pr, v, DEPLOYED[lang]) for v in ("A", "B", "C")}
                    for k, (i, r) in zip(keys, rows.iterrows()):
                        for uri in str(r["expected_skill_uris"]).split("|"):
                            uri = uri.strip()
                            row = {"language": lang, "sentence": r["sentence"],
                                   "source_course": r.get("source_course", ""),
                                   "skill": uri, "label": preferred.get(uri, "?")}
                            for v in ("A", "B", "C"):
                                top = [d for d, _ in ranked[v][k][:PROBE_DEPTH]]
                                row[f"rank_{v}"] = top.index(uri) + 1 if uri in top else np.nan
                            probe_rows.append(row)
        dense_idx.unload()

    test = pd.DataFrame(agg_rows)
    paired = pd.DataFrame(paired_rows)
    dev = pd.DataFrame(dev_rows)
    sizes = pd.DataFrame(size_rows)
    probe_df = pd.DataFrame(probe_rows)
    timing = pd.DataFrame(TIMING)

    verdict = decide(paired, probe_df, probe is not None)
    RESULTS.mkdir(exist_ok=True)
    test.to_csv(RESULTS / "hidden_labels_test.csv", index=False)
    paired.to_csv(RESULTS / "hidden_labels_paired.csv", index=False)
    dev.to_csv(RESULTS / "hidden_labels_dev.csv", index=False)
    sizes.to_csv(RESULTS / "hidden_labels_sizes.csv", index=False)
    pd.DataFrame([verdict["flat"]]).to_csv(RESULTS / "hidden_labels_decision.csv", index=False)
    if len(probe_df):
        probe_df.to_csv(RESULTS / "hidden_labels_probe.csv", index=False)
    timing.to_csv(RESULTS / "hidden_labels_timing.csv", index=False)
    (RESULTS / "hidden_labels.md").write_text(
        render(test, paired, dev, sizes, probe_df, timing, verdict, args.probe, no_fit),
        encoding="utf-8")
    print("\n" + "\n".join(verdict["lines"]))
    print("\nwrote results/hidden_labels_{test,paired,dev,sizes,decision,timing}.csv"
          + (", hidden_labels_probe.csv" if len(probe_df) else "") + " and hidden_labels.md")


def _row(paired, comp, slice_, metric, lang="en", system="hybrid"):
    r = paired[(paired["system"] == system) & (paired["comparison"] == comp)
               & (paired["language"] == lang) & (paired["slice"] == slice_)
               & (paired["metric"] == metric)]
    return r.iloc[0] if len(r) else None


def decide(paired: pd.DataFrame, probe: pd.DataFrame, has_probe: bool) -> dict:
    lines, flat = [], {}
    checks = []
    for s in ("all", "triggered-nongold-new"):
        for m in ("ndcg@10", "precision@10"):
            r = _row(paired, "B−A", s, m)
            ok = r is not None and r["lo"] > HARM_FLOOR
            checks.append(ok)
            lo = "n/a" if r is None else f"{r['lo']:+.4f}"
            lines.append(f"rule 1: B−A {m} {s}: lower bound {lo} "
                         f"{'>' if ok else 'not >'} {HARM_FLOOR}")
    r1 = all(checks)

    if not has_probe:
        r2, better, worse, dropped = False, None, None, None
        lines.append("rule 2: probe file missing; not evaluable, so it does not hold")
    else:
        rank = lambda x: PROBE_DEPTH + 1 if pd.isna(x) else x  # noqa: E731
        en = probe[probe["language"] == "en"] if len(probe) else probe
        better = worse = dropped = 0
        for _, g in en.groupby("sentence", sort=False):
            up = (g["rank_B"].map(rank) < g["rank_A"].map(rank)).any()
            down = (g["rank_B"].map(rank) > g["rank_A"].map(rank)).any()
            better += up and not down
            worse += down and not up
            dropped += int(((g["rank_A"].map(rank) <= 10) & (g["rank_B"].map(rank) > 10)).sum())
        r2 = better - worse >= PROBE_MARGIN and dropped == 0
        lines.append(f"rule 2: probe sentences better {better}, worse {worse}, "
                     f"expected skills leaving the top 10 {dropped}: "
                     f"{'holds' if r2 else 'does not hold'}")
    switch = r1 and r2
    c_better = all((r := _row(paired, "C−B", "all", m)) is not None and r["lo"] > 0
                   for m in ("ndcg@10", "precision@10"))
    choice = ("C" if c_better else "B") if switch else "A"
    lines.append(f"rule 1 {'holds' if r1 else 'does not hold'}; rule 2 "
                 f"{'holds' if r2 else 'does not hold'}; C beats B on both: "
                 f"{'yes' if c_better else 'no'}")
    lines.append(f"rule 3: {'switch to ' + choice if switch else 'no switch, keep A'}")
    flat = {"rule1": r1, "rule2": r2, "probe_present": has_probe,
            "probe_better": better, "probe_worse": worse, "probe_dropped_top10": dropped,
            "c_beats_b": c_better, "choice": choice}
    return {"lines": lines, "flat": flat}


def fmt(r) -> str:
    return f"{r['mean']:+.4f} [{r['lo']:+.4f}, {r['hi']:+.4f}]"


def render(test, paired, dev, sizes, probe, timing, verdict, probe_path,
           no_fit: pd.DataFrame | None = None) -> str:
    out: list[str] = []
    w = out.append
    w("# Hidden labels in the skill documents\n")
    w("A is `labels_desc` as deployed, B adds each skill's hidden labels to BM25 only, C "
      "adds them to BM25 and EmbeddingGemma. Hybrid is weighted score fusion at the "
      "deployed BM25 weights (0.4 English, 0.3 Portuguese). Test queries, scored once. "
      "Intervals are 95% percentile bootstrap over queries, paired. The decision rule is "
      "in `experiments/17_hidden_labels.py`.\n")

    w("## Sizes\n")
    w("| language | hidden labels | skills with hidden | documents changed | "
      "skills adding new tokens | all | affected | triggered-gold-new | triggered-nongold-new |")
    w("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for _, r in sizes.iterrows():
        cells = [r["language"], f"{r['hidden_labels']:,}", r["skills_with_hidden"],
                 r["documents_changed"], r["skills_adding_new_tokens"],
                 *(r[f"slice_{s}"] for s in SLICES)]
        w("| " + " | ".join(str(c) for c in cells) + " |")
    w("")

    w("## Test results\n")
    for lang in LANGUAGES:
        w(f"### {lang}\n")
        w("| system | variant | slice | queries | nDCG@10 | P@10 | R@10 | MRR |")
        w("|---|---|---|---:|---:|---:|---:|---:|")
        sub = test[test["language"] == lang]
        for _, r in sub.iterrows():
            w(f"| {r['system']} | {r['variant']} | {r['slice']} | {r['queries']} "
              f"| {r['ndcg@10']:.4f} | {r['precision@10']:.4f} | {r['recall@10']:.4f} "
              f"| {r['mrr']:.4f} |")
        w("")

    w("## Paired differences\n")
    w("Mean per-query difference with its interval; won and lost are the shares of "
      "queries where the first variant scored higher and lower.\n")
    for lang in LANGUAGES:
        w(f"### {lang}\n")
        w("| system | comparison | slice | n | nDCG@10 | P@10 | R@10 | MRR | won / lost (nDCG@10) |")
        w("|---|---|---|---:|---|---|---|---|---:|")
        sub = paired[paired["language"] == lang]
        for (system, comp, s), g in sub.groupby(["system", "comparison", "slice"], sort=False):
            by = g.set_index("metric")
            nd = by.loc["ndcg@10"]
            w(f"| {system} | {comp} | {s} | {int(nd['n'])} | "
              + " | ".join(fmt(by.loc[m]) for m in METRICS)
              + f" | {nd['won']:.0%} / {nd['lost']:.0%} |")
        w("")

    w("## Weight dev would select\n")
    w("BM25's weight in the hybrid, swept on dev by nDCG@10. Reported, not adopted.\n")
    w("| language | variant | dev-selected weight | dev nDCG@10 | deployed weight | dev nDCG@10 at deployed |")
    w("|---|---|---:|---:|---:|---:|")
    for (lang, v), g in dev.groupby(["language", "variant"], sort=False):
        best = g.loc[g["ndcg@10"].idxmax()]
        at = g.loc[np.isclose(g["weight"], DEPLOYED[lang]), "ndcg@10"].item()
        w(f"| {lang} | {v} | {best['weight']:.1f} | {best['ndcg@10']:.4f} "
          f"| {DEPLOYED[lang]:.1f} | {at:.4f} |")
    w("")

    w("## Course-text probe\n")
    if not len(probe):
        rel = probe_path.relative_to(REPO_ROOT) if probe_path.is_absolute() and \
            probe_path.is_relative_to(REPO_ROOT) else probe_path
        w(f"`{rel}` was not present, so the probe was skipped and rule 2 could not "
          "be evaluated.\n")
    else:
        w(f"Rank of each expected skill in the fused top {PROBE_DEPTH}; blank is not in "
          f"the top {PROBE_DEPTH}.\n")
        w("| language | sentence | course | expected skill | A | B | C |")
        w("|---|---|---|---|---:|---:|---:|")
        r_ = lambda x: "" if pd.isna(x) else f"{int(x)}"  # noqa: E731
        for _, r in probe.iterrows():
            w(f"| {r['language']} | {r['sentence']} | {r['source_course']} | {r['label']} "
              f"| {r_(r['rank_A'])} | {r_(r['rank_B'])} | {r_(r['rank_C'])} |")
        w("")
    if no_fit is not None and len(no_fit):
        w("No-fit sentences, labelled with no expected skill. Not ranked, and not "
          "counted in rule 2:\n")
        w("| sentence | course |")
        w("|---|---|")
        for _, r in no_fit.iterrows():
            w(f"| {r['sentence']} | {r.get('source_course', '')} |")
        w("")

    w("## Decision\n")
    for line in verdict["lines"]:
        w(f"- {line}")
    w("")
    w("The deployed configuration is unchanged by this experiment.\n")

    w("## Timing\n")
    w("| step | seconds |")
    w("|---|---:|")
    for _, r in timing.iterrows():
        w(f"| {r['step']} | {r['seconds']:.1f} |")
    w("")
    return "\n".join(out)


if __name__ == "__main__":
    main()
