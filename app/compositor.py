from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFont, ImageOps


def _font(size: int):
    for path in ("C:/Windows/Fonts/segoeui.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _placeholder(width: int, height: int, layer: dict) -> Image.Image:
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    name, kind = layer["name"], layer["kind"]
    if kind == "background":
        draw.rectangle((0, 0, width, height), fill="#283047")
        draw.ellipse((-width * .15, height * .35, width * .65, height * 1.15), fill="#394764")
        draw.line((0, height * .72, width, height * .48), fill="#7583a0", width=max(2, width // 500))
    elif kind == "character":
        transform = layer.get("transform", {})
        scale = max(.05, float(transform.get("scale", 1)))
        cx = int(width * float(transform.get("x", .5)))
        body_w, body_h = int(width * .14 * scale), int(height * .48 * scale)
        bottom = int(height * float(transform.get("y", .58)) + body_h / 2)
        draw.ellipse((cx-body_w*.32, bottom-body_h-body_w*.4, cx+body_w*.32, bottom-body_h+body_w*.25), fill="#d36d59")
        draw.rounded_rectangle((cx-body_w/2, bottom-body_h, cx+body_w/2, bottom), radius=max(8, width//100), fill="#a84d4c")
    else:
        draw.rounded_rectangle((width*.25, height*.3, width*.75, height*.7), radius=max(8,width//100), fill="#6a536f")
    draw.text((width*.04, height*.06), f"{kind.upper()}  /  {name}", fill="#f4eee4", font=_font(max(14, width//55)))
    return image


def _load_layer(source: Path | None, width: int, height: int, layer: dict) -> Image.Image:
    if source and source.exists():
        try:
            with Image.open(source) as opened:
                raw = opened.convert("RGBA")
            if layer["kind"] == "background":
                return ImageOps.fit(raw, (width, height), method=Image.Resampling.LANCZOS)
            scale = max(.05, float(layer["transform"].get("scale", 1)))
            target_height = max(1, int(height * .7 * scale))
            raw.thumbnail((int(width * .8 * scale), target_height), Image.Resampling.LANCZOS)
            canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            x = int(width * float(layer["transform"].get("x", .5)) - raw.width / 2)
            y = int(height * float(layer["transform"].get("y", .55)) - raw.height / 2)
            canvas.alpha_composite(raw, (x, y))
            return canvas
        except Exception:
            pass
    return _placeholder(width, height, layer)


def _blend(base: Image.Image, layer: Image.Image, mode: str) -> Image.Image:
    alpha = layer.getchannel("A")
    if mode == "multiply":
        mixed = ImageChops.multiply(base.convert("RGB"), layer.convert("RGB")).convert("RGBA")
        mixed.putalpha(alpha)
        return Image.alpha_composite(base, mixed)
    if mode == "screen":
        mixed = ImageChops.screen(base.convert("RGB"), layer.convert("RGB")).convert("RGBA")
        mixed.putalpha(alpha)
        return Image.alpha_composite(base, mixed)
    return Image.alpha_composite(base, layer)


def render_composite(layers: list[dict], output: Path, width: int, height: int, color_grade: dict) -> None:
    canvas = Image.new("RGBA", (width, height), "#11131a")
    for layer in sorted((item for item in layers if item.get("visible", True)), key=lambda item: item["z_index"]):
        rendered = _load_layer(layer.get("source"), width, height, layer)
        rotation = float(layer["transform"].get("rotation", 0))
        if rotation:
            rendered = rendered.rotate(-rotation, resample=Image.Resampling.BICUBIC, center=(width // 2, height // 2))
        opacity = max(0, min(1, float(layer.get("opacity", 1))))
        if opacity < 1:
            rendered.putalpha(rendered.getchannel("A").point(lambda value: int(value * opacity)))
        canvas = _blend(canvas, rendered, layer.get("blend_mode", "normal"))
    result = canvas.convert("RGB")
    result = ImageEnhance.Brightness(result).enhance(float(color_grade.get("exposure", 1)))
    result = ImageEnhance.Contrast(result).enhance(float(color_grade.get("contrast", 1)))
    result = ImageEnhance.Color(result).enhance(float(color_grade.get("saturation", 1)))
    output.parent.mkdir(parents=True, exist_ok=True)
    result.save(output, "PNG", optimize=True)
