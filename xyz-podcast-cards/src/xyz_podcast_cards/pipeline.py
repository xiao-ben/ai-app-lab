from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal

from .comic_renderer import render_comic_cards
from .content import build_segments_from_episode
from .fetcher import EpisodeInfo, fetch_episode
from .models import Credentials, RenderOptions
from .renderer import render_cards
from .public_script import PublicScriptError, build_public_script_document
from .summarizer import EpisodeSummary, summarize_episode
from .transcript import TranscriptError, fetch_transcript_document, load_credentials
from .transcript_models import TranscriptDocument
from .transcript_summarizer import render_summary_markdown, summarize_from_transcript

DEFAULT_CREDENTIAL_PATHS = (
    Path("credentials.json"),
    Path.home() / ".xyz" / "credentials.json",
    Path.home() / ".config" / "xyz-podcast-cards" / "credentials.json",
)


def resolve_credentials(path: str | Path | None) -> Path:
    if path:
        candidate = Path(path)
        if candidate.exists():
            return candidate
        raise FileNotFoundError(f"未找到 credentials 文件: {candidate}")

    env_path = os.environ.get("XIAOYUZHOU_CREDENTIALS", "").strip()
    if env_path and Path(env_path).exists():
        return Path(env_path)

    for candidate in DEFAULT_CREDENTIAL_PATHS:
        if candidate.exists():
            return candidate

    raise FileNotFoundError(
        "未找到小宇宙登录凭证。请提供 --credentials credentials.json，"
        "或设置环境变量 XIAOYUZHOU_CREDENTIALS。"
    )


def save_transcript_files(document: TranscriptDocument, output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "json": output_dir / "transcript.json",
        "txt": output_dir / "transcript.txt",
        "srt": output_dir / "transcript.srt",
    }
    paths["json"].write_text(document.model_dump_json(indent=2, ensure_ascii=False), encoding="utf-8")
    paths["txt"].write_text(document.to_plain_text(), encoding="utf-8")
    paths["srt"].write_text(document.to_srt(), encoding="utf-8")
    return paths


def _save_summary_files(
    episode: EpisodeInfo,
    document: TranscriptDocument,
    summary: EpisodeSummary,
    output_path: Path,
) -> tuple[Path, Path]:
    summary_md_path = output_path / "summary.md"
    summary_md_path.write_text(render_summary_markdown(episode, document, summary), encoding="utf-8")
    summary_json_path = output_path / "summary.json"
    summary_json_path.write_text(
        json.dumps(
            {
                "episode_title": episode.title,
                "episode_url": episode.episode_url,
                "source": document.source,
                "core_question": summary.core_question,
                "hook": summary.hook,
                "takeaways": summary.takeaways,
                "segment_count": len(document.segments),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return summary_md_path, summary_json_path


def _render_cards_from_document(
    episode: EpisodeInfo,
    document: TranscriptDocument,
    summary: EpisodeSummary,
    output_path: Path,
    *,
    card_style: Literal["extract", "comic", "both"],
    max_chars: int,
) -> dict[str, list[Path]]:
    cards: dict[str, list[Path]] = {}
    options = RenderOptions(max_chars_per_card=max_chars)
    paragraphs = document.paragraphs(group_size=8)

    if card_style in {"extract", "both"}:
        extract_dir = output_path / "cards-extract"
        segments = build_segments_from_episode(
            episode,
            source="transcript",
            transcript_paragraphs=paragraphs,
            options=options,
        )
        cards["extract"] = render_cards(episode, segments, extract_dir, options=options)

    if card_style in {"comic", "both"}:
        comic_dir = output_path / "cards-comic"
        saved_comic, _ = render_comic_cards(episode, comic_dir, summary=summary)
        cards["comic"] = saved_comic
    return cards


def run_public_pipeline(
    episode: EpisodeInfo,
    *,
    output_dir: str | Path,
    card_style: Literal["extract", "comic", "both"] = "both",
    max_chars: int = 280,
) -> dict[str, object]:
    """xyz-dl 同款免登录方案：公开页 __NEXT_DATA__ → 节目文稿 → 摘要 → 卡片。"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    document = build_public_script_document(episode)
    transcript_paths = save_transcript_files(document, output_path)

    if document.source == "public-web":
        summary = summarize_episode(episode)
        if len(document.segments) >= 3:
            from .transcript_summarizer import summarize_from_transcript

            summary = summarize_from_transcript(episode, document, max_cards=min(6, max(3, len(document.segments) // 4)))
    else:
        summary = summarize_from_transcript(episode, document)

    summary_md_path, summary_json_path = _save_summary_files(episode, document, summary, output_path)

    result: dict[str, object] = {
        "transcript": document,
        "summary": summary,
        "transcript_paths": transcript_paths,
        "summary_md": summary_md_path,
        "summary_json": summary_json_path,
        "cards": _render_cards_from_document(
            episode,
            document,
            summary,
            output_path,
            card_style=card_style,
            max_chars=max_chars,
        ),
    }

    episode_json = output_path / "episode.json"
    episode_json.write_text(episode.model_dump_json(indent=2, exclude_none=True), encoding="utf-8")
    result["episode_json"] = episode_json
    return result


def run_transcript_pipeline(
    episode: EpisodeInfo,
    *,
    credentials: Credentials,
    output_dir: str | Path,
    card_style: Literal["extract", "comic", "both"] = "both",
    max_chars: int = 280,
) -> dict[str, object]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    document = fetch_transcript_document(
        eid=episode.eid,
        media_id=episode.transcript_media_id,
        title=episode.title,
        credentials=credentials,
    )
    transcript_paths = save_transcript_files(document, output_path)
    summary = summarize_from_transcript(episode, document)
    summary_md_path, summary_json_path = _save_summary_files(episode, document, summary, output_path)

    result: dict[str, object] = {
        "transcript": document,
        "summary": summary,
        "transcript_paths": transcript_paths,
        "summary_md": summary_md_path,
        "summary_json": summary_json_path,
        "cards": _render_cards_from_document(
            episode,
            document,
            summary,
            output_path,
            card_style=card_style,
            max_chars=max_chars,
        ),
    }

    episode_json = output_path / "episode.json"
    episode_json.write_text(episode.model_dump_json(indent=2, exclude_none=True), encoding="utf-8")
    result["episode_json"] = episode_json
    return result

