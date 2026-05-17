import os
import shutil
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile

from models.schemas import IngestRequest, IngestResponse, LocalIngestRequest
from services import github_fetcher, repo_parser
from services.job_store import create_job, fail_job, set_result, update


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


@router.post("/local", response_model=IngestResponse)
async def ingest_local(request: LocalIngestRequest):
    local_path = request.local_path.strip()

    if not local_path:
        raise HTTPException(status_code=400, detail="Provide local_path")
    if not os.path.exists(local_path):
        raise HTTPException(status_code=400, detail=f"Path does not exist: {local_path}")
    if not os.path.isdir(local_path):
        raise HTTPException(status_code=400, detail=f"Path is not a directory: {local_path}")

    job_id = str(uuid.uuid4())
    job_dir = os.path.join("uploads", job_id)
    repo_dir = os.path.join(job_dir, "repo")
    os.makedirs(job_dir, exist_ok=True)
    create_job(job_id, job_id)

    try:
        shutil.copytree(local_path, repo_dir)
    except Exception as exc:
        fail_job(job_id, "failed", str(exc))
        raise HTTPException(status_code=500, detail=f"Failed to copy repository: {exc}") from exc

    try:
        files = repo_parser.scan_files(repo_dir)
    except Exception as exc:
        fail_job(job_id, "failed", str(exc))
        raise HTTPException(status_code=500, detail=f"Failed to scan repository: {exc}") from exc

    if not files:
        fail_job(job_id, "failed", "No supported code files found")
        raise HTTPException(status_code=422, detail="No supported code files found in the directory")

    update(job_id, 100, "ingested")
    set_result(job_id, {
        "files_found": len(files),
        "repo_dir": repo_dir,
        "original_local_path": os.path.abspath(local_path),
    })
    return _metadata_response(job_id, files)
