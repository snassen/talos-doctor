# Working on talos-doctor

talos-doctor checks that a Mac is ready for Talos and prints the next step, and screens a change (a pull
request, a diff) for text aimed at a model before an agent reads it (`src/talos_doctor/screen/`). It is public; keep it free of
any one person's data: invented names, `.example` domains, no real accounts, addresses or machine names
(`tests/test_traces.py`).

The promises, held by tests/test_doctor.py:

1. **Read only.** Every command goes through `Probe.run`, limited to `ALLOWED`; files are only read; the
   database only in a read-only transaction; the only web request is to 127.0.0.1.
2. **Never a secret.** Keychain items are looked up by name (`security find-generic-password` without -w or -g).
3. **Standard library only**, so `uvx` runs it before anything else is installed.

4. **The screen never repeats what it flags.** A Finding carries a rule, a place and a safe description,
   never the matched text; the cleaned view withholds flagged lines. `tests/test_screen.py` holds it with
   canary samples. Test samples carry a harmless canary (reply with CANARY-…), never a real payload.
5. **A pull request is read as text** through GitHub's API (GET /repos/…/pulls only), never checked out.

A new screen rule: an entry in `screen/rules.json` with a reason (`why`), a canary sample in
`tests/test_screen.py` that it catches, and a run over ordinary code (`talos-doctor scan <a big repository>`)
that shows it does not fire there.

A new check: a function in `checks.py` with `@check(id, phase, needs)` returning `Result`s, a test in
`tests/test_doctor.py` against `tests/fakes.py`, and its guide in `src/talos_doctor/guides/` when it needs one.
Each `fix` is an exact command or one short instruction.

```bash
uv sync && uv run pytest -q
```
