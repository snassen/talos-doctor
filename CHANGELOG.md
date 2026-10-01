# Changelog

## [Unreleased]

### Changed
- The README leads with what talos-doctor mostly is: a pull request checker that makes a change safe for an
  ordinary LLM to read, made for Talos and usable on any repository.

## [0.2.0] - 2026-10-01

### Added
- **The screen**: `talos-doctor pr OWNER/REPO NUMBER` and `talos-doctor scan` check a change for text aimed at a
  model before any agent reads it, for any repository. 24 deterministic rules, as data (`screen/rules.json`):
  hidden characters (Unicode tags, direction controls, zero-width, variation runs, look-alike letters),
  encoded blobs (decoded and screened again), hiding places in markup, instruction-like phrasing in five
  languages (also when broken up by hidden or look-alike characters), and files agents read as instructions
  or that run code. A pull request is read through GitHub's API as text, never checked out.
- The verdict (block, review, clean), a report, the findings as JSON, and a cleaned view in which flagged
  lines are withheld and hidden characters shown. None of them repeats a flagged text.

## [0.1.0] - 2026-10-01

### Added
- The first checks: the Mac, the code, the database, the personal part, each account, the model, the
  background services and the extras, each with its next step.
- Nine step-by-step guides (`talos-doctor --guides`).
- `--json` for agents and scripts, `--only` for one phase, `--repo` and `--home` for unusual places.
