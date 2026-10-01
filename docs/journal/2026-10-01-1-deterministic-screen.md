# 1. The deterministic screen (talos-doctor 0.2.0)

**The problem.** A coding agent reviewing a pull request reads all of it: code, comments, docs, data files, the
title and description, the commit messages. Text in any of them can be written for the agent rather than for the
people (prompt injection), and an agent with tools can be steered into using them. The first reader of an
untrusted change should therefore be something that cannot act.

**What was built.**

- The change is read as text through GitHub's API (GET only); nothing is checked out, so nothing in it runs.
- 24 rules as data (`src/talos_doctor/screen/rules.json`), each with the reason it exists, written from the
  known techniques (OWASP's LLM01 and its prevention cheat sheet, the published work on invisible-character
  smuggling and Trojan Source): hidden characters, encoded blobs (decoded and screened again), hiding places in
  markup, instruction-like phrasing in five languages, chat-template tokens, requests to conceal or approve, and
  files that agents read as instructions or that run code.
- A verdict (block, review, clean), and a cleaned view in which flagged lines are withheld and hidden characters
  shown. The principle: **nothing the screen writes repeats a flagged text**, so its output is safe for an agent.

**Calibration on ordinary code.** The rules were run over Talos itself (about 55,000 lines, no injections in it):

- Two block verdicts were false alarms: a `<system>` placeholder in a file path, and a labeller's name read as
  "as Claude". The chat-markup rule now needs text after a system tag, and "as …" now counts only when a word like AI or
  language model follows.
- What remained were flags worth a glance: long lines, base64 images in SVG files, code that reads the Keychain.

**A gap found by the tests.** An injection phrase broken up with zero-width characters, Cyrillic look-alike
letters or fullwidth letters slipped past the phrase rules, and the cleaned view would then have shown it
readably. Every phrase rule now also reads the line normalized (hidden characters removed, compatibility forms
folded, look-alikes made Latin). Three tests hold it.

**Tests.** Synthetic attacks whose payload is a harmless canary ("reply with CANARY-…"), one per technique, and a
test that the canary reaches none of the three output files.
