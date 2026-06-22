from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from xyz_podcast_cards.asr import AsrError, transcribe_audio_file
from xyz_podcast_cards.audio_downloader import AudioDownloadError, download_episode_audio
from xyz_podcast_cards.models import EpisodeInfo, PodcastInfo
from xyz_podcast_cards.pipeline import run_asr_pipeline


def _sample_episode(*, audio_url: str = "https://media.example.com/ep.m4a") -> EpisodeInfo:
    return EpisodeInfo(
        eid="abc123abc123abc123abc123",
        pid="pid",
        title="测试单集",
        audio_url=audio_url,
        podcast=PodcastInfo(pid="pid", title="知行小酒馆"),
    )


class _FakeStreamResponse:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def __enter__(self) -> _FakeStreamResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def raise_for_status(self) -> None:
        return None

    def iter_bytes(self, chunk_size: int = 0) -> list[bytes]:
        return [self._payload]


class _FakeClient:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def stream(self, method: str, url: str) -> _FakeStreamResponse:
        return _FakeStreamResponse(self._payload)

    def close(self) -> None:
        return None


def test_download_episode_audio_writes_file(tmp_path: Path) -> None:
    episode = _sample_episode()
    client = _FakeClient(b"fake-audio-bytes")
    saved = download_episode_audio(episode, tmp_path, client=client)  # type: ignore[arg-type]
    assert saved.exists()
    assert saved.read_bytes() == b"fake-audio-bytes"
    assert saved.suffix == ".m4a"


def test_download_episode_audio_requires_url(tmp_path: Path) -> None:
    episode = _sample_episode(audio_url="")
    with pytest.raises(AudioDownloadError):
        download_episode_audio(episode, tmp_path)


def test_transcribe_audio_file_builds_document(tmp_path: Path) -> None:
    audio_path = tmp_path / "clip.m4a"
    audio_path.write_bytes(b"audio")

    fake_segment = SimpleNamespace(text="  你好世界  ", start=1.0, end=2.5)
    fake_whisper = MagicMock()
    fake_whisper.transcribe.return_value = ([fake_segment], SimpleNamespace(language="zh"))

    with patch("xyz_podcast_cards.asr._require_faster_whisper", return_value=lambda *_a, **_k: fake_whisper):
        document = transcribe_audio_file(
            audio_path,
            eid="eid",
            title="标题",
            model_name="tiny",
            device="cpu",
        )

    assert document.source == "asr-whisper"
    assert document.segments[0].text == "你好世界"
    assert document.segments[0].start_ms == 1000
    assert document.full_text == "你好世界"


def test_transcribe_audio_file_missing_path(tmp_path: Path) -> None:
    with pytest.raises(AsrError):
        transcribe_audio_file(tmp_path / "missing.m4a")


@patch("xyz_podcast_cards.pipeline.transcribe_audio_file")
@patch("xyz_podcast_cards.pipeline.download_episode_audio")
def test_run_asr_pipeline(
    mock_download: MagicMock,
    mock_transcribe: MagicMock,
    tmp_path: Path,
) -> None:
    from xyz_podcast_cards.transcript_models import TranscriptDocument, TranscriptSegment

    episode = _sample_episode()
    audio_path = tmp_path / "audio" / "test.m4a"
    audio_path.parent.mkdir(parents=True)
    audio_path.write_bytes(b"x")
    mock_download.return_value = audio_path
    mock_transcribe.return_value = TranscriptDocument(
        eid=episode.eid,
        title=episode.title,
        segments=[
            TranscriptSegment(text="我觉得工作很重要。", start_ms=0, end_ms=2000),
            TranscriptSegment(text="其实价值感也可以来自爱好。", start_ms=2000, end_ms=4000),
        ],
        source="asr-whisper",
    )

    result = run_asr_pipeline(
        episode,
        output_dir=tmp_path / "out",
        card_style="extract",
        keep_audio=True,
    )

    assert (tmp_path / "out" / "transcript.txt").exists()
    assert (tmp_path / "out" / "summary.json").exists()
    assert "extract" in result["cards"]
    mock_download.assert_called_once()
    mock_transcribe.assert_called_once()
