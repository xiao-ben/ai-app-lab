from __future__ import annotations

import json
from pathlib import Path

from xyz_podcast_cards.content import build_segments_from_episode
from xyz_podcast_cards.fetcher import episode_from_payload, extract_next_data, parse_episode_id
from xyz_podcast_cards.parser import html_to_text, split_sections

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE_EPISODE_ID = "6888a0148e06fe8de74811af"


def test_parse_episode_id_from_url() -> None:
    assert parse_episode_id("https://www.xiaoyuzhoufm.com/episode/6888a0148e06fe8de74811af") == SAMPLE_EPISODE_ID
    assert parse_episode_id("6888a0148e06fe8de74811af") == SAMPLE_EPISODE_ID


def test_extract_next_data_from_fixture() -> None:
    html = (FIXTURES / "episode_page_snippet.html").read_text(encoding="utf-8")
    payload = extract_next_data(html)
    episode = payload["props"]["pageProps"]["episode"]
    info = episode_from_payload(episode, f"https://www.xiaoyuzhoufm.com/episode/{episode['eid']}")
    assert info.title
    assert info.podcast is not None
    assert info.transcript_media_id


def test_split_sections() -> None:
    text = "🕰️ 摘要\n这是摘要内容。\n\n💿 时间轴\n00:00 开场"
    sections = split_sections(text)
    assert len(sections) >= 2
    assert "摘要" in sections[0][0]


def test_build_segments_contains_cover() -> None:
    html = (FIXTURES / "episode_page_snippet.html").read_text(encoding="utf-8")
    payload = extract_next_data(html)
    episode = episode_from_payload(
        payload["props"]["pageProps"]["episode"],
        "https://www.xiaoyuzhoufm.com/episode/test",
    )
    segments = build_segments_from_episode(episode)
    assert segments[0].kind == "cover"
    assert len(segments) > 1


def test_html_to_text_strips_tags() -> None:
    text = html_to_text("<p>你好<br/>世界</p>")
    assert "你好" in text
    assert "世界" in text
