# Microsoft 365 (work mail, calendar and Teams)

Talos reads Microsoft 365 through Microsoft Graph, as an app registered in your organisation's Entra. The
app is a public client: it has no secret. You sign in with a device code, so your password never passes
through Talos. Registering the app and consenting to its permissions needs an administrator of the
organisation (it may be you).

## 1. Register the app

1. Open https://entra.microsoft.com, then **Identity → Applications → App registrations → New registration**.
2. Name: `Talos (local)`. Supported account types: **Accounts in this organizational directory only**.
   Leave Redirect URI empty. Press **Register**.
3. On the app's Overview, copy the **Application (client) ID** and the **Directory (tenant) ID**.
4. **Authentication → Advanced settings → Allow public client flows: Yes**. Save.

## 2. Give it its permissions

**API permissions → Add a permission → Microsoft Graph → Delegated permissions**, and add:

| Permission | What Talos does with it |
|---|---|
| User.Read | knows who signed in |
| Mail.Read | reads your mail (the sync) |
| Calendars.Read | reads your calendar |
| Chat.Read, ChannelMessage.Read.All | reads your Teams chats and channels |
| Team.ReadBasic.All, Channel.ReadBasic.All | lists the teams and channels you are in |
| Mail.Send | sends a mail you composed, after you confirmed it |
| Mail.ReadWrite | moves mail, only in changesets you commit |
| Calendars.ReadWrite | saves calendar entries you make in Talos |
| ChatMessage.Send, ChannelMessage.Send | posts in Teams when you press Enter in a conversation |

Then press **Grant admin consent for <your organisation>**. Leave out the ones you will not use (the last
four write); Talos asks for each write permission only when that feature is used.

## 3. Tell Talos

In accounts.json, the Microsoft 365 account (`"provider": "graph"`) gets the two IDs in its settings:

    "settings": {"tenant_id": "<Directory (tenant) ID>", "client_id": "<Application (client) ID>"}

A Teams account (`"provider": "teams"`) gets the same two IDs and `"token_account": "<the graph account's id>"`.

## 4. Sign in

    uv run talos auth graph <the account's id>

It prints a code. Open https://microsoft.com/devicelogin, enter the code, and sign in. The token is kept in the
Keychain (`graph-token-cache:<id>`) and renewed by itself.

Check: `talos-doctor --only accounts`. Then: `uv run talos sync <the account's id> --limit 500`.
