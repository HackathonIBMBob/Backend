from __future__ import annotations

from threading import Lock
from typing import Any, Dict, Optional


jobs: Dict[str, Dict[str, Any]] = {}
_jobs_lock = Lock()


def create_job(job_id: str, source_job_id: str) -> Dict[str, Any]:
    job = {
        "job_id": job_id,
        "source_job_id": source_job_id,
        "status": "pending",
        "progress": 0,
        "stage": "queued",
        "result": {},
    }
    with _jobs_lock:
        jobs[job_id] = job
    return job


def update(job_id: str, progress: int, stage: str) -> None:
    with _jobs_lock:
        job = jobs.get(job_id)
        if job is None:
            return
        job["progress"] = max(0, min(100, int(progress)))
        job["stage"] = stage
        job["status"] = "completed" if job["progress"] >= 100 else "running"


def set_result(job_id: str, result: Dict[str, Any]) -> None:
    with _jobs_lock:
        job = jobs.get(job_id)
        if job is None:
            return
        job["result"] = result


def fail_job(job_id: str, stage: str, error: str) -> None:
    with _jobs_lock:
        job = jobs.get(job_id)
        if job is None:
            jobs[job_id] = {
                "job_id": job_id,
                "status": "failed",
                "progress": 0,
                "stage": stage,
                "result": {"error": error},
            }
            return

        job["status"] = "failed"
        job["stage"] = stage
        job["result"] = {"error": error}


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    with _jobs_lock:
        job = jobs.get(job_id)
        return dict(job) if job is not None else None
