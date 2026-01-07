import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any


Color = Tuple[int, int, int, int]  # RGBA
Box = Tuple[int, int, int, int]  # x, y, width, height


@dataclass
class BackgroundConfig:
    kind: str = "color"  # color | image | gradient
    value: str = "#ffffff"
    opacity: float = 1.0
    gradient_type: Optional[str] = None  # linear | radial
    gradient_stops: Optional[List[Dict[str, Any]]] = field(default_factory=list)  # [{"color": "#ff0000", "position": 0.0}, ...]
    gradient_angle: Optional[float] = None  # degrees for linear (0-360, 0=top to bottom)
    gradient_center: Optional[Tuple[float, float]] = None  # [x, y] as 0-1 for radial


@dataclass
class Slot:
    """Defines an image slot (e.g., screenshot) inside the template."""

    key: str
    box: Box
    radius: int = 0
    fit: str = "cover"  # cover | contain
    padding: int = 0
    align_x: str = "center"  # left | center | right
    align_y: str = "center"  # top | center | bottom
    rotation: float = 0.0  # degrees, positive = clockwise


@dataclass
class TextStyle:
    font: Optional[str] = None
    size: int = 42
    color: str = "#000000"
    align: str = "left"  # left | center | right
    max_width: Optional[int] = None
    line_spacing: float = 1.2
    stroke_width: int = 0
    stroke_fill: Optional[str] = None
    shadow: Optional[Dict[str, Any]] = None  # {offset:[x,y], color:str, blur:int}


@dataclass
class TextBlock:
    key: str  # title | subtitle | custom
    box: Box
    style: TextStyle = field(default_factory=TextStyle)


@dataclass
class TemplateDefinition:
    key: str
    name: str
    size: Tuple[int, int] = (1080, 1920)
    background: BackgroundConfig = field(default_factory=BackgroundConfig)
    slots: List[Slot] = field(default_factory=list)
    texts: List[TextBlock] = field(default_factory=list)


@dataclass
class RenderInput:
    # New-schema-only render input (CSV columns map by key)
    template_key: str
    output_name: str
    background_path: Optional[str]
    texts: Dict[str, str] = field(default_factory=dict)  # textKey -> content
    slot_paths: Dict[str, str] = field(default_factory=dict)  # slotKey -> image path


def _ensure_int_tuple(value, expected_len: int, default: Tuple[int, ...]) -> Tuple[int, ...]:
    if not isinstance(value, (list, tuple)) or len(value) != expected_len:
        return default
    return tuple(int(v) for v in value)


def _parse_color(value: str) -> str:
    if isinstance(value, str) and value.startswith("#"):
        return value
    return "#000000"


def load_template_from_json(data: Dict[str, Any]) -> TemplateDefinition:
    key = data.get("key") or data.get("id") or "template"
    size = _ensure_int_tuple(data.get("size"), 2, (1080, 1920))

    bg_raw = data.get("background", {}) or {}
    stops_raw = bg_raw.get("gradient_stops", []) or []
    gradient_center_raw = bg_raw.get("gradient_center")
    gradient_center = None
    if gradient_center_raw and isinstance(gradient_center_raw, (list, tuple)) and len(gradient_center_raw) >= 2:
        gradient_center = (float(gradient_center_raw[0]), float(gradient_center_raw[1]))
    background = BackgroundConfig(
        kind=bg_raw.get("kind", "color"),
        value=bg_raw.get("value", "#ffffff"),
        opacity=float(bg_raw.get("opacity", 1.0)),
        gradient_type=bg_raw.get("gradient_type"),
        gradient_stops=stops_raw if isinstance(stops_raw, list) else [],
        gradient_angle=float(bg_raw["gradient_angle"]) if bg_raw.get("gradient_angle") is not None else None,
        gradient_center=gradient_center,
    )

    slots = []
    for slot in data.get("slots", []) or []:
        box = _ensure_int_tuple(slot.get("box"), 4, (0, 0, size[0], size[1]))
        slots.append(
            Slot(
                key=str(slot.get("key", f"slot-{len(slots)}")),
                box=box,
                radius=int(slot.get("radius", 0)),
                fit=slot.get("fit", "cover"),
                padding=int(slot.get("padding", 0)),
                align_x=slot.get("align_x", "center"),
                align_y=slot.get("align_y", "center"),
                rotation=float(slot.get("rotation", 0) or 0),
            )
        )

    texts = []
    for text in data.get("texts", []) or []:
        box = _ensure_int_tuple(text.get("box"), 4, (0, 0, size[0], 200))
        style_raw = text.get("style", {}) or {}
        style = TextStyle(
            font=style_raw.get("font"),
            size=int(style_raw.get("size", 42)),
            color=_parse_color(style_raw.get("color", "#000000")),
            align=style_raw.get("align", "left"),
            max_width=style_raw.get("max_width"),
            line_spacing=float(style_raw.get("line_spacing", 1.2)),
            stroke_width=int(style_raw.get("stroke_width", 0)),
            stroke_fill=style_raw.get("stroke_fill"),
            shadow=style_raw.get("shadow"),
        )
        texts.append(TextBlock(key=str(text.get("key", "text")), box=box, style=style))

    return TemplateDefinition(
        key=key,
        name=data.get("name", key),
        size=size,
        background=background,
        slots=slots,
        texts=texts,
    )


def load_template_from_file(path: Path) -> TemplateDefinition:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return load_template_from_json(data)


def render_input_from_row(row: Dict[str, Any]) -> RenderInput:
    def _clean_col(s: str) -> str:
        # Strip whitespace and common zero-width/BOM characters injected by Excel/WPS exports.
        # - U+FEFF: BOM / zero width no-break space
        # - U+200B/200C/200D: zero width space/joiners
        # - U+2060: word joiner
        return (s or "").strip().lstrip("\ufeff\u200b\u200c\u200d\u2060")

    def _get_case_insensitive(keys: List[str]) -> Optional[Any]:
        for k in keys:
            if k in row:
                return row.get(k)
        lower_map = {_clean_col(str(k)).lower(): k for k in row.keys()}
        for k in keys:
            original = lower_map.get(_clean_col(str(k)).lower())
            if original is not None:
                return row.get(original)
        return None

    def _as_str(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        return str(value).strip()

    row = row or {}

    # Strict new-schema validation: no legacy columns, no unknown columns.
    legacy_cols = {
        "title",
        "subtitle",
        "background",
        "screenshots",
        "screenshot",
        "template",
        "layout",
        "layout_key",
        "output",
    }
    allowed_reserved = {"template_key", "output_name", "background_path"}

    lower_cols = {_clean_col(str(k)).lower() for k in row.keys() if k is not None and _clean_col(str(k))}
    offending_legacy = sorted(c for c in lower_cols if c in legacy_cols)
    if offending_legacy:
        raise ValueError(
            "CSV 使用了旧 schema 列名（已不再支持）："
            + ", ".join(offending_legacy)
            + "。请改为新 schema：template_key, output_name, background_path, text.<key>, slot.<key>"
        )

    unknown = sorted(
        c
        for c in lower_cols
        if c not in allowed_reserved and not (c.startswith("text.") or c.startswith("slot."))
    )
    if unknown:
        raise ValueError(
            "CSV 包含不支持的列名："
            + ", ".join(unknown)
            + "。仅支持：template_key, output_name, background_path, text.<key>, slot.<key>"
        )

    # 1) key-addressable mappings
    texts: Dict[str, str] = {}
    slot_paths: Dict[str, str] = {}
    for col, raw in row.items():
        if col is None:
            continue
        col_str = _clean_col(str(col))
        if not col_str:
            continue
        low = col_str.lower()
        if low.startswith("text."):
            key = col_str.split(".", 1)[1].strip()
            if key:
                texts[key] = _as_str(raw)
        elif low.startswith("slot."):
            key = col_str.split(".", 1)[1].strip()
            if key:
                slot_paths[key] = _as_str(raw)

    # 2) reserved columns (new schema)
    template_key = _as_str(_get_case_insensitive(["template_key"]))
    if not template_key:
        raise ValueError("CSV 缺少必填列 template_key 或该单元格为空")

    output_name = _as_str(_get_case_insensitive(["output_name"]))
    if not output_name:
        raise ValueError("CSV 缺少必填列 output_name 或该单元格为空")

    background_path = _as_str(_get_case_insensitive(["background_path"])) or None

    return RenderInput(
        template_key=template_key,
        output_name=output_name,
        background_path=background_path,
        texts=texts,
        slot_paths=slot_paths,
    )

