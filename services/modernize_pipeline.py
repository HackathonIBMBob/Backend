from __future__ import annotations

import asyncio
import os
from typing import Any, Dict, List

from ai_pipeline import BobOrchestrator
from services import bob_client, docx_generator, file_transformer, repo_parser
from services.job_store import fail_job, set_result, update


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

        update(job_id, 30, "analyzing code")
        bob = BobOrchestrator(bob_client)
        analysis = await bob.analyze(files)

        update(job_id, 60, "refactoring code")
        refactor = await bob.refactor(files, analysis)

        update(job_id, 80, "generating documentation")
        documentation = await bob.document(files, analysis, refactor)

        update(job_id, 85, "modernizing files")
        results = await _modernize_files(files, refactor)

        update(job_id, 95, "creating zip")
        modernized_dir = await asyncio.to_thread(file_transformer.write_modernized_files, job_id, results)
        zip_output_path = os.path.join(job_dir, "modernized_repo.zip")
        await asyncio.to_thread(file_transformer.create_zip, modernized_dir, zip_output_path)

        await asyncio.to_thread(
            docx_generator.generate_report_docx,
            job_id,
            results,
            os.path.join(job_dir, "report.docx"),
        )

        result = {
            "analysis": analysis,
            "refactor_plan": refactor,
            "documentation": documentation,
            "files_processed": len(results),
            "zip_url": f"/download/zip/{job_id}",
            "docx_url": f"/download/docx/{job_id}",
        }
        set_result(job_id, result)
        update(job_id, 100, "completed")
        return result
    except Exception as exc:
        fail_job(job_id, "failed", str(exc))
        raise


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
