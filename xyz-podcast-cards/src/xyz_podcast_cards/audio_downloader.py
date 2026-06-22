from __future__ import annotations

import re
from pathlib import Path

import httpx

from .fetcher import DEFAULT_HEADERS, EpisodeInfo


class AudioDownloadError(RuntimeError):
    pass


def _safe_filename(value: str, *, max_len: int = 80) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*]', "", value).strip()
    cleaned = re.sub(r"\s+", "_", cleaned)
    return cleaned[:max_len] or "episode"


def _guess_extension(audio_url: str) -> str:
    lowered = audio_url.lower().split("?", 1)[0]
    for ext in (".m4a", ".mp3", ".aac", ".wav", ".ogg"):
        if lowered.endswith(ext):
            return ext
    return ".m4a"


def download_episode_audio(
    episode: EpisodeInfo,
    output_dir: str | Path,
    *,
    filename: str | None = None,
    client: httpx.Client | None = None,
) -> Path:
    """免登录下载公开单集音频（参考 casts_down / xyz-dl 公开页方案）。"""
    if not episode.audio_url:
        raise AudioDownloadError("该单集没有公开音频链接")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    ext = _guess_extension(episode.audio_url)
    target = output_path / (filename or f"{_safe_filename(episode.title)}_{episode.eid}{ext}")

    headers = {
        **DEFAULT_HEADERS,
        "Referer": "https://www.xiaoyuzhoufm.com/",
    }

    owns_client = client is None
    if owns_client:
        client = httpx.Client(headers=headers, follow_redirects=True, timeout=httpx.Timeout(3600.0))

    temp_path = target.with_suffix(target.suffix + ".part")
    try:
        with client.stream("GET", episode.audio_url) as response:
            response.raise_for_status()
            with temp_path.open("wb") as handle:
                for chunk in response.iter_bytes(chunk_size=1024 * 256):
                    handle.write(chunk)
        if target.exists():
            target.unlink()
        temp_path.rename(target)
        return target
    except httpx.HTTPError as exc:
        raise AudioDownloadError(f"音频下载失败: {exc}") from exc
    finally:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)
        if owns_client and client is not None:
            client.close()
