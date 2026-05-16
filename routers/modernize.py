import asyncio
import os
import uuid

from fastapi import APIRouter, HTTPException

from models.schemas import ModernizeRequest, ModernizeStartResponse
from services.job_store import create_job, get_job
from services.modernize_pipeline import run_pipeline


router = APIRouter()
_background_tasks: set[asyncio.Task] = set()


@router.post("", response_model=ModernizeStartResponse)
@router.post("/full-repo", response_model=ModernizeStartResponse)
async def modernize_full_repo(request: ModernizeRequest):
    if get_job(request.job_id) is None:
        raise HTTPException(status_code=404, detail="Job not found")

    source_repo_dir = os.path.join("uploads", request.job_id, "repo")
    if not os.path.isdir(source_repo_dir):
        raise HTTPException(status_code=404, detail="Repository files not found for this job")

    internal_job_id = str(uuid.uuid4())
    create_job(internal_job_id, request.job_id)

    task = asyncio.create_task(run_pipeline(internal_job_id, request.job_id))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

    return ModernizeStartResponse(job_id=internal_job_id, status="started")
