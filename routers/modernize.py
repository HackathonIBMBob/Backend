import os

from fastapi import APIRouter, HTTPException

from models.schemas import ModernizeRequest, ModernizeResponse
from services import bob_client, docx_generator, file_transformer, repo_parser


router = APIRouter()


@router.post("/full-repo", response_model=ModernizeResponse)
async def modernize_full_repo(request: ModernizeRequest):
    job_dir = os.path.join("uploads", request.job_id)
    repo_dir = os.path.join(job_dir, "repo")

    if not os.path.isdir(job_dir):
        raise HTTPException(status_code=404, detail="Job not found")
    if not os.path.isdir(repo_dir):
        raise HTTPException(status_code=404, detail="Repository files not found for this job")

    files = repo_parser.scan_files(repo_dir)
    if not files:
        raise HTTPException(status_code=400, detail="No supported code files found for this job")

    architecture = bob_client.analyze_architecture(files)
    if architecture.get("error"):
        raise HTTPException(status_code=502, detail=f"Watsonx architecture analysis failed: {architecture['error']}")

    modernization_plan = architecture.get("modernization_plan", architecture)

    results = []
    for file_info in files:
        transformed = bob_client.modernize_file(
            filename=file_info["path"],
            code=file_info["content"],
            language=file_info["language"],
            plan=str(modernization_plan),
        )

        if transformed.get("error"):
            raise HTTPException(
                status_code=502,
                detail=f"Watsonx modernization failed for {file_info['path']}: {transformed['error']}",
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

    modernized_dir = file_transformer.write_modernized_files(request.job_id, results)
    zip_output_path = os.path.join(job_dir, "modernized_repo.zip")
    file_transformer.create_zip(modernized_dir, zip_output_path)

    docx_generator.generate_report_docx(
        request.job_id,
        results,
        os.path.join(job_dir, "report.docx"),
    )

    return ModernizeResponse(
        job_id=request.job_id,
        files_processed=len(results),
        zip_url=f"/download/zip/{request.job_id}",
        docx_url=f"/download/docx/{request.job_id}",
        summary=f"Done. {len(results)} files modernized.",
    )
