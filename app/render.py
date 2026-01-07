from __future__ import annotations

import math
from copy import deepcopy
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from .models import RenderInput, TemplateDefinition, Slot, TextBlock


def load_font(path: Optional[str], size: int) -> ImageFont.FreeTypeFont:
    try:
        if path and Path(path).exists():
            return ImageFont.truetype(path, size=size)
    except Exception:
        pass
    return ImageFont.load_default()


def _apply_shadow(img: Image.Image, draw: ImageDraw.Draw, text: str, position: Tuple[int, int], font: ImageFont.FreeTypeFont, style):
    shadow = style.shadow
    if not shadow:
        return
    offset = shadow.get("offset", [2, 2])
    color = shadow.get("color", "#00000088")
    blur = int(shadow.get("blur", 0))
    x, y = position
    shadow_pos = (x + offset[0], y + offset[1])
    if blur > 0:
        # draw blurred shadow on a temp layer then composite onto base image
        tmp = Image.new("RGBA", img.size, (0, 0, 0, 0))
        tmp_draw = ImageDraw.Draw(tmp)
        tmp_draw.text(shadow_pos, text, font=font, fill=color, align=style.align)
        tmp = tmp.filter(ImageFilter.GaussianBlur(radius=blur))
        img.alpha_composite(tmp)
    else:
        draw.text(shadow_pos, text, font=font, fill=color, align=style.align)


def draw_text_block(img: Image.Image, block: TextBlock, text: str):
    x, y, w, h = block.box
    draw = ImageDraw.Draw(img)
    font = load_font(block.style.font, block.style.size)

    def wrap_lines(content: str):
        words = content.split()
        lines = []
        current = ""
        max_width = block.style.max_width or w
        for word in words:
            trial = (current + " " + word).strip()
            if not trial:
                continue
            bbox = draw.textbbox((0, 0), trial, font=font)
            if bbox[2] - bbox[0] <= max_width:
                current = trial
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines or [""]

    lines = wrap_lines(text)
    line_height = font.getbbox("Ag")[3] - font.getbbox("Ag")[1]
    total_height = int(len(lines) * line_height * block.style.line_spacing)
    offset_y = y
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        text_w = bbox[2] - bbox[0]
        align = block.style.align
        if align == "center":
            pos_x = x + (w - text_w) / 2
        elif align == "right":
            pos_x = x + w - text_w
        else:
            pos_x = x
        pos = (int(pos_x), int(offset_y))
        _apply_shadow(img, draw, line, pos, font, block.style)
        if block.style.stroke_width and block.style.stroke_fill:
            draw.text(pos, line, font=font, fill=block.style.color, stroke_width=block.style.stroke_width, stroke_fill=block.style.stroke_fill, align=align)
        else:
            draw.text(pos, line, font=font, fill=block.style.color, align=align)
        offset_y += int(line_height * block.style.line_spacing)


def _resize_fit(img: Image.Image, target_size: Tuple[int, int], fit: str, align_x: str = "center", align_y: str = "center") -> Image.Image:
    tw, th = target_size
    iw, ih = img.size
    if fit == "contain":
        scale = min(tw / iw, th / ih)
    else:
        scale = max(tw / iw, th / ih)
    new_size = (max(1, int(iw * scale)), max(1, int(ih * scale)))
    resized = img.resize(new_size, Image.Resampling.LANCZOS)
    if fit == "contain":
        canvas = Image.new("RGBA", target_size, (0, 0, 0, 0))
        # Calculate x position based on align_x
        if align_x == "left":
            cx = 0
        elif align_x == "right":
            cx = tw - resized.size[0]
        else:  # center
            cx = (tw - resized.size[0]) // 2
        # Calculate y position based on align_y
        if align_y == "top":
            cy = 0
        elif align_y == "bottom":
            cy = th - resized.size[1]
        else:  # center
            cy = (th - resized.size[1]) // 2
        canvas.paste(resized, (cx, cy), resized)
        return canvas
    # cover
    # Calculate crop position based on align_x
    if align_x == "left":
        left = 0
    elif align_x == "right":
        left = resized.size[0] - tw
    else:  # center
        left = (resized.size[0] - tw) // 2
    # Calculate crop position based on align_y
    if align_y == "top":
        top = 0
    elif align_y == "bottom":
        top = resized.size[1] - th
    else:  # center
        top = (resized.size[1] - th) // 2
    return resized.crop((left, top, left + tw, top + th))


def _round_corners(img: Image.Image, radius: int) -> Image.Image:
    """
    Apply rounded corners to an image using supersampling for anti-aliasing.
    """
    if radius <= 0:
        return img
    
    # 1. 设置超采样因子（4倍能获得很好的平滑效果）
    factor = 4
    w, h = img.size
    
    # 2. 创建放大后的 mask 画布
    # 使用 'L' 模式 (8-bit pixels, black and white)
    mask = Image.new("L", (w * factor, h * factor), 0)
    draw = ImageDraw.Draw(mask)
    
    # 3. 在高清画布上绘制圆角矩形
    # 注意：坐标和半径都需要乘以 factor
    draw.rounded_rectangle(
        [(0, 0), (w * factor, h * factor)], 
        radius=radius * factor, 
        fill=255
    )
    
    # 4. 缩小回原尺寸，使用 LANCZOS 滤镜进行抗锯齿处理
    # 这一步会产生边缘的半透明像素，消除锯齿
    mask = mask.resize((w, h), Image.Resampling.LANCZOS)
    
    # 5. 应用遮罩
    img = img.copy()
    img.putalpha(mask)
    
    return img


def _project_slot_quad(w: int, h: int, rotate_x: float, rotate_y: float, rotate_z: float, camera_k: float = 2.5):
    """
    Project a rectangle (slot layer) with 3D rotations to a 2D quad in the same (w,h) output space.

    Coordinate convention:
    - X: right
    - Y: down (image coords)
    - Z: towards viewer (out of screen)

    Perspective uses a fixed camera distance: d = camera_k * max(w, h).
    Returns 4 points [(x0,y0), (x1,y1), (x2,y2), (x3,y3)] corresponding to
    source corners [(0,0), (w,0), (w,h), (0,h)].
    """
    cx, cy = w / 2.0, h / 2.0

    # Clamp to avoid extreme projection instability
    rx = max(-89.0, min(89.0, float(rotate_x or 0.0)))
    ry = max(-89.0, min(89.0, float(rotate_y or 0.0)))
    rz = float(rotate_z or 0.0)

    ax, ay, az = math.radians(rx), math.radians(ry), math.radians(rz)
    cosx, sinx = math.cos(ax), math.sin(ax)
    cosy, siny = math.cos(ay), math.sin(ay)
    cosz, sinz = math.cos(az), math.sin(az)

    # Fixed camera distance
    d = max(1.0, float(camera_k) * float(max(w, h)))
    eps = 1e-6

    def rot_z(X, Y, Z):
        return (X * cosz - Y * sinz, X * sinz + Y * cosz, Z)

    def rot_x(X, Y, Z):
        return (X, Y * cosx - Z * sinx, Y * sinx + Z * cosx)

    def rot_y(X, Y, Z):
        return (X * cosy + Z * siny, Y, -X * siny + Z * cosy)

    def project(X, Y, Z):
        denom = (d - Z)
        if abs(denom) < eps:
            denom = eps if denom >= 0 else -eps
        s = d / denom
        return (X * s + cx, Y * s + cy)

    corners = [(-cx, -cy, 0.0), (cx, -cy, 0.0), (cx, cy, 0.0), (-cx, cy, 0.0)]
    out = []
    for X, Y, Z in corners:
        X, Y, Z = rot_z(X, Y, Z)
        X, Y, Z = rot_x(X, Y, Z)
        X, Y, Z = rot_y(X, Y, Z)
        out.append(project(X, Y, Z))
    return out


def _perspective_coeffs(dst_quad, src_quad):
    """
    Compute Pillow PERSPECTIVE coefficients that map output (dst) -> input (src).
    dst_quad/src_quad are 4 points [(x,y), ...] in corresponding order.
    """
    if len(dst_quad) != 4 or len(src_quad) != 4:
        raise ValueError("dst_quad/src_quad must have 4 points")

    A = []
    B = []
    for (x, y), (u, v) in zip(dst_quad, src_quad):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y])
        B.append(u)
        B.append(v)
    A = np.asarray(A, dtype=np.float64)
    B = np.asarray(B, dtype=np.float64)

    # Solve A * coeffs = B
    coeffs = np.linalg.solve(A, B)
    return tuple(float(x) for x in coeffs.tolist())


def place_slot(base: Image.Image, slot: Slot, content_path: Path):
    if not content_path.exists():
        return
    img = Image.open(content_path).convert("RGBA")
    x, y, w, h = slot.box
    pad = slot.padding
    target_size = (max(1, w - pad * 2), max(1, h - pad * 2))
    fitted = _resize_fit(img, target_size, slot.fit, slot.align_x, slot.align_y)
    rounded = _round_corners(fitted, slot.radius)
    # Compose into a slot-sized layer so we can rotate the whole slot (including padding + rounded corners)
    slot_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    slot_layer.alpha_composite(rounded, dest=(pad, pad))

    rotate_x = float(getattr(slot, "rotate_x", 0) or 0)
    rotate_y = float(getattr(slot, "rotate_y", 0) or 0)
    rotate_z = float(getattr(slot, "rotation", 0) or 0)  # keep existing field name/semantics

    if rotate_x or rotate_y or rotate_z:
        dst_quad = _project_slot_quad(w, h, rotate_x=rotate_x, rotate_y=rotate_y, rotate_z=rotate_z, camera_k=2.5)

        # Expand output canvas to rotated quad bounds so we don't clip.
        xs = [p[0] for p in dst_quad]
        ys = [p[1] for p in dst_quad]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        out_w = max(1, int(math.ceil(max_x - min_x)))
        out_h = max(1, int(math.ceil(max_y - min_y)))

        # Supersample warp to reduce jagged edges on slanted boundaries.
        factor = 2
        w_hi, h_hi = w * factor, h * factor
        out_w_hi, out_h_hi = out_w * factor, out_h * factor

        slot_layer_hi = slot_layer.resize((w_hi, h_hi), Image.Resampling.LANCZOS)

        # Shift quad into output canvas space (0..out_w/out_h) and scale to hi-res
        dst_quad_shifted_hi = [((px - min_x) * factor, (py - min_y) * factor) for (px, py) in dst_quad]
        src_quad_hi = [(0.0, 0.0), (float(w_hi), 0.0), (float(w_hi), float(h_hi)), (0.0, float(h_hi))]

        coeffs_hi = _perspective_coeffs(dst_quad_shifted_hi, src_quad_hi)
        warped_hi = slot_layer_hi.transform(
            (out_w_hi, out_h_hi),
            Image.Transform.PERSPECTIVE,
            coeffs_hi,
            resample=Image.Resampling.BICUBIC,
        )
        warped = warped_hi.resize((out_w, out_h), Image.Resampling.LANCZOS)

        dest_x = int(round(x + min_x))
        dest_y = int(round(y + min_y))
        base.alpha_composite(warped, dest=(dest_x, dest_y))
    else:
        base.alpha_composite(slot_layer, dest=(x, y))


def _draw_gradient(img: Image.Image, config) -> Image.Image:
    """Draw gradient background based on config (optimized with numpy)."""
    w, h = img.size
    
    if not config.gradient_stops or len(config.gradient_stops) < 2:
        return img
    
    stops = sorted(config.gradient_stops, key=lambda s: float(s.get("position", 0.0)))
    
    def hex_to_rgba(hex_str: str, opacity: float) -> Tuple[int, int, int, int]:
        hex_str = hex_str.lstrip("#")
        if len(hex_str) == 6:
            r, g, b = tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))
        else:
            r, g, b = (255, 255, 255)
        a = int(255 * max(0, min(opacity, 1)))
        return (r, g, b, a)
    
    # Convert to numpy array for faster processing
    arr = np.zeros((h, w, 4), dtype=np.uint8)
    
    if config.gradient_type == "radial":
        # Radial gradient
        center_x = w * (config.gradient_center[0] if config.gradient_center else 0.5)
        center_y = h * (config.gradient_center[1] if config.gradient_center else 0.5)
        max_radius = math.sqrt(w * w + h * h) / 2
        
        y_coords, x_coords = np.ogrid[:h, :w]
        dx = x_coords - center_x
        dy = y_coords - center_y
        dist = np.sqrt(dx * dx + dy * dy)
        pos = np.clip(dist / max_radius, 0.0, 1.0)
    else:
        # Linear gradient
        angle = config.gradient_angle if config.gradient_angle is not None else 90.0
        angle_rad = math.radians(angle)
        cos_a, sin_a = math.cos(angle_rad), math.sin(angle_rad)
        
        center_x, center_y = w / 2, h / 2
        max_dist = math.sqrt(w * w + h * h) / 2
        
        y_coords, x_coords = np.ogrid[:h, :w]
        dx = x_coords - center_x
        dy = y_coords - center_y
        dist = dx * cos_a + dy * sin_a
        pos = np.clip((dist / max_dist + 1.0) / 2.0, 0.0, 1.0)
    
    # Interpolate colors
    for i in range(len(stops) - 1):
        p1, p2 = float(stops[i].get("position", 0.0)), float(stops[i+1].get("position", 1.0))
        if p2 <= p1:
            continue
        mask = (pos >= p1) & (pos <= p2)
        if not np.any(mask):
            continue
        
        t = np.clip((pos[mask] - p1) / (p2 - p1), 0.0, 1.0)
        c1 = np.array(hex_to_rgba(stops[i].get("color", "#ffffff"), config.opacity), dtype=np.uint8)
        c2 = np.array(hex_to_rgba(stops[i+1].get("color", "#ffffff"), config.opacity), dtype=np.uint8)
        
        for ch in range(4):
            arr[mask, ch] = (c1[ch] + (c2[ch] - c1[ch]) * t).astype(np.uint8)
    
    # Fill remaining pixels with first/last stop
    if len(stops) > 0:
        first_pos = float(stops[0].get("position", 0.0))
        last_pos = float(stops[-1].get("position", 1.0))
        first_mask = pos < first_pos
        last_mask = pos > last_pos
        if np.any(first_mask):
            c = np.array(hex_to_rgba(stops[0].get("color", "#ffffff"), config.opacity), dtype=np.uint8)
            arr[first_mask] = c
        if np.any(last_mask):
            c = np.array(hex_to_rgba(stops[-1].get("color", "#ffffff"), config.opacity), dtype=np.uint8)
            arr[last_mask] = c
    
    img = Image.fromarray(arr, "RGBA")
    return img


def apply_background(template: TemplateDefinition, background_path: Optional[str]) -> Image.Image:
    w, h = template.size
    bg_color = (255, 255, 255, 255)
    
    if template.background.kind == "gradient":
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        img = _draw_gradient(img, template.background)
    elif template.background.kind == "color":
        bg_color = tuple(ImageColor_get(template.background.value, template.background.opacity))
        img = Image.new("RGBA", (w, h), bg_color)
    else:
        img = Image.new("RGBA", (w, h), bg_color)
    
    if background_path:
        try:
            bg = Image.open(background_path).convert("RGBA")
        except Exception:
            bg = None
        if bg:
            bg_fitted = _resize_fit(bg, (w, h), "cover")
            img.alpha_composite(bg_fitted)
            return img
    if template.background.kind == "image" and template.background.value:
        path = Path(template.background.value)
        if path.exists():
            bg = Image.open(path).convert("RGBA")
            bg_fitted = _resize_fit(bg, (w, h), "cover")
            img.alpha_composite(bg_fitted)
    return img


def ImageColor_get(hex_value: str, opacity: float):
    hex_value = hex_value.lstrip("#")
    if len(hex_value) == 6:
        r, g, b = tuple(int(hex_value[i:i+2], 16) for i in (0, 2, 4))
    else:
        r, g, b = (255, 255, 255)
    a = int(255 * max(0, min(opacity, 1)))
    return r, g, b, a


def compose_cover(render_input: RenderInput, template: TemplateDefinition) -> Image.Image:
    base = apply_background(template, render_input.background_path)

    # place slots (new schema only)
    keyed_mode = True
    for idx, slot in enumerate(template.slots):
        slot_path = None
        raw = (render_input.slot_paths or {}).get(slot.key)
        if raw:
            slot_path = raw
        if slot_path:
            place_slot(base, slot, Path(slot_path))

    # texts
    for text in template.texts:
        content = (render_input.texts or {}).get(text.key, "")
        override = (getattr(render_input, "text_colors", None) or {}).get(text.key)
        if isinstance(override, str) and override.strip().startswith("#"):
            # Avoid mutating template objects in registry: copy then override.
            tmp = deepcopy(text)
            tmp.style.color = override.strip()
            draw_text_block(base, tmp, content)
        else:
            draw_text_block(base, text, content)

    return base


def render_to_file(render_input: RenderInput, template: TemplateDefinition, output_path: Path) -> Path:
    img = compose_cover(render_input, template)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, format="PNG")
    return output_path


def build_preview(render_input: RenderInput, template: TemplateDefinition, max_size: int = 480) -> Image.Image:
    img = compose_cover(render_input, template)
    w, h = img.size
    scale = min(max_size / max(w, h), 1.0)
    if scale < 1.0:
        img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
    return img

