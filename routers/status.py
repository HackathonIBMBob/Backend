from fastapi import APIRouter, HTTPException

from models.schemas import JobStatusResponse
from services.job_store import get_job


router = APIRouter()


@router.get("/status/{job_id}", response_model=JobStatusResponse)
def get_status(job_id: str):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobStatusResponse(
        job_id=job["job_id"],
        status=job["status"],
        progress=job["progress"],
        stage=job["stage"],
        result=job.get("result", {}),
    )
