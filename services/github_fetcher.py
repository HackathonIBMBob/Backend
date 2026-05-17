import io
import os
import re
import zipfile
from typing import List

import requests
from fastapi import HTTPException

from services.repo_parser import scan_files

_GITHUB_URL_RE = re.compile(
    r"https?://(?:www\.)?github\.com/(?P<owner>[^/]+)/(?P<repo>[^/\s]+?)(?:\.git)?/?$"
)

_DOWNLOAD_TIMEOUT = 60


def _parse_owner_repo(github_url: str):
    m = _GITHUB_URL_RE.match(github_url.strip())
    if not m:
        raise HTTPException(status_code=400, detail=f"Invalid GitHub URL: {github_url}")
    return m.group("owner"), m.group("repo")


def _download_zip(owner: str, repo: str) -> bytes:
    """Try main then master branch; return raw ZIP bytes."""
    for branch in ("main", "master"):
        url = f"https://github.com/{owner}/{repo}/archive/refs/heads/{branch}.zip"
        try:
            resp = requests.get(url, timeout=_DOWNLOAD_TIMEOUT, allow_redirects=True)
        except requests.RequestException as exc:
            raise HTTPException(status_code=500, detail=f"Network error downloading repo: {exc}") from exc

        if resp.status_code == 200:
            return resp.content
        if resp.status_code in (401, 403):
            raise HTTPException(
                status_code=401,
                detail="Repository is private. Only public GitHub repositories are supported.",
            )

    # Both branches returned 404
    raise HTTPException(status_code=404, detail="Repository not found. Check the URL and make sure it is public.")


def _extract_zip(zip_bytes: bytes, dest: str) -> None:
    """Extract ZIP into dest, stripping the top-level {repo}-{branch}/ folder GitHub adds."""
    os.makedirs(dest, exist_ok=True)
    dest_abs = os.path.abspath(dest)

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        members = zf.infolist()
        # GitHub always adds a single top-level directory; detect and strip it
        top_dirs = {m.filename.split("/")[0] for m in members if "/" in m.filename}
        strip_prefix = (top_dirs.pop() + "/") if len(top_dirs) == 1 else ""

        for member in members:
            rel = member.filename[len(strip_prefix):] if strip_prefix else member.filename
            if not rel:
                continue

            target = os.path.abspath(os.path.join(dest, rel))
            if not target.startswith(dest_abs + os.sep) and target != dest_abs:
                raise HTTPException(status_code=400, detail=f"Unsafe path in ZIP: {member.filename}")

            if member.is_dir():
                os.makedirs(target, exist_ok=True)
            else:
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with zf.open(member) as src, open(target, "wb") as out:
                    out.write(src.read())


def clone_repo(github_url: str, dest: str) -> List[dict]:
    owner, repo = _parse_owner_repo(github_url)
    zip_bytes = _download_zip(owner, repo)
    _extract_zip(zip_bytes, dest)
    return scan_files(dest)
