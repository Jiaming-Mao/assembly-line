import json
from pathlib import Path
from typing import Dict, List, Optional

from .models import TemplateDefinition, load_template_from_file, load_template_from_json


class TemplateRegistry:
    def __init__(self):
        self._templates: Dict[str, TemplateDefinition] = {}
        self.template_dir: Optional[Path] = None

    def clear(self):
        self._templates = {}

    def load_dir(self, directory: Path) -> None:
        self.template_dir = directory
        if not directory.exists():
            return
        for path in sorted(directory.glob("*.json")):
            try:
                template = load_template_from_file(path)
                self._templates[template.key] = template
            except Exception as exc:
                print(f"[template] failed to load {path}: {exc}")

    def load_with_default(self, directory: Path) -> None:
        """Load templates; if none found, write and register a default template."""
        self.clear()
        self.load_dir(directory)
        if not self._templates:
            directory.mkdir(parents=True, exist_ok=True)
            default = default_template()
            self.save_template(default, directory / f"{default.key}.json")

    def import_json(self, json_path: Path) -> TemplateDefinition:
        template = load_template_from_file(json_path)
        self._templates[template.key] = template
        return template

    def add_from_dict(self, data: dict) -> TemplateDefinition:
        template = load_template_from_json(data)
        self._templates[template.key] = template
        return template

    def save_template(self, template: TemplateDefinition, target_path: Optional[Path] = None) -> Path:
        directory = target_path.parent if target_path else self.template_dir
        if directory is None:
            raise ValueError("template directory not set")
        directory.mkdir(parents=True, exist_ok=True)
        path = target_path or directory / f"{template.key}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(template_to_dict(template), f, ensure_ascii=False, indent=2)
        self._templates[template.key] = template
        return path

    def get(self, key: str) -> Optional[TemplateDefinition]:
        return self._templates.get(key)

    def all(self) -> List[TemplateDefinition]:
        return list(self._templates.values())

    def keys(self) -> List[str]:
        return list(self._templates.keys())


def template_to_dict(template: TemplateDefinition) -> dict:
    bg_dict = {
        "kind": template.background.kind,
        "value": template.background.value,
        "opacity": template.background.opacity,
    }
    if template.background.gradient_type:
        bg_dict["gradient_type"] = template.background.gradient_type
        bg_dict["gradient_stops"] = template.background.gradient_stops
        if template.background.gradient_angle is not None:
            bg_dict["gradient_angle"] = template.background.gradient_angle
        if template.background.gradient_center:
            bg_dict["gradient_center"] = [template.background.gradient_center[0], template.background.gradient_center[1]]
    
    return {
        "key": template.key,
        "name": template.name,
        "size": [template.size[0], template.size[1]],
        "background": bg_dict,
        "slots": [
            {
                "key": slot.key,
                "box": list(slot.box),
                "radius": slot.radius,
                "fit": slot.fit,
                "padding": slot.padding,
                "align_x": slot.align_x,
                "align_y": slot.align_y,
                "rotation": slot.rotation,
            }
            for slot in template.slots
        ],
        "texts": [
            {
                "key": text.key,
                "box": list(text.box),
                "style": {
                    "font": text.style.font,
                    "size": text.style.size,
                    "color": text.style.color,
                    "align": text.style.align,
                    "max_width": text.style.max_width,
                    "line_spacing": text.style.line_spacing,
                    "stroke_width": text.style.stroke_width,
                    "stroke_fill": text.style.stroke_fill,
                    "shadow": text.style.shadow,
                },
            }
            for text in template.texts
        ],
    }


def default_template() -> TemplateDefinition:
    data = {
        "key": "default",
        "name": "Default Cover",
        "size": [1080, 1920],
        "background": {"kind": "color", "value": "#f5f5f5", "opacity": 1},
        "slots": [
            {"key": "screenshot-1", "box": [90, 420, 900, 1080], "radius": 32, "fit": "cover", "padding": 0, "align_x": "center", "align_y": "center"},
        ],
        "texts": [
            {"key": "title", "box": [90, 120, 900, 180], "style": {"size": 64, "color": "#111111", "align": "left"}},
            {"key": "subtitle", "box": [90, 280, 900, 100], "style": {"size": 36, "color": "#444444", "align": "left"}},
        ],
    }
    return load_template_from_json(data)

