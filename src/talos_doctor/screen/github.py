"""A pull request fetched as text, never checked out.

A checkout can itself run code (git hooks, .gitattributes filters, submodules, LFS), so the screen only reads
what GitHub's API returns: the title, the description, the commit messages and each file's diff. GET requests
to api.github.com only. A token is optional (GITHUB_TOKEN or GH_TOKEN): public repositories need none, and it
only raises GitHub's rate limit.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from talos_doctor import __version__
from talos_doctor.screen.engine import Piece, parse_diff, text_piece

API = "https://api.github.com"
MAX_PAGES = 30          # 3,000 files, GitHub's own limit for a pull request's file list


class FetchError(RuntimeError):
    pass


def _get(path: str, env: dict | None = None):
    env = os.environ if env is None else env
    if not path.startswith("/repos/"):
        raise FetchError("the screen reads only repositories' pull requests")
    req = urllib.request.Request(API + path, headers={
        "Accept": "application/vnd.github+json", "User-Agent": f"talos-doctor/{__version__}",
        "X-GitHub-Api-Version": "2022-11-28"})
    token = env.get("GITHUB_TOKEN") or env.get("GH_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise FetchError(f"GitHub answered {e.code} for {path}") from None
    except OSError as e:
        raise FetchError(f"could not reach GitHub: {e}") from None


def pull_request(repo: str, number: int, env: dict | None = None) -> tuple[dict, list[Piece]]:
    """({title, author, url, base, head, files, commits}, pieces) for owner/name and a PR number."""
    if repo.count("/") != 1 or not all(repo.split("/")):
        raise FetchError("the repository is owner/name, for example octocat/hello-world")
    base = f"/repos/{repo}/pulls/{int(number)}"
    pr = _get(base, env)
    files = []
    for page in range(1, MAX_PAGES + 1):
        got = _get(f"{base}/files?per_page=100&page={page}", env)
        files += got
        if len(got) < 100:
            break
    commits = _get(f"{base}/commits?per_page=100", env)
    pieces = [text_piece("title", "pull request title", pr.get("title") or ""),
              text_piece("body", "pull request description", pr.get("body") or "")]
    for c in commits:
        sha = (c.get("sha") or "")[:7]
        pieces.append(text_piece("commit", f"commit {sha}", (c.get("commit") or {}).get("message") or ""))
    for f in files:
        name, status = f.get("filename", "?"), f.get("status", "modified")
        patch = f.get("patch")
        if patch is None:
            pieces.append(Piece("file", name, [], "unscreened", f.get("previous_filename", "")))
            continue
        pc = parse_diff(f"diff --git a/{name} b/{name}\n--- a/{name}\n+++ b/{name}\n{patch}\n")[0]
        pc.status, pc.old_path = status, f.get("previous_filename", "")
        pieces.append(pc)
    meta = {"title_chars": len(pr.get("title") or ""), "author": (pr.get("user") or {}).get("login"),
            "url": pr.get("html_url"), "base": (pr.get("base") or {}).get("ref"), "head": (pr.get("head") or {}).get("label"),
            "files": len(files), "commits": len(commits), "state": pr.get("state")}
    return meta, pieces
