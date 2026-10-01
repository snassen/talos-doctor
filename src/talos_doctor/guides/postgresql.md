# PostgreSQL 18 on port 5433

Talos keeps its database in PostgreSQL 18 with three extensions (pgvector, pg_trgm, unaccent), on port
**5433**, so it never collides with another PostgreSQL on the default port 5432.

1. Install it with pgvector:

       brew install postgresql@18 pgvector

2. Set the port. Open the configuration file (on Apple silicon):

       open -e /opt/homebrew/var/postgresql@18/postgresql.conf

   Find the line `#port = 5432`, change it to `port = 5433` (without the `#`), and save.
3. Start it, and let it start with the Mac:

       brew services start postgresql@18

4. Check: `talos-doctor --only database`. "PostgreSQL answers" and "The pgvector extension" should say ok.
   "Talos's database" says ok after `uv run talos setup` in the Talos folder.

Talos connects over the local socket in /tmp as your macOS user; no password is involved. To use another
server or database, set TALOS_DSN (for example `host=/tmp port=5433 dbname=talos`).
