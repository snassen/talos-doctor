# talos-doctor

Is this Mac ready for Talos (the `talos-core` repository, beside this one), and if not, what is the next step?
And is this pull request safe for an agent to read?

`talos-doctor` checks everything a Talos installation needs, in the order you set it up: the Mac, the
code, the database, your personal part, each of your accounts, the model, the background services and the
extras. For anything missing it prints the exact command to run, or the step-by-step guide to read, and the
first thing to fix comes first.

```
Machine
  ok    A Mac: macOS 26.0
  ok    Homebrew
  ok    uv: uv 0.9.0
Database
  FAIL  PostgreSQL answers: nothing answers on /tmp port 5433
  skip  The pgvector extension: needs postgresql-running first
...
Next steps (1), the first one first:
  1. PostgreSQL answers: nothing answers on /tmp port 5433
       brew services start postgresql@18 (and set port = 5433 in its postgresql.conf)
       Guide: talos-doctor --guide postgresql
```

## Run it

It needs nothing but [uv](https://docs.astral.sh/uv/), so it runs before Talos is installed:

```bash
uvx --from git+<this repository's URL> talos-doctor
```

Inside a Talos installation it is also `uv run talos doctor`.

```bash
talos-doctor                    # every check, then the next steps
talos-doctor --only accounts    # one phase: machine, code, database, personal, accounts, model, services, extras
talos-doctor --guides           # the step-by-step guides
talos-doctor --guide microsoft-365
talos-doctor --json             # for an agent or a script
talos-doctor --repo ~/code/talos   # when the Talos code is not in a usual place
```

The exit code is 1 when a check failed, so a script can stop on it.

## Screening a pull request before an agent reads it

An agent that reviews a pull request reads everything in it, and a pull request can carry text written for
the agent rather than for you: instructions hidden in invisible characters, in an HTML comment, in a base64
blob, or just written plainly in a code comment. `talos-doctor pr` reads the change first, without any model:

```bash
talos-doctor pr octocat/hello-world 42 --out review/    # any public repository; GITHUB_TOKEN for private ones
talos-doctor scan --diff change.patch --out review/      # a diff
talos-doctor scan path/to/folder                         # files, every line as if added
```

- **block**: no agent should read this change, cleaned or not, before you have looked.
- **review**: an agent may read `review/cleaned.diff` only: flagged lines are withheld («withheld: rule»),
  hidden characters shown («U+200B»).
- **clean**: no rule fired.

`report.md`, `findings.json` and `cleaned.diff` never repeat a flagged text, so they are safe to give an agent.
The pull request is read through GitHub's API as text; nothing is checked out and nothing in it runs. The rules
are data (`src/talos_doctor/screen/rules.json`), each with the reason it exists.

This is the deterministic first stage. A model screen (Jev, which has no tools and answers only with
probabilities) comes next, and the rules are trained further in Talos. It screens what a model reads; running
the change is a separate risk it does not cover.

## What it promises

- **The checks read only.** They run a short list of commands, each limited to the subcommands that only look
  (`talos_doctor/probe.py`, `ALLOWED`); the database is asked in a read-only transaction; the only web request
  is to Talos Web on this Mac. The tests hold it.
- **It never reads a secret.** Keychain items are looked up by name, which says whether one exists without
  reading it (and without macOS asking you for permission).
- **It needs no packages**: the Python standard library only.

## The guides

| Guide | For |
|---|---|
| `install` | from nothing to a first sync, step by step |
| `postgresql` | PostgreSQL 18 with pgvector on port 5433 |
| `personal-part` | your owner.json, accounts.json and the rest |
| `gmail` | Gmail with an app password |
| `microsoft-365` | registering Talos in Entra, its permissions, signing in |
| `imap` | iCloud and other IMAP accounts |
| `jev` | the model that judges new mail (optional) |
| `services` | Talos Web's sign-in and the background services |
| `tailscale` | Talos Web on your phone (optional) |

## Working on it

```bash
uv sync
uv run pytest -q
```

The checks are in `src/talos_doctor/checks.py`, one function each, registered with `@check(id, phase, needs)`.
Every check runs against a made-up Mac in the tests (`tests/fakes.py`), never the real one. A new check
gets a test, and a new command it runs must be added to `ALLOWED` with only its read-only subcommands.

MIT licensed: see [LICENSE](LICENSE).
