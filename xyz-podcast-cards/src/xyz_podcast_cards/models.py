from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class PodcastInfo(BaseModel):
    pid: str
    title: str
    author: str = ""
    image_url: str = ""


class EpisodeInfo(BaseModel):
    eid: str
    pid: str
    title: str
    description: str = ""
    shownotes_html: str = ""
    duration_sec: int = 0
    image_url: str = ""
    audio_url: str = ""
    pub_date: datetime | None = None
    podcast: PodcastInfo | None = None
    transcript_media_id: str = ""
    episode_url: str = ""


class CardSegment(BaseModel):
    title: str = ""
    body: str
    kind: Literal["cover", "section", "transcript"] = "section"
    index: int = 0


class RenderOptions(BaseModel):
    width: int = 1080
    height: int = 1440
    max_chars_per_card: int = 280
    font_size_title: int = 52
    font_size_body: int = 38
    font_size_meta: int = 30
    accent_color: str = "#FF6B35"
    background_color: str = "#FFF8F0"
    text_color: str = "#1A1A1A"
    watermark: str = "小宇宙 · 播客卡片"


class Credentials(BaseModel):
    access_token: str = ""
    refresh_token: str = ""
    device_id: str = ""
