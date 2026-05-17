import json
import os
import shutil
import zipfile
from typing import Any, Dict, List, Optional


def _find_free_output_dir(parent: str, stem: str) -> str:
    """Return the first non-existing path of the form {parent}/{stem}_modernized[_N]."""
    candidate = os.path.join(parent, f"{stem}_modernized")
    if not os.path.exists(candidate):
        return candidate
    counter = 2
    while True:
        candidate = os.path.join(parent, f"{stem}_modernized_{counter}")
        if not os.path.exists(candidate):
            return candidate
        counter += 1


def write_full_output(
    source_dir: str,
    output_parent: str,
    output_stem: str,
    results: List[dict],
    docx_src: Optional[str],
    bob_report: Dict[str, Any],
) -> str:
    """
    Write the complete modernized output next to the original repo dir.

    Steps:
      1. Copy *all* files from source_dir (preserves unsupported files like .png, .md).
      2. Overwrite only the files that were modernized with their new content.
      3. Copy report.docx into the root of the output dir.
      4. Write bob_report.json into the root of the output dir.

    Returns the absolute path of the created output directory.
    """
    output_dir = _find_free_output_dir(output_parent, output_stem)

    # 1. Full copy — maintains directory structure, includes every file
    shutil.copytree(source_dir, output_dir)

    # 2. Overwrite with modernized versions (path-traversal guard)
    output_abs = os.path.abspath(output_dir)
    for result in results:
        relative_path = result.get("filename") or result.get("path")
        if not relative_path:
            continue

        dest = os.path.abspath(os.path.join(output_dir, relative_path))
        if not dest.startswith(output_abs + os.sep):
            raise ValueError(f"Unsafe output path detected: {relative_path}")

        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w", encoding="utf-8") as fh:
            fh.write(result.get("modernized_code", ""))

    # 3. Copy report.docx if it was generated
    if docx_src and os.path.exists(docx_src):
        shutil.copy2(docx_src, os.path.join(output_dir, "report.docx"))

    # 4. Write structured JSON report
    with open(os.path.join(output_dir, "bob_report.json"), "w", encoding="utf-8") as fh:
        json.dump(bob_report, fh, indent=2, ensure_ascii=False)

    return output_dir


# Kept for reference; the pipeline now uses write_full_output instead.
def write_modernized_files(job_id: str, results: List[dict]) -> str:
    base_dir = os.path.join("uploads", job_id, "modernized")
    os.makedirs(base_dir, exist_ok=True)

    for result in results:
        relative_path = result.get("filename") or result.get("path")
        if not relative_path:
            continue

        output_path = os.path.abspath(os.path.join(base_dir, relative_path))
        base_abs = os.path.abspath(base_dir)
        if not output_path.startswith(base_abs + os.sep):
            raise ValueError(f"Unsafe output path: {relative_path}")

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as handle:
            handle.write(result.get("modernized_code", ""))

    return base_dir


def create_zip(source_dir: str, output_path: str) -> str:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for root, _, files in os.walk(source_dir):
            for filename in files:
                full_path = os.path.join(root, filename)
                arcname = os.path.relpath(full_path, source_dir)
                archive.write(full_path, arcname)
    return output_path
