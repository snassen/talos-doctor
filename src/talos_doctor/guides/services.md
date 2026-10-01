# The background services and Talos Web

Talos runs as launchd services under your user: the sync every five minutes, and Talos Web kept alive.
Their names start with the `service_prefix` in your owner.json.

1. Set up Talos Web's sign-in first, in your own Terminal (it asks for a password and shows a QR code for
   your authenticator app; every page is closed until this is done):

       uv run talos web setup

2. Print each service, save it under ~/Library/LaunchAgents, and load it. The printed text ends with the
   exact file name and command:

       uv run talos launchd           # the sync, every five minutes
       uv run talos launchd --web     # Talos Web

3. Open http://127.0.0.1:7420 and sign in.

Check: `talos-doctor --only services`. If you set TALOS_HOME, TALOS_DSN or TALOS_CONFIG, run `talos launchd`
with them set: the printed job carries them, since launchd gives a service none of your shell's settings.
