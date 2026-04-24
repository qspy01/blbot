import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from celery.result import AsyncResult
from worker.celery_app import celery_app

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# WAŻNE: downloads jest teraz w głównym katalogu /app/
app.mount("/downloads", StaticFiles(directory="/app/downloads"), name="downloads")

class DownloadRequest(BaseModel):
    url: str
    start_time: int | None = None
    end_time: int | None = None

@app.post("/api/v1/downloads")
def start_download(request: DownloadRequest):
    try:
        from worker.celery_app import process_download_task
        task = process_download_task.delay(request.url, request.start_time, request.end_time)
        return {"task_id": task.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/downloads/status/{task_id}")
def get_task_status(task_id: str):
    result = AsyncResult(task_id, app=celery_app)
    if result.state == 'SUCCESS':
        return {"status": "SUCCESS", "url": result.result.get("url")}
    elif result.state == 'FAILURE':
        return {"status": "FAILURE", "error": "Błąd pobierania (YouTube blokuje serwer)"}
    return {"status": result.state}
