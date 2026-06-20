from __future__ import annotations

import json
from pathlib import Path

import httpx
from PIL import Image, ImageDraw

from .comic_characters import draw_doodles, draw_stick_character
from .fetcher import DEFAULT_HEADERS, format_duration, format_pub_date
from .models import EpisodeInfo
from .renderer import _download_image, _hex_to_rgb, _load_font, _wrap_text
from .summarizer import ComicCardContent, EpisodeSummary, summarize_episode

PALETTE_MAP = {
    "cream": ("#F7F1E8", "#FFFDF8", "#FF6B35"),
    "mint": ("#E4F4EF", "#F8FFFC", "#3AA68B"),
    "blush": ("#F8E8EE", "#FFFAFC", "#E76F8F"),
    "lavender": ("#ECE8F7", "#FAF8FF", "#7B6FD6"),
    "peach": ("#FFEDE3", "#FFFAF6", "#FF8C42"),
    "sky": ("#E5F1FA", "#F8FCFF", "#4A90D9"),
}


def _speech_bubble(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    *,
    fill: tuple[int, int, int],
    outline: tuple[int, int, int],
    tail: tuple[int, int] | None = None,
) -> None:
    draw.rounded_rectangle(box, radius=28, fill=fill, outline=outline, width=3)
    if tail:
        tx, ty = tail
        draw.polygon([(tx, ty), (tx + 18, ty + 24), (tx + 34, ty)], fill=fill, outline=outline)


def render_comic_card(
    episode: EpisodeInfo,
    card: ComicCardContent,
    *,
    page_no: int,
    total_pages: int,
    width: int = 1080,
    height: int = 1440,
    cover_image: Image.Image | None = None,
    card_index: int = 0,
) -> Image.Image:
    bg_top, bg_bottom, accent = (_hex_to_rgb(PALETTE_MAP.get(card.palette, PALETTE_MAP["cream"])[i]) for i in range(3))
    canvas = Image.new("RGB", (width, height), bg_top)
    draw = ImageDraw.Draw(canvas)

    for y in range(height):
        ratio = y / height
        color = tuple(int(bg_top[i] * (1 - ratio) + bg_bottom[i] * ratio) for i in range(3))
        draw.line((0, y, width, y), fill=color)

    draw_doodles(draw, width, height, seed=card_index * 17 + page_no, accent=accent)

    margin = 64
    panel = (margin, margin, width - margin, height - margin - 20)
    draw.rounded_rectangle(panel, radius=40, fill=(255, 255, 255), outline=accent, width=4)

    inset = (panel[0] + 18, panel[1] + 18, panel[2] - 18, panel[3] - 18)
    draw.rounded_rectangle(inset, radius=30, outline=(230, 230, 230), width=2)

    title_font = _load_font(46)
    subtitle_font = _load_font(30)
    body_font = _load_font(34)
    meta_font = _load_font(26)
    quote_font = _load_font(32)

    ink = (35, 35, 35)
    y = panel[1] + 42

    podcast = episode.podcast.title if episode.podcast else "小宇宙播客"
    draw.text((panel[0] + 36, y), f"✦ {podcast}", fill=accent, font=meta_font)
    y += 48

    if page_no == 1 and cover_image is not None:
        thumb = cover_image.copy()
        thumb.thumbnail((220, 220), Image.Resampling.LANCZOS)
        canvas.paste(thumb, (panel[2] - 36 - thumb.width, panel[1] + 36), thumb)

    title_lines = _wrap_text(card.title, title_font, panel[2] - panel[0] - 120)[:3]
    for line in title_lines:
        line_width = title_font.getlength(line)
        draw.rounded_rectangle(
            (panel[0] + 32, y + title_font.size - 6, panel[0] + 36 + line_width, y + title_font.size + 8),
            radius=6,
            fill=tuple(min(255, c + 120) for c in accent),
        )
        draw.text((panel[0] + 36, y), line, fill=ink, font=title_font)
        y += 58

    if card.subtitle:
        y += 8
        subtitle_lines = _wrap_text(card.subtitle, subtitle_font, panel[2] - panel[0] - 120)[:2]
        for line in subtitle_lines:
            draw.text((panel[0] + 36, y), line, fill=(100, 100, 100), font=subtitle_font)
            y += 40
        y += 6

    bubble_bottom = panel[3] - 260
    bubble_box = (panel[0] + 36, y, panel[2] - 220, bubble_bottom)
    _speech_bubble(
        draw,
        bubble_box,
        fill=(255, 255, 255),
        outline=accent,
        tail=(bubble_box[2] - 10, bubble_box[3] - 20),
    )

    content_y = bubble_box[1] + 28
    for bullet in card.bullets[:4]:
        wrapped = _wrap_text(bullet, body_font, bubble_box[2] - bubble_box[0] - 48)
        for line in wrapped[:4]:
            if content_y > bubble_box[3] - 40:
                break
            draw.text((bubble_box[0] + 24, content_y), f"• {line}" if line == wrapped[0] else f"  {line}", fill=ink, font=body_font)
            content_y += 42

    if card.quote and content_y < bubble_box[3] - 70:
        content_y += 12
        quote_lines = _wrap_text(f"「{card.quote}」", quote_font, bubble_box[2] - bubble_box[0] - 48)[:2]
        for line in quote_lines:
            draw.text((bubble_box[0] + 24, content_y), line, fill=accent, font=quote_font)
            content_y += 40

    char_x = panel[2] - 120
    char_y = panel[3] - 210
    draw_stick_character(draw, char_x, char_y, pose=card.character_pose, scale=1.15, accent=accent)

    footer = f"AI 漫画摘要 {page_no}/{total_pages}"
    meta = " · ".join(part for part in [format_duration(episode.duration_sec), format_pub_date(episode.pub_date)] if part)
    draw.text((panel[0] + 36, panel[3] - 52), footer, fill=accent, font=meta_font)
    if meta:
        draw.text((panel[0] + 36, panel[3] - 86), meta, fill=(130, 130, 130), font=meta_font)

    draw.text((panel[2] - 36 - meta_font.getlength("sketch"), panel[3] - 52), "sketch", fill=(180, 180, 180), font=meta_font)
    return canvas


def render_comic_cards(
    episode: EpisodeInfo,
    output_dir: str | Path,
    *,
    summary: EpisodeSummary | None = None,
    client: httpx.Client | None = None,
) -> tuple[list[Path], EpisodeSummary]:
    summary = summary or summarize_episode(episode)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    owns_client = client is None
    if owns_client:
        client = httpx.Client(headers=DEFAULT_HEADERS, follow_redirects=True, timeout=30.0)

    cover_image = _download_image(episode.image_url, client)
    saved: list[Path] = []
    total = len(summary.cards)

    try:
        for index, card in enumerate(summary.cards):
            image = render_comic_card(
                episode,
                card,
                page_no=index + 1,
                total_pages=total,
                cover_image=cover_image,
                card_index=index,
            )
            filename = f"{index:02d}_comic_{card.character_pose}.png"
            path = output_path / filename
            image.save(path, format="PNG", optimize=True)
            saved.append(path)

        summary_path = output_path / "ai_summary.json"
        summary_path.write_text(
            json.dumps(
                {
                    "episode_title": episode.title,
                    "episode_url": episode.episode_url,
                    "core_question": summary.core_question,
                    "hook": summary.hook,
                    "takeaways": summary.takeaways,
                    "cards": [
                        {
                            "title": card.title,
                            "subtitle": card.subtitle,
                            "bullets": card.bullets,
                            "quote": card.quote,
                            "pose": card.character_pose,
                            "palette": card.palette,
                        }
                        for card in summary.cards
                    ],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return saved, summary
    finally:
        if owns_client and client is not None:
            client.close()
