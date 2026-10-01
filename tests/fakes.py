"""A made-up Mac for the tests: files, commands, Keychain items, database answers and Talos Web, all in memory."""

from __future__ import annotations

import json
from pathlib import Path

from talos_doctor.probe import ALLOWED, NotAllowed, Probe

HOME = Path("/Users/alex")
REPO = HOME / "talos"


class FakeMac(Probe):
    def __init__(self, **kw):
        super().__init__(env={"HOME": str(HOME), "PATH": "/usr/bin", "PWD": str(HOME)})
        self.os = kw.get("os", "Darwin")
        self.tools = set(kw.get("tools", {"brew", "uv", "psql", "pg_isready", "security", "launchctl", "sw_vers", "tailscale"}))
        self.files: dict[str, str] = {}
        self.dirs: dict[str, list[str]] = {}
        self.keychain: set[str] = set(kw.get("keychain", ()))
        self.pg_up = kw.get("pg_up", True)
        self.extensions = kw.get("extensions", 3)
        self.migrations = kw.get("migrations", 32)      # None: no database yet
        self.loaded: set[str] = set(kw.get("loaded", ()))
        self.web = kw.get("web", 200)
        self.free = kw.get("free", 200.0)
        self.ran: list[list[str]] = []
        self.db_enabled: dict[str, bool] = dict(kw.get("db_enabled", {}))

    # files
    def put(self, path, content) -> "FakeMac":
        self.files[str(path)] = content if isinstance(content, str) else json.dumps(content)
        return self

    def system(self):
        return self.os

    def which(self, name):
        return f"/opt/homebrew/bin/{name}" if name in self.tools else None

    def exists(self, path):
        p = str(path)
        return p in self.files or p in self.dirs or any(f.startswith(p.rstrip("/") + "/") for f in self.files)

    def read(self, path):
        return self.files.get(str(path))

    def listdir(self, path):
        p = str(path).rstrip("/") + "/"
        names = {f[len(p):].split("/")[0] for f in self.files if f.startswith(p)}
        return sorted(names | set(self.dirs.get(str(path), [])))

    def free_gb(self, path):
        return self.free

    def run(self, args, timeout=10, env=None):
        tool = Path(args[0]).name
        if tool not in ALLOWED or (ALLOWED[tool] is not None and args[1] not in ALLOWED[tool]):
            raise NotAllowed(" ".join(args[:2]))
        self.ran.append(args)
        if tool not in self.tools:
            return -1, ""
        if tool == "security":
            return (0, "") if args[args.index("-a") + 1] in self.keychain else (44, "not found")
        if tool == "pg_isready":
            return (0, "accepting") if self.pg_up else (2, "no response")
        if tool == "launchctl":
            return 0, "\n".join(f"123\t0\t{label}" for label in sorted(self.loaded))
        if tool == "psql":
            assert env and "default_transaction_read_only=on" in env.get("PGOPTIONS", "")
            q = args[args.index("-c") + 1]
            if not self.pg_up:
                return 2, "could not connect"
            if "pg_available_extensions" in q:
                return 0, f"{self.extensions}\n"
            if "from account" in q:
                return 0, "".join(f"{k}\t{'t' if v else 'f'}\n" for k, v in self.db_enabled.items())
            if "schema_migration" in q:
                return (0, f"{self.migrations}\n") if self.migrations is not None else (1, 'relation "schema_migration" does not exist')
        if tool == "uv":
            return 0, "uv 0.9.0"
        if tool == "sw_vers":
            return 0, "26.0"
        if tool == "tailscale":
            return 0, ""
        return 0, ""

    def http_status(self, url, timeout=5):
        assert url.startswith("http://127.0.0.1:")
        return self.web


def ready_mac(**kw) -> FakeMac:
    """A Mac where everything is set up, to break one thing at a time."""
    mac = FakeMac(keychain={"gmail:alex@gmail.com", "graph-token-cache:work", "typesafe-api-key", "web:password", "web:totp"},
                  loaded={"com.alex.talos.sync", "com.alex.talos.web"}, **kw)
    mac.put(REPO / "src/talos/__init__.py", '__version__ = "0.14.0"\n').put(REPO / ".venv/bin/talos", "")
    for i in range(1, 33):
        mac.put(REPO / f"src/talos/sql/{i:03}_x.sql", "")
    mac.put(REPO / "rules/accounts.example.json", {"accounts": [{"id": "gmail"}], "my_addresses": {}})
    cfg = HOME / "TalosData/config"
    mac.put(cfg / "owner.json", {"id": "alex", "name": "Alex", "service_prefix": "com.alex.talos"})
    mac.put(cfg / "recipient.txt", "Alex, who runs IT at a small company.")
    mac.put(cfg / "accounts.json", {"accounts": [
        {"id": "gmail", "provider": "gmail", "enabled": True, "settings": {"secret": "gmail:alex@gmail.com"}},
        {"id": "work", "provider": "graph", "enabled": True, "settings": {"tenant_id": "t-1", "client_id": "c-1"}},
        {"id": "teams", "provider": "teams", "enabled": True, "settings": {"token_account": "work"}},
        {"id": "club", "provider": "imap", "enabled": False, "settings": {}},
    ], "my_addresses": {}})
    mac.put(HOME / "TalosData/backups/2026-10-01/manifest.json", "{}")
    return mac
