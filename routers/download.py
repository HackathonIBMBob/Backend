import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse


router = APIRouter()


@router.get("/zip/{job_id}")
def download_zip(job_id: str):
    path = os.path.join("uploads", job_id, "modernized_repo.zip")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="ZIP not found")
    return FileResponse(path, media_type="application/zip", filename="modernized_repo.zip")


@router.get("/docx/{job_id}")
def download_docx(job_id: str):
    path = os.path.join("uploads", job_id, "report.docx")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="DOCX report not found")
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename="legacy_whisperer_report.docx",
    )
