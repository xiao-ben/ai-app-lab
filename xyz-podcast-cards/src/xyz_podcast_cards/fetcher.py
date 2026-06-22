from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx

from .models import EpisodeInfo, PodcastInfo

EPISODE_URL_RE = re.compile(
    r"(?:https?://)?(?:www\.)?xiaoyuzhoufm\.com/episode/([a-f0-9]+)",
    re.IGNORECASE,
)
EPISODE_ID_RE = re.compile(r"^[a-f0-9]{24}$", re.IGNORECASE)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9",
}


class FetchError(RuntimeError):
    pass


def parse_episode_id(value: str) -> str:
    value = value.strip()
    match = EPISODE_URL_RE.search(value)
    if match:
        return match.group(1)
    if EPISODE_ID_RE.fullmatch(value):
        return value
    raise FetchError(f"无法识别小宇宙单集链接或 ID: {value}")


def episode_page_url(eid: str) -> str:
    return f"https://www.xiaoyuzhoufm.com/episode/{eid}"


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _image_url(image: Any) -> str:
    if isinstance(image, str):
        return image
    if isinstance(image, dict):
        return (
            image.get("largePicUrl")
            or image.get("picUrl")
            or image.get("middlePicUrl")
            or image.get("thumbnailUrl")
            or ""
        )
    return ""


def _audio_url(episode: dict[str, Any]) -> str:
    media = episode.get("media") or {}
    source = media.get("source") or {}
    if source.get("url"):
        return source["url"]
    enclosure = episode.get("enclosure") or {}
    return enclosure.get("url", "")


def _parse_podcast(podcast: dict[str, Any] | None) -> PodcastInfo | None:
    if not podcast:
        return None
    return PodcastInfo(
        pid=podcast.get("pid", ""),
        title=podcast.get("title", ""),
        author=podcast.get("author", "") or podcast.get("publisher", ""),
        image_url=_image_url(podcast.get("image")),
    )


def episode_from_payload(episode: dict[str, Any], episode_url: str) -> EpisodeInfo:
    podcast = _parse_podcast(episode.get("podcast"))
    return EpisodeInfo(
        eid=episode.get("eid", ""),
        pid=episode.get("pid", "") or (podcast.pid if podcast else ""),
        title=episode.get("title", "").strip(),
        description=episode.get("description", "").strip(),
        shownotes_html=episode.get("shownotes", "") or "",
        duration_sec=int(episode.get("duration") or 0),
        image_url=_image_url(episode.get("image")),
        audio_url=_audio_url(episode),
        pub_date=_parse_datetime(episode.get("pubDate")),
        podcast=podcast,
        transcript_media_id=episode.get("transcriptMediaId", "") or "",
        episode_url=episode_url,
    )


def extract_next_data(html: str) -> dict[str, Any]:
    match = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        html,
        re.DOTALL,
    )
    if not match:
        raise FetchError("页面中未找到 __NEXT_DATA__，可能不是有效的小宇宙单集页")
    import json

    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise FetchError("解析页面数据失败") from exc


def fetch_episode(value: str, *, client: httpx.Client | None = None) -> EpisodeInfo:
    eid = parse_episode_id(value)
    url = episode_page_url(eid)
    owns_client = client is None
    if owns_client:
        client = httpx.Client(headers=DEFAULT_HEADERS, follow_redirects=True, timeout=30.0)
    try:
        response = client.get(url)
        response.raise_for_status()
        payload = extract_next_data(response.text)
        page_props = payload.get("props", {}).get("pageProps", {})
        episode = page_props.get("episode")
        if not episode:
            raise FetchError(f"未找到单集数据: {eid}")
        return episode_from_payload(episode, url)
    except httpx.HTTPError as exc:
        raise FetchError(f"请求单集页面失败: {exc}") from exc
    finally:
        if owns_client and client is not None:
            client.close()


def format_duration(seconds: int) -> str:
    if seconds <= 0:
        return ""
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def format_pub_date(value: datetime | None) -> str:
    if not value:
        return ""
    local = value.astimezone() if value.tzinfo else value.replace(tzinfo=timezone.utc).astimezone()
    return local.strftime("%Y-%m-%d")
