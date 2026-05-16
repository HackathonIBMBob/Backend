from typing import List

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


class ModernizeResponse(BaseModel):
    job_id: str
    files_processed: int
    zip_url: str
    docx_url: str
    summary: str


class FileResult(BaseModel):
    filename: str
    language: str
    original_code: str
    modernized_code: str
    changes_summary: str
    documentation: str
