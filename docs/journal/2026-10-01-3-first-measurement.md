# 3. The lab's first measurement

**The lab.** Talos's screen lab (`talos screen`) holds samples of prompt injection and of ordinary text. Each
source is a module, switched on or off, with its own cap (a stratified sample, the same every time), pinned to
the revision it was imported at. Duplicates across all sources, exact (the same normalized text) or near
(MinHash on word 5-shingles, 3 of 16 bands shared), point at the sample they repeat and are left out of every
measurement. Samples are handled by code and by Jev only, and never printed.

## Sources (imported 1 October 2026)

| Source | Licence | Revision | Imported | Attack | Ordinary | Duplicates |
|---|---|---|---|---|---|---|
| prompt-injection-repo-dataset (prodnull, Hugging Face, gated) | Apache-2.0 | 6c56b897ee4a | 5,671 | 2,916 | 2,755 | 78 |
| LLMail-Inject phase 2, judged (Microsoft, Hugging Face), cap 20,000 | MIT | 1063bdf01ec8 | 19,999 | 19,808 | 191 | 8,195 |
| deepset/prompt-injections (Hugging Face) | Apache-2.0 | 4f61ecb038e9 | 662 | 263 | 399 | 33 |
| AgentInjectionBench (GitHub) | Apache-2.0 | file 606cb74f5ce8 | 182 | 142 | 40 | 0 |
| agent-injection-bench (GitHub) | MIT | file 73e1d4274d0f | 24 | 21 | 3 | 0 |
| Talos's own code and docs, in 60-line pieces, cap 5,000 | MIT | 2b8995740637 | 1,253 | 0 | 1,253 | 4 |

19,481 unique samples: 14,963 attacks, 4,518 ordinary.

**Data decisions.**

- *LLMail-Inject's "not an attack" submissions are left out.* They were written for an injection challenge, and
  many carry chat-template markup or invisible text: no trustworthy ordinary text. The challenge's own
  false-positive e-mails are the ordinary e-mail instead. (Kept in at first, they made up 172 of the rules' 204
  false alarms.)
- *deepset's ordinary samples are requests to a chatbot* ("translate this", "write a poem"): instructions to a
  model by nature. In a pull request they would deserve a look, so they count as false alarms below, but read
  the rates without them too.
- *Duplicates matter.* 42% of the LLMail sample were near repeats (attackers resubmitting variants); counted
  twice, they would have inflated every rate.

## Results

| | Caught | Blocked | False alarms |
|---|---|---|---|
| The rules (24, version 079312b2dff7) | 13.1% | 6.2% | 0.7% |
| Jev (question version 05f3075c93b5f203, threshold 0.5) | 77.4% | 38.8% | 7.3% |
| Combined (the stricter verdict) | 79.2% | | 7.8% |

"Caught" is any verdict but clean (an agent sees only the cleaned view); "blocked" is block alone. The Jev run
judged all 19,481 samples for $0.39.

**The two complement each other.** Of the attacks, both caught 1,688, Jev alone 9,899 (free wording), the rules
alone 270 (hidden characters and encoded text a model reads past), neither 3,106.

**Per source** (caught / false alarms): repository files, rules 7.1% / 0.0%, Jev 43.1% / 8.2%; LLMail e-mail,
rules 14.5% / 0.0%, Jev 85.5% / 0.0%; agent benchmarks, Jev 89–95%; Talos's own code, false alarms rules 2.2%
(the agent-instruction files, flagged by design) and Jev 1.0%.

**Precision of the rules where they fire** (on attacks / ordinary text): override phrasing 98.5%, speaking to the
model 99.4%, base64 97.1%, escapes, run-this and conceal 100%; the weakest, chat markup 80.0% and system-prompt
talk 82.2%.

**The threshold is a dial** (Jev's "steers a model" score, or a rule; deepset left out):

| Threshold | 0.1 | 0.2 | 0.3 | 0.5 | 0.7 | 0.9 |
|---|---|---|---|---|---|---|
| Caught, all sources | 88.7% | 86.1% | 83.8% | 79.0% | 71.8% | 57.4% |
| False alarms, all sources | 13.6% | 11.0% | 9.3% | 6.3% | 4.7% | 1.9% |
| Caught, repository files | 57.3% | 53.0% | 50.3% | 45.2% | 39.4% | 30.3% |
| False alarms, repository files | 17.9% | 14.6% | 12.4% | 8.2% | 6.0% | 1.8% |

## Findings

1. **Rules alone are not enough**; they are precise but catch little of what attackers write freely. Jev is the
   strong half, the rules the cheap and certain half.
2. **Review and block want different thresholds.** A false "review" costs almost nothing (the agent reads the
   cleaned view); a false "block" costs a person's time. Hence the tiers in entry 4.
3. **Repository files are the weak spot**, and the one that matters most. Part of it is the dataset counting
   malicious *code* (credential harvesting, poisoned CI steps) as attacks: that is no instruction to a model, and
   the screen does not claim to judge whether running a change is safe. Part is room to improve (see next.md).
