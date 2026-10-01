from fastapi import FastAPI, HTTPException, Request
from typing import Any, Dict, Optional
import asyncio
import json
import os
from .cloudflyer import CloudflyerClient
from .classification import classify_images

app = FastAPI(title="Unified Captcha Gateway")
client: Optional[CloudflyerClient] = None


@app.on_event("startup")
async def startup():
    global client
    base = os.getenv("CLOUDFLYER_BASE_URL", "http://cloudflyer:3000")
    key = os.getenv("CLIENTT_KEY")
    if not key:
        raise RuntimeError("CLIENTT_KEY is required")
    client = CloudflyerClient(base, key, timeout=120)


@app.post("/createTask")
async def create_task(request: Request):
    body = await request.json()
    task_type = body.get("type")
    if task_type == "classification":
        return {"taskId": "classification", "status": "processing"}
    if not client:
        raise HTTPException(status_code=503, detail="solver not ready")
    task = await client.create_and_wait(
        task_type=task_type,
        url=body.get("url"),
        site_key=body.get("siteKey"),
        action=body.get("action"),
        user_agent=body.get("userAgent"),
        proxy=body.get("proxy"),
        content=body.get("content", False),
    )
    return {"taskId": task.get("taskId") or "classification"}


@app.post("/getTaskResult")
async def get_task_result(request: Request):
    body = await request.json()
    task_id = body.get("taskId")
    if task_id == "classification":
        return {"status": "completed", "result": classify_images(body)}
    if not client or task_id is None:
        raise HTTPException(status_code=400, detail="invalid taskId")
    result = await client.create_and_wait(
        task_type="Turnstile",
        url="",
        site_key="",
        action=None,
        user_agent=None,
        proxy=None,
        content=False,
    )
    return {"status": "completed", "result": result}
