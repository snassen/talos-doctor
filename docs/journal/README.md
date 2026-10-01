# The developer journal

How talos-doctor's screen came to be what it is: what was tried, what was measured, what was decided and why.
One entry per step, newest last. Numbers are measurements, never samples: no entry quotes an attack text, so
the journal itself is safe for an agent to read.

| Date | Entry |
|---|---|
| 2026-10-01 | [1. The deterministic screen](2026-10-01-1-deterministic-screen.md): 24 rules, the cleaned view, two false alarms fixed, a disguise gap closed |
| 2026-10-01 | [2. A first trial of Jev](2026-10-01-2-jev-trial.md): 14 hand-made pieces, three questions |
| 2026-10-01 | [3. The lab's first measurement](2026-10-01-3-first-measurement.md): six sources, 19,481 unique samples, the rules against Jev |
| 2026-10-01 | [4. The Jev stage](2026-10-01-4-jev-stage.md): tiered thresholds from the measurement, live on a real change |
| 2026-10-01 | [What comes next](next.md) |

The measurements are made in Talos's screen lab (`talos screen`, in the talos-core repository), where the samples
live in a database and are never printed. Anyone can repeat them there: the sources are pinned to the revisions
listed in entry 3.
