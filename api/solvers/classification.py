import base64
import io
import os
import re
from typing import Any

from PIL import Image
from PIL import ImageFilter


OCR_ENSEMBLE_ENABLED = (
    os.environ.get("OCR_ENSEMBLE_ENABLED", "true").strip().lower() == "true"
)
OCR_ENSEMBLE_MAX_ALTERNATIVES = max(
    0, int(os.environ.get("OCR_ENSEMBLE_MAX_ALTERNATIVES", "3"))
)


def _load_image(data: str) -> Image.Image:
    raw = data
    if "," in raw and raw.strip().startswith("data:"):
        raw = raw.split(",", 1)[1]
    try:
        decoded = base64.b64decode(raw)
    except Exception as exc:
        raise ValueError("invalid base64 image") from exc
    return Image.open(io.BytesIO(decoded)).convert("RGB")


def _normalize_text(value: Any) -> str:
    text = re.sub(r"\s+", "", str(value or "")).strip()
    return (
        text.replace("\u00d7", "x")
        .replace("\u2212", "-")
        .replace("\uff0b", "+")
    )


def _orange_mask(image: Image.Image) -> Image.Image:
    pixels = []
    for red, green, blue in image.getdata():
        is_orange = red - green > 45 and red - blue > 45 and green < 220
        pixels.append(0 if is_orange else 255)
    mask = Image.new("L", image.size)
    mask.putdata(pixels)
    return mask


def _preprocessed_image(image: Image.Image) -> Image.Image:
    """Remove thin orange interference while retaining the glyph strokes."""
    mask = _orange_mask(image)
    opened = mask.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3))
    width, height = opened.size
    top = max(0, round(height * 0.14))
    bottom = min(height, round(height * 0.82))
    cropped = opened.crop((0, top, width, bottom))
    return cropped.resize(
        (width * 4, (bottom - top) * 4),
        Image.Resampling.NEAREST,
    ).convert("RGB")


def _is_euserv_task(task: dict[str, Any]) -> bool:
    haystack = " ".join(
        str(task.get(key) or "")
        for key in ("websiteURL", "url", "question", "page")
    )
    return "euserv" in haystack.lower()


def _encoded_png(image: Image.Image) -> bytes:
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def _classify_one(
    image: Image.Image,
    ocr: Any,
    beta_ocr: Any = None,
    ensemble: bool = False,
) -> tuple[str, list[str]]:
    """Return a primary OCR result plus a small, ordered candidate list."""
    variants = [("raw", image)]
    if ensemble:
        variants.append(("preprocessed", _preprocessed_image(image)))

    candidates: list[str] = []
    for _name, variant in variants:
        try:
            text = _normalize_text(ocr.classification(_encoded_png(variant)))
        except Exception:
            continue
        if text and text not in candidates:
            candidates.append(text)

    if ensemble and beta_ocr is not None:
        for _name, variant in variants:
            try:
                text = _normalize_text(beta_ocr.classification(_encoded_png(variant)))
            except Exception:
                continue
            if text and text not in candidates:
                candidates.append(text)

    if not candidates:
        raise ValueError("OCR returned no text")
    return candidates[0], candidates[1 : 1 + OCR_ENSEMBLE_MAX_ALTERNATIVES]


def classify_images(task: dict[str, Any]) -> dict[str, Any]:
    """Read characters from images with ddddocr.

    EUserv's orange CAPTCHA has thin interference lines. For that task only,
    return a bounded set of OCR candidates from the default and beta models so
    the caller can validate them against the same server-side session.
    """
    question = str(task.get("question") or task.get("websiteURL") or "")
    images = task.get("images") or task.get("queries") or []
    if isinstance(images, str):
        images = [images]
    if not images:
        body = task.get("body") or task.get("image")
        if body:
            images = [body]
    if not images:
        raise ValueError("classification task missing images")

    try:
        import ddddocr
    except Exception as exc:
        raise RuntimeError("ddddocr is not available") from exc

    ensemble = OCR_ENSEMBLE_ENABLED and _is_euserv_task(task)
    ocr = ddddocr.DdddOcr(show_ad=False)
    beta_ocr = None
    if ensemble:
        try:
            beta_ocr = ddddocr.DdddOcr(show_ad=False, beta=True)
        except Exception:
            beta_ocr = None

    texts = []
    alternatives = []
    for item in images:
        image = _load_image(item)
        primary, candidates = _classify_one(image, ocr, beta_ocr, ensemble)
        texts.append(primary)
        alternatives.append(candidates)

    if len(texts) == 1:
        return {
            "text": texts[0],
            "alternatives": alternatives[0],
            "objects": [texts[0], *alternatives[0]],
            "question": question,
        }
    return {"text": texts, "objects": texts, "question": question}
