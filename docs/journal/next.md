# What comes next

1. **Rules mined from Jev's catches.** The 9,899 attacks Jev caught and the rules missed are the material:
   phrasings frequent among attacks and absent from all ordinary text (Talos's code, the false-positive e-mails,
   the repository files' ordinary side), proposed as rule candidates, each measured for precision and catch on the
   lab before a person accepts it. Measured on a held-out part of the samples, so the rules are not just fitted to
   the datasets. Every accepted rule makes the free stage stronger and leaves Jev less to do.
2. **The repository files.** Question wording tried on that source alone ($0.12 a try); and perhaps a fourth
   question for changes that do harm when run or installed, if the screen is to cover that side at all.
3. **Finer withholding.** A piece Jev flags could be split and asked again, so that only the lines that carry the
   attack are withheld.
4. **More sources**, each a module in the lab: garak's generators (encodings, invisible characters, look-alikes)
   for variants, AgentDojo's injection tasks, and the GitInject study's pull-request attacks; and a weekly check for
   new revisions of the pinned ones, re-measuring when one changes.
