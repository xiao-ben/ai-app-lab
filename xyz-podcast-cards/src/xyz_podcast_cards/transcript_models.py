from __future__ import annotations

from pydantic import BaseModel, Field


class TranscriptSegment(BaseModel):
    text: str
    start_ms: int = 0
    end_ms: int = 0
    speaker: str = ""


class TranscriptDocument(BaseModel):
    eid: str
    title: str
    media_id: str = ""
    source: str = "official"
    segments: list[TranscriptSegment] = Field(default_factory=list)

    @property
    def full_text(self) -> str:
        return "".join(segment.text for segment in self.segments)

    def paragraphs(self, *, group_size: int = 8) -> list[str]:
        texts = [segment.text.strip() for segment in self.segments if segment.text.strip()]
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

    def to_plain_text(self) -> str:
        lines: list[str] = []
        for segment in self.segments:
            if not segment.text.strip():
                continue
            if segment.start_ms:
                stamp = _format_ms(segment.start_ms)
                lines.append(f"[{stamp}] {segment.text}")
            else:
                lines.append(segment.text)
        return "\n".join(lines)

    def to_srt(self) -> str:
        blocks: list[str] = []
        for index, segment in enumerate(self.segments, start=1):
            if not segment.text.strip():
                continue
            start = _format_srt(segment.start_ms)
            end = _format_srt(segment.end_ms or segment.start_ms + 2000)
            blocks.append(f"{index}\n{start} --> {end}\n{segment.text.strip()}\n")
        return "\n".join(blocks)


def _format_ms(value: int) -> str:
    seconds, ms = divmod(max(value, 0), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def _format_srt(value: int) -> str:
    seconds, ms = divmod(max(value, 0), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{ms:03d}"
