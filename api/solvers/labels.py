from __future__ import annotations

from typing import Any, Iterable

COCO_NAMES = [
    "person",
    "bicycle",
    "car",
    "motorcycle",
    "airplane",
    "bus",
    "train",
    "truck",
    "boat",
    "traffic light",
    "fire hydrant",
    "stop sign",
    "parking meter",
    "bench",
    "bird",
    "cat",
    "dog",
    "horse",
    "sheep",
    "cow",
    "elephant",
    "bear",
    "zebra",
    "giraffe",
    "backpack",
    "umbrella",
    "handbag",
    "tie",
    "suitcase",
    "frisbee",
    "skis",
    "snowboard",
    "sports ball",
    "kite",
    "baseball bat",
    "baseball glove",
    "skateboard",
    "surfboard",
    "tennis racket",
    "bottle",
    "wine glass",
    "cup",
    "fork",
    "knife",
    "spoon",
    "bowl",
    "banana",
    "apple",
    "sandwich",
    "orange",
    "broccoli",
    "carrot",
    "hot dog",
    "pizza",
    "donut",
    "cake",
    "chair",
    "couch",
    "potted plant",
    "bed",
    "dining table",
    "toilet",
    "tv",
    "laptop",
    "mouse",
    "remote",
    "keyboard",
    "cell phone",
    "microwave",
    "oven",
    "toaster",
    "sink",
    "refrigerator",
    "book",
    "clock",
    "vase",
    "scissors",
    "teddy bear",
    "hair drier",
    "toothbrush",
]

COCO_INDEX = {name: idx for idx, name in enumerate(COCO_NAMES)}

# Longer keys first. Empty tuple means recognized but not solvable by YOLO.
ALIASES: dict[str, tuple[str, ...]] = {
    "traffic lights": ("traffic light",),
    "traffic light": ("traffic light",),
    "fire hydrants": ("fire hydrant",),
    "fire hydrant": ("fire hydrant",),
    "parking meters": ("parking meter",),
    "parking meter": ("parking meter",),
    "stop signs": ("stop sign",),
    "stop sign": ("stop sign",),
    "motorcycles": ("motorcycle",),
    "motorcycle": ("motorcycle",),
    "motorbikes": ("motorcycle",),
    "motorbike": ("motorcycle",),
    "bicycles": ("bicycle",),
    "bicycle": ("bicycle",),
    "airplanes": ("airplane",),
    "airplane": ("airplane",),
    "aeroplanes": ("airplane",),
    "aeroplane": ("airplane",),
    "vehicles": ("car", "truck", "bus"),
    "vehicle": ("car", "truck", "bus"),
    "pedestrians": ("person",),
    "pedestrian": ("person",),
    "people": ("person",),
    "person": ("person",),
    "crosswalks": (),
    "crosswalk": (),
    "chimneys": (),
    "chimney": (),
    "bridges": (),
    "bridge": (),
    "mountains": (),
    "mountain": (),
    "palm trees": (),
    "palm tree": (),
    "tractors": ("truck",),
    "tractor": ("truck",),
    "taxis": ("car",),
    "taxi": ("car",),
    "stairs": (),
    "stairway": (),
    "stair": (),
    "buses": ("bus",),
    "bus": ("bus",),
    "trucks": ("truck",),
    "truck": ("truck",),
    "cars": ("car",),
    "car": ("car",),
    "boats": ("boat",),
    "boat": ("boat",),
    "bikes": ("bicycle",),
    "bike": ("bicycle", "motorcycle"),
    "hydrant": ("fire hydrant",),
    "hydrants": ("fire hydrant",),
    "红绿灯": ("traffic light",),
    "交通灯": ("traffic light",),
    "信号灯": ("traffic light",),
    "消防栓": ("fire hydrant",),
    "消火栓": ("fire hydrant",),
    "人行横道": (),
    "斑马线": (),
    "停车咪表": ("parking meter",),
    "停车计时器": ("parking meter",),
    "停车收费表": ("parking meter",),
    "停止标志": ("stop sign",),
    "停车标志": ("stop sign",),
    "摩托车": ("motorcycle",),
    "电摩": ("motorcycle",),
    "自行车": ("bicycle",),
    "单车": ("bicycle",),
    "脚踏车": ("bicycle",),
    "飞机": ("airplane",),
    "轿车": ("car",),
    "小车": ("car",),
    "汽车": ("car",),
    "车辆": ("car", "truck", "bus"),
    "出租车": ("car",),
    "的士": ("car",),
    "公交车": ("bus",),
    "公共汽车": ("bus",),
    "巴士": ("bus",),
    "卡车": ("truck",),
    "货车": ("truck",),
    "拖拉机": ("truck",),
    "行人": ("person",),
"traffic signals": ("traffic light",),
    "signal lights": ("traffic light",),
    "lorries": ("truck",),
    "lorry": ("truck",),
    "pickups": ("truck",),
    "pickup": ("truck",),
    "suvs": ("car",),
    "suv": ("car",),
    "minivans": ("car",),
    "minivan": ("car",),
    "coaches": ("bus",),
    "coach": ("bus",),
    "seaplanes": ("airplane",),
    "seaplane": ("airplane",),
    "jets": ("airplane",),
    "jet": ("airplane",),
    "trains": ("train",),
    "umbrellas": ("umbrella",),
    "backpacks": ("backpack",),
    "suitcases": ("suitcase",),
    "handbags": ("handbag",),
    "chairs": ("chair",),
    "birds": ("bird",),
    "cats": ("cat",),
    "dogs": ("dog",),
    "horses": ("horse",),
    "cows": ("cow",),
    "elephants": ("elephant",),
    "bears": ("bear",),
    "zebras": ("zebra",),
    "giraffes": ("giraffe",),
    "交通信号灯": ("traffic light",),
    "红灯": ("traffic light",),
    "大巴": ("bus",),
    "客车": ("bus",),
    "皮卡": ("truck",),
    "面包车": ("car",),
    "越野车": ("car",),
    "火车": ("train",),
    "高铁": ("train",),
    "列车": ("train",),
    "路人": ("person",),
    "雨伞": ("umbrella",),
    "伞": ("umbrella",),
    "双肩包": ("backpack",),
    "背包": ("backpack",),
    "手提包": ("handbag",),
    "行李箱": ("suitcase",),
    "箱子": ("suitcase",),
    "马": ("horse",),
    "牛": ("cow",),
    "羊": ("sheep",),
    "大象": ("elephant",),
    "熊": ("bear",),
    "斑马": ("zebra",),
    "长颈鹿": ("giraffe",),
    "帆船": ("boat",),
    "小船": ("boat",),
    "游艇": ("boat",),
    "摩托": ("motorcycle",),
    "楼梯": (),
    "台阶": (),
    "烟囱": (),
    "桥梁": (),
    "大桥": (),
    "桥": (),
    "山脉": (),
    "山": (),
    "棕榈树": (),
    "船": ("boat",),
    "船只": ("boat",),
    "狗": ("dog",),
    "猫": ("cat",),
    "鸟": ("bird",),
    "椅子": ("chair",),
    "长椅": ("bench",),
    "长凳": ("bench",),
    "bench": ("bench",),
    "benches": ("bench",),
}

CLICK_HINTS = (
    "选出",
    "選擇",
    "选择所有",
    "点选",
    "點選",
    "select all",
    "click all",
    "images with",
    "pictures of",
    "containing",
    "包含",
    "请选出",
    "請選出",
)

STRIP_PATTERNS = (
    "aws:grid:",
    "aws:grid",
    "please click each image containing",
    "please select all squares with",
    "select all images with a",
    "select all images with",
    "select all squares with",
    "select all pictures of",
    "click on all images that contain",
    "click all images with",
    "images containing",
    "pictures containing",
    "选出所有包含",
    "选出所有的",
    "选出所有",
    "選擇所有包含",
    "選擇所有",
    "选择所有包含",
    "选择所有",
    "请选出所有包含",
    "请选出所有",
    "請選出所有包含",
    "請選出所有",
    "点选所有",
    "點選所有",
    "的图片",
    "的圖片",
    "的方块",
    "的方塊",
    "pictures of a",
    "pictures of",
    "images of a",
    "images of",
)


def has_image_payload(payload: dict[str, Any]) -> bool:
    for key in ("images", "queries", "photos", "tiles", "body", "image"):
        value = payload.get(key)
        if value:
            return True
    return False


def question_text(payload: dict[str, Any]) -> str:
    for key in ("question", "instructions", "instruction", "prompt", "caption", "object", "class", "label"):
        value = payload.get(key)
        if value:
            return str(value)
    return ""


def is_click_question(text: str) -> bool:
    raw = (text or "").strip()
    if not raw:
        return False
    low = raw.lower()
    if any(hint in raw or hint in low for hint in CLICK_HINTS):
        return True
    parsed = parse_question(raw)
    return bool(parsed["query"])


def parse_question(text: str) -> dict[str, Any]:
    raw = (text or "").strip()
    normalized = _normalize(raw)
    names: list[str] = []
    unsupported = ""
    query = ""

    for alias, mapped in sorted(ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        alias_l = alias.lower()
        if alias_l in normalized or alias in raw:
            query = alias
            if mapped:
                names = list(mapped)
            else:
                unsupported = alias
            break

    if not names and not unsupported:
        for name in COCO_NAMES:
            if name in normalized:
                query = name
                names = [name]
                break

    indexes = [COCO_INDEX[name] for name in names if name in COCO_INDEX]
    return {
        "raw": raw,
        "normalized": normalized,
        "query": query or normalized,
        "names": names,
        "indexes": indexes,
        "unsupported": unsupported,
    }


def _normalize(text: str) -> str:
    low = text.strip().lower().replace("_", " ").replace("-", " ")
    for pattern in sorted(STRIP_PATTERNS, key=len, reverse=True):
        low = low.replace(pattern, " ")
    return " ".join(low.split())


def collect_image_payloads(task: dict[str, Any]) -> list[Any]:
    images: list[Any] = []
    for key in ("images", "queries", "photos", "tiles"):
        value = task.get(key)
        if value is None:
            continue
        images.extend(_as_items(value))
    if images:
        return images
    for key in ("body", "image"):
        value = task.get(key)
        if value:
            return _as_items(value)
    return []


def _as_items(value: Any) -> list[Any]:
    if value is None or value is False:
        return []
    if isinstance(value, (bytes, str, dict)):
        return [value]
    if isinstance(value, Iterable):
        return [item for item in value if item is not None and item is not False]
    return [value]
