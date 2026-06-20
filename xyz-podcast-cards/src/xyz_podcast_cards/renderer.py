from __future__ import annotations

import io
import textwrap
from pathlib import Path

import httpx
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .fetcher import DEFAULT_HEADERS, format_duration, format_pub_date
from .models import CardSegment, EpisodeInfo, RenderOptions

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "C:/Windows/Fonts/msyh.ttc",
]


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def _load_font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in FONT_CANDIDATES:
        if not Path(path).exists():
            continue
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _download_image(url: str, client: httpx.Client) -> Image.Image | None:
    if not url:
        return None
    try:
        response = client.get(
            url,
            headers={**DEFAULT_HEADERS, "Referer": "https://www.xiaoyuzhoufm.com/"},
        )
        response.raise_for_status()
        return Image.open(io.BytesIO(response.content)).convert("RGBA")
    except (httpx.HTTPError, OSError):
        return None


def _wrap_text(text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    if not text:
        return []
    lines: list[str] = []
    for paragraph in text.split("\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            lines.append("")
            continue
        current = ""
        for char in paragraph:
            candidate = current + char
            width = font.getlength(candidate)
            if width <= max_width or not current:
                current = candidate
            else:
                lines.append(current)
                current = char
        if current:
            lines.append(current)
    return lines


def _fit_cover(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    target_w, target_h = size
    image = image.copy()
    image.thumbnail((target_w, target_h), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", size, (255, 255, 255, 0))
    offset = ((target_w - image.width) // 2, (target_h - image.height) // 2)
    canvas.paste(image, offset, image if image.mode == "RGBA" else None)
    return canvas


def _draw_rounded_rectangle(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    radius: int,
    fill: tuple[int, int, int],
) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill)


def render_cover_card(
    episode: EpisodeInfo,
    *,
    cover_image: Image.Image | None,
    options: RenderOptions,
) -> Image.Image:
    width, height = options.width, options.height
    accent = _hex_to_rgb(options.accent_color)
    background = _hex_to_rgb(options.background_color)
    text_color = _hex_to_rgb(options.text_color)

    canvas = Image.new("RGB", (width, height), background)
    if cover_image is not None:
        blurred = cover_image.convert("RGB").resize((width, height), Image.Resampling.LANCZOS)
        blurred = blurred.filter(ImageFilter.GaussianBlur(24))
        canvas.paste(blurred, (0, 0))
        overlay = Image.new("RGBA", (width, height), (255, 248, 240, 170))
        canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")

    draw = ImageDraw.Draw(canvas)
    margin = 72
    card_box = (margin, margin + 80, width - margin, height - margin - 80)
    _draw_rounded_rectangle(draw, card_box, 36, (255, 255, 255))

    title_font = _load_font(options.font_size_title)
    meta_font = _load_font(options.font_size_meta)
    body_font = _load_font(options.font_size_body)

    y = card_box[1] + 48
    if cover_image is not None:
        cover = _fit_cover(cover_image, (width - margin * 2 - 120, width - margin * 2 - 120))
        x = (width - cover.width) // 2
        canvas.paste(cover, (x, y), cover)
        y += cover.height + 36

    podcast_name = episode.podcast.title if episode.podcast else "小宇宙播客"
    draw.text((margin + 48, y), podcast_name, fill=accent, font=meta_font)
    y += 52

    title_lines = _wrap_text(episode.title, title_font, width - margin * 2 - 96)
    for line in title_lines[:4]:
        draw.text((margin + 48, y), line, fill=text_color, font=title_font)
        y += options.font_size_title + 12

    meta_parts = [
        format_duration(episode.duration_sec),
        format_pub_date(episode.pub_date),
    ]
    meta = " · ".join(part for part in meta_parts if part)
    if meta:
        y += 12
        draw.text((margin + 48, y), meta, fill=(90, 90, 90), font=meta_font)

    footer = options.watermark
    draw.text((margin + 48, card_box[3] - 72), footer, fill=accent, font=meta_font)
    return canvas


def render_content_card(
    episode: EpisodeInfo,
    segment: CardSegment,
    *,
    page_no: int,
    total_pages: int,
    options: RenderOptions,
) -> Image.Image:
    width, height = options.width, options.height
    accent = _hex_to_rgb(options.accent_color)
    background = _hex_to_rgb(options.background_color)
    text_color = _hex_to_rgb(options.text_color)

    canvas = Image.new("RGB", (width, height), background)
    draw = ImageDraw.Draw(canvas)
    margin = 72

    draw.rounded_rectangle((margin, margin, width - margin, height - margin), 36, (255, 255, 255))
    draw.rectangle((margin, margin, width - margin, margin + 12), fill=accent)

    title_font = _load_font(options.font_size_title - 8)
    body_font = _load_font(options.font_size_body)
    meta_font = _load_font(options.font_size_meta)

    podcast_name = episode.podcast.title if episode.podcast else "小宇宙播客"
    draw.text((margin + 48, margin + 40), podcast_name, fill=accent, font=meta_font)

    y = margin + 96
    if segment.title and segment.kind != "cover":
        for line in _wrap_text(segment.title, title_font, width - margin * 2 - 96)[:3]:
            draw.text((margin + 48, y), line, fill=text_color, font=title_font)
            y += options.font_size_title

    y += 16
    for line in _wrap_text(segment.body, body_font, width - margin * 2 - 96):
        if y > height - margin - 120:
            break
        draw.text((margin + 48, y), line, fill=text_color, font=body_font)
        y += options.font_size_body + 10

    footer_left = episode.title[:28] + ("…" if len(episode.title) > 28 else "")
    footer_right = f"{page_no}/{total_pages}"
    draw.text((margin + 48, height - margin - 64), footer_left, fill=(120, 120, 120), font=meta_font)
    draw.text((width - margin - 48 - meta_font.getlength(footer_right), height - margin - 64), footer_right, fill=accent, font=meta_font)
    return canvas


def render_cards(
    episode: EpisodeInfo,
    segments: list[CardSegment],
    output_dir: str | Path,
    *,
    options: RenderOptions | None = None,
    client: httpx.Client | None = None,
) -> list[Path]:
    options = options or RenderOptions()
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    owns_client = client is None
    if owns_client:
        client = httpx.Client(headers=DEFAULT_HEADERS, follow_redirects=True, timeout=30.0)

    cover_image = _download_image(episode.image_url, client)
    saved: list[Path] = []
    content_segments = [segment for segment in segments if segment.kind != "cover"]
    total_pages = max(len(content_segments), 1)

    try:
        page_no = 0
        for segment in segments:
            if segment.kind == "cover":
                image = render_cover_card(episode, cover_image=cover_image, options=options)
                filename = "00_cover.png"
            else:
                page_no += 1
                image = render_content_card(
                    episode,
                    segment,
                    page_no=page_no,
                    total_pages=total_pages,
                    options=options,
                )
                filename = f"{segment.index:02d}_{segment.kind}.png"

            path = output_path / filename
            image.save(path, format="PNG", optimize=True)
            saved.append(path)
        return saved
    finally:
        if owns_client and client is not None:
            client.close()
