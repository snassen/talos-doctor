"""talos-doctor: is this Mac ready for Talos, and if not, what is the next step?

    talos-doctor                  every check, then the next steps in order
    talos-doctor --only accounts  one phase (machine, code, database, personal, accounts, model, services, extras)
    talos-doctor --json           the results as JSON (for an agent or a script)
    talos-doctor --guide NAME     a step-by-step guide (talos-doctor --guides lists them)
    talos-doctor --repo PATH      where the Talos code is, when it is not in a usual place

It reads only, and never reads a secret (talos_doctor.probe). The exit code is 1 when a check failed.
"""

from __future__ import annotations

import argparse
import sys
from importlib import resources

from talos_doctor import __version__
from talos_doctor.checks import FAIL, PHASES, WARN, Context, as_json, run_all
from talos_doctor.probe import Probe

MARK = {"ok": "ok  ", "warn": "warn", "fail": "FAIL", "skip": "skip", "info": "info"}


def guides() -> dict[str, str]:
    """name: first heading, of every guide shipped with the doctor."""
    out = {}
    for f in sorted(resources.files("talos_doctor").joinpath("guides").iterdir(), key=lambda p: p.name):
        if f.name.endswith(".md"):
            out[f.name[:-3]] = f.read_text(encoding="utf-8").splitlines()[0].lstrip("# ").strip()
    return out


def guide(name: str) -> str | None:
    f = resources.files("talos_doctor").joinpath("guides", f"{name}.md")
    return f.read_text(encoding="utf-8") if f.is_file() else None


def report(results, ctx: Context) -> str:
    lines = [f"Talos doctor {__version__}: reads only, changes nothing, never reads a secret.", ""]
    if ctx.repo:
        lines.append(f"Talos code: {ctx.repo}")
    lines += [f"Data folder: {ctx.home}", f"Personal part: {ctx.config}", ""]
    for phase in PHASES:
        rows = [r for r in results if r.phase == phase]
        if not rows:
            continue
        lines.append(phase.capitalize())
        for r in rows:
            lines.append(f"  {MARK[r.status]}  {r.title}" + (f": {r.detail}" if r.detail else ""))
        lines.append("")
    todo = [r for r in results if r.status in (FAIL, WARN) and (r.fix or r.guide)]
    if todo:
        lines.append(f"Next steps ({len(todo)}), the first one first:")
        for i, r in enumerate(todo, 1):
            lines.append(f"  {i}. {r.title}: {r.detail}")
            if r.fix:
                lines.append(f"       {r.fix}")
            if r.guide:
                lines.append(f"       Guide: talos-doctor --guide {r.guide}")
    else:
        lines.append("Nothing to fix.")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None, probe: Probe | None = None) -> int:
    p = argparse.ArgumentParser(prog="talos-doctor", description="Is this Mac ready for Talos? Reads only.")
    p.add_argument("--version", action="version", version=f"talos-doctor {__version__}")
    p.add_argument("--json", action="store_true", help="the results as JSON")
    p.add_argument("--only", action="append", choices=PHASES, help="only this phase (may be given twice)")
    p.add_argument("--repo", help="the Talos code's folder")
    p.add_argument("--home", help="the data folder (default TALOS_HOME, else ~/TalosData)")
    p.add_argument("--guide", metavar="NAME", help="print a step-by-step guide")
    p.add_argument("--guides", action="store_true", help="list the guides")
    a = p.parse_args(argv)
    if a.guides:
        for name, title in guides().items():
            print(f"{name:<16} {title}")
        return 0
    if a.guide:
        text = guide(a.guide)
        if text is None:
            print(f"no guide {a.guide!r}; talos-doctor --guides lists them", file=sys.stderr)
            return 2
        print(text, end="")
        return 0
    probe = probe or Probe()
    ctx = Context.find(probe, repo=a.repo, home=a.home)
    results = run_all(ctx, set(a.only) if a.only else None)
    print(as_json(results) if a.json else report(results, ctx), end="" if not a.json else "\n")
    return 1 if any(r.status == FAIL for r in results) else 0


def entry() -> None:
    sys.exit(main())
