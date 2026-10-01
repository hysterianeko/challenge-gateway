from __future__ import annotations

import base64
import io
import math
import threading
from pathlib import Path
from typing import Any

from solvers.labels import collect_image_payloads, parse_question, question_text

MODEL_PATH = Path(__file__).resolve().parents[1] / "models" / "yolov5n.onnx"
INPUT_SIZE = 640
DEFAULT_THRESHOLD = 0.22

_session = None
_session_lock = threading.Lock()
_input_name = "images"
_input_dtype = None


class ClickSolverError(ValueError):
    pass


def solve_click(task: dict[str, Any]) -> dict[str, Any]:
    question = question_text(task)
    parsed = parse_question(question)
    if parsed["unsupported"] and not parsed["indexes"]:
        raise ClickSolverError(
            f"已识别点选目标「{parsed['unsupported']}」，但当前 YOLO 模型还解不了这一类。"
            "目前能解汽车/公交车/卡车/自行车/摩托车/红绿灯/消防栓/船/飞机等 COCO 物体。"
        )
    if not parsed["indexes"]:
        raise ClickSolverError("无法从题目解析出要点选的目标，请传 question，例如「选出所有红绿灯」或 bus")

    tiles = _tiles_from_task(task)
    if not tiles:
        raise ClickSolverError("点选任务缺少 images / queries")

    threshold = _threshold(task)
    session = _get_session()
    scores: list[float] = []
    labels: list[str] = []
    hits: list[bool] = []
    indexes: list[int] = []

    for idx, tile in enumerate(tiles):
        score, label = _tile_match(session, tile, parsed["indexes"], parsed["names"])
        scores.append(round(score, 4))
        labels.append(label)
        hit = score >= threshold
        hits.append(hit)
        if hit:
            indexes.append(idx)

    return {
        "type": "click_select",
        "question": question,
        "target": parsed["names"],
        "objects": indexes,
        "indexes": indexes,
        "hasObject": hits,
        "scores": scores,
        "labels": labels,
        "threshold": threshold,
        "count": len(tiles),
    }


def _threshold(task: dict[str, Any]) -> float:
    raw = task.get("threshold") or task.get("confidence") or DEFAULT_THRESHOLD
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return DEFAULT_THRESHOLD
    return min(max(value, 0.05), 0.9)


def _tiles_from_task(task: dict[str, Any]) -> list:
    payloads = collect_image_payloads(task)
    images = [_load_image(item) for item in payloads]
    if not images:
        return []

    rows, cols = _grid_size(task, len(images))
    if len(images) == 1 and rows > 1 and cols > 1:
        return _split_grid(images[0], rows, cols)
    return images


def _grid_size(task: dict[str, Any], count: int) -> tuple[int, int]:
    rows = _as_int(task.get("rows") or task.get("row"))
    cols = _as_int(task.get("columns") or task.get("cols") or task.get("column"))
    grid = _as_int(task.get("gridSize") or task.get("grid"))
    if rows and cols:
        return rows, cols
    if grid:
        return grid, grid
    if count == 1:
        return 1, 1
    root = int(math.isqrt(count))
    if root * root == count:
        return root, root
    return 1, count


def _as_int(value: Any) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return 0
    return number if number > 0 else 0


def _split_grid(image, rows: int, cols: int) -> list:
    width, height = image.size
    tile_w = width // cols
    tile_h = height // rows
    tiles = []
    for row in range(rows):
        for col in range(cols):
            box = (col * tile_w, row * tile_h, (col + 1) * tile_w, (row + 1) * tile_h)
            tiles.append(image.crop(box))
    return tiles


def _load_image(data: Any):
    from PIL import Image
    if isinstance(data, Image.Image):
        return data.convert("RGB")
    if isinstance(data, dict):
        data = data.get("base64") or data.get("body") or data.get("image") or data.get("data")
    if isinstance(data, bytes):
        raw = data
    else:
        text = str(data).strip()
        if "," in text and text.startswith("data:"):
            text = text.split(",", 1)[1]
        try:
            raw = base64.b64decode(text)
        except Exception as exc:
            raise ClickSolverError("invalid base64 image") from exc
    try:
        from PIL import Image
        return Image.open(io.BytesIO(raw)).convert("RGB")
    except Exception as exc:
        raise ClickSolverError("invalid image payload") from exc


def _get_session():
    global _session, _input_name, _input_dtype
    if _session is not None:
        return _session
    with _session_lock:
        if _session is not None:
            return _session
        if not MODEL_PATH.is_file():
            raise ClickSolverError(f"click model missing: {MODEL_PATH}")
        try:
            import numpy as np
            import onnxruntime as ort
        except Exception as exc:
            raise ClickSolverError("onnxruntime is not available") from exc
        _session = ort.InferenceSession(str(MODEL_PATH), providers=["CPUExecutionProvider"])
        model_input = _session.get_inputs()[0]
        _input_name = model_input.name
        _input_dtype = np.float16 if "float16" in (model_input.type or "") else np.float32
        return _session


def _tile_match(session, image, class_ids: list[int], names: list[str]) -> tuple[float, str]:
    prepared = _letterbox(_upscale(image))
    output = session.run(None, {_input_name: prepared})[0]
    pred = _as_predictions(output)
    if pred.size == 0:
        return 0.0, ""

    objectness = pred[:, 4:5]
    classes = pred[:, 5:]
    conf = objectness * classes if classes.shape[1] >= 80 else classes
    best_score = 0.0
    best_name = names[0] if names else ""
    for class_id, name in zip(class_ids, names):
        if class_id < 0 or class_id >= conf.shape[1]:
            continue
        score = float(conf[:, class_id].max())
        if score > best_score:
            best_score = score
            best_name = name
    return best_score, best_name


def _upscale(image):
    from PIL import Image as PILImage
    width, height = image.size
    shortest = min(width, height)
    if shortest >= 160:
        return image
    scale = 160 / max(shortest, 1)
    return image.resize((max(1, int(width * scale)), max(1, int(height * scale))), PILImage.BICUBIC)


def _letterbox(image, size: int = INPUT_SIZE, fill: int = 114):
    import numpy as np
    from PIL import Image

    width, height = image.size
    scale = min(size / height, size / width)
    new_w = max(1, int(round(width * scale)))
    new_h = max(1, int(round(height * scale)))
    resized = image.resize((new_w, new_h), Image.BILINEAR)
    canvas = Image.new("RGB", (size, size), (fill, fill, fill))
    canvas.paste(resized, ((size - new_w) // 2, (size - new_h) // 2))
    dtype = _input_dtype if _input_dtype is not None else np.float32
    arr = (np.asarray(canvas).astype("float32") / 255.0).astype(dtype)
    return arr.transpose(2, 0, 1)[None]


def _as_predictions(output) -> Any:
    import numpy as np

    pred = np.asarray(output)
    pred = np.squeeze(pred)
    if pred.ndim == 3:
        pred = pred[0]
    if pred.ndim != 2:
        return np.empty((0, 85), dtype="float32")
    if pred.shape[0] in (84, 85) and pred.shape[1] > pred.shape[0]:
        pred = pred.T
    if pred.shape[1] < 6:
        return np.empty((0, 85), dtype="float32")
    return pred
