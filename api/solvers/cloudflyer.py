import asyncio
from typing import Any, Optional

import httpx


class CloudflyerError(Exception):
    pass


class CloudflyerClient:
    def __init__(self, base_url: str, client_key: str, timeout: int = 120):
        self.base_url = base_url.rstrip("/")
        self.client_key = client_key
        self.timeout = timeout

    async def create_and_wait(
        self,
        task_type: str,
        url: str,
        site_key: Optional[str] = None,
        action: Optional[str] = None,
        user_agent: Optional[str] = None,
        proxy: Optional[dict] = None,
        content: bool = False,
    ) -> dict:
        payload: dict[str, Any] = {
            "clientKey": self.client_key,
            "type": task_type,
            "url": url,
        }
        if site_key:
            payload["siteKey"] = site_key
        if action:
            payload["action"] = action
        if user_agent:
            payload["userAgent"] = user_agent
        if proxy:
            payload["proxy"] = proxy
        if content:
            payload["content"] = True

        async with httpx.AsyncClient(timeout=30) as client:
            created = await client.post(f"{self.base_url}/createTask", json=payload)
            created.raise_for_status()
            data = created.json()
            task_id = data.get("taskId")
            if not task_id:
                raise CloudflyerError(f"createTask failed: {data}")

            deadline = asyncio.get_event_loop().time() + self.timeout
            while asyncio.get_event_loop().time() < deadline:
                result = await client.post(
                    f"{self.base_url}/getTaskResult",
                    json={"clientKey": self.client_key, "taskId": task_id},
                )
                result.raise_for_status()
                body = result.json()
                status = (body.get("status") or "").lower()
                if status == "completed":
                    inner = body.get("result") or {}
                    if inner.get("success") is False:
                        raise CloudflyerError(inner.get("error") or "cloudflyer task failed")
                    return inner
                if status not in {"processing", "pending", "idle", ""}:
                    raise CloudflyerError(f"unknown status: {status}")
                await asyncio.sleep(2)
        raise CloudflyerError("wait task timeout")
