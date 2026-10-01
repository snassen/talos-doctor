# Gmail

Talos reads Gmail over IMAP with an app password: Google never gives Talos your real password, and you can
withdraw the app password at any time.

1. Turn on two-step verification for the Google account, if it is not on: https://myaccount.google.com/security
2. Make an app password: https://myaccount.google.com/apppasswords. Name it "Talos" and copy the 16
   letters it shows.
3. Put it in the Keychain under the name your account's `settings.secret` says in accounts.json (for
   example `gmail:you@gmail.com`). Paste the 16 letters at the prompt; they are not shown:

       security add-generic-password -U -s talos -a gmail:you@gmail.com -w

4. Check: `talos-doctor --only accounts`. Then a first slice: `uv run talos sync gmail --limit 500`.

The Google calendar takes no app password; it needs a sign-in of its own (`uv run talos auth google`, see
Talos's docs/calendar.md).
