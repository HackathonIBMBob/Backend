from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import download, ingest, modernize, status


app = FastAPI(title="Legacy Whisperer API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://legacy-whisperer.vercel.app",
        "https://legacy-whisperer-git-main-dannamendez1109s-projects.vercel.app",
        "*",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest.router, prefix="/ingest", tags=["Ingest"])
app.include_router(modernize.router, prefix="/modernize", tags=["Modernize"])
app.include_router(status.router, tags=["Status"])
app.include_router(download.router, prefix="/download", tags=["Download"])


@app.get("/")
def health():
    return {"status": "ok", "service": "Legacy Whisperer"}
