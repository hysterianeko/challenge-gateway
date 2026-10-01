from __future__ import annotations

import re
from typing import Any, Iterable, Optional

from solvers.labels import has_image_payload, is_click_question, question_text

TURNSTILE_KEY = re.compile(r"0x[0-9A-Za-z]{16,}")
RECAPTCHA_KEY = re.compile(r"6L[0-9A-Za-z_-]{20,}")
UUID_KEY = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)
DATA_SITEKEY = re.compile(r'data-sitekey=["\']([^"\']+)["\']', re.I)
IFRAME_SRC = re.compile(r'<iframe[^>]+src=["\']([^"\']+)["\']', re.I)
SCRIPT_SRC = re.compile(r'<script[^>]+src=["\']([^"\']+)["\']', re.I)

SOLVER_CLOUDFLYER = "cloudflyer"
SOLVER_OCR = "ocr"
SOLVER_CLICK = "click"
SOLVER_NONE = "unsupported"
GRID_KINDS = {"recaptcha_v2", "hcaptcha", "aws_waf", "bcaptcha"}

ALIAS_TO_KIND = {
    "turnstile": "turnstile",
    "cloudflareturnstile": "turnstile",
    "antiturnstiletaskproxyless": "turnstile",
    "antiturnstiletask": "turnstile",
    "cloudflarechallenge": "cloudflare_challenge",
    "cloudflare5s": "cloudflare_challenge",
    "cloudflare5秒盾": "cloudflare_challenge",
    "anticloudflaretask": "cloudflare_challenge",
    "anticloudflaretaskproxyless": "cloudflare_challenge",
    "recaptcha": "recaptcha_invisible",
    "recaptchainvisible": "recaptcha_invisible",
    "recaptchav3": "recaptcha_v3",
    "recaptchav3taskproxyless": "recaptcha_v3",
    "recaptchav3task": "recaptcha_v3",
    "recaptchav2": "recaptcha_v2",
    "recaptchav2taskproxyless": "recaptcha_v2",
    "recaptchav2task": "recaptcha_v2",
    "hcaptcha": "hcaptcha",
    "hcaptchatask": "hcaptcha",
    "hcaptchataskproxyless": "hcaptcha",
    "funcaptcha": "funcaptcha",
    "funcaptchatask": "funcaptcha",
    "funcaptchataskproxyless": "funcaptcha",
    "arkoselabs": "funcaptcha",
    "awsclassification": "aws_classification",
    "awswafclassification": "aws_classification",
    "bcaptchaclassification": "bcaptcha_classification",
    "binanceclassification": "bcaptcha_classification",
    "funcaptchaclassification": "funcaptcha_classification",
    "hcaptchaclassification": "hcaptcha_classification",
    "recaptchav2classification": "recaptcha_classification",
    "imagetotext": "image_to_text",
    "ocr": "image_to_text",
    "click": "click_select",
    "clickselect": "click_select",
    "gridclick": "click_select",
    "imageselect": "click_select",
    "autodetect": "auto",
    "auto": "auto",
    "detect": "auto",
}

CF_TYPES = {
    "turnstile": "Turnstile",
    "cloudflare_challenge": "CloudflareChallenge",
    "recaptcha_v2": "RecaptchaInvisible",
    "recaptcha_v3": "RecaptchaInvisible",
    "recaptcha_invisible": "RecaptchaInvisible",
}


def norm_type(value: Optional[str]) -> str:
    return "".join(ch for ch in (value or "").lower() if ch.isalnum() or ch in "秒")


def canonical_kind(value: Optional[str]) -> str:
    return ALIAS_TO_KIND.get(norm_type(value), "")


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [f"{k}:{v}" for k, v in value.items()]
    if isinstance(value, Iterable):
        return [str(item) for item in value if item is not None]
    return [str(value)]


def _blob(payload: dict[str, Any]) -> str:
    chunks: list[str] = []
    for key in ("html", "content", "page", "url", "websiteURL", "userAgent"):
        if payload.get(key):
            chunks.append(str(payload[key]))
    for key in ("iframes", "scripts", "cookies", "headers", "source"):
        chunks.extend(_as_list(payload.get(key)))
    return "\n".join(chunks)


def _sitekeys(payload: dict[str, Any], blob: str) -> list[str]:
    keys: list[str] = []
    for key in ("siteKey", "sitekey", "websiteKey", "publicKey", "key"):
        if payload.get(key):
            keys.append(str(payload[key]))
    keys.extend(DATA_SITEKEY.findall(blob))
    keys.extend(TURNSTILE_KEY.findall(blob))
    keys.extend(RECAPTCHA_KEY.findall(blob))
    seen: set[str] = set()
    unique: list[str] = []
    for item in keys:
        item = item.strip()
        if item and item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


def _urls(payload: dict[str, Any], blob: str) -> list[str]:
    urls = _as_list(payload.get("iframes")) + _as_list(payload.get("scripts"))
    urls.extend(IFRAME_SRC.findall(blob))
    urls.extend(SCRIPT_SRC.findall(blob))
    if payload.get("url"):
        urls.append(str(payload["url"]))
    return urls


def _hit(blob: str, *needles: str) -> bool:
    low = blob.lower()
    return any(needle.lower() in low for needle in needles)


def _challenge(
    kind: str,
    *,
    confidence: float,
    evidence: list[str],
    solver: str,
    sitekey: str = "",
    cloudflyer_type: Optional[str] = None,
) -> dict[str, Any]:
    return {
        "type": kind,
        "confidence": round(confidence, 2),
        "siteKey": sitekey,
        "evidence": evidence,
        "solver": solver,
        "cloudflyerType": cloudflyer_type,
        "solvable": solver != SOLVER_NONE,
    }


def detect(payload: dict[str, Any]) -> dict[str, Any]:
    blob = _blob(payload)
    keys = _sitekeys(payload, blob)
    urls = _urls(payload, blob)
    joined_urls = "\n".join(urls)
    haystack = blob + "\n" + joined_urls
    found: list[dict[str, Any]] = []

    turnstile_key = next((k for k in keys if k.startswith("0x")), "")
    recaptcha_key = next((k for k in keys if k.startswith("6L")), "")
    uuid_key = next((k for k in keys if UUID_KEY.fullmatch(k)), "")

    if _hit(haystack, "arkoselabs", "funcaptcha", "fc-token", "enforcement.arkoselabs", "client-api.arkoselabs"):
        found.append(_challenge("funcaptcha", confidence=0.95, sitekey=uuid_key, evidence=["arkoselabs/funcaptcha"], solver=SOLVER_NONE))

    has_images = has_image_payload(payload)
    question = question_text(payload)

    if _hit(haystack, "hcaptcha.com", "h-captcha", "newassets.hcaptcha"):
        found.append(_challenge(
            "hcaptcha",
            confidence=0.95,
            sitekey=uuid_key,
            evidence=["hcaptcha"],
            solver=SOLVER_CLICK if has_images else SOLVER_NONE,
        ))

    if _hit(haystack, "challenges.cloudflare.com/turnstile", "cf-turnstile", "cf.turnstile") or turnstile_key:
        found.append(_challenge(
            "turnstile",
            confidence=0.97 if turnstile_key else 0.9,
            sitekey=turnstile_key,
            evidence=["turnstile"],
            solver=SOLVER_CLOUDFLYER,
            cloudflyer_type="Turnstile",
        ))

    if _hit(
        haystack,
        "cdn-cgi/challenge-platform",
        "cf-browser-verification",
        "cf_chl_",
        "just a moment",
        "managed-challenge",
        "cloudflare challenge",
    ) and not any(item["type"] == "turnstile" for item in found):
        found.append(_challenge(
            "cloudflare_challenge",
            confidence=0.93,
            evidence=["cloudflare-challenge"],
            solver=SOLVER_CLOUDFLYER,
            cloudflyer_type="CloudflareChallenge",
        ))

    if _hit(haystack, "recaptcha", "g-recaptcha", "grecaptcha", "google.com/recaptcha"):
        v3 = _hit(haystack, "recaptcha/api.js?render", "grecaptcha.execute", "recaptcha/enterprise.js?render")
        invisible = _hit(haystack, "size=invisible", "invisible")
        if v3:
            kind, conf = "recaptcha_v3", 0.94
        elif invisible:
            kind, conf = "recaptcha_invisible", 0.9
        else:
            kind, conf = "recaptcha_v2", 0.8
        recaptcha_click = has_images and kind == "recaptcha_v2"
        found.append(_challenge(
            kind,
            confidence=0.96 if recaptcha_click else conf,
            sitekey=recaptcha_key,
            evidence=["recaptcha"],
            solver=SOLVER_CLICK if recaptcha_click else SOLVER_CLOUDFLYER,
            cloudflyer_type=None if recaptcha_click else "RecaptchaInvisible",
        ))

    if _hit(haystack, "awswaf", "aws-waf-token", "captcha.awswaf.com"):
        found.append(_challenge(
            "aws_waf",
            confidence=0.96 if has_images else 0.9,
            evidence=["awswaf"],
            solver=SOLVER_CLICK if has_images else SOLVER_NONE,
        ))

    if _hit(haystack, "bcaptcha", "binance captcha"):
        found.append(_challenge(
            "bcaptcha",
            confidence=0.95 if has_images else 0.88,
            evidence=["bcaptcha"],
            solver=SOLVER_CLICK if has_images else SOLVER_NONE,
        ))

    if has_images:
        clickish = is_click_question(question) or any(item["type"] in GRID_KINDS for item in found)
        if clickish:
            for item in found:
                if item["type"] in GRID_KINDS or item["type"].endswith("classification"):
                    item["solver"] = SOLVER_CLICK
                    item["solvable"] = True
                    item["confidence"] = max(item["confidence"], 0.96)
                    item["cloudflyerType"] = None
            if not any(item["solver"] == SOLVER_CLICK for item in found):
                found.append(_challenge("click_select", confidence=0.93, evidence=["images+question"], solver=SOLVER_CLICK))
        elif not any(item["solver"] in {SOLVER_OCR, SOLVER_CLICK} for item in found):
            found.append(_challenge("image_to_text", confidence=0.7, evidence=["images"], solver=SOLVER_OCR))

    explicit = canonical_kind(payload.get("type") or payload.get("kind"))
    if explicit and explicit != "auto" and not any(item["type"] == explicit for item in found):
        if explicit in CF_TYPES:
            solver = SOLVER_CLICK if explicit == "recaptcha_v2" and has_images else SOLVER_CLOUDFLYER
        elif "classification" in explicit or explicit == "click_select":
            solver = SOLVER_CLICK
        elif explicit == "image_to_text":
            solver = SOLVER_CLICK if is_click_question(question) else SOLVER_OCR
        else:
            solver = SOLVER_NONE
        found.insert(0, _challenge(
            explicit,
            confidence=0.99,
            sitekey=(keys[0] if keys else ""),
            evidence=["explicit-type"],
            solver=solver,
            cloudflyer_type=CF_TYPES.get(explicit),
        ))

    found.sort(key=lambda item: item["confidence"], reverse=True)
    return {
        "challenges": found,
        "primary": found[0] if found else None,
        "siteKeys": keys,
        "url": str(payload.get("url") or payload.get("websiteURL") or ""),
    }


def kind_from_task(raw_type: str, task: dict[str, Any]) -> dict[str, Any]:
    detected = detect({**task, "type": raw_type})
    if detected.get("primary"):
        return detected
    if raw_type:
        return {
            "challenges": [],
            "primary": _challenge(
                canonical_kind(raw_type) or norm_type(raw_type) or "unknown",
                confidence=0.2,
                evidence=["unknown-type"],
                solver=SOLVER_NONE,
            ),
            "siteKeys": _sitekeys(task, _blob(task)),
            "url": str(task.get("url") or task.get("websiteURL") or ""),
        }
    return detected
