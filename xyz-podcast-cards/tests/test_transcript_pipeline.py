from xyz_podcast_cards.models import EpisodeInfo, PodcastInfo
from xyz_podcast_cards.transcript_models import TranscriptDocument, TranscriptSegment
from xyz_podcast_cards.transcript_summarizer import summarize_from_transcript


def _sample_document() -> TranscriptDocument:
    return TranscriptDocument(
        eid="test",
        title="测试单集",
        media_id="media",
        segments=[
            TranscriptSegment(text="欢迎来到知行小酒馆。", start_ms=0, end_ms=2000),
            TranscriptSegment(text="我觉得工作很重要，但它不该定义全部的我。", start_ms=2000, end_ms=5000),
            TranscriptSegment(text="其实价值感也可以来自陪伴、爱好和坦诚。", start_ms=5000, end_ms=8000),
            TranscriptSegment(text="小猫在新家打滚的那一刻，我突然觉得窝囊气都不重要了。", start_ms=8000, end_ms=12000),
            TranscriptSegment(text="原来坦白自己不行，并不会让爱消逝。", start_ms=12000, end_ms=15000),
            TranscriptSegment(text="所以最重要的是重新学会爱自己。", start_ms=15000, end_ms=18000),
        ],
    )


def test_summarize_from_transcript_builds_cards() -> None:
    episode = EpisodeInfo(
        eid="test",
        pid="pid",
        title="E234 当我不再被工作定义",
        podcast=PodcastInfo(pid="pid", title="知行小酒馆"),
    )
    summary = summarize_from_transcript(episode, _sample_document(), max_cards=2)
    assert summary.core_question
    assert len(summary.cards) >= 4
    assert any("逐字稿" in card.title for card in summary.cards)


def test_transcript_document_exports() -> None:
    document = _sample_document()
    assert "欢迎" in document.full_text
    assert "[00:02]" in document.to_plain_text()
    assert document.to_srt().startswith("1")
