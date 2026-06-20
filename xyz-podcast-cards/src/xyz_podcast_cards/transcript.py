from __future__ import annotations

import json
from typing import Any

import httpx

from .fetcher import DEFAULT_HEADERS
from .models import Credentials
from .transcript_models import TranscriptDocument, TranscriptSegment

API_BASE = "https://api.xiaoyuzhoufm.com"


class TranscriptError(RuntimeError):
    pass


def load_credentials(path: str | Any) -> Credentials:
    from pathlib import Path

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return Credentials.model_validate(data)


def _api_headers(credentials: Credentials) -> dict[str, str]:
    headers = {
        **DEFAULT_HEADERS,
        "Content-Type": "application/json",
        "applicationid": "app.podcast.cosmos",
        "app-version": "2.99.1",
        "User-Agent": "Xiaoyuzhou/2.99.1(android 28)",
    }
    if credentials.access_token:
        headers["x-jike-access-token"] = credentials.access_token
    if credentials.device_id:
        headers["x-jike-device-id"] = credentials.device_id
    return headers


def _extract_transcript_url(payload: dict[str, Any]) -> str:
    data = payload.get("data") or payload
    if isinstance(data, dict):
        if data.get("transcriptUrl"):
            return data["transcriptUrl"]
        inner = data.get("data")
        if isinstance(inner, dict) and inner.get("transcriptUrl"):
            return inner["transcriptUrl"]
    raise TranscriptError("接口响应中未找到 transcriptUrl")


def _parse_segments(payload: Any) -> list[TranscriptSegment]:
    if isinstance(payload, list):
        raw_items = payload
    elif isinstance(payload, dict):
        raw_items = None
        for key in ("data", "segments", "body", "content", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                raw_items = value
                break
        if raw_items is None:
            raise TranscriptError("无法解析逐字稿 JSON 结构")
    else:
        raise TranscriptError("无法解析逐字稿 JSON 结构")

    segments: list[TranscriptSegment] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text", "")).strip()
        if not text:
            continue
        segments.append(
            TranscriptSegment(
                text=text,
                start_ms=int(item.get("startTime") or item.get("start") or item.get("begin") or 0),
                end_ms=int(item.get("endTime") or item.get("end") or item.get("finish") or 0),
                speaker=str(item.get("speaker") or item.get("role") or ""),
            )
        )
    return segments


def fetch_transcript_document(
    *,
    eid: str,
    media_id: str,
    title: str,
    credentials: Credentials,
    client: httpx.Client | None = None,
) -> TranscriptDocument:
    if not credentials.access_token or not credentials.device_id:
        raise TranscriptError("获取逐字稿需要 credentials.json 中的 access_token 与 device_id")

    owns_client = client is None
    if owns_client:
        client = httpx.Client(headers=_api_headers(credentials), timeout=30.0)

    try:
        response = client.post(
            f"{API_BASE}/v1/episode-transcript/get",
            json={"eid": eid, "mediaId": media_id},
        )
        if response.status_code == 401:
            raise TranscriptError("认证失败，请更新 access_token / device_id")
        response.raise_for_status()
        transcript_url = _extract_transcript_url(response.json())

        transcript_response = client.get(
            transcript_url,
            headers={
                "Host": "transcript-highlight.xyzcdn.net",
                "Accept": "application/json",
                "User-Agent": "Xiaoyuzhou/2.99.1(android 28)",
            },
        )
        transcript_response.raise_for_status()
        segments = _parse_segments(transcript_response.json())
        if not segments:
            raise TranscriptError("逐字稿为空")
        return TranscriptDocument(eid=eid, title=title, media_id=media_id, segments=segments)
    except httpx.HTTPError as exc:
        raise TranscriptError(f"下载逐字稿失败: {exc}") from exc
    finally:
        if owns_client and client is not None:
            client.close()


def fetch_transcript_paragraphs(
    *,
    eid: str,
    media_id: str,
    credentials: Credentials,
    client: httpx.Client | None = None,
    group_size: int = 6,
) -> list[str]:
    document = fetch_transcript_document(
        eid=eid,
        media_id=media_id,
        title="",
        credentials=credentials,
        client=client,
    )
    return document.paragraphs(group_size=group_size)
