"""Draw the README figures from the committed result files.

Every value is read from `results/*.csv`, so a figure cannot drift from the
numbers it illustrates: rerun an experiment, rerun this, and the picture
follows. Nothing here computes a new result.

Each figure is written twice, for GitHub's light and dark themes, with a
transparent background, and the READMEs pick one with a <picture> element.

Writes:
    results/figures/systems_{light,dark}.svg
    results/figures/language_gap_{light,dark}.svg

Usage:
    python -m experiments.make_figures
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS = REPO_ROOT / "results"
FIGURES = RESULTS / "figures"
METRIC = "ndcg@10"

# Portuguese and English, validated for colour-vision deficiency against
# GitHub's light (#ffffff) and dark (#0d1117) backgrounds.
THEMES = {
    "light": {"pt": "#2a78d6", "en": "#eb6834", "ink": "#1f2328",
              "muted": "#59636e", "grid": "#d1d9e0", "band": "#8c959f",
              "bar": "#59636e"},
    "dark": {"pt": "#3987e5", "en": "#d95926", "ink": "#f0f6fc",
             "muted": "#9198a1", "grid": "#3d444d", "band": "#9198a1",
             "bar": "#9198a1"},
}
LANG_NAME = {"pt": "Portuguese", "en": "English"}


def read(name: str) -> pd.DataFrame:
    path = RESULTS / name
    if not path.exists():
        raise SystemExit(f"results/{name} is missing; run the experiment "
                         f"that writes it first.")
    return pd.read_csv(path)


def by_lang(df: pd.DataFrame) -> dict[str, float]:
    return dict(zip(df["language"], df[METRIC]))


def collect() -> tuple[list[tuple[str, dict]], dict[int, dict]]:
    """Each system's nDCG@10 per language, in pipeline order."""
    bm25 = read("bm25_tuned_test.csv")
    bi = read("bi_encoder_test.csv")
    ce = read("rerank_test.csv")
    qwen = read("llm_rerank_test_qwen3-4b-local.csv")
    ds = read("llm_rerank_test_deepseek.csv")

    systems = [
        ("BM25", by_lang(bm25[bm25["setting"] == "default"])),
        ("Bi-encoder (EmbeddingGemma)",
         by_lang(bi[bi["model"] == "embeddinggemma"])),
        ("Hybrid fusion", by_lang(qwen[qwen["stage"] == "first stage"])),
        ("+ cross-encoder (bge-m3)", by_lang(ce[ce["stage"] == "reranked"])),
        ("+ Qwen3-4B, local", by_lang(qwen[qwen["stage"] == "llm reranked"])),
        ("+ DeepSeek, API", by_lang(ds[ds["stage"] == "llm reranked"])),
    ]
    oracle: dict[int, dict] = {}
    for depth, sub in ce[ce["stage"] == "oracle"].groupby("depth"):
        oracle[int(depth)] = by_lang(sub)
    return systems, oracle


def style(ax, t: dict) -> None:
    ax.set_facecolor("none")
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(t["grid"])
    ax.tick_params(colors=t["muted"], length=0, labelsize=9)
    ax.xaxis.grid(True, color=t["grid"], linewidth=0.6)
    ax.set_axisbelow(True)


def systems_figure(systems, oracle, theme: str) -> plt.Figure:
    t = THEMES[theme]
    fig, ax = plt.subplots(figsize=(8.2, 4.6))
    fig.patch.set_alpha(0)
    style(ax, t)

    h = 0.36
    n = len(systems)
    for i, (name, v) in enumerate(systems):
        y = n - 1 - i
        for j, lang in enumerate(("pt", "en")):
            yy = y + (h / 2 + 0.02) * (1 if lang == "pt" else -1)
            ax.barh(yy, v[lang], height=h, color=t[lang],
                    label=LANG_NAME[lang] if i == 0 else None)
            ax.text(v[lang] + 0.006, yy, f"{v[lang]:.3f}", va="center",
                    fontsize=8, color=t["ink"])

    # Ceilings: what perfect ordering of the same shortlist would reach.
    for depth, note in ((20, "perfect ordering\nof the top 20"),
                        (100, "perfect ordering\nof the top 100")):
        if depth not in oracle:
            continue
        lo, hi = sorted(oracle[depth].values())
        ax.axvspan(lo, hi, color=t["band"], alpha=0.18, linewidth=0)
        ax.text((lo + hi) / 2, n - 0.35, note, ha="center", va="bottom",
                fontsize=8, color=t["muted"])

    ax.set_yticks(range(n))
    ax.set_yticklabels([s[0] for s in reversed(systems)], color=t["ink"],
                       fontsize=9.5)
    ax.set_xlim(0, 0.9)
    ax.set_ylim(-0.6, n + 0.35)
    ax.set_xlabel("nDCG@10 on 608 test occupations", color=t["muted"],
                  fontsize=9)
    leg = ax.legend(loc="lower right", frameon=False, fontsize=9)
    for txt in leg.get_texts():
        txt.set_color(t["ink"])
    fig.tight_layout()
    return fig


def gap_rows(systems, oracle):
    """Absolute EN minus PT gap, with a paired interval where one exists."""
    cmp_ = read("llm_compare.csv")
    ci = {}
    for label, key in (("Hybrid fusion", "first stage"),
                       ("+ Qwen3-4B, local", "Qwen3-4B (local)"),
                       ("+ DeepSeek, API", "DeepSeek (API)")):
        r = cmp_[cmp_["comparison"] == f"language gap, {key}"]
        if len(r):
            ci[label] = (float(r["lo"].iloc[0]), float(r["hi"].iloc[0]))

    rows = []
    for name, v in systems:
        if name.startswith("+ cross"):
            continue
        rows.append((name, v["en"] - v["pt"], v["en"] / v["pt"] - 1,
                     ci.get(name), False))
    for depth in (20, 100):
        if depth in oracle:
            v = oracle[depth]
            rows.append((f"Perfect ordering, top {depth}", v["en"] - v["pt"],
                         v["en"] / v["pt"] - 1, None, True))
    return rows


def gap_figure(rows, theme: str) -> plt.Figure:
    t = THEMES[theme]
    fig, ax = plt.subplots(figsize=(8.2, 4.0))
    fig.patch.set_alpha(0)
    style(ax, t)

    n = len(rows)
    for i, (name, gap, rel, ci, ceiling) in enumerate(rows):
        y = n - 1 - i
        if ceiling:
            ax.barh(y, gap, height=0.55, facecolor="none",
                    edgecolor=t["bar"], hatch="////", linewidth=0.8)
        else:
            ax.barh(y, gap, height=0.55, color=t["bar"])
        end = gap
        if ci:
            ax.errorbar(gap, y, xerr=[[gap - ci[0]], [ci[1] - gap]],
                        fmt="none", ecolor=t["ink"], elinewidth=1,
                        capsize=3)
            end = ci[1]
        ax.text(end + 0.0015, y, f"{gap:.3f}  ({rel:+.1%})", va="center",
                fontsize=8, color=t["ink"])

    ax.set_yticks(range(n))
    ax.set_yticklabels([r[0] for r in reversed(rows)], color=t["ink"],
                       fontsize=9.5)
    ax.set_xlim(0, 0.08)
    ax.set_xlabel("English minus Portuguese, nDCG@10 (relative gap in "
                  "brackets; whiskers are paired 95% intervals)",
                  color=t["muted"], fontsize=9)
    fig.tight_layout()
    return fig


def main() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    systems, oracle = collect()
    rows = gap_rows(systems, oracle)
    for theme in THEMES:
        for name, fig in (("systems", systems_figure(systems, oracle, theme)),
                          ("language_gap", gap_figure(rows, theme))):
            path = FIGURES / f"{name}_{theme}.svg"
            fig.savefig(path, format="svg", transparent=True)
            plt.close(fig)
            print(f"wrote {path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()