# Jev, the model that judges new mail (optional)

Rules and your own decisions sort mail without any model. Jev, a paid hosted classifier, adds the
judgement of new mail: what kind of mail it is, its topic, and whether it asks something of you. It is
asked bounded questions only; what it answers is a proposal, accepted at levels of sureness you set.

1. Get an API key from Jev's provider, TypeSafe.
2. Put it in the Keychain, pasting it at the prompt:

       security add-generic-password -U -s talos -a typesafe-api-key -w

3. Write `recipient.txt` in your personal part (`--guide personal-part`): who you are, in a few sentences.
4. Turn on the judging of new mail in `~/TalosData/enrich.json`, with a daily budget:

       {"enabled": true, "every_minutes": 15, "daily_budget": 0.5}

Another model can take Jev's place, but it needs an adapter written for it: Talos's `talos.jev` is the one
to copy.
