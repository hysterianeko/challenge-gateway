import base64
import io
from typing import Any

from PIL import Image


def _load_image(data: str) -> Image.Image:
    raw = data
    if "," in raw and raw.strip().startswith("data:"):
        raw = raw.split(",", 1)[1]
    try:
        decoded = base64.b64decode(raw)
    except Exception as exc:
        raise ValueError("invalid base64 image") from exc
    return Image.open(io.BytesIO(decoded)).convert("RGB")


def classify_images(task: dict[str, Any]) -> dict[str, Any]:
    """Read characters from images with ddddocr. Click-select grids go to solvers.click."""
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

    ocr = ddddocr.DdddOcr(show_ad=False)
    texts = []
    for item in images:
        image = _load_image(item)
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        texts.append(ocr.classification(buf.getvalue()))

    if len(texts) == 1:
        return {"text": texts[0], "objects": texts, "question": question}
    return {"text": texts, "objects": texts, "question": question}
