"""The checks, in the order a new installation needs them: the machine, the code, the database, the personal
part, the accounts, the model, the background services, and the extras.

Each check is a function that takes the Context and returns one Result (or several, one per account). A
Result says what was found (ok, warn, fail, skip or info), why it matters, and the next step: the exact
command to run, or the guide to read (`talos-doctor --guide NAME`). A check that needs another one which did
not pass is skipped with a pointer to it, so the first thing to fix is always at the top.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from talos_doctor.probe import Probe, load_json

OK, WARN, FAIL, SKIP, INFO = "ok", "warn", "fail", "skip", "info"
PHASES = ("machine", "code", "database", "personal", "accounts", "model", "services", "extras")
ZERO_ID = "00000000-0000-0000-0000-000000000000"
REPO_GUESSES = ("talos", "Github repos/talos", "GitHub/talos", "src/talos", "code/talos", "dev/talos", "Projects/talos")


@dataclass
class Result:
    id: str
    phase: str
    title: str
    status: str
    detail: str = ""
    fix: str = ""           # a command to run, or a short instruction
    guide: str = ""         # a guide's name: talos-doctor --guide NAME

    def as_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v != ""}


@dataclass
class Context:
    """What the checks share: where Talos's parts are, found once."""
    probe: Probe
    repo: Path | None = None
    home: Path | None = None
    config: Path | None = None
    dsn: dict = field(default_factory=dict)
    results: dict = field(default_factory=dict)

    @classmethod
    def find(cls, probe: Probe, *, repo: str | None = None, home: str | None = None) -> "Context":
        env, h = probe.env, probe.home()
        ctx = cls(probe)
        ctx.home = Path(home or env.get("TALOS_HOME") or h / "TalosData").expanduser()
        ctx.config = Path(env["TALOS_CONFIG"]).expanduser() if env.get("TALOS_CONFIG") else ctx.home / "config"
        ctx.dsn = parse_dsn(env.get("TALOS_DSN") or "host=/tmp port=5433 dbname=talos")
        candidates = [Path(repo).expanduser()] if repo else (
            ([Path(env["TALOS_REPO"]).expanduser()] if env.get("TALOS_REPO") else [])
            + [Path(env.get("PWD") or ".")] + [h / g for g in REPO_GUESSES])
        ctx.repo = next((c for c in candidates if probe.exists(c / "src" / "talos" / "__init__.py")), None)
        return ctx

    def personal(self, name: str):
        """A personal file, parsed (JSON) or as text; None when absent, ValueError when not valid JSON."""
        text = self.probe.read(self.config / name)
        return load_json(text) if name.endswith(".json") else text

    def example(self, name: str):
        return load_json(self.probe.read(self.repo / "rules" / name)) if self.repo else None

    def owner(self) -> dict:
        o = self.personal("owner.json")
        return {"id": "owner", "service_prefix": "local.talos", **(o if isinstance(o, dict) else {})}

    def accounts(self) -> list[dict]:
        a = self.personal("accounts.json")
        return a.get("accounts", []) if isinstance(a, dict) else []


def parse_dsn(dsn: str) -> dict:
    return dict(re.findall(r"(\w+)=(\S+)", dsn))


CHECKS: list = []


def check(id: str, phase: str, needs: tuple[str, ...] = ()):
    def wrap(fn):
        CHECKS.append((id, phase, needs, fn))
        return fn
    return wrap


def run_all(ctx: Context, only: set[str] | None = None) -> list[Result]:
    out = []
    for id, phase, needs, fn in CHECKS:   # every check runs (a phase's checks need earlier ones); only shows a part
        blocked = [n for n in needs if ctx.results.get(n) not in (OK, WARN, INFO)]
        if blocked:
            r = Result(id, phase, fn.__doc__.strip().splitlines()[0], SKIP, f"needs {', '.join(blocked)} first")
            ctx.results[id] = SKIP
            out.append(r)
            continue
        got = fn(ctx)
        got = got if isinstance(got, list) else [got]
        worst = FAIL if any(r.status == FAIL for r in got) else (got[0].status if got else SKIP)
        ctx.results[id] = worst
        out.extend(got)
    return [r for r in out if not only or r.phase in only]


# ---------------------------------------------------------------- machine

@check("macos", "machine")
def _macos(ctx):
    """A Mac"""
    if ctx.probe.system() != "Darwin":
        return Result("macos", "machine", "A Mac", FAIL, f"this is {ctx.probe.system()}",
                      "Talos runs on macOS only: it keeps secrets in the Keychain and runs as launchd services.")
    code, out = ctx.probe.run(["sw_vers", "-productVersion"])
    return Result("macos", "machine", "A Mac", OK, f"macOS {out.strip()}" if code == 0 else "macOS")


@check("homebrew", "machine", ("macos",))
def _brew(ctx):
    """Homebrew"""
    if ctx.probe.which("brew"):
        return Result("homebrew", "machine", "Homebrew", OK)
    return Result("homebrew", "machine", "Homebrew", FAIL, "not installed",
                  "Install it from https://brew.sh, then open a new Terminal window.")


@check("uv", "machine")
def _uv(ctx):
    """uv, the Python tool Talos runs with"""
    code, out = ctx.probe.run(["uv", "--version"])
    if code == 0:
        return Result("uv", "machine", "uv", OK, out.strip())
    return Result("uv", "machine", "uv", FAIL, "not installed", "brew install uv")


@check("disk", "machine")
def _disk(ctx):
    """Free disk space"""
    free = ctx.probe.free_gb(ctx.probe.home())
    if free is None:
        return Result("disk", "machine", "Free disk space", INFO, "could not tell")
    detail = f"{free:.0f} GB free"
    if free < 20:
        return Result("disk", "machine", "Free disk space", WARN, detail,
                      "The vault holds every original: about as much as all your mailboxes together. Free some room.")
    return Result("disk", "machine", "Free disk space", OK, detail)


# ---------------------------------------------------------------- code

@check("repo", "code")
def _repo(ctx):
    """The Talos code"""
    if not ctx.repo:
        return Result("repo", "code", "The Talos code", FAIL, "not found (looked in the usual places)",
                      "git clone <the Talos repository's URL> talos, then run the doctor there or with --repo PATH",
                      "install")
    init = ctx.probe.read(ctx.repo / "src" / "talos" / "__init__.py") or ""
    m = re.search(r'__version__ = "([^"]+)"', init)
    return Result("repo", "code", "The Talos code", OK, f"{ctx.repo} (version {m.group(1) if m else '?'})")


@check("venv", "code", ("repo", "uv"))
def _venv(ctx):
    """Talos installed in its folder"""
    if ctx.probe.exists(ctx.repo / ".venv" / "bin" / "talos"):
        return Result("venv", "code", "Talos installed in its folder", OK)
    return Result("venv", "code", "Talos installed in its folder", FAIL, "no .venv yet", f"cd \"{ctx.repo}\" && uv sync")


# ---------------------------------------------------------------- database

@check("postgresql", "database", ("homebrew",))
def _pg(ctx):
    """PostgreSQL 18"""
    if ctx.probe.which("psql") and ctx.probe.which("pg_isready"):
        return Result("postgresql", "database", "PostgreSQL 18", OK)
    return Result("postgresql", "database", "PostgreSQL 18", FAIL, "not installed",
                  "brew install postgresql@18 pgvector", "postgresql")


@check("postgresql-running", "database", ("postgresql",))
def _pg_up(ctx):
    """PostgreSQL answers"""
    d = ctx.dsn
    code, out = ctx.probe.run(["pg_isready", "-h", d.get("host", "/tmp"), "-p", d.get("port", "5433")])
    where = f"{d.get('host', '/tmp')} port {d.get('port', '5433')}"
    if code == 0:
        return Result("postgresql-running", "database", "PostgreSQL answers", OK, where)
    return Result("postgresql-running", "database", "PostgreSQL answers", FAIL, f"nothing answers on {where}",
                  "brew services start postgresql@18 (and set port = 5433 in its postgresql.conf)", "postgresql")


@check("pgvector", "database", ("postgresql-running",))
def _pgvector(ctx):
    """The pgvector extension"""
    ok, rows = ctx.probe.sql({**ctx.dsn, "dbname": "postgres"},
                             "select count(*) from pg_available_extensions where name in ('vector', 'pg_trgm', 'unaccent')")
    if not ok:
        return Result("pgvector", "database", "The pgvector extension", FAIL, str(rows)[:200], "", "postgresql")
    if rows and rows[0][0] == "3":
        return Result("pgvector", "database", "The pgvector extension", OK, "vector, pg_trgm and unaccent available")
    return Result("pgvector", "database", "The pgvector extension", FAIL, "not available to this server",
                  "brew install pgvector, then brew services restart postgresql@18", "postgresql")


@check("database", "database", ("pgvector", "repo"))
def _db(ctx):
    """Talos's database, migrated"""
    ok, rows = ctx.probe.sql(ctx.dsn, "select count(*) from schema_migration")
    name = ctx.dsn.get("dbname", "talos")
    if not ok:
        return Result("database", "database", "Talos's database, migrated", FAIL, f"{name}: not set up yet",
                      "uv run talos setup   (in the Talos folder)", "postgresql")
    applied = int(rows[0][0]) if rows else 0
    known = len([n for n in ctx.probe.listdir(ctx.repo / "src" / "talos" / "sql") if n.endswith(".sql")])
    if applied < known:
        return Result("database", "database", "Talos's database, migrated", WARN,
                      f"{name}: {applied} of {known} migrations applied", "uv run talos setup")
    return Result("database", "database", "Talos's database, migrated", OK, f"{name}: {applied} migrations")


# ---------------------------------------------------------------- personal part

@check("data-folder", "personal")
def _home(ctx):
    """The data folder"""
    if ctx.probe.exists(ctx.home):
        return Result("data-folder", "personal", "The data folder", OK, str(ctx.home))
    return Result("data-folder", "personal", "The data folder", FAIL, f"{ctx.home} does not exist",
                  "uv run talos setup   (it makes the folder)", "personal-part")


@check("personal-part", "personal", ("data-folder",))
def _config(ctx):
    """Your personal part"""
    if not ctx.probe.exists(ctx.config):
        return Result("personal-part", "personal", "Your personal part", FAIL, f"{ctx.config} does not exist",
                      "uv run talos config init", "personal-part")
    bad = [n for n in ("owner.json", "accounts.json") if ctx.personal(n) is ValueError]
    if bad:
        return Result("personal-part", "personal", "Your personal part", FAIL, f"not valid JSON: {', '.join(bad)}",
                      "Fix the file (a missing comma or quote is the usual cause).", "personal-part")
    missing = [n for n in ("owner.json", "accounts.json", "recipient.txt") if not ctx.probe.exists(ctx.config / n)]
    if missing:
        return Result("personal-part", "personal", "Your personal part", WARN, f"missing: {', '.join(missing)}",
                      "uv run talos config init   (adds what is missing, never overwrites)", "personal-part")
    return Result("personal-part", "personal", "Your personal part", OK, str(ctx.config))


@check("personal-filled", "personal", ("personal-part",))
def _filled(ctx):
    """Your personal part is yours, not the examples"""
    still = []
    if ctx.owner().get("id") == "owner":
        still.append("owner.json (id is still 'owner')")
    ex = ctx.example("accounts.example.json")
    if ex and ctx.personal("accounts.json") == ex:
        still.append("accounts.json (the example's accounts)")
    if still:
        return Result("personal-filled", "personal", "Your personal part is yours", WARN, "still the examples: " + "; ".join(still),
                      f"Edit them in {ctx.config}.", "personal-part")
    return Result("personal-filled", "personal", "Your personal part is yours", OK, f"owner id '{ctx.owner()['id']}'")


# ---------------------------------------------------------------- accounts

@check("accounts", "accounts", ("personal-part",))
def _accounts(ctx):
    """Each account can sign in"""
    out = []
    by_id = {a.get("id"): a for a in ctx.accounts()}
    # accounts.json only seeds new accounts: once the database has them, its "enabled" is the truth
    enabled = None
    if ctx.results.get("database") in (OK, WARN):
        ok, rows = ctx.probe.sql(ctx.dsn, "select id, enabled from account")
        if ok:
            enabled = {r[0]: r[1] == "t" for r in rows if len(r) == 2}
    for a in ctx.accounts():
        aid, prov, s = a.get("id", "?"), a.get("provider"), a.get("settings") or {}
        title = f"Account {aid} ({prov})"
        on = enabled.get(aid, a.get("enabled", True)) if enabled is not None else a.get("enabled", True)
        if not on:
            out.append(Result(f"account:{aid}", "accounts", title, INFO, "not enabled"))
            continue
        if prov in ("gmail", "imap"):
            item = s.get("secret")
            guide = "gmail" if prov == "gmail" else "imap"
            if not item:
                out.append(Result(f"account:{aid}", "accounts", title, FAIL, "names no Keychain item (settings.secret)",
                                  "Add \"secret\": \"<provider>:<address>\" to its settings in accounts.json.", guide))
            elif ctx.probe.keychain_has(item):
                out.append(Result(f"account:{aid}", "accounts", title, OK, f"Keychain item {item}"))
            else:
                out.append(Result(f"account:{aid}", "accounts", title, FAIL, f"Keychain item {item} is missing",
                                  f"security add-generic-password -U -s talos -a {item} -w   (paste the app password at the prompt)", guide))
        elif prov == "graph":
            if not s.get("tenant_id") or not s.get("client_id") or ZERO_ID in (s.get("tenant_id"), s.get("client_id")):
                out.append(Result(f"account:{aid}", "accounts", title, FAIL, "tenant_id and client_id are not set",
                                  "Register the app in Entra and put its IDs in accounts.json.", "microsoft-365"))
            elif ctx.probe.keychain_has(f"graph-token-cache:{aid}"):
                out.append(Result(f"account:{aid}", "accounts", title, OK, "signed in"))
            else:
                out.append(Result(f"account:{aid}", "accounts", title, FAIL, "not signed in yet",
                                  f"uv run talos auth graph {aid}", "microsoft-365"))
        elif prov == "teams":
            via = s.get("token_account")
            if not via or via not in by_id:
                out.append(Result(f"account:{aid}", "accounts", title, FAIL, "token_account names no Microsoft 365 account",
                                  "Set settings.token_account to the id of your Microsoft 365 account.", "microsoft-365"))
            else:
                out.append(Result(f"account:{aid}", "accounts", title, OK, f"signs in through {via}"))
        else:
            out.append(Result(f"account:{aid}", "accounts", title, INFO, "nothing to check"))
    return out or [Result("accounts", "accounts", "Each account can sign in", WARN, "accounts.json lists no account",
                          "Add your accounts to accounts.json.", "personal-part")]


# ---------------------------------------------------------------- model

@check("jev", "model", ("personal-part",))
def _jev(ctx):
    """Jev, the model that judges new mail (optional)"""
    if ctx.probe.keychain_has("typesafe-api-key"):
        return Result("jev", "model", "Jev (optional)", OK, "API key in the Keychain")
    return Result("jev", "model", "Jev (optional)", INFO,
                  "no API key: rules and your own decisions still work; new mail is not judged by a model",
                  "", "jev")


# ---------------------------------------------------------------- services

@check("services", "services", ("venv", "database"))
def _services(ctx):
    """The background services"""
    prefix = ctx.owner().get("service_prefix", "local.talos")
    code, out = ctx.probe.run(["launchctl", "list"])
    loaded = {line.split("\t")[-1] for line in out.splitlines()} if code == 0 else set()
    res = []
    for name, what, flag in (("sync", "mail every 5 minutes", ""), ("web", "Talos Web", " --web")):
        label = f"{prefix}.{name}"
        if label in loaded:
            res.append(Result(f"service:{name}", "services", f"Service {label}", OK, what))
        else:
            res.append(Result(f"service:{name}", "services", f"Service {label}", WARN, f"not loaded ({what})",
                              f"uv run talos launchd{flag}   (prints the job; save it in ~/Library/LaunchAgents and load it)",
                              "services"))
    return res


@check("web", "services", ("venv",))
def _web(ctx):
    """Talos Web answers"""
    code = ctx.probe.http_status("http://127.0.0.1:7420/auth/status")
    if code == 200:
        return Result("web", "services", "Talos Web answers", OK, "http://127.0.0.1:7420")
    return Result("web", "services", "Talos Web answers", WARN, "nothing answers on 127.0.0.1:7420",
                  "uv run talos serve   (or load the web service)", "services")


@check("door", "services", ("web",))
def _door(ctx):
    """Talos Web's sign-in is set up"""
    if ctx.probe.keychain_has("web:password") and ctx.probe.keychain_has("web:totp"):
        return Result("door", "services", "Talos Web's sign-in", OK, "password and authenticator set")
    return Result("door", "services", "Talos Web's sign-in", FAIL, "not set up: every page is closed until it is",
                  "uv run talos web setup   (in your own Terminal: it asks for your password)", "services")


# ---------------------------------------------------------------- extras

@check("tailscale", "extras")
def _tailscale(ctx):
    """Tailscale, to reach Talos from your phone (optional)"""
    code, _ = ctx.probe.run(["tailscale", "status"])
    if code == 0:
        return Result("tailscale", "extras", "Tailscale (optional)", OK, "running")
    return Result("tailscale", "extras", "Tailscale (optional)", INFO, "not running: Talos Web is reachable on this Mac only",
                  "", "tailscale")


@check("backup", "extras", ("data-folder",))
def _backup(ctx):
    """The nightly backup of your own work"""
    days = [d for d in ctx.probe.listdir(ctx.home / "backups") if re.fullmatch(r"\d{4}-\d{2}-\d{2}", d)]
    if days:
        return Result("backup", "extras", "The nightly backup", OK, f"latest {days[-1]} ({len(days)} kept)")
    return Result("backup", "extras", "The nightly backup", INFO, "none yet: the first full sync after 02:00 makes one",
                  "uv run talos backup   (makes one now)")


def as_json(results: list[Result]) -> str:
    return json.dumps([r.as_dict() for r in results], indent=2, ensure_ascii=False)
