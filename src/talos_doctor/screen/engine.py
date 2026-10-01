"""The deterministic screen: rules as data (rules.json) over the text of a change, before any model reads it.

A change is a list of Pieces: each file's diff, and the pull request's title, description and commit
messages. Every rule looks at the lines it applies to ("added" lines, or "all" of them) and yields Findings:
which rule, where, and a description that is safe to show. **A Finding never carries the text it found**, so
nothing the screen writes (the report, the JSON, the cleaned view) can carry an injection on to the agent that
reads it.

The cleaned view is the change as the agent may see it: invisible characters are shown as «U+XXXX» marks, and
every line a phrase, markup or encoding rule flagged is replaced by «withheld: rule ids». The verdict is
"block" when any block rule fired (no agent should read this change, cleaned or not, before a person has), "review"
when a flag rule fired (an agent may read the cleaned view only), else "clean".

Encoded blobs (base64, escape runs) are decoded and screened again: an injection inside one is reported as such.
"""

from __future__ import annotations

import base64
import binascii
import codecs
import json
import re
import unicodedata
from dataclasses import dataclass, field
from importlib import resources

SEVERITY = {"block": 3, "flag": 2, "note": 1}
WITHHOLD_KINDS = ("regex", "long_line", "decoded")    # their lines are withheld from the cleaned view
LATIN, OTHER = "LATIN", ("CYRILLIC", "GREEK")


@dataclass
class Line:
    number: int | None   # the line in the new file (None for a removed line, or text without numbers)
    kind: str            # "+" added, "-" removed, " " context
    text: str


@dataclass
class Piece:
    source: str          # file, title, body, commit
    path: str            # the file's path, or a label ("pull request title", "commit 1a2b3c4")
    lines: list[Line] = field(default_factory=list)
    status: str = ""     # file: added, modified, removed, renamed; "unscreened" when no text came with it
    old_path: str = ""


@dataclass
class Finding:
    rule: str
    severity: str
    why: str
    source: str
    path: str
    line: int | None = None
    detail: str = ""     # safe to show: never the matched text
    kind: str = field(default="", repr=False)      # the rule's kind (path, chars, regex, decoded…)
    index: int | None = field(default=None, repr=False)   # the line's place in its Piece

    def as_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v not in ("", None) and k not in ("kind", "index")}


def load_rules(path=None) -> list[dict]:
    text = open(path, encoding="utf-8").read() if path else \
        resources.files("talos_doctor.screen").joinpath("rules.json").read_text(encoding="utf-8")
    rules = json.loads(text)["rules"]
    for r in rules:
        if r.get("pattern"):
            r["_re"] = re.compile(r["pattern"], (re.I if r.get("ignore_case") else 0) | re.M)
        r["_paths"] = [re.compile(p) for p in r.get("paths", [])]
        r["_ranges"] = [(int(a, 16), int(b, 16)) for a, b in r.get("ranges", [])]
    return rules


def parse_diff(text: str) -> list[Piece]:
    """A unified diff (git diff, or a .patch) into one Piece per file, with new-file line numbers."""
    pieces, cur, new_no = [], None, 0
    for raw in text.splitlines():
        if raw.startswith("diff --git "):
            m = re.match(r"diff --git a/(.*) b/(.*)$", raw)
            cur = Piece("file", m.group(2) if m else raw[11:], status="modified", old_path=m.group(1) if m else "")
            pieces.append(cur)
        elif cur is None and raw.startswith("+++ "):
            cur = Piece("file", raw[4:].removeprefix("b/").strip(), status="modified")
            pieces.append(cur)
        elif raw.startswith("+++ ") or raw.startswith("--- "):
            if raw.startswith("+++ ") and cur is not None and raw[4:].strip() != "/dev/null":
                cur.path = raw[4:].strip().removeprefix("b/")
            continue
        elif raw.startswith("new file mode") and cur:
            cur.status = "added"
        elif raw.startswith("deleted file mode") and cur:
            cur.status = "removed"
        elif raw.startswith("Binary files") and cur:
            cur.status = "unscreened"
        elif raw.startswith("@@"):
            m = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)", raw)
            new_no = int(m.group(1)) if m else 0
        elif cur is not None and raw[:1] in ("+", "-", " "):
            kind = raw[0]
            cur.lines.append(Line(new_no if kind != "-" else None, kind, raw[1:]))
            if kind != "-":
                new_no += 1
    return pieces


def text_piece(source: str, label: str, text: str) -> Piece:
    """Text that is not a diff (a description, a commit message, a whole file): every line counts as added."""
    return Piece(source, label, [Line(i, "+", t) for i, t in enumerate((text or "").splitlines(), 1)])


# ---------------------------------------------------------------- matching

def _in(cp: int, ranges) -> bool:
    return any(a <= cp <= b for a, b in ranges)


def _chars(rule, text: str, at_start: bool) -> list[int]:
    hits = [ord(c) for i, c in enumerate(text) if _in(ord(c), rule["_ranges"])
            and not (rule.get("ignore_bom_at_start") and at_start and i == 0 and c == "﻿")]
    return hits


def _run(rule, text: str) -> int:
    best = n = 0
    for c in text:
        n = n + 1 if _in(ord(c), rule["_ranges"]) else 0
        best = max(best, n)
    return best if best >= rule.get("min_run", 1) else 0


def _scripts(word: str) -> set[str]:
    out = set()
    for c in word:
        if c.isalpha():
            name = unicodedata.name(c, "")
            out.add(LATIN if name.startswith("LATIN") else next((s for s in OTHER if name.startswith(s)), "OTHER"))
    return out


def _mixed(text: str) -> int:
    return sum(1 for w in re.findall(r"\w{3,}", text) if LATIN in (s := _scripts(w)) and s & set(OTHER))


def _decode(kind: str, blob: str) -> str | None:
    try:
        if kind == "base64":
            raw = base64.b64decode(blob + "=" * (-len(blob) % 4), validate=False)
        else:
            raw = codecs.decode(blob, "unicode_escape").encode("latin-1", "ignore")
        text = raw.decode("utf-8")
    except (binascii.Error, ValueError, UnicodeDecodeError):
        return None
    printable = sum(1 for c in text if c.isprintable() or c in "\n\t")
    return text if text and printable / len(text) > 0.9 else None


# Cyrillic and Greek letters that look like Latin ones, for reading a line the way a person (or a model) does.
CONFUSABLE = str.maketrans("аеорсухіјѕԁԛԝАВЕКМНОРСТХІЈЅοаνρτχκιΑΒΕΖΗΙΚΜΝΟΡΤΥΧ",
                           "aeopcyxijsdqwABEKMHOPCTXIJSoavptxkiABEZHIKMNOPTYX")
HIDDEN = [(0x200B, 0x200F), (0x2060, 0x2064), (0x180E, 0x180E), (0xFE00, 0xFE0F), (0xE0000, 0xE007F),
          (0xE0100, 0xE01EF), (0x202A, 0x202E), (0x2066, 0x2069), (0x00AD, 0x00AD), (0xFEFF, 0xFEFF)]


def normalize(text: str) -> str:
    """The line as it reads: hidden characters removed, compatibility forms folded, look-alike letters made Latin."""
    visible = "".join(c for c in text if not _in(ord(c), HIDDEN))
    return unicodedata.normalize("NFKC", visible).translate(CONFUSABLE)


def _desc(cps: list[int]) -> str:
    first = ", ".join(f"U+{cp:04X}" for cp in sorted(set(cps))[:3])
    return f"{len(cps)} character{'s' if len(cps) != 1 else ''} ({first}{'…' if len(set(cps)) > 3 else ''})"


def screen_text(rules: list[dict], text: str, *, at_start: bool = False, path: str = "") -> list[tuple[dict, str]]:
    """(rule, safe detail) for one line of text."""
    out = []
    norm = normalize(text)
    for r in rules:
        if r["_paths"] and r["kind"] != "path" and not any(p.search(path) for p in r["_paths"]):
            continue
        k = r["kind"]
        if k == "chars":
            cps = _chars(r, text, at_start)
            if cps:
                out.append((r, _desc(cps)))
        elif k == "char_run":
            n = _run(r, text)
            if n:
                out.append((r, f"a run of {n} variation selectors"))
        elif k == "mixed_script":
            n = _mixed(text)
            if n:
                out.append((r, f"{n} word{'s' if n != 1 else ''} mixing Latin with Cyrillic or Greek"))
        elif k == "long_line":
            if len(text) > r.get("max_len", 1000):
                out.append((r, f"{len(text):,} characters"))
        elif k == "regex":
            for m in r["_re"].finditer(text):
                if r.get("decode"):
                    out.append((r, f"{r['decode']} blob of {len(m.group(0)):,} characters"))
                    decoded = _decode(r["decode"], m.group(0))
                    if decoded is not None:
                        inner = [x for x in screen_text([q for q in rules if not q.get("decode") and q["kind"] != "path"
                                                         and q["kind"] != "long_line"], decoded, path=path)]
                        for q, d in inner:
                            out.append(({**q, "kind": "decoded"}, f"inside the decoded {r['decode']} blob: {d or q['id']}"))
                else:
                    out.append((r, "matched"))
                    break
            else:
                if not r.get("decode") and norm != text and r["_re"].search(norm):
                    out.append((r, "matched once hidden or look-alike characters are read through"))
    return out


def screen(pieces: list[Piece], rules: list[dict] | None = None) -> list[Finding]:
    rules = rules if rules is not None else load_rules()
    line_rules = [r for r in rules if r["kind"] != "path"]
    findings = []
    for pc in pieces:
        if pc.source == "file":
            for r in (r for r in rules if r["kind"] == "path"):
                if any(p.search(pc.path) or (pc.old_path and p.search(pc.old_path)) for p in r["_paths"]):
                    findings.append(Finding(r["id"], r["severity"], r["why"], pc.source, pc.path, None, pc.status or "changed",
                                            kind="path"))
            if pc.status == "unscreened":
                findings.append(Finding("file.unscreened", "flag", "No text came with this file (binary, or too large "
                                        "to show): a person must look at it.", pc.source, pc.path, kind="path"))
        for i, ln in enumerate(pc.lines):
            for r, detail in screen_text(line_rules, ln.text, at_start=(i == 0), path=pc.path):
                if r.get("applies", "added") == "added" and ln.kind != "+":
                    continue
                findings.append(Finding(r["id"], r["severity"], r["why"], pc.source, pc.path,
                                        ln.number if ln.number is not None else None,
                                        detail if detail != "matched" else ("in a removed line" if ln.kind == "-" else ""),
                                        kind=r["kind"], index=i))
    return findings


def verdict(findings: list[Finding]) -> str:
    worst = max((SEVERITY[f.severity] for f in findings), default=0)
    return "block" if worst == 3 else "review" if worst == 2 else "clean"


# ---------------------------------------------------------------- the cleaned view

def _reveal(text: str, rules: list[dict]) -> str:
    """Invisible and look-alike characters made visible as «U+XXXX»."""
    ranges = [rg for r in rules if r["kind"] in ("chars", "char_run") for rg in r["_ranges"]]
    return "".join(f"«U+{ord(c):04X}»" if _in(ord(c), ranges) else c for c in text)


def cleaned(pieces: list[Piece], findings: list[Finding], rules: list[dict] | None = None) -> str:
    """The change as an agent may read it: flagged lines withheld, invisible characters shown, path notes on top."""
    rules = rules if rules is not None else load_rules()
    withheld: dict[tuple[str, str, int], set[str]] = {}
    by_path: dict[tuple[str, str], list[str]] = {}
    for f in findings:
        if f.kind in WITHHOLD_KINDS or f.kind == "mixed_script":
            withheld.setdefault((f.source, f.path, f.index), set()).add(f.rule)
        elif f.kind == "path":
            by_path.setdefault((f.source, f.path), []).append(f.rule)
    out = []
    for pc in pieces:
        head = f"### {pc.source}: {pc.path}" + (f" ({pc.status})" if pc.status else "")
        out.append(head)
        for rule in by_path.get((pc.source, pc.path), []):
            out.append(f"«note: {rule}»")
        for i, ln in enumerate(pc.lines):
            rules_here = withheld.get((pc.source, pc.path, i))
            body = f"«withheld: {', '.join(sorted(rules_here))}»" if rules_here else _reveal(ln.text, rules)
            out.append(f"{ln.kind if pc.source == 'file' else ''}{body}")
        out.append("")
    return "\n".join(out)
