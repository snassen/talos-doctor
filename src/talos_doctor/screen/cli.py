"""talos-doctor pr / scan: screen a change before an agent reads it.

    talos-doctor pr OWNER/REPO NUMBER [--out DIR] [--json]   a GitHub pull request, fetched as text only
    talos-doctor scan --diff FILE [--out DIR] [--json]        a unified diff (git diff, a .patch)
    talos-doctor scan PATH… [--out DIR] [--json]              files or folders, every line as if added
    … --jev [--max-usd 0.05]                                  and let Jev read it after the rules (talos_doctor.screen.jev)

The verdict: block (no agent reads it before a person has), review (an agent may read the cleaned view only),
clean (no rule fired). --out writes report.md, findings.json and cleaned.diff, all safe to give an agent: none
of them repeats a flagged text. The exit code is 2 for block, 1 for review, 0 for clean.

The rules always run; Jev (--jev) reads the change after them. The screen covers what a model would read; it does
not make running the change safe.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from talos_doctor import __version__
from talos_doctor.screen import engine
from talos_doctor.screen import jev as jevstage
from talos_doctor.screen.github import FetchError, pull_request

TEXT_SUFFIXES = {".py", ".js", ".ts", ".tsx", ".jsx", ".md", ".txt", ".json", ".toml", ".yml", ".yaml", ".sh", ".html",
                 ".css", ".sql", ".rs", ".go", ".rb", ".java", ".kt", ".swift", ".c", ".h", ".cpp", ".mdx", ".rst", ".cfg",
                 ".ini", ".xml", ".svg", ".ipynb", ".env", ".lock"}
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache", ".mypy_cache", "dist", "build"}
VERDICT_TEXT = {"block": "BLOCK: no agent should read this change, cleaned or not, before a person has looked.",
                "review": "REVIEW: an agent may read the cleaned view only (cleaned.diff), never the raw change.",
                "clean": "CLEAN: no rule fired. The cleaned view is the change with invisible characters shown."}
EXIT = {"block": 2, "review": 1, "clean": 0}


def _files(paths: list[str]) -> list[engine.Piece]:
    out = []
    for p in map(Path, paths):
        for f in ([p] if p.is_file() else sorted(x for x in p.rglob("*") if x.is_file() and not SKIP_DIRS & set(x.parts))):
            if f.suffix.lower() in TEXT_SUFFIXES or f.name in ("Makefile", "Dockerfile", "AGENTS.md", ".cursorrules"):
                try:
                    pc = engine.text_piece("file", str(f), f.read_text(encoding="utf-8"))
                except UnicodeDecodeError:
                    pc = engine.Piece("file", str(f), [], "unscreened")
                pc.status = pc.status or "added"
                out.append(pc)
    return out


def report(findings, verdict: str, meta: dict) -> str:
    stages = "the rules and Jev" if meta.get("jev") else "the rules (Jev not asked: --jev)"
    lines = [f"# Screen of {meta.get('what', 'a change')}", "",
             f"talos-doctor {__version__}, {stages}. {VERDICT_TEXT[verdict]}", ""]
    if meta.get("jev"):
        j = meta["jev"]
        lines.append(f"Jev read {j['chunks']} pieces for ${j['spent_usd']:.4f}.")
    findings = [f for f in findings if not (f.rule.startswith("jev.") and not f.detail)]   # one line per piece
    for k in ("url", "author", "base", "head", "files", "commits"):
        if meta.get(k) not in (None, ""):
            lines.append(f"- {k}: {meta[k]}")
    counts = Counter(f.severity for f in findings)
    lines += ["", f"Findings: {counts.get('block', 0)} block, {counts.get('flag', 0)} flag, {counts.get('note', 0)} note.", ""]
    for sev in ("block", "flag", "note"):
        group = [f for f in findings if f.severity == sev]
        if not group:
            continue
        lines.append(f"## {sev}")
        by_rule: dict[str, list] = {}
        for f in group:
            by_rule.setdefault(f.rule, []).append(f)
        for rule, fs in by_rule.items():
            lines.append(f"- **{rule}**: {fs[0].why}")
            for f in fs[:20]:
                where = f"{f.path}" + (f":{f.line}" if f.line else "")
                lines.append(f"  - {where}" + (f" ({f.detail})" if f.detail else ""))
            if len(fs) > 20:
                lines.append(f"  - … and {len(fs) - 20} more")
        lines.append("")
    lines.append("Nothing above repeats a flagged text. Running the change is a separate risk this screen does not cover.")
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog=f"talos-doctor {argv[0]}", description="Screen a change before an agent reads it.")
    if argv[0] == "pr":
        p.add_argument("repo", help="owner/name")
        p.add_argument("number", type=int)
    else:
        p.add_argument("paths", nargs="*", help="files or folders (every line counts as added)")
        p.add_argument("--diff", help="a unified diff file ('-' for standard input)")
    p.add_argument("--out", help="write report.md, findings.json and cleaned.diff here")
    p.add_argument("--json", action="store_true", help="the findings as JSON on standard output")
    p.add_argument("--rules", help="another rules file (default: the one shipped with the doctor)")
    p.add_argument("--jev", action="store_true", help="let Jev read the change after the rules (needs a Jev key)")
    p.add_argument("--max-usd", type=float, default=0.05, help="the most the Jev stage may cost (default 0.05)")
    a = p.parse_args(argv[1:])
    rules = engine.load_rules(a.rules)
    try:
        if argv[0] == "pr":
            meta, pieces = pull_request(a.repo, a.number)
            meta["what"] = f"{a.repo} pull request {a.number}"
        elif a.diff:
            text = sys.stdin.read() if a.diff == "-" else Path(a.diff).read_text(encoding="utf-8", errors="replace")
            meta, pieces = {"what": f"the diff {a.diff}"}, engine.parse_diff(text)
        else:
            if not a.paths:
                p.error("give --diff FILE, or files or folders to scan")
            meta, pieces = {"what": ", ".join(a.paths)}, _files(a.paths)
    except FetchError as e:
        print(f"talos-doctor: {e}", file=sys.stderr)
        return 3
    findings = engine.screen(pieces, rules)
    if a.jev:
        try:
            jf, meta["jev"] = jevstage.screen(pieces, max_usd=a.max_usd)
        except jevstage.JevError as e:
            print(f"talos-doctor: {e}", file=sys.stderr)
            return 3
        findings += jf
    v = engine.verdict(findings)
    rep = report(findings, v, meta)
    if a.out:
        out = Path(a.out)
        out.mkdir(parents=True, exist_ok=True)
        (out / "report.md").write_text(rep, encoding="utf-8")
        (out / "findings.json").write_text(json.dumps({"verdict": v, **{k: v2 for k, v2 in meta.items()},
                                                       "findings": [f.as_dict() for f in findings]}, indent=2), encoding="utf-8")
        (out / "cleaned.diff").write_text(engine.cleaned(pieces, findings, rules), encoding="utf-8")
    if a.json:
        print(json.dumps({"verdict": v, "findings": [f.as_dict() for f in findings]}, indent=2))
    else:
        print(rep, end="")
        if a.out:
            print(f"\nWritten: {a.out}/report.md, findings.json, cleaned.diff")
    return EXIT[v]
