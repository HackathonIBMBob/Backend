import os
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile

from models.schemas import IngestRequest, IngestResponse
from services import github_fetcher, repo_parser
from services.job_store import create_job, set_result, update, fail_job


router = APIRouter()


def _metadata_response(job_id: str, files: list[dict]) -> IngestResponse:
    file_metadata = [
        {
            "path": file_info["path"],
            "language": file_info["language"],
            "size_lines": file_info["size_lines"],
        }
        for file_info in files
    ]

    return IngestResponse(job_id=job_id, files_found=len(files), files=file_metadata)


@router.post("", response_model=IngestResponse)
async def ingest(
    file: UploadFile = File(None),
):
    job_id = str(uuid.uuid4())
    job_dir = os.path.join("uploads", job_id)
    repo_dir = os.path.join(job_dir, "repo")
    os.makedirs(job_dir, exist_ok=True)
    create_job(job_id, job_id)

    if file is not None:
        if not file.filename or not file.filename.lower().endswith(".zip"):
            fail_job(job_id, "failed", "Uploaded file must be a ZIP archive")
            raise HTTPException(status_code=400, detail="Uploaded file must be a ZIP archive")

        zip_path = os.path.join(job_dir, "repo.zip")
        with open(zip_path, "wb") as handle:
            handle.write(await file.read())

        try:
            files = repo_parser.extract_repo(zip_path, repo_dir)
        except Exception as exc:
            fail_job(job_id, "failed", str(exc))
            raise HTTPException(status_code=400, detail=f"Failed to extract repository: {exc}") from exc
    else:
        fail_job(job_id, "failed", "Provide a zip file")
        raise HTTPException(status_code=400, detail="Provide a zip file")

    update(job_id, 100, "ingested")
    set_result(job_id, {"files_found": len(files), "repo_dir": repo_dir})

    return _metadata_response(job_id, files)


@router.post("/github", response_model=IngestResponse)
async def ingest_github(request: IngestRequest):
    if not request.github_url:
        raise HTTPException(status_code=400, detail="Provide github_url")

    job_id = str(uuid.uuid4())
    job_dir = os.path.join("uploads", job_id)
    repo_dir = os.path.join(job_dir, "repo")
    os.makedirs(job_dir, exist_ok=True)
    create_job(job_id, job_id)

    try:
        files = github_fetcher.clone_repo(request.github_url, repo_dir)
    except HTTPException as exc:
        fail_job(job_id, "failed", str(exc.detail))
        raise

    update(job_id, 100, "ingested")
    set_result(job_id, {"files_found": len(files), "repo_dir": repo_dir})
    return _metadata_response(job_id, files)
