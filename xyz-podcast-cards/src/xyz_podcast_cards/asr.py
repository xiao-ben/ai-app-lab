from __future__ import annotations

from pathlib import Path

from .transcript_models import TranscriptDocument, TranscriptSegment


class AsrError(RuntimeError):
    pass


def _require_faster_whisper():
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise AsrError(
            "未安装 faster-whisper。请运行: pip install -e \".[asr]\""
        ) from exc
    return WhisperModel


def transcribe_audio_file(
    audio_path: Path,
    *,
    eid: str = "",
    title: str = "",
    model_name: str = "small",
    language: str = "zh",
    device: str = "auto",
) -> TranscriptDocument:
    """使用 faster-whisper 本地转写（参考 casts_down / podcast-transcription-skill）。"""
    if not audio_path.exists():
        raise AsrError(f"音频文件不存在: {audio_path}")

    WhisperModel = _require_faster_whisper()

    if device == "auto":
        try:
            whisper = WhisperModel(model_name, device="cuda")
            _ = whisper.model
        except Exception:
            whisper = WhisperModel(model_name, device="cpu")
    else:
        whisper = WhisperModel(model_name, device=device)

    segments_iter, info = whisper.transcribe(str(audio_path), language=language, word_timestamps=False)
    segments: list[TranscriptSegment] = []
    for item in segments_iter:
        text = (item.text or "").strip()
        if not text:
            continue
        segments.append(
            TranscriptSegment(
                text=text,
                start_ms=int(item.start * 1000),
                end_ms=int(item.end * 1000),
                speaker="asr",
            )
        )

    if not segments:
        raise AsrError("转写结果为空")

    return TranscriptDocument(
        eid=eid or audio_path.stem,
        title=title or audio_path.stem,
        media_id=str(audio_path),
        source="asr-whisper",
        segments=segments,
    )
