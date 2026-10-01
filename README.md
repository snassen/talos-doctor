# talos-doctor

**A pull request checker for the age of coding agents.** Before you let an AI agent read a change, talos-doctor
reads it first, without any model that can act, and tells you whether the change carries text written to steer
the agent rather than to inform you. What it hands on is a cleaned version an ordinary LLM can read safely.

It was made for [Talos](#made-for-talos) (the `talos-core` repository, beside this one), whose own changes it
screens, but nothing in the screen is specific to Talos: point it at any pull request, any diff, any folder.

## Why

An agent that reviews a pull request reads everything in it: code, comments, docs, data files, the title and
description, the commit messages. Any of that can carry instructions meant for the agent: plainly in a code
comment, in an HTML comment that never shows on the rendered page, in a base64 blob, in invisible Unicode
characters, or broken up with look-alike letters so a simple search misses it. If the agent has tools (a
shell, your files, your accounts), whoever wrote the pull request can borrow them.

talos-doctor sits in front: it screens the change, decides whether an agent may read it, and gives the agent
only a cleaned copy, never the raw text.

## Run it

It needs nothing but [uv](https://docs.astral.sh/uv/), and no packages beyond Python's own:

```bash
uvx --from git+<this repository's URL> talos-doctor pr octocat/hello-world 42 --out review/
```

```bash
talos-doctor pr OWNER/REPO NUMBER --out review/   # a GitHub pull request (GITHUB_TOKEN for private ones)
talos-doctor scan --diff change.patch             # a unified diff, or - for standard input
talos-doctor scan path/to/folder                  # files and folders, every line as if added
talos-doctor scan ... --json                      # the findings as JSON, for a script or a pipeline
```

The verdict, and the exit code:

| Verdict | Exit | Meaning |
|---|---|---|
| **block** | 2 | No agent reads this change, cleaned or not, before a person has looked. |
| **review** | 1 | An agent may read `review/cleaned.diff` only. |
| **clean** | 0 | No rule fired. |

`--out DIR` writes three files, and **none of them repeats a flagged text**, so all three are safe to give an
agent:

- `report.md`: the verdict, and each finding with its rule, its place and why it matters;
- `findings.json`: the same, for machines;
- `cleaned.diff`: the change as an agent may read it, with every flagged line replaced by
  `«withheld: rule»` and hidden characters shown as `«U+200B»`.

## How it screens

1. **Read the change as text, never run it.** A pull request comes through GitHub's API (GET requests only):
   title, description, commit messages and each file's diff. Nothing is checked out, so nothing in the change
   (git hooks, attribute filters, install scripts, tests) can run.
2. **Deterministic rules.** 24 rules, as data in `src/talos_doctor/screen/rules.json`, each with the reason it
   exists:
   - **Hidden characters**: Unicode tag characters (ASCII smuggling), direction controls (Trojan Source),
     zero-width characters, runs of variation selectors, control and private-use characters, words mixing
     Latin with Cyrillic or Greek look-alikes.
   - **Encoded text**: long base64 and escape-sequence blobs are decoded and screened again; very long lines.
   - **Hiding places in markup**: HTML comments and invisible styles in Markdown and HTML.
   - **Instruction-like text**, in English, Swedish, German, French and Spanish: telling a model to drop its
     instructions, speaking to "the AI", chat-template tokens, asking to hide something from the user or to
     approve without review, asking to run a command. Each line is also read with hidden characters removed and
     look-alike letters made Latin, so a broken-up phrase is still caught.
   - **Files that matter more**: files agents read as instructions (`AGENTS.md`, `CLAUDE.md`, `.cursorrules`,
     Copilot instructions, skills, MCP configuration), files that run code (CI, install scripts, hooks,
     `conftest.py`), git plumbing, dependencies.
3. **A model that cannot act (next).** Rules miss paraphrases. The next stage asks Jev, a hosted classifier
   with no tools that answers only with probabilities, three bounded questions about each piece: does it try to
   steer a model, does it hide something from the reviewers, does it push for approval? In a first trial it
   recognised all 7 test attacks, including 5 paraphrased ones the rules missed, for a fraction of a cent.
4. **The agent reads the cleaned copy**, in a session with no access to anything that matters, and reports to
   you. You decide.

What it does **not** cover: whether *running* the change is safe. Malicious code needs no instructions to a
model; read and test it in a throwaway environment as you always would.

## Made for Talos

Talos is a local command center over your own mail and Teams, built to be developed with AI agents. Its pull
requests are screened by talos-doctor before an agent reviews them, and the screen's rules are trained in
Talos's own lab: an answer key, Jev's judgements, rules mined from where they agree, and a person deciding.
Every sample used in that training carries a harmless canary instead of a real payload, so no model is ever
fed a working injection.

talos-doctor also checks that a Mac is ready for Talos (`talos doctor` inside Talos):

```bash
talos-doctor                    # every check: the Mac, the code, the database, your personal part, each
                                # account, the model, the services, the extras; then the next steps in order
talos-doctor --only accounts    # one phase
talos-doctor --guides           # step-by-step guides: install, postgresql, personal-part, gmail,
talos-doctor --guide microsoft-365   # microsoft-365, imap, jev, services, tailscale
```

## What it promises

- **The screen never repeats what it flags.** A finding carries a rule, a place and a safe description, never
  the matched text. The tests hold it with synthetic attacks whose payload is a canary.
- **It reads changes as text.** GitHub's API, GET requests for pull requests only; no checkout.
- **The Talos checks read only, and never read a secret.** Commands are limited to their read-only
  subcommands (`talos_doctor/probe.py`), the database is asked in a read-only transaction, and Keychain items
  are looked up by name only.
- **No packages**: the Python standard library only.

## Working on it

```bash
uv sync
uv run pytest -q
```

A new screen rule is an entry in `screen/rules.json` with a reason, a canary sample in `tests/test_screen.py`
that it catches, and a run over ordinary code (`talos-doctor scan <a big repository>`) showing it stays quiet
there. A new Talos check is a function in `checks.py` with a test against the made-up Mac in `tests/fakes.py`.
Agents working on this repository follow [CLAUDE.md](CLAUDE.md).

MIT licensed: see [LICENSE](LICENSE).
