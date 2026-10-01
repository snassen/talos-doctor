# What comes next

Revised after entry 5: rules mined from single phrasings add little until the ordinary side is far broader, so
the effort goes to Jev's side first.

1. **A learned combination of Jev's answers.** Today the verdict uses one score and two fixed thresholds. A small
   model over all three probabilities, the rules that fired and the kind of text, fitted on the lab's samples and
   measured on a held-back part, ships as a handful of numbers (standard library only). Example of what it should
   learn: a chatbot request steers a model but hides nothing and pushes nothing; an attack usually does both.
2. **Question wording, on repository files.** The weak spot (43% caught). Each wording is tried on that source
   alone ($0.12 a try) and kept only if it measures better; a separate question for changes that do harm when run
   or installed is one option, if the screen is to cover that side at all.
3. **A broader ordinary side.** Public code and documentation from many repositories (READMEs above all) and
   ordinary e-mail at scale, so false alarms are measured against what real changes look like, and mining can be
   tried again.
4. **Finer withholding.** A piece Jev flags split and asked again, so only the lines carrying the attack are withheld.
5. **More sources**, each a module in the lab: garak's generators for variants, AgentDojo's injection tasks, the
   GitInject study's pull-request attacks; a weekly check for new revisions of the pinned ones.
