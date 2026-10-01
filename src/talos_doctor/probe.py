"""Everything the doctor learns about the machine goes through a Probe, so it can promise two things.

**It reads only.** The commands it may run are listed in ALLOWED, each with the only subcommands it may
use, and none of them changes anything. Files are opened for reading. The database is asked read-only
questions in a read-only transaction. The one web request is a GET to Talos Web's own status page on
this Mac.

**It never reads a secret.** A Keychain item is looked up by name (`security find-generic-password`
without -w or -g), which says whether it exists without touching its contents, and without the
dialog macOS shows when a secret is read.

Tests replace the Probe with a fake one (tests/fakes.py), so no check depends on the machine it runs on.
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

# The commands the doctor may run, and the first argument each must have (None: any, for a read-only
# tool). Anything else is refused before it runs.
ALLOWED = {
    "security": {"find-generic-password"},
    "launchctl": {"list"},
    "pg_isready": None,
    "psql": None,          # only with PGOPTIONS forcing a read-only transaction (see sql())
    "brew": {"--prefix"},
    "uv": {"--version"},
    "tailscale": {"status"},
    "sw_vers": {"-productVersion"},
}
TAILSCALE_APP = "/Applications/Tailscale.app/Contents/MacOS/Tailscale"
PG_BIN = ("/opt/homebrew/opt/postgresql@18/bin", "/usr/local/opt/postgresql@18/bin")


class NotAllowed(RuntimeError):
    pass


class Probe:
    """The real machine."""

    def __init__(self, env: dict | None = None):
        self.env = dict(os.environ if env is None else env)

    # ---- the system
    def system(self) -> str:
        return platform.system()

    def home(self) -> Path:
        return Path(self.env.get("HOME") or Path.home())

    def which(self, name: str) -> str | None:
        if name in ("psql", "pg_isready"):
            for d in PG_BIN:
                if (Path(d) / name).exists():
                    return str(Path(d) / name)
        if name == "tailscale" and Path(TAILSCALE_APP).exists() and not shutil.which(name, path=self.env.get("PATH")):
            return TAILSCALE_APP      # the Mac app's command line, not on the PATH by default
        return shutil.which(name, path=self.env.get("PATH"))

    def run(self, args: list[str], timeout: float = 10, env: dict | None = None) -> tuple[int, str]:
        """(exit code, output) of an allowed command; -1 when it is not installed or timed out."""
        tool = Path(args[0]).name
        if tool not in ALLOWED or (ALLOWED[tool] is not None and (len(args) < 2 or args[1] not in ALLOWED[tool])):
            raise NotAllowed(f"the doctor does not run {' '.join(args[:2])}")
        exe = self.which(args[0]) if "/" not in args[0] else args[0]
        if not exe:
            return -1, ""
        try:
            r = subprocess.run([exe, *args[1:]], capture_output=True, text=True, timeout=timeout,
                               env={**self.env, **(env or {})}, stdin=subprocess.DEVNULL)
        except (OSError, subprocess.TimeoutExpired):
            return -1, ""
        return r.returncode, (r.stdout or "") + (r.stderr or "")

    # ---- files
    def exists(self, path: Path) -> bool:
        return Path(path).exists()

    def read(self, path: Path) -> str | None:
        try:
            return Path(path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None

    def listdir(self, path: Path) -> list[str]:
        try:
            return sorted(p.name for p in Path(path).iterdir())
        except OSError:
            return []

    def free_gb(self, path: Path) -> float | None:
        try:
            return shutil.disk_usage(path).free / 1e9
        except OSError:
            return None

    # ---- services
    def keychain_has(self, item: str, service: str = "talos") -> bool:
        """Whether the item exists. Never reads its secret (no -w, no -g), so macOS never asks."""
        code, _ = self.run(["security", "find-generic-password", "-s", service, "-a", item])
        return code == 0

    def sql(self, dsn: dict, query: str) -> tuple[bool, list[list[str]] | str]:
        """(ok, rows) of a read-only query, or (False, the error) when it could not run."""
        args = ["psql", "-X", "-At", "-F", "\t", "-v", "ON_ERROR_STOP=1", "-c", query]
        for key, flag in (("host", "-h"), ("port", "-p"), ("user", "-U"), ("dbname", "-d")):
            if dsn.get(key):
                args += [flag, dsn[key]]
        code, out = self.run(args, env={"PGOPTIONS": "-c default_transaction_read_only=on", "PGCONNECT_TIMEOUT": "5"})
        if code != 0:
            return False, out.strip() or "psql is not installed"
        return True, [line.split("\t") for line in out.splitlines() if line]

    def http_status(self, url: str, timeout: float = 5) -> int | None:
        if not url.startswith("http://127.0.0.1:"):
            raise NotAllowed("the doctor only asks Talos Web on this Mac")
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"Host": url.split("/")[2]}),
                                        timeout=timeout) as r:
                return r.status
        except urllib.error.HTTPError as e:
            return e.code
        except OSError:
            return None


def load_json(text: str | None):
    if text is None:
        return None
    try:
        return json.loads(text)
    except ValueError:
        return ValueError
