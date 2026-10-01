# iCloud and other IMAP accounts

Any IMAP account works the same way: a host, an address, and an app password (or the account's password,
where the provider has no app passwords) in the Keychain.

1. In accounts.json, give the account `"provider": "imap"`, its `address`, and in `settings` the `host`
   (iCloud: `imap.mail.me.com`) and the Keychain item's name in `secret` (for example `imap:you@icloud.com`).
2. iCloud: make an app-specific password at https://account.apple.com (Sign-In and Security, App-Specific
   Passwords).
3. Put it in the Keychain, pasting it at the prompt:

       security add-generic-password -U -s talos -a imap:you@icloud.com -w

4. Set `"enabled": true` for the account, and check: `talos-doctor --only accounts`.

To send from the account as well, Talos needs its SMTP server: `smtp_host` (and `smtp_port`) in its settings,
when Talos does not know it already.
