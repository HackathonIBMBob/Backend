import os
import zipfile
from typing import Dict, List


LANGUAGE_MAP = {
    ".py": "python",
    ".java": "java",
    ".php": "php",
    ".js": "javascript",
    ".ts": "typescript",
    ".cs": "csharp",
    ".go": "go",
    ".rb": "ruby",
}

MAX_FILE_SIZE_BYTES = 500 * 1024


def _safe_extract(zip_path: str, dest: str) -> None:
    os.makedirs(dest, exist_ok=True)
    dest_abs = os.path.abspath(dest)

    with zipfile.ZipFile(zip_path, "r") as archive:
        for member in archive.infolist():
            target = os.path.abspath(os.path.join(dest, member.filename))
            if not target.startswith(dest_abs + os.sep) and target != dest_abs:
                raise ValueError(f"Unsafe zip member path: {member.filename}")
        archive.extractall(dest)


def _read_text_file(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as handle:
        return handle.read()


def scan_files(source_dir: str) -> List[Dict[str, object]]:
    files: List[Dict[str, object]] = []
    source_abs = os.path.abspath(source_dir)

    for root, dirs, filenames in os.walk(source_abs):
        dirs[:] = [name for name in dirs if name not in {".git", "__pycache__", "node_modules"}]

        for filename in filenames:
            ext = os.path.splitext(filename)[1].lower()
            if ext not in LANGUAGE_MAP:
                continue

            full_path = os.path.join(root, filename)
            if os.path.getsize(full_path) > MAX_FILE_SIZE_BYTES:
                continue

            content = _read_text_file(full_path)
            relative_path = os.path.relpath(full_path, source_abs).replace(os.sep, "/")
            files.append(
                {
                    "path": relative_path,
                    "language": LANGUAGE_MAP[ext],
                    "size_lines": len(content.splitlines()),
                    "content": content,
                }
            )

    return files


def extract_repo(zip_path: str, dest: str) -> List[dict]:
    _safe_extract(zip_path, dest)
    return scan_files(dest)
