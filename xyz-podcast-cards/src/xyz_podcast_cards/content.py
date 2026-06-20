from __future__ import annotations

import re

from .models import CardSegment, EpisodeInfo, RenderOptions
from .parser import merge_description_and_shownotes, normalize_text, split_sections


def _chunk_text(text: str, max_chars: int) -> list[str]:
    text = normalize_text(text)
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current = ""

    def flush() -> None:
        nonlocal current
        if current.strip():
            chunks.append(current.strip())
        current = ""

    for paragraph in paragraphs:
        if len(paragraph) > max_chars:
            flush()
            sentence_parts = re.split(r"(?<=[。！？!?；;])", paragraph)
            buffer = ""
            for part in sentence_parts:
                if not part:
                    continue
                if len(buffer) + len(part) <= max_chars:
                    buffer += part
                else:
                    if buffer:
                        chunks.append(buffer.strip())
                    buffer = part
            if buffer:
                chunks.append(buffer.strip())
            continue

        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) <= max_chars:
            current = candidate
        else:
            flush()
            current = paragraph
    flush()
    return chunks


def build_segments_from_episode(
    episode: EpisodeInfo,
    *,
    source: str = "auto",
    transcript_paragraphs: list[str] | None = None,
    options: RenderOptions | None = None,
) -> list[CardSegment]:
    options = options or RenderOptions()
    segments: list[CardSegment] = [CardSegment(title=episode.title, body="", kind="cover", index=0)]

    if source == "transcript" and transcript_paragraphs:
        for idx, paragraph in enumerate(transcript_paragraphs, start=1):
            for chunk in _chunk_text(paragraph, options.max_chars_per_card):
                segments.append(
                    CardSegment(
                        title="逐字稿",
                        body=chunk,
                        kind="transcript",
                        index=len(segments),
                    )
                )
        return segments

    merged = merge_description_and_shownotes(episode.description, episode.shownotes_html)
    if source in {"description", "shownotes"}:
        merged = episode.description if source == "description" else merged

    sections = split_sections(merged)
    if not sections:
        for chunk in _chunk_text(merged, options.max_chars_per_card):
            segments.append(
                CardSegment(title=episode.title, body=chunk, kind="section", index=len(segments))
            )
        return segments

    for title, body in sections:
        content = body or title
        section_title = title if body else episode.title
        for chunk in _chunk_text(content, options.max_chars_per_card):
            segments.append(
                CardSegment(
                    title=section_title,
                    body=chunk,
                    kind="section",
                    index=len(segments),
                )
            )
    return segments
