import asyncio
import os
import uuid
from typing import Any, Optional

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from detector import detect, kind_from_task
from solvers.classification import classify_images
from solvers.click import ClickSolverError, solve_click
from solvers.cloudflyer import CloudflyerClient, CloudflyerError
from solvers.labels import has_image_payload, is_click_question, question_text

APP_KEY = os.getenv("CLIENTT_KEY", "")
CLOUDFLYER_URL = os.getenv("CLOUDFLYER_URL", "http://127.0.0.1:3000")
DOMAIN = os.getenv("DOMAIN", "challenge.cool.pp.ua")
TASKS: dict[str, dict[str, Any]] = {}

app = FastAPI(title="Challenge Gateway", version="1.0.0", docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
cf = CloudflyerClient(CLOUDFLYER_URL, APP_KEY, timeout=int(os.getenv("CLOUDFLYER_TIMEOUT", "120")))


def _auth_ok(client_key: Optional[str]) -> bool:
    return bool(APP_KEY) and client_key == APP_KEY


def _request_key(request: Request, body: Optional[dict[str, Any]] = None) -> Optional[str]:
    if body and body.get("clientKey"):
        return str(body.get("clientKey"))
    header_key = request.headers.get("x-client-key") or request.headers.get("x-api-key")
    if header_key:
        return header_key
    auth = request.headers.get("authorization") or ""
    if auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()
    return None


def _extract_task(body: dict[str, Any]) -> tuple[str, dict[str, Any], str]:
    if isinstance(body.get("task"), dict):
        task = dict(body["task"])
        return str(task.get("type") or body.get("type") or ""), task, "capsolver"
    return str(body.get("type") or ""), body, "cloudflyer"


def _site_key(task: dict[str, Any], detected: dict[str, Any]) -> str:
    return str(
        task.get("websiteKey")
        or task.get("siteKey")
        or task.get("sitekey")
        or (detected.get("primary") or {}).get("siteKey")
        or ""
    )


def _url(task: dict[str, Any], detected: dict[str, Any]) -> str:
    return str(task.get("websiteURL") or task.get("url") or detected.get("url") or "")


def _action(task: dict[str, Any]) -> Optional[str]:
    return task.get("pageAction") or task.get("action")


def cap_ok(task_id: str) -> dict[str, Any]:
    return {"errorId": 0, "taskId": task_id}


def cap_processing() -> dict[str, Any]:
    return {"errorId": 0, "status": "processing"}


def cap_ready(solution: dict[str, Any]) -> dict[str, Any]:
    return {"errorId": 0, "status": "ready", "solution": solution}


def cap_err(message: str, code: str = "ERROR_TASK_FAILED") -> dict[str, Any]:
    return {"errorId": 1, "errorCode": code, "errorDescription": message}


@app.get("/")
async def index():
    return JSONResponse({"error": "not found"}, status_code=404)


@app.get("/health")
async def health():
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(f"{CLOUDFLYER_URL}/docs")
            cf_ok = r.status_code < 500
    except Exception:
        cf_ok = False
    return {"ok": bool(cf_ok)}


@app.post("/detect")
async def detect_endpoint(request: Request):
    body = await request.json()
    if not _auth_ok(_request_key(request, body)):
        return JSONResponse(cap_err("invalid clientKey", "ERROR_KEY_DENIED"), status_code=403)
    return detect(body)


@app.post("/createTask")
async def create_task(request: Request):
    body = await request.json()
    if not _auth_ok(_request_key(request, body)):
        return JSONResponse(cap_err("invalid clientKey", "ERROR_KEY_DENIED"), status_code=403)

    raw_type, task, dialect = _extract_task(body)
    task_id = str(uuid.uuid4())
    TASKS[task_id] = {"status": "processing", "dialect": dialect, "solution": None, "error": None, "detected": None}
    asyncio.create_task(_run_task(task_id, raw_type, task, dialect))
    if dialect == "capsolver":
        return cap_ok(task_id)
    return {"taskId": task_id}


@app.post("/getTaskResult")
async def get_task_result(request: Request):
    body = await request.json()
    if not _auth_ok(_request_key(request, body)):
        return JSONResponse(cap_err("invalid clientKey", "ERROR_KEY_DENIED"), status_code=403)
    task_id = body.get("taskId")
    item = TASKS.get(str(task_id) if task_id is not None else "")
    if not item:
        if body.get("task") or body.get("type"):
            return JSONResponse(cap_err("task not found", "ERROR_INVALID_TASK_ID"), status_code=404)
        return JSONResponse({"status": "failed", "result": {"success": False, "error": "task not found"}}, status_code=404)
    dialect = item.get("dialect") or "cloudflyer"
    if item["status"] == "processing":
        return cap_processing() if dialect == "capsolver" else {"status": "processing"}
    if item["status"] == "failed":
        if dialect == "capsolver":
            return cap_err(item.get("error") or "task failed")
        return {"status": "completed", "result": {"success": False, "error": item.get("error")}}
    if dialect == "capsolver":
        return cap_ready(item.get("solution") or {})
    return {"status": "completed", "result": item.get("raw") or {"success": True, "response": item.get("solution")}}


@app.post("/solve")
async def solve_endpoint(request: Request):
    body = await request.json()
    if not _auth_ok(_request_key(request, body)):
        return JSONResponse(cap_err("invalid clientKey", "ERROR_KEY_DENIED"), status_code=403)
    raw_type, task, _dialect = _extract_task(body)
    detected = kind_from_task(raw_type, task)
    try:
        solution, raw = await _solve(detected, task)
    except (ClickSolverError, CloudflyerError) as exc:
        return JSONResponse(cap_err(str(exc)), status_code=400)
    return {"detected": detected, "solution": solution, "raw": raw}


async def _run_task(task_id: str, raw_type: str, task: dict[str, Any], dialect: str) -> None:
    try:
        detected = kind_from_task(raw_type, task)
        solution, raw = await _solve(detected, task)
        TASKS[task_id] = {
            "status": "ready",
            "dialect": dialect,
            "solution": solution,
            "raw": raw,
            "error": None,
            "detected": detected,
        }
    except Exception as exc:
        TASKS[task_id] = {
            "status": "failed",
            "dialect": dialect,
            "solution": None,
            "raw": None,
            "error": str(exc),
            "detected": None,
        }


async def _solve(detected: dict[str, Any], task: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    primary = detected.get("primary") or {}
    kind = primary.get("type") or "unknown"
    solver = primary.get("solver")
    url = _url(task, detected)
    sitekey = _site_key(task, detected)

    clickish = (
        solver == "click"
        or kind.endswith("classification")
        or kind == "click_select"
        or (
            (solver == "ocr" or kind == "image_to_text")
            and has_image_payload(task)
            and is_click_question(question_text(task))
        )
    )
    if clickish and has_image_payload(task):
        solution = await asyncio.to_thread(solve_click, task)
        solution["type"] = kind if kind and kind != "unknown" else "click_select"
        return solution, {"success": True, "response": solution}

    if solver == "ocr" or kind == "image_to_text":
        solution = await asyncio.to_thread(classify_images, task)
        solution["type"] = kind
        return solution, {"success": True, "response": solution}

    if solver != "cloudflyer":
        raise CloudflyerError(
            f"已识别为 {kind}，但当前容器还没有对应的完整求解后端。"
            "Turnstile / Cloudflare 5秒盾 / reCAPTCHA Invisible 可以直接解；"
            "点选请把格子图和 question 一起发过来。"
        )

    cf_type = primary.get("cloudflyerType") or "Turnstile"
    if cf_type == "CloudflareChallenge":
        inner = await cf.create_and_wait(
            "CloudflareChallenge",
            url,
            user_agent=task.get("userAgent"),
            proxy=task.get("proxy"),
            content=bool(task.get("content")),
        )
        response = inner.get("response") or {}
        cookies = response.get("cookies") or {}
        solution = {
            "cookies": cookies,
            "userAgent": (response.get("headers") or {}).get("User-Agent"),
            "token": cookies.get("cf_clearance"),
            "type": "CloudflareChallenge",
        }
        return solution, inner

    inner = await cf.create_and_wait(
        cf_type,
        url,
        site_key=sitekey,
        action=_action(task),
        user_agent=task.get("userAgent"),
        proxy=task.get("proxy"),
    )
    token = _token_from_cf(inner)
    solution = {"token": token, "type": kind}
    if kind.startswith("recaptcha"):
        solution["gRecaptchaResponse"] = token
    return solution, inner


def _token_from_cf(inner: dict[str, Any]) -> str:
    response = inner.get("response") or {}
    if isinstance(response, str) and response:
        return response
    if isinstance(response, dict):
        token = response.get("token") or response.get("value")
        if token:
            return token
    raise CloudflyerError(f"cloudflyer response missing token: {inner}")
