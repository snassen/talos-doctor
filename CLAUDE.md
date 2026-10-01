# Working on talos-doctor

talos-doctor checks that a Mac is ready for Talos and prints the next step. It is public; keep it free of
any one person's data: invented names, `.example` domains, no real accounts, addresses or machine names
(`tests/test_traces.py`).

The promises, held by tests/test_doctor.py:

1. **Read only.** Every command goes through `Probe.run`, limited to `ALLOWED`; files are only read; the
   database only in a read-only transaction; the only web request is to 127.0.0.1.
2. **Never a secret.** Keychain items are looked up by name (`security find-generic-password` without -w or -g).
3. **Standard library only**, so `uvx` runs it before anything else is installed.

A new check: a function in `checks.py` with `@check(id, phase, needs)` returning `Result`s, a test in
`tests/test_doctor.py` against `tests/fakes.py`, and its guide in `src/talos_doctor/guides/` when it needs one.
Each `fix` is an exact command or one short instruction.

```bash
uv sync && uv run pytest -q
```
