from __future__ import annotations

import re
from typing import Any

from .fetcher import DEFAULT_HEADERS, episode_page_url, extract_next_data
from .models import EpisodeInfo
from .parser import html_to_text, merge_description_and_shownotes, normalize_text
from .transcript_models import TranscriptDocument, TranscriptSegment

TIMELINE_LINE_RE = re.compile(r"^(\d{1,2}:\d{2}(?::\d{2})?)\s+(.+)$", re.MULTILINE)
STORY_HEADER_RE = re.compile(r"^🟤\s*\d+\s*(.+)$", re.MULTILINE)


class PublicScriptError(RuntimeError):
    pass


def _timestamp_to_ms(value: str) -> int:
    parts = value.strip().split(":")
    try:
        if len(parts) == 2:
            minutes, seconds = (int(parts[0]), int(parts[1]))
            return (minutes * 60 + seconds) * 1000
        if len(parts) == 3:
            hours, minutes, seconds = (int(parts[0]), int(parts[1]), int(parts[2]))
            return (hours * 3600 + minutes * 60 + seconds) * 1000
    except ValueError:
        return 0
    return 0


def fetch_public_episode_payload(eid: str, *, client: Any | None = None) -> dict[str, Any]:
    """与 xyz-dl 相同：从公开单集页 __NEXT_DATA__ 读取 episode JSON。"""
    import httpx

    url = episode_page_url(eid)
    owns_client = client is None
    if owns_client:
        client = httpx.Client(headers=DEFAULT_HEADERS, follow_redirects=True, timeout=30.0)
    try:
        response = client.get(url)
        response.raise_for_status()
        payload = extract_next_data(response.text)
        episode = payload.get("props", {}).get("pageProps", {}).get("episode")
        if not isinstance(episode, dict) or not episode:
            raise PublicScriptError(f"公开页面未找到单集数据: {eid}")
        return episode
    except httpx.HTTPError as exc:
        raise PublicScriptError(f"请求公开单集页面失败: {exc}") from exc
    finally:
        if owns_client and client is not None:
            client.close()


def _intro_segments(text: str) -> list[TranscriptSegment]:
    segments: list[TranscriptSegment] = []
    for paragraph in normalize_text(text).split("\n\n"):
        paragraph = paragraph.strip()
        if not paragraph or paragraph.startswith("🟤"):
            continue
        if TIMELINE_LINE_RE.search(paragraph):
            continue
        segments.append(TranscriptSegment(text=paragraph, speaker="shownotes"))
    return segments


def _timeline_segments(text: str) -> list[TranscriptSegment]:
    segments: list[TranscriptSegment] = []
    current_speaker = ""

    for line in normalize_text(text).split("\n"):
        line = line.strip()
        if not line:
            continue

        story_match = STORY_HEADER_RE.match(line)
        if story_match:
            current_speaker = story_match.group(1).strip()
            segments.append(TranscriptSegment(text=f"【{current_speaker}】", speaker=current_speaker))
            continue

        timeline_match = TIMELINE_LINE_RE.match(line)
        if timeline_match:
            stamp, body = timeline_match.groups()
            prefix = f"{current_speaker}：" if current_speaker else ""
            segments.append(
                TranscriptSegment(
                    text=f"{prefix}{body.strip()}",
                    start_ms=_timestamp_to_ms(stamp),
                    speaker=current_speaker or "timeline",
                )
            )
            continue

    return segments


def build_public_script_document(episode: EpisodeInfo, payload: dict[str, Any] | None = None) -> TranscriptDocument:
    payload = payload or fetch_public_episode_payload(episode.eid)
    merged = merge_description_and_shownotes(
        payload.get("description", episode.description),
        payload.get("shownotes", episode.shownotes_html),
    )
    if not merged.strip():
        raise PublicScriptError("公开页面中没有可用的节目文稿（description / shownotes 为空）")

    segments: list[TranscriptSegment] = []
    segments.extend(_intro_segments(merged))
    segments.extend(_timeline_segments(merged))

    if not segments:
        plain = html_to_text(payload.get("shownotes", "")) or normalize_text(payload.get("description", ""))
        for paragraph in plain.split("\n\n"):
            paragraph = paragraph.strip()
            if paragraph:
                segments.append(TranscriptSegment(text=paragraph, speaker="shownotes"))

    return TranscriptDocument(
        eid=episode.eid,
        title=episode.title,
        media_id=payload.get("transcriptMediaId", episode.transcript_media_id),
        source="public-web",
        segments=segments,
    )
