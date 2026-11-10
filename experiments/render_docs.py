"""Render the READMEs from docs/templates/ and the figure registry.

Templates are the hand-written READMEs with every number replaced by a
placeholder naming a figure in `experiments/figures.py`:

    {{bm25.test.pt.ndcg10:.4f}}    Python format spec after the colon
    {{gap.rel.bm25:+.1%}}          negative values are written with U+2212, and a
                                   value that rounds to zero carries no sign
    {{deepseek.run_date:date}}     2026-11-09 -> 9 November 2026
    {{fusion.rrf.failed:w}}        small integers as words: 4 -> four
    {{sources}}                    once per section (## heading) that has numbers:
                                   links to the reports its figures come from

Writes README.md, results/README.md, data/README.md and
results/figure_sources.md, which lists every figure with its full-precision
value and its source.

Usage:
    python -m experiments.render_docs           render and write
    python -m experiments.render_docs --check   exit non-zero if a placeholder
                                                does not resolve, a rendered
                                                file differs from the committed
                                                one, or a template holds a
                                                hand-typed number
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import date

from experiments.figures import (_REF, NOTES, REGISTRY, REPO_ROOT, RESULTS, files_of,
                                 report_for, value)

TEMPLATES = REPO_ROOT / "docs" / "templates"
OUTPUTS = {
    "README.md": "README.md",
    "results/README.md": "results/README.md",
    "data/README.md": "data/README.md",
}
SOURCES = "results/figure_sources.md"

PLACEHOLDER = re.compile(r"\{\{\s*([^:}\s]+)\s*(?::([^}]*))?\}\}")
WORDS = ("zero one two three four five six seven eight nine ten eleven twelve "
         "thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty").split()

# Numbers a template may contain outside placeholders because they are not
# results: versions, setup, dates, and approximate readings of a table that
# have no single source. Matched as exact substrings.
ALLOWLIST = (
    "ESCO v1.2.1", "version **v1.2.1**", "| **v1.2.1** |",  # release
    "Python 3.12", "CUDA 13.2",  # setup
    "Apache 2.0", "Jina's v3.5", "CC-BY-NC-4.0", "qwen3-0.6b",  # licences and model names
    "95% CI",  # interval level in table headers
    "worst 5 to 10%", "Roughly 90%",  # reading of the percentile table, experiment 07
    "roughly 13,000",  # non-gold skills per query, as an order of magnitude
    "1.5 / 0.75 / 0.25",  # rank_bm25 defaults
    # grid points of the BM25 sweep (experiment 06) and the fusion sweep (13)
    "`b` between 0.75 and 1.0", "with 0.9 giving", "1.0 giving", "with 0.9 at", "and 0.75 at",
    "| 0.0 | 0.2 | 0.4 | 0.6 | 0.8 | 1.0 |",
    "\n| 0.0 |", "\n| 0.2 |", "\n| **0.4** |", "\n| 0.6 |", "\n| 0.8 |", "\n| 1.0 |",  # row labels
)
# Hand-typed decimals, percentages, percentage points and thousands.
LITERAL = re.compile(r"\d+(?:\.\d+)?\s?%|\d+(?:\.\d+)? pp|\d+\.\d+|\d{1,3}(?:,\d{3})+")


def fmt(name: str, spec: str | None) -> str:
    v = value(name)
    if spec == "date":
        d = date.fromisoformat(str(v))
        return f"{d.day} {d:%B %Y}"
    if spec == "w":
        return WORDS[int(v)]
    s = format(v, spec or "")
    if not re.search(r"[1-9]", s):  # rounds to zero: no sign
        s = s.lstrip("+-")
    return s.replace("-", "−")


SOURCES_MARK = "{{sources}}"


def has_constant(name: str) -> bool:
    f = REGISTRY[name]
    if f.kind == "formula":
        return any(has_constant(r) for r in _REF.findall(f.source) if r in REGISTRY)
    return f.kind == "constant"


def sources_line(names: list[str], out: str) -> str:
    """Links, relative to `out`, to the reports behind `names`: the report
    behind the most figures first, ties in order of first use."""
    here = os.path.dirname(REPO_ROOT / out)
    link = lambda f: f"[`{f}`]({os.path.relpath(RESULTS / f, here)})"
    uses: dict[str, int] = {}
    for n in dict.fromkeys(n for n in names if n in REGISTRY):
        for r in dict.fromkeys(report_for(f) for f in files_of(n)):
            uses[r] = uses.get(r, 0) + 1
    reports = sorted(uses, key=lambda r: -uses[r])
    parts = [link(r) for r in reports]
    if any(has_constant(n) for n in names if n in REGISTRY):
        parts.append("constants recorded in " + link("figure_sources.md"))
    if not reports:
        return f"Figures in this section are {parts[0]}."
    text = parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]
    return f"Figures in this section come from {text}."


def fill_sources(text: str, out: str, errors: list[str], where: str) -> str:
    """Replace each section's marker with its sources line. A section is
    everything from one `## ` heading to the next."""
    parts = re.split(r"(?m)^(?=## )", text)
    for i, sec in enumerate(parts):
        names = [m.group(1) for m in PLACEHOLDER.finditer(sec) if m.group(1) != "sources"]
        marks = sec.count(SOURCES_MARK)
        title = sec.split("\n", 1)[0] or "(top)"
        if names and marks != 1:
            errors.append(f"{where}: section {title!r} has figures and {marks} {SOURCES_MARK} markers, needs 1")
        elif not names and marks:
            errors.append(f"{where}: section {title!r} has a {SOURCES_MARK} marker but no figures")
        elif names:
            parts[i] = sec.replace(SOURCES_MARK, sources_line(names, out))
    return "".join(parts)


def render(text: str, errors: list[str], where: str) -> str:
    def sub(m: re.Match) -> str:
        try:
            return fmt(m.group(1), m.group(2))
        except Exception as e:  # noqa: BLE001 - every failure is reported
            errors.append(f"{where}: {{{{{m.group(1)}}}}}: {type(e).__name__}: {e}")
            return m.group(0)
    return PLACEHOLDER.sub(sub, text)


def hand_typed(text: str) -> list[tuple[int, str]]:
    """Numbers outside placeholders, code, links and the allowlist."""
    text = re.sub(r"```.*?```", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)
    text = PLACEHOLDER.sub("", text)
    for a in ALLOWLIST:
        text = text.replace(a, re.sub(r"[^\n]", " ", a))
    text = re.sub(r"`[^`\n]*`", "", text)
    text = re.sub(r"\]\([^)]*\)|(?:src|srcset|href)=\"[^\"]*\"|https?://\S+", "", text)
    return [(text.count("\n", 0, m.start()) + 1, m.group(0)) for m in LITERAL.finditer(text)]


def with_inputs(names: set[str]) -> set[str]:
    """The named figures plus every figure their formulas refer to."""
    todo, seen = list(names), set()
    while todo:
        n = todo.pop()
        if n in seen or n not in REGISTRY:
            continue
        seen.add(n)
        if REGISTRY[n].kind == "formula":
            todo += _REF.findall(REGISTRY[n].source)
    return seen


def sources_md(used: set[str]) -> str:
    out = ["# Figure sources", "",
           "Generated by `python -m experiments.render_docs`; do not edit. Every number in "
           "`README.md`, `results/README.md` and `data/README.md` is rendered from one of the "
           "figures below. A **lookup** reads one cell of a committed file, a **formula** is "
           "computed from other figures at full precision (`{name}` stands for a figure), a "
           "**computed** figure is an aggregate over a committed per-query file, and a "
           "**constant** cites where it comes from. Constants marked \"not reproducible from "
           "results/\" are recorded nowhere in this repository. Listed: every figure the "
           "READMEs use, and every figure those formulas are built from.", "",
           "The registry is `experiments/figures.py`.", "", "## Notes", ""]
    out += [f"- {n}" for n in NOTES]
    out += ["", "## Figures", "", "| figure | value | kind | source |", "|---|---:|---|---|"]
    for name in sorted(with_inputs(used)):
        v = value(name)
        shown = repr(v) if isinstance(v, str) else (f"{v:.0f}" if float(v).is_integer() else repr(v))
        src = REGISTRY[name].source.replace("|", "\\|")
        out.append(f"| `{name}` | {shown} | {REGISTRY[name].kind} | {src} |")
    return "\n".join(out) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    errors: list[str] = []
    rendered: dict[str, str] = {}
    templates = {tpl: (TEMPLATES / tpl).read_text(encoding="utf-8") for tpl in OUTPUTS}
    for tpl, out in OUTPUTS.items():
        text = templates[tpl]
        text = fill_sources(text, out, errors, f"docs/templates/{tpl}")
        rendered[out] = render(text, errors, f"docs/templates/{tpl}")
        if args.check:
            errors += [f"docs/templates/{tpl}:{line}: hand-typed number {lit!r}"
                       for line, lit in hand_typed(text)]
    used = {m.group(1) for text in templates.values() for m in PLACEHOLDER.finditer(text)}
    rendered[SOURCES] = sources_md(used)

    if args.check:
        for out, text in rendered.items():
            path = REPO_ROOT / out
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                errors.append(f"{out}: differs from its rendering; run python -m experiments.render_docs")
        for e in errors:
            print(e, file=sys.stderr)
        print(f"{len(REGISTRY)} figures, {len(rendered)} files: "
              f"{'FAILED, ' + str(len(errors)) + ' problem(s)' if errors else 'ok'}")
        sys.exit(1 if errors else 0)

    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        sys.exit(1)
    for out, text in rendered.items():
        (REPO_ROOT / out).write_text(text, encoding="utf-8")
        print(f"wrote {out}")


if __name__ == "__main__":
    main()
