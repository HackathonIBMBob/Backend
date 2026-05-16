import os
import zipfile
from typing import List


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
