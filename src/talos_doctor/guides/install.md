# Installing Talos, from nothing to a first sync

Run `talos-doctor` after each step: the step you just did should say ok, and the next one is at the top
of "Next steps".

1. **Homebrew and uv.** Install Homebrew from https://brew.sh, then `brew install uv`.
2. **PostgreSQL 18**, on port 5433: `talos-doctor --guide postgresql`.
3. **The code.** Clone the Talos repository and install it:

       git clone <the Talos repository's URL> talos
       cd talos
       uv sync

4. **The database.** In the Talos folder: `uv run talos setup`. It makes the data folder (~/TalosData),
   applies the migrations and loads the value lists.
5. **Your personal part**: `talos-doctor --guide personal-part`.
6. **Your accounts**, one at a time: `--guide gmail`, `--guide microsoft-365`, `--guide imap`.
7. **A first read-only slice**, then the rest:

       uv run talos sync gmail --limit 500
       uv run talos sync

8. **Talos Web**: `talos-doctor --guide services`.
9. **Optional**: Jev to judge new mail (`--guide jev`), Tailscale to reach Talos from your phone
   (`--guide tailscale`).
