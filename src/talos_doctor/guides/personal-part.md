# Your personal part

Everything that describes you lives outside the Talos code, in your personal part: by default
`~/TalosData/config` (TALOS_CONFIG names another folder, for example a private git repository of your own).
Nothing in it is secret: passwords and tokens go in the Keychain.

1. Make it from the examples (it never overwrites a file):

       uv run talos config init

2. Fill in the files:
   - `owner.json`: `id` is the name your own decisions are stored under (choose it once, short and
     lowercase, and keep it); `name` is how a record names you when the model reads mail you sent;
     `service_prefix` names your background services (for example `com.yourname.talos`).
   - `accounts.json`: one entry per mailbox or chat source, and every address that is you in
     `my_addresses`. Each account names the Keychain item its password is in (`settings.secret`). Optional
     per account: `jev_label`, `sphere` (work or personal) and `ui` (its name, letter and colour).
   - `recipient.txt`: who you are, in a few sentences, for the model that judges your mail. Every word is
     sent with every question, so keep it short.
   - Optional: `questions.json` (your own wording of the model's questions), `taxonomy.json` (your own value
     lists), `structure.json` (where mail should go), `rules/`, `argus-services.json` (your other services
     for the monitor), `AGENTS.md` (your rules for coding agents).
3. Check: `talos-doctor --only personal`. "Your personal part is yours" says ok once owner.json and
   accounts.json are no longer the examples.

`uv run talos where` shows where every part of Talos is on your Mac, and why.
