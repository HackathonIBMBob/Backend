import subprocess
import sys
from typing import List

from fastapi import HTTPException

from services.repo_parser import scan_files

try:
    import git
except ImportError:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'gitpython'])
    import git


def clone_repo(github_url: str, dest: str) -> List[dict]:

    try:
        git.Repo.clone_from(github_url, dest, depth=1)
    except git.exc.GitCommandNotFound as exc:
        raise HTTPException(status_code=500, detail="Git is required. Run: apt-get install git") from exc
    except git.exc.GitCommandError as exc:
        message = str(exc).lower()
        if "repository not found" in message or "not found" in message or "404" in message:
            raise HTTPException(status_code=404, detail="Repository not found. Check the URL.") from exc
        if (
            "authentication failed" in message
            or "could not read username" in message
            or "permission denied" in message
            or "403" in message
        ):
            raise HTTPException(status_code=401, detail="Repository is private. Only public GitHub repositories are supported.") from exc
        raise HTTPException(status_code=400, detail=f"Failed to clone repository: {exc}") from exc

    return scan_files(dest)
