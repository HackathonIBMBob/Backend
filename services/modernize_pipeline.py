from __future__ import annotations

import asyncio
import os
from typing import Any, Dict, List

from ai_pipeline import BobOrchestrator
from services import bob_client, docx_generator, file_transformer, repo_parser
from services.job_store import fail_job, get_job, set_result, update


async def run_pipeline(job_id: str, repo_id: str) -> Dict[str, Any]:
    job_dir = os.path.join("uploads", job_id)
    repo_dir = os.path.join("uploads", repo_id, "repo")

    try:
        update(job_id, 10, "loading repo")
        if not os.path.isdir(repo_dir):
            raise FileNotFoundError(f"Repository files not found for job {repo_id}")

        files = await asyncio.to_thread(repo_parser.scan_files, repo_dir)
        if not files:
            raise ValueError("No supported code files found for this job")

        dep_files = await asyncio.to_thread(repo_parser.scan_dependency_files, repo_dir)
        if dep_files:
            print(f"[pipeline] found dependency files: {[d['path'] for d in dep_files]}")

        update(job_id, 30, "analyzing code")
        bob = BobOrchestrator(bob_client)
        analysis = await bob.analyze(files)

        update(job_id, 60, "refactoring code")
        refactor = await bob.refactor(files, analysis, dep_files)

        update(job_id, 80, "generating documentation")
        documentation = await bob.document(files, analysis, refactor)

        update(job_id, 85, "modernizing files")
        results = await _modernize_files(files, refactor)

        # Generate docx first so write_full_output can include it in the output dir.
        # This step is optional — a Node/docx failure must not abort the pipeline.
        update(job_id, 90, "generating report")
        docx_path = os.path.join(job_dir, "report.docx")
        docx_result = await asyncio.to_thread(
            docx_generator.generate_report_docx, job_id, results, docx_path
        )
        if docx_result is None:
            print(f"[pipeline] job {job_id}: docx generation skipped, continuing without report")
            docx_path = None

        # Determine where to write the _modernized folder.
        # For local-path ingests the ingest job stores the user's original path;
        # for GitHub/ZIP ingests we place the folder next to uploads/{repo_id}/repo/.
        update(job_id, 95, "writing output")
        ingest_job = get_job(repo_id) or {}
        original_local_path = ingest_job.get("result", {}).get("original_local_path")

        if original_local_path and os.path.isdir(os.path.dirname(original_local_path)):
            output_parent = os.path.dirname(original_local_path)
            output_stem = os.path.basename(original_local_path)
        else:
            # Fallback: place next to uploads/{repo_id}/repo/
            repo_dir_abs = os.path.abspath(repo_dir)
            output_parent = os.path.dirname(repo_dir_abs)
            output_stem = os.path.basename(repo_dir_abs)

        # Merge dependency_updates into results so they get written alongside modernized files
        dep_updates = refactor.get("dependency_updates") or []
        dep_update_results = _dep_updates_to_results(dep_updates)
        if dep_update_results:
            print(f"[pipeline] applying {len(dep_update_results)} dependency file update(s): "
                  f"{[r['filename'] for r in dep_update_results]}")

        all_results = results + dep_update_results

        bob_report = {
            "analysis": analysis,
            "refactor_plan": refactor,
            "documentation": documentation,
            "files_processed": len(results),
            "dependency_updates_applied": [r["filename"] for r in dep_update_results],
        }

        output_path = await asyncio.to_thread(
            file_transformer.write_full_output,
            repo_dir,
            output_parent,
            output_stem,
            all_results,
            docx_path,
            bob_report,
        )

        # Build the zip from the complete output dir so it includes unsupported files too
        zip_output_path = os.path.join(job_dir, "modernized_repo.zip")
        await asyncio.to_thread(file_transformer.create_zip, output_path, zip_output_path)

        result = {
            "analysis": analysis,
            "refactor_plan": refactor,
            "documentation": documentation,
            "files_processed": len(results),
            "output_path": output_path,
            "zip_url": f"/download/zip/{job_id}",
            "docx_url": f"/download/docx/{job_id}",
        }
        set_result(job_id, result)
        update(job_id, 100, "completed")
        return result
    except Exception as exc:
        fail_job(job_id, "failed", str(exc))
        raise


def _dep_updates_to_results(dep_updates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert refactor-plan dependency_updates into the same shape as modernized file results."""
    out = []
    for update_item in dep_updates:
        filename = update_item.get("file", "").strip()
        content = update_item.get("updated_content", "")
        if not filename or not content:
            continue
        out.append({
            "filename": filename,
            "language": "xml" if filename.endswith(".xml") else "json",
            "original_code": "",
            "modernized_code": content,
            "changes_summary": update_item.get("reason", "Dependency update from refactor plan"),
            "documentation": "",
        })
    return out


async def _modernize_files(files: List[dict], refactor: Dict[str, Any]) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for file_info in files:
        transformed = await asyncio.to_thread(
            bob_client.modernize_file,
            filename=file_info["path"],
            code=file_info["content"],
            language=file_info["language"],
            plan=str(refactor),
        )

        if transformed.get("error"):
            raise RuntimeError(
                f"Watsonx modernization failed for {file_info['path']}: {transformed['error']}"
            )

        results.append(
            {
                "filename": file_info["path"],
                "language": file_info["language"],
                "original_code": file_info["content"],
                "modernized_code": transformed.get("modernized_code", file_info["content"]),
                "changes_summary": transformed.get("changes_summary", ""),
                "documentation": transformed.get("documentation", ""),
            }
        )

    return results
