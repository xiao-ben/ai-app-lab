from xyz_podcast_cards.fetcher import fetch_episode
from xyz_podcast_cards.public_script import build_public_script_document


def test_build_public_script_document_from_real_episode() -> None:
    episode = fetch_episode("69fd8a69e1eb34a939f868c0")
    document = build_public_script_document(episode)
    assert document.source == "public-web"
    assert len(document.segments) >= 5
    assert any("价值感" in segment.text or "工作" in segment.text for segment in document.segments)
    assert document.to_plain_text()


def test_public_script_parses_timeline_timestamp() -> None:
    from xyz_podcast_cards.models import EpisodeInfo, PodcastInfo

    episode = EpisodeInfo(
        eid="test",
        pid="pid",
        title="测试",
        description="🟤 01 小阳\n13:10 做编剧近十年后，我不再兴奋\n23:27 在家乡初春里骑行",
        podcast=PodcastInfo(pid="pid", title="测试播客"),
    )
    document = build_public_script_document(
        episode,
        payload={
            "description": episode.description,
            "shownotes": "",
            "transcriptMediaId": "",
        },
    )
    timed = [segment for segment in document.segments if segment.start_ms > 0]
    assert timed
    assert timed[0].start_ms == (13 * 60 + 10) * 1000
