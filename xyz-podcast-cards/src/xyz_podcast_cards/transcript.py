from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx

from .fetcher import DEFAULT_HEADERS
from .models import Credentials

API_BASE = "https://api.xiaoyuzhoufm.com"


class TranscriptError(RuntimeError):
    pass


def load_credentials(path: str | Path) -> Credentials:
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


def _segments_to_paragraphs(segments: list[dict[str, Any]], *, group_size: int = 6) -> list[str]:
    texts = [str(item.get("text", "")).strip() for item in segments if item.get("text")]
    paragraphs: list[str] = []
    buffer: list[str] = []
    for text in texts:
        buffer.append(text)
        if len(buffer) >= group_size:
            paragraphs.append("".join(buffer))
            buffer = []
    if buffer:
        paragraphs.append("".join(buffer))
    return paragraphs


def fetch_transcript_paragraphs(
    *,
    eid: str,
    media_id: str,
    credentials: Credentials,
    client: httpx.Client | None = None,
    group_size: int = 6,
) -> list[str]:
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
        payload = transcript_response.json()

        if isinstance(payload, list):
            return _segments_to_paragraphs(payload, group_size=group_size)

        for key in ("data", "segments", "body", "content", "items"):
            value = payload.get(key) if isinstance(payload, dict) else None
            if isinstance(value, list):
                return _segments_to_paragraphs(value, group_size=group_size)

        raise TranscriptError("无法解析逐字稿 JSON 结构")
    except httpx.HTTPError as exc:
        raise TranscriptError(f"下载逐字稿失败: {exc}") from exc
    finally:
        if owns_client and client is not None:
            client.close()
