from __future__ import annotations

import csv
import json
import tkinter as tk
import sys
from copy import deepcopy
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable, Optional, Tuple

from PIL import ImageTk

# Allow running as `python app/main.py`
if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parent.parent))

from .models import RenderInput, load_template_from_json, render_input_from_row
from .render import build_preview, render_to_file
from .templates import TemplateRegistry, default_template, template_to_dict


ROOT_DIR = Path(__file__).resolve().parent.parent
APP_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = APP_DIR / "templates"
OUTPUT_DIR = ROOT_DIR / "output"


class TemplateEditor(tk.Toplevel):
    """Lightweight visual editor for template slots and text blocks."""

    def __init__(self, master, template_data: dict, registry: TemplateRegistry, on_save: Callable):
        super().__init__(master)
        self.title("Template Editor")
        self.registry = registry
        self.on_save = on_save
        self.geometry("1000x700")
        self.resizable(True, True)

        self.canvas_w = 420
        self.canvas_h = 640

        self.state = deepcopy(template_data)
        self.selected: Optional[Tuple[str, int]] = None  # ("slot"/"text", index)

        self._build_ui()
        self.redraw()

    # UI ---------------------------------------------------------------------
    def _build_ui(self):
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        left = ttk.Frame(self, padding=8)
        left.grid(row=0, column=0, sticky="ns")

        center = ttk.Frame(self, padding=8)
        center.grid(row=0, column=1, sticky="nsew")
        center.columnconfigure(0, weight=1)
        center.rowconfigure(0, weight=1)

        right = ttk.Frame(self, padding=8)
        right.grid(row=0, column=2, sticky="ns")

        # Global settings
        ttk.Label(left, text="Key").grid(row=0, column=0, sticky="w")
        self.key_var = tk.StringVar(value=self.state.get("key", "template"))
        ttk.Entry(left, textvariable=self.key_var, width=20).grid(row=0, column=1)

        ttk.Label(left, text="Name").grid(row=1, column=0, sticky="w")
        self.name_var = tk.StringVar(value=self.state.get("name", "Template"))
        ttk.Entry(left, textvariable=self.name_var, width=20).grid(row=1, column=1)

        size_frame = ttk.Frame(left)
        size_frame.grid(row=2, column=0, columnspan=2, pady=(6, 2), sticky="w")
        ttk.Label(size_frame, text="Size (w,h)").grid(row=0, column=0, sticky="w")
        self.w_var = tk.IntVar(value=self.state.get("size", [1080, 1920])[0])
        self.h_var = tk.IntVar(value=self.state.get("size", [1080, 1920])[1])
        ttk.Entry(size_frame, textvariable=self.w_var, width=7).grid(row=0, column=1, padx=2)
        ttk.Entry(size_frame, textvariable=self.h_var, width=7).grid(row=0, column=2, padx=2)

        bg_frame = ttk.Labelframe(left, text="Background", padding=6)
        bg_frame.grid(row=3, column=0, columnspan=2, pady=8, sticky="ew")
        self.bg_kind = tk.StringVar(value=self.state.get("background", {}).get("kind", "color"))
        ttk.Radiobutton(bg_frame, text="Color", variable=self.bg_kind, value="color", command=self._on_bg_kind).grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(bg_frame, text="Image", variable=self.bg_kind, value="image", command=self._on_bg_kind).grid(row=0, column=1, sticky="w")
        ttk.Radiobutton(bg_frame, text="Gradient", variable=self.bg_kind, value="gradient", command=self._on_bg_kind).grid(row=0, column=2, sticky="w")
        ttk.Label(bg_frame, text="Value").grid(row=1, column=0, sticky="w")
        self.bg_value = tk.StringVar(value=self.state.get("background", {}).get("value", "#f5f5f5"))
        ttk.Entry(bg_frame, textvariable=self.bg_value, width=18).grid(row=1, column=1, sticky="w")
        ttk.Button(bg_frame, text="Pick File", command=self._pick_bg_file).grid(row=1, column=2, padx=4)
        ttk.Label(bg_frame, text="Opacity").grid(row=2, column=0, sticky="w")
        self.bg_opacity = tk.DoubleVar(value=self.state.get("background", {}).get("opacity", 1.0))
        ttk.Scale(bg_frame, from_=0, to=1, orient="horizontal", variable=self.bg_opacity, command=lambda _: None).grid(row=2, column=1, columnspan=2, sticky="ew")
        
        # Gradient options
        self.gradient_frame = ttk.Labelframe(bg_frame, text="Gradient", padding=4)
        self.gradient_frame.grid(row=3, column=0, columnspan=3, pady=4, sticky="ew")
        ttk.Label(self.gradient_frame, text="Type").grid(row=0, column=0, sticky="w")
        self.gradient_type = tk.StringVar(value=self.state.get("background", {}).get("gradient_type", "linear"))
        ttk.Combobox(self.gradient_frame, values=["linear", "radial"], textvariable=self.gradient_type, width=10, state="readonly").grid(row=0, column=1, sticky="w", padx=2)
        ttk.Label(self.gradient_frame, text="Angle").grid(row=1, column=0, sticky="w")
        self.gradient_angle = tk.DoubleVar(value=self.state.get("background", {}).get("gradient_angle", 90.0))
        ttk.Entry(self.gradient_frame, textvariable=self.gradient_angle, width=10).grid(row=1, column=1, sticky="w", padx=2)
        ttk.Label(self.gradient_frame, text="Center (x,y 0-1)").grid(row=2, column=0, sticky="w")
        center_raw = self.state.get("background", {}).get("gradient_center", [0.5, 0.5])
        self.gradient_center_x = tk.DoubleVar(value=float(center_raw[0]) if isinstance(center_raw, (list, tuple)) and len(center_raw) >= 1 else 0.5)
        self.gradient_center_y = tk.DoubleVar(value=float(center_raw[1]) if isinstance(center_raw, (list, tuple)) and len(center_raw) >= 2 else 0.5)
        ttk.Entry(self.gradient_frame, textvariable=self.gradient_center_x, width=6).grid(row=2, column=1, sticky="w", padx=2)
        ttk.Entry(self.gradient_frame, textvariable=self.gradient_center_y, width=6).grid(row=2, column=2, sticky="w", padx=2)
        ttk.Label(self.gradient_frame, text="Stops (JSON)").grid(row=3, column=0, sticky="w")
        stops_raw = self.state.get("background", {}).get("gradient_stops", [])
        stops_str = json.dumps(stops_raw, ensure_ascii=False) if stops_raw else '[{"color":"#ff0000","position":0.0},{"color":"#0000ff","position":1.0}]'
        self.gradient_stops = tk.StringVar(value=stops_str)
        ttk.Entry(self.gradient_frame, textvariable=self.gradient_stops, width=30).grid(row=3, column=1, columnspan=2, sticky="ew")
        self._update_gradient_visibility()

        # Elements list
        ttk.Label(left, text="Elements").grid(row=4, column=0, columnspan=2, sticky="w", pady=(8, 2))
        self.listbox = tk.Listbox(left, height=12, exportselection=False)
        self.listbox.grid(row=5, column=0, columnspan=2, sticky="ew")
        self.listbox.bind("<<ListboxSelect>>", self._on_list_select)
        btn_row = ttk.Frame(left)
        btn_row.grid(row=6, column=0, columnspan=2, pady=4, sticky="ew")
        ttk.Button(btn_row, text="+ Slot", command=self._add_slot).grid(row=0, column=0, padx=2)
        ttk.Button(btn_row, text="+ Text", command=self._add_text).grid(row=0, column=1, padx=2)
        ttk.Button(btn_row, text="Normalize Keys", command=self._normalize_keys).grid(row=0, column=2, padx=2)
        ttk.Button(btn_row, text="Delete", command=self._delete_selected).grid(row=0, column=3, padx=2)

        # Canvas preview
        self.canvas = tk.Canvas(center, width=self.canvas_w, height=self.canvas_h, bg="#f0f0f0", highlightthickness=1, highlightbackground="#ccc")
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)

        # Element detail editor
        self.detail = ttk.Labelframe(right, text="Element", padding=8)
        self.detail.grid(row=0, column=0, sticky="ns")
        self.detail.columnconfigure(1, weight=1)
        ttk.Label(self.detail, text="Key").grid(row=0, column=0, sticky="w")
        self.elem_key = tk.StringVar()
        ttk.Entry(self.detail, textvariable=self.elem_key, width=20).grid(row=0, column=1, sticky="ew")
        ttk.Label(self.detail, text="CSV Column").grid(row=0, column=2, sticky="w", padx=(8, 0))
        self.csv_col_var = tk.StringVar(value="")
        ttk.Label(self.detail, textvariable=self.csv_col_var).grid(row=0, column=3, sticky="w")

        self.elem_type = tk.StringVar(value="slot")
        ttk.Label(self.detail, text="Type").grid(row=1, column=0, sticky="w")
        ttk.Label(self.detail, textvariable=self.elem_type).grid(row=1, column=1, sticky="w")

        coord_frame = ttk.Frame(self.detail)
        coord_frame.grid(row=2, column=0, columnspan=2, pady=4, sticky="ew")
        ttk.Label(coord_frame, text="x").grid(row=0, column=0)
        ttk.Label(coord_frame, text="y").grid(row=0, column=1)
        ttk.Label(coord_frame, text="w").grid(row=0, column=2)
        ttk.Label(coord_frame, text="h").grid(row=0, column=3)
        self.x_var = tk.IntVar()
        self.y_var = tk.IntVar()
        self.w_box_var = tk.IntVar()
        self.h_box_var = tk.IntVar()
        ttk.Entry(coord_frame, textvariable=self.x_var, width=6).grid(row=1, column=0, padx=2)
        ttk.Entry(coord_frame, textvariable=self.y_var, width=6).grid(row=1, column=1, padx=2)
        ttk.Entry(coord_frame, textvariable=self.w_box_var, width=6).grid(row=1, column=2, padx=2)
        ttk.Entry(coord_frame, textvariable=self.h_box_var, width=6).grid(row=1, column=3, padx=2)

        # Slot options
        slot_frame = ttk.Labelframe(self.detail, text="Slot", padding=6)
        slot_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=4)
        ttk.Label(slot_frame, text="Radius").grid(row=0, column=0, sticky="w")
        self.radius_var = tk.IntVar()
        ttk.Entry(slot_frame, textvariable=self.radius_var, width=6).grid(row=0, column=1, sticky="w")
        ttk.Label(slot_frame, text="Fit").grid(row=1, column=0, sticky="w")
        self.fit_var = tk.StringVar(value="cover")
        ttk.Combobox(slot_frame, values=["cover", "contain"], textvariable=self.fit_var, width=8, state="readonly").grid(row=1, column=1, sticky="w")
        ttk.Label(slot_frame, text="Padding").grid(row=2, column=0, sticky="w")
        self.pad_var = tk.IntVar()
        ttk.Entry(slot_frame, textvariable=self.pad_var, width=6).grid(row=2, column=1, sticky="w")
        ttk.Label(slot_frame, text="Align X").grid(row=3, column=0, sticky="w")
        self.align_x_var = tk.StringVar(value="center")
        ttk.Combobox(slot_frame, values=["left", "center", "right"], textvariable=self.align_x_var, width=8, state="readonly").grid(row=3, column=1, sticky="w")
        ttk.Label(slot_frame, text="Align Y").grid(row=4, column=0, sticky="w")
        self.align_y_var = tk.StringVar(value="center")
        ttk.Combobox(slot_frame, values=["top", "center", "bottom"], textvariable=self.align_y_var, width=8, state="readonly").grid(row=4, column=1, sticky="w")
        ttk.Label(slot_frame, text="Rotation (deg, cw+)").grid(row=5, column=0, sticky="w")
        self.rotation_var = tk.StringVar(value="0")
        ttk.Entry(slot_frame, textvariable=self.rotation_var, width=8).grid(row=5, column=1, sticky="w")

        # Text options
        text_frame = ttk.Labelframe(self.detail, text="Text", padding=6)
        text_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=4)
        ttk.Label(text_frame, text="Font file").grid(row=0, column=0, sticky="w")
        self.font_var = tk.StringVar()
        ttk.Entry(text_frame, textvariable=self.font_var, width=20).grid(row=0, column=1, sticky="w")
        ttk.Button(text_frame, text="Pick", command=self._pick_font).grid(row=0, column=2, padx=2)
        ttk.Label(text_frame, text="Size").grid(row=1, column=0, sticky="w")
        self.font_size_var = tk.IntVar(value=42)
        ttk.Entry(text_frame, textvariable=self.font_size_var, width=6).grid(row=1, column=1, sticky="w")
        ttk.Label(text_frame, text="Color").grid(row=2, column=0, sticky="w")
        self.font_color_var = tk.StringVar(value="#111111")
        ttk.Entry(text_frame, textvariable=self.font_color_var, width=10).grid(row=2, column=1, sticky="w")
        ttk.Label(text_frame, text="Align").grid(row=3, column=0, sticky="w")
        self.align_var = tk.StringVar(value="left")
        ttk.Combobox(text_frame, values=["left", "center", "right"], textvariable=self.align_var, width=8, state="readonly").grid(row=3, column=1, sticky="w")

        ttk.Button(self.detail, text="Apply Changes", command=self._apply_detail).grid(row=5, column=0, columnspan=2, pady=6, sticky="ew")
        ttk.Button(self.detail, text="Save Template", command=self._save).grid(row=6, column=0, columnspan=2, pady=6, sticky="ew")

    # Helpers ----------------------------------------------------------------
    def _scale(self):
        w = max(1, self.state.get("size", [1080, 1920])[0])
        h = max(1, self.state.get("size", [1080, 1920])[1])
        return min(self.canvas_w / w, self.canvas_h / h)

    def _boxes(self):
        slots = self.state.get("slots", [])
        texts = self.state.get("texts", [])
        return [("slot", i, slots[i]["box"]) for i in range(len(slots))] + [("text", i, texts[i]["box"]) for i in range(len(texts))]

    def redraw(self):
        self._sync_list()
        self.canvas.delete("all")
        scale = self._scale()
        w, h = self.state.get("size", [1080, 1920])
        self.canvas.create_rectangle(0, 0, w * scale, h * scale, fill="#ffffff", outline="#cccccc")

        for kind, idx, box in self._boxes():
            x, y, bw, bh = box
            cx1, cy1 = x * scale, y * scale
            cx2, cy2 = (x + bw) * scale, (y + bh) * scale
            color = "#83bff6" if kind == "slot" else "#f6c483"
            tag = f"{kind}-{idx}"
            self.canvas.create_rectangle(cx1, cy1, cx2, cy2, outline="#333333", width=2, fill=color, stipple="gray25", tags=tag)
            label = self.state[kind + "s"][idx].get("key", f"{kind}-{idx}")
            self.canvas.create_text(cx1 + 6, cy1 + 6, anchor="nw", text=label, font=("Arial", 10), tags=tag)
            if self.selected == (kind, idx):
                self.canvas.create_rectangle(cx1, cy1, cx2, cy2, outline="#ff3366", width=2)

    def _sync_list(self):
        self.listbox.delete(0, tk.END)
        for s in self.state.get("slots", []):
            self.listbox.insert(tk.END, f"[slot] {s.get('key')}")
        for t in self.state.get("texts", []):
            self.listbox.insert(tk.END, f"[text] {t.get('key')}")

    # Background -------------------------------------------------------------
    def _pick_bg_file(self):
        path = filedialog.askopenfilename(
            title="Pick background image",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.webp"), ("All files", "*")],
        )
        if path:
            self.bg_value.set(path)

    def _update_gradient_visibility(self):
        if self.bg_kind.get() == "gradient":
            self.gradient_frame.grid()
        else:
            self.gradient_frame.grid_remove()
    
    def _on_bg_kind(self):
        if self.bg_kind.get() == "color":
            if not self.bg_value.get().startswith("#"):
                self.bg_value.set("#f5f5f5")
        self._update_gradient_visibility()

    # Element ops ------------------------------------------------------------
    def _add_slot(self):
        size = self.state.get("size", [1080, 1920])
        self.state.setdefault("slots", []).append({"key": f"slot-{len(self.state.get('slots', [])) + 1}", "box": [50, 50, size[0] // 2, size[1] // 3], "radius": 24, "fit": "cover", "padding": 0, "align_x": "center", "align_y": "center", "rotation": 0})
        self.selected = ("slot", len(self.state["slots"]) - 1)
        self.redraw()
        self._load_detail()

    def _add_text(self):
        size = self.state.get("size", [1080, 1920])
        default_h = 80
        next_idx = len(self.state.get("texts", [])) + 1
        self.state.setdefault("texts", []).append(
            {
                "key": f"text-{next_idx}",
                "box": [60, 60, size[0] // 2, default_h],
                "style": {"size": 32, "color": "#111111", "align": "left"},
            }
        )
        self.selected = ("text", len(self.state["texts"]) - 1)
        self.redraw()
        self._load_detail()

    def _delete_selected(self):
        if not self.selected:
            return
        kind, idx = self.selected
        self.state[kind + "s"].pop(idx)
        self.selected = None
        self.redraw()
        self._load_detail()

    def _on_list_select(self, event):
        idx = self.listbox.curselection()
        if not idx:
            return
        idx = idx[0]
        slots_len = len(self.state.get("slots", []))
        if idx < slots_len:
            self.selected = ("slot", idx)
        else:
            self.selected = ("text", idx - slots_len)
        self._load_detail()
        self.redraw()

    def _load_detail(self):
        if not self.selected:
            self.elem_key.set("")
            self.csv_col_var.set("")
            return
        kind, idx = self.selected
        item = self.state[kind + "s"][idx]
        self.elem_type.set(kind)
        current_key = item.get("key", "")
        self.elem_key.set(current_key)
        if kind == "slot":
            self.csv_col_var.set(f"slot.{current_key}" if current_key else "")
        else:
            self.csv_col_var.set(f"text.{current_key}" if current_key else "")
        x, y, w, h = item.get("box", [0, 0, 100, 100])
        self.x_var.set(x)
        self.y_var.set(y)
        self.w_box_var.set(w)
        self.h_box_var.set(h)
        if kind == "slot":
            self.radius_var.set(item.get("radius", 0))
            self.fit_var.set(item.get("fit", "cover"))
            self.pad_var.set(item.get("padding", 0))
            self.align_x_var.set(item.get("align_x", "center"))
            self.align_y_var.set(item.get("align_y", "center"))
            self.rotation_var.set(str(item.get("rotation", 0) or 0))
        else:
            style = item.get("style", {})
            self.font_var.set(style.get("font", ""))
            self.font_size_var.set(style.get("size", 42))
            self.font_color_var.set(style.get("color", "#111111"))
            self.align_var.set(style.get("align", "left"))

    def _apply_detail(self):
        if not self.selected:
            return
        kind, idx = self.selected
        item = self.state[kind + "s"][idx]
        item["key"] = self.elem_key.get().strip() or item.get("key")
        # update CSV hint immediately
        k = item.get("key", "")
        self.csv_col_var.set((f"slot.{k}" if kind == "slot" else f"text.{k}") if k else "")
        # Safely get integer values from Entry widgets
        try:
            x_val = int(self.x_var.get())
            y_val = int(self.y_var.get())
            w_val = max(10, int(self.w_box_var.get()))
            h_val = max(10, int(self.h_box_var.get()))
        except (ValueError, tk.TclError):
            # If conversion fails, keep existing values
            x_val, y_val, w_val, h_val = item.get("box", [0, 0, 100, 100])
        item["box"] = [x_val, y_val, w_val, h_val]
        if kind == "slot":
            try:
                item["radius"] = int(self.radius_var.get())
            except (ValueError, tk.TclError):
                pass
            item["fit"] = self.fit_var.get()
            try:
                item["padding"] = int(self.pad_var.get())
            except (ValueError, tk.TclError):
                pass
            item["align_x"] = self.align_x_var.get()
            item["align_y"] = self.align_y_var.get()
            try:
                item["rotation"] = float(self.rotation_var.get())
            except (ValueError, tk.TclError):
                item["rotation"] = 0
        else:
            style = item.get("style", {})
            style["font"] = self.font_var.get().strip() or None
            try:
                style["size"] = int(self.font_size_var.get())
            except (ValueError, tk.TclError):
                pass
            style["color"] = self.font_color_var.get() or "#111111"
            style["align"] = self.align_var.get()
            item["style"] = style
        self.redraw()

    # Canvas interaction -----------------------------------------------------
    def _on_canvas_click(self, event):
        scale = self._scale()
        for kind, idx, box in reversed(self._boxes()):
            x, y, w, h = box
            if x * scale <= event.x <= (x + w) * scale and y * scale <= event.y <= (y + h) * scale:
                self.selected = (kind, idx)
                self._load_detail()
                self.redraw()
                self.drag_start = (event.x, event.y, x, y)
                return
        self.selected = None
        self._load_detail()
        self.redraw()

    def _on_canvas_drag(self, event):
        if not getattr(self, "drag_start", None) or not self.selected:
            return
        kind, idx = self.selected
        _, _, orig_x, orig_y = self.drag_start
        dx = (event.x - self.drag_start[0]) / self._scale()
        dy = (event.y - self.drag_start[1]) / self._scale()
        item = self.state[kind + "s"][idx]
        x, y, w, h = item["box"]
        new_x = int(orig_x + dx)
        new_y = int(orig_y + dy)
        item["box"] = [max(0, new_x), max(0, new_y), w, h]
        self._load_detail()
        self.redraw()

    def _on_canvas_release(self, _event):
        self.drag_start = None

    def _pick_font(self):
        path = filedialog.askopenfilename(
            title="Pick font",
            filetypes=[("Font", "*.ttf *.otf"), ("All files", "*")],
        )
        if path:
            self.font_var.set(path)

    # Save -------------------------------------------------------------------
    def _save(self):
        # Apply any pending changes from UI to state before saving
        if self.selected:
            self._apply_detail()

        # Validate keys (new schema relies on keys for CSV columns)
        err = self._validate_keys()
        if err:
            messagebox.showerror("Error", err)
            return
        
        bg_data = {"kind": self.bg_kind.get(), "value": self.bg_value.get(), "opacity": float(self.bg_opacity.get())}
        if self.bg_kind.get() == "gradient":
            bg_data["gradient_type"] = self.gradient_type.get()
            bg_data["gradient_angle"] = float(self.gradient_angle.get())
            bg_data["gradient_center"] = [float(self.gradient_center_x.get()), float(self.gradient_center_y.get())]
            try:
                bg_data["gradient_stops"] = json.loads(self.gradient_stops.get())
            except Exception:
                bg_data["gradient_stops"] = [{"color": "#ff0000", "position": 0.0}, {"color": "#0000ff", "position": 1.0}]
        data = {
            "key": self.key_var.get().strip() or "template",
            "name": self.name_var.get().strip() or "Template",
            "size": [max(10, self.w_var.get()), max(10, self.h_var.get())],
            "background": bg_data,
            "slots": self.state.get("slots", []),
            "texts": self.state.get("texts", []),
        }
        try:
            template = load_template_from_json(data)
            self.on_save(template)
            messagebox.showinfo("Saved", f"Template '{template.key}' saved.")
            self.destroy()
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to save template: {exc}")

    def _validate_keys(self) -> Optional[str]:
        def _norm(s: str) -> str:
            return (s or "").strip()

        for group in ["slots", "texts"]:
            items = self.state.get(group, []) or []
            seen = set()
            for i, it in enumerate(items, start=1):
                key = _norm(it.get("key", ""))
                if not key:
                    return f"{group} 第 {i} 项的 key 为空"
                if "." in key:
                    return f"{group} 第 {i} 项的 key 不允许包含 '.'（当前：{key}）"
                lower = key.lower()
                if lower in seen:
                    return f"{group} 存在重复 key（大小写不敏感）：{key}"
                seen.add(lower)
        return None

    def _normalize_keys(self):
        """Heuristic key normalization to align with recommended schema."""
        # Slots: prefer background/main/overlay
        slot_items = self.state.get("slots", []) or []
        used_slots = set()
        for s in slot_items:
            k = (s.get("key") or "").strip()
            kl = k.lower()
            if kl in {"background", "bg"}:
                nk = "background"
            elif kl in {"glass", "overlay"}:
                nk = "overlay"
            elif kl in {"screenshot-1", "screenshot", "ui-1", "ui", "main", "slot-1"}:
                nk = "main"
            else:
                nk = k or "main"
            # ensure unique
            base = nk
            suffix = 2
            while nk.lower() in used_slots:
                nk = f"{base}_{suffix}"
                suffix += 1
            used_slots.add(nk.lower())
            s["key"] = nk

        # Texts: prefer title/subtitle/body
        text_items = self.state.get("texts", []) or []
        used_texts = set()
        preferred = ["title", "subtitle", "body"]
        pref_idx = 0
        for t in text_items:
            k = (t.get("key") or "").strip()
            kl = k.lower()
            if kl in {"title", "subtitle", "body"}:
                nk = kl
            elif kl.startswith("text-") or kl in {"text", ""}:
                nk = preferred[min(pref_idx, len(preferred) - 1)]
                pref_idx += 1
            else:
                nk = k or preferred[min(pref_idx, len(preferred) - 1)]
                pref_idx += 1
            base = nk
            suffix = 2
            while nk.lower() in used_texts:
                nk = f"{base}_{suffix}"
                suffix += 1
            used_texts.add(nk.lower())
            t["key"] = nk

        # refresh UI
        self.redraw()
        self._load_detail()


class CoverApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Cover Generator")
        self.geometry("1200x800")

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        self.registry = TemplateRegistry()
        self.registry.load_with_default(TEMPLATE_DIR)
        keys = self.registry.keys()
        self.template_var = tk.StringVar(value=keys[0] if keys else "")
        self.output_dir_var = tk.StringVar(value=str(OUTPUT_DIR))

        self.preview_img_tk = None

        self._build_ui()
        self.log("Ready.")

    # UI ---------------------------------------------------------------------
    def _build_ui(self):
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)

        # Header actions
        top = ttk.Frame(self, padding=8)
        top.grid(row=0, column=0, columnspan=2, sticky="ew")
        ttk.Label(top, text="Template").grid(row=0, column=0, sticky="w")
        self.template_select = ttk.Combobox(top, values=self.registry.keys(), textvariable=self.template_var, width=20, state="readonly")
        self.template_select.grid(row=0, column=1, padx=4)
        self.template_select.bind("<<ComboboxSelected>>", lambda _e: self.on_template_change())
        ttk.Button(top, text="Reload", command=self.reload_templates).grid(row=0, column=2, padx=2)
        ttk.Button(top, text="Import JSON", command=self.import_template).grid(row=0, column=3, padx=2)
        ttk.Button(top, text="Template Editor", command=self.open_template_editor).grid(row=0, column=4, padx=2)

        ttk.Label(top, text="Output Dir").grid(row=0, column=5, padx=(16, 2))
        ttk.Entry(top, textvariable=self.output_dir_var, width=30).grid(row=0, column=6)
        ttk.Button(top, text="Browse", command=self.pick_output_dir).grid(row=0, column=7, padx=2)

        # Main area
        notebook = ttk.Notebook(self)
        notebook.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)
        self._build_form_tab(notebook)
        self._build_csv_tab(notebook)

        # Preview
        preview_frame = ttk.Labelframe(self, text="Preview", padding=8)
        preview_frame.grid(row=1, column=1, sticky="nsew", padx=(0, 8), pady=8)
        preview_frame.rowconfigure(0, weight=1)
        preview_frame.columnconfigure(0, weight=1)
        self.preview_label = ttk.Label(preview_frame)
        self.preview_label.grid(row=0, column=0, sticky="nsew")

        # Log
        log_frame = ttk.Labelframe(self, text="Log", padding=6)
        log_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 8))
        self.log_text = tk.Text(log_frame, height=6, state="disabled")
        self.log_text.pack(fill="both", expand=True)

    def _build_form_tab(self, notebook):
        frame = ttk.Frame(notebook, padding=8)
        notebook.add(frame, text="表单")
        frame.columnconfigure(1, weight=1)

        # reserved inputs (new schema)
        self.background_var = tk.StringVar()  # background_path override
        self.output_name_var = tk.StringVar(value="cover.png")

        ttk.Label(frame, text="背景(可选)").grid(row=0, column=0, sticky="w")
        bg_row = ttk.Frame(frame)
        bg_row.grid(row=0, column=1, sticky="ew")
        ttk.Entry(bg_row, textvariable=self.background_var).pack(side="left", fill="x", expand=True)
        ttk.Button(bg_row, text="选择", command=self.pick_background).pack(side="left", padx=4)

        ttk.Label(frame, text="输出文件名").grid(row=1, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.output_name_var).grid(row=1, column=1, sticky="ew")

        # dynamic inputs per template
        self.form_dynamic = ttk.Frame(frame)
        self.form_dynamic.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(10, 0))
        frame.rowconfigure(2, weight=1)

        self.text_vars = {}
        self.slot_vars = {}
        self.rebuild_form_fields()

        action_row = ttk.Frame(frame)
        action_row.grid(row=3, column=0, columnspan=2, pady=8, sticky="ew")
        ttk.Button(action_row, text="预览", command=self.preview_form).pack(side="left", padx=4)
        ttk.Button(action_row, text="导出", command=self.export_form).pack(side="left", padx=4)

    def on_template_change(self):
        self.rebuild_form_fields()

    def rebuild_form_fields(self):
        """Rebuild form inputs based on currently selected template (new schema only)."""
        for child in self.form_dynamic.winfo_children():
            child.destroy()
        self.text_vars = {}
        self.text_color_vars = {}
        self.slot_vars = {}

        template = self._get_template(self.template_var.get())

        if template.texts:
            text_frame = ttk.Labelframe(self.form_dynamic, text="Texts", padding=8)
            text_frame.pack(fill="x", expand=False, pady=(0, 8))
            text_frame.columnconfigure(1, weight=1)
            for i, t in enumerate(template.texts):
                key = t.key
                var = tk.StringVar()
                color_var = tk.StringVar()
                self.text_vars[key] = var
                self.text_color_vars[key] = color_var
                ttk.Label(text_frame, text=f"{key}  (text.{key})").grid(row=i, column=0, sticky="w", pady=2)
                ttk.Entry(text_frame, textvariable=var).grid(row=i, column=1, sticky="ew", pady=2)
                ttk.Label(text_frame, text="color").grid(row=i, column=2, sticky="w", padx=(8, 2), pady=2)
                ttk.Entry(text_frame, textvariable=color_var, width=10).grid(row=i, column=3, sticky="w", pady=2)

        if template.slots:
            slot_frame = ttk.Labelframe(self.form_dynamic, text="Slots", padding=8)
            slot_frame.pack(fill="x", expand=False)
            slot_frame.columnconfigure(1, weight=1)
            for i, s in enumerate(template.slots):
                key = s.key
                var = tk.StringVar()
                self.slot_vars[key] = var
                ttk.Label(slot_frame, text=f"{key}  (slot.{key})").grid(row=i, column=0, sticky="w", pady=2)
                entry = ttk.Entry(slot_frame, textvariable=var)
                entry.grid(row=i, column=1, sticky="ew", pady=2)
                ttk.Button(slot_frame, text="选择", command=lambda k=key: self.pick_slot_file(k)).grid(row=i, column=2, padx=4)

    def pick_slot_file(self, slot_key: str):
        path = filedialog.askopenfilename(
            title=f"选择图片: {slot_key}",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.webp"), ("All files", "*")],
        )
        if path:
            self.slot_vars.get(slot_key, tk.StringVar()).set(path)

    def _build_csv_tab(self, notebook):
        frame = ttk.Frame(notebook, padding=8)
        notebook.add(frame, text="CSV 批量")
        frame.columnconfigure(1, weight=1)

        self.csv_path_var = tk.StringVar()
        ttk.Label(frame, text="CSV 文件").grid(row=0, column=0, sticky="w")
        csv_row = ttk.Frame(frame)
        csv_row.grid(row=0, column=1, sticky="ew")
        ttk.Entry(csv_row, textvariable=self.csv_path_var).pack(side="left", fill="x", expand=True)
        ttk.Button(csv_row, text="选择", command=self.pick_csv).pack(side="left", padx=4)

        self.csv_count_var = tk.StringVar(value="未加载")
        ttk.Label(frame, textvariable=self.csv_count_var).grid(row=1, column=1, sticky="w")

        actions = ttk.Frame(frame)
        actions.grid(row=2, column=1, pady=8, sticky="w")
        ttk.Button(actions, text="导出 CSV 模板", command=self.export_csv_template).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="批量生成", command=self.run_batch).pack(side="left")

    # Logging ----------------------------------------------------------------
    def log(self, message: str):
        self.log_text.configure(state="normal")
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.configure(state="disabled")
        self.log_text.see(tk.END)

    # Template operations ----------------------------------------------------
    def refresh_templates(self, select_key: Optional[str] = None):
        keys = self.registry.keys()
        if not keys:
            default = default_template()
            self.registry.save_template(default, TEMPLATE_DIR / f"{default.key}.json")
            keys = self.registry.keys()
        self.template_select["values"] = keys
        self.template_var.set(select_key if select_key in keys else keys[0])

    def reload_templates(self):
        self.registry.load_with_default(TEMPLATE_DIR)
        self.refresh_templates(self.template_var.get())
        self.on_template_change()
        self.log("Templates reloaded.")

    def import_template(self):
        path = filedialog.askopenfilename(
            title="Import template JSON",
            filetypes=[("JSON", "*.json"), ("All files", "*")],
        )
        if not path:
            return
        try:
            template = self.registry.import_json(Path(path))
            self.refresh_templates(template.key)
            self.on_template_change()
            self.log(f"Imported template {template.key}")
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to import: {exc}")

    def open_template_editor(self):
        current = self.registry.get(self.template_var.get()) or default_template()
        data = template_to_dict(current)

        def _on_save(template):
            self.registry.save_template(template, TEMPLATE_DIR / f"{template.key}.json")
            self.refresh_templates(template.key)
            self.on_template_change()

        TemplateEditor(self, data, self.registry, _on_save)

    # Path pickers -----------------------------------------------------------
    def pick_output_dir(self):
        path = filedialog.askdirectory(title="选择输出目录", initialdir=self.output_dir_var.get())
        if path:
            self.output_dir_var.set(path)

    def pick_background(self):
        path = filedialog.askopenfilename(
            title="选择背景",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.webp"), ("All files", "*")],
        )
        if path:
            self.background_var.set(path)

    def add_screenshots(self):
        # legacy UI removed (new schema only)
        return

    def remove_screenshots(self):
        # legacy UI removed (new schema only)
        return

    def pick_csv(self):
        path = filedialog.askopenfilename(
            title="选择 CSV",
            filetypes=[("CSV", "*.csv"), ("All files", "*")],
        )
        if path:
            self.csv_path_var.set(path)
            try:
                # Use utf-8-sig to transparently handle UTF-8 BOM from Excel/WPS exports
                with open(path, newline="", encoding="utf-8-sig") as f:
                    reader = csv.DictReader(f)
                    fieldnames = reader.fieldnames or []
                    rows = list(reader)

                ok, msg = self._validate_csv_header(fieldnames)
                self.csv_count_var.set(f"{len(rows)} 行" + ("" if ok else f"（表头有问题：{msg}）"))
                if not ok:
                    messagebox.showwarning("CSV 表头校验", msg)
            except Exception as exc:
                self.csv_count_var.set("读取失败")
                messagebox.showerror("Error", f"读取 CSV 失败: {exc}")

    def _validate_csv_header(self, fieldnames):
        def _clean_col(x: str) -> str:
            # Strip whitespace and common zero-width/BOM characters injected by Excel/WPS exports.
            # - U+FEFF: BOM / zero width no-break space
            # - U+200B/200C/200D: zero width space/joiners
            # - U+2060: word joiner
            return (x or "").strip().lstrip("\ufeff\u200b\u200c\u200d\u2060")

        lower = [_clean_col(str(x)).lower() for x in (fieldnames or []) if x is not None and _clean_col(str(x))]
        cols = set(lower)
        missing = [c for c in ["template_key", "output_name"] if c not in cols]
        legacy = sorted(
            c
            for c in cols
            if c
            in {
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
        )
        unknown = sorted(
            c
            for c in cols
            if c not in {"template_key", "output_name", "background_path"} and not (c.startswith("text.") or c.startswith("slot."))
        )
        if missing or legacy or unknown:
            parts = []
            if missing:
                parts.append("缺少必填列: " + ", ".join(missing))
            if legacy:
                parts.append("包含旧列名(不再支持): " + ", ".join(legacy))
            if unknown:
                parts.append("包含未知列名: " + ", ".join(unknown))
            return False, "；".join(parts)
        return True, "OK"

    # Helpers ----------------------------------------------------------------
    def _get_template(self, key: str):
        template = self.registry.get(key)
        if template:
            return template
        keys = self.registry.keys()
        return self.registry.get(keys[0]) if keys else default_template()

    def _build_render_input(self) -> RenderInput:
        texts = {k: v.get() for k, v in (self.text_vars or {}).items() if v.get().strip()}
        text_colors = {k: v.get().strip() for k, v in (getattr(self, "text_color_vars", None) or {}).items() if v.get().strip()}
        slot_paths = {k: v.get() for k, v in (self.slot_vars or {}).items() if v.get().strip()}
        return RenderInput(
            background_path=self.background_var.get() or None,
            template_key=self.template_var.get(),
            output_name=self.output_name_var.get() or "cover.png",
            texts=texts,
            text_colors=text_colors,
            slot_paths=slot_paths,
        )

    def _show_preview(self, render_input: RenderInput, template_key: str):
        template = self._get_template(template_key)
        try:
            img = build_preview(render_input, template)
            self.preview_img_tk = ImageTk.PhotoImage(img)
            self.preview_label.configure(image=self.preview_img_tk)
            self.log("Preview updated.")
        except Exception as exc:
            messagebox.showerror("Error", f"预览失败: {exc}")
            self.log(f"Preview failed: {exc}")

    # Actions ----------------------------------------------------------------
    def preview_form(self):
        ri = self._build_render_input()
        self._show_preview(ri, ri.template_key)

    def export_form(self):
        ri = self._build_render_input()
        template = self._get_template(ri.template_key)
        output_path = Path(self.output_dir_var.get()) / ri.output_name
        try:
            render_to_file(ri, template, output_path)
            self.log(f"Saved {output_path}")
            messagebox.showinfo("完成", f"已保存到 {output_path}")
        except Exception as exc:
            messagebox.showerror("Error", f"导出失败: {exc}")

    def run_batch(self):
        csv_path = self.csv_path_var.get()
        if not csv_path:
            messagebox.showwarning("提示", "请选择 CSV 文件")
            return
        try:
            # Use utf-8-sig to transparently handle UTF-8 BOM from Excel/WPS exports
            with open(csv_path, newline="", encoding="utf-8-sig") as f:
                rows = list(csv.DictReader(f))
        except Exception as exc:
            messagebox.showerror("Error", f"读取 CSV 失败: {exc}")
            return
        out_dir = Path(self.output_dir_var.get())
        out_dir.mkdir(parents=True, exist_ok=True)
        success = 0
        for idx, row in enumerate(rows, start=1):
            try:
                ri = render_input_from_row(row)
            except Exception as exc:
                self.log(f"行 {idx} 解析失败: {exc}")
                continue
            template = self._get_template(ri.template_key)
            output_path = out_dir / ri.output_name
            try:
                render_to_file(ri, template, output_path)
                success += 1
            except Exception as exc:
                self.log(f"行 {idx} 渲染失败: {exc}")
        self.log(f"批量完成 {success}/{len(rows)}")
        messagebox.showinfo("完成", f"批量完成 {success}/{len(rows)}")

    def export_csv_template(self):
        template = self._get_template(self.template_var.get())
        default_name = f"template-{template.key}.csv"
        path = filedialog.asksaveasfilename(
            title="导出 CSV 模板",
            defaultextension=".csv",
            initialfile=default_name,
            filetypes=[("CSV", "*.csv"), ("All files", "*")],
        )
        if not path:
            return

        headers = ["template_key", "output_name", "background_path"]
        # Deterministic order: follow template list order
        for t in template.texts:
            headers.append(f"text.{t.key}")
            headers.append(f"text.{t.key}.color")
        headers += [f"slot.{s.key}" for s in template.slots]

        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(headers)
            self.log(f"CSV 模板已导出: {path}")
            messagebox.showinfo("完成", f"CSV 模板已导出: {path}")
        except Exception as exc:
            messagebox.showerror("Error", f"导出 CSV 模板失败: {exc}")


def main():
    app = CoverApp()
    app.mainloop()


if __name__ == "__main__":
    main()

