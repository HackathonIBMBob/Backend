from typing import Any, List

from pydantic import BaseModel


class IngestRequest(BaseModel):
    github_url: str


class FileInfo(BaseModel):
    path: str
    language: str
    size_lines: int


class IngestResponse(BaseModel):
    job_id: str
    files_found: int
    files: List[FileInfo]


class ModernizeRequest(BaseModel):
    job_id: str


class ModernizeStartResponse(BaseModel):
    job_id: str
    status: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: int
    stage: str
    result: Any


class FileResult(BaseModel):
    filename: str
    language: str
    original_code: str
    modernized_code: str
    changes_summary: str
    documentation: str
