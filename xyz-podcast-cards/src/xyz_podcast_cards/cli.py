from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Optional

import typer

from .comic_renderer import render_comic_cards
from .content import build_segments_from_episode
from .fetcher import FetchError, fetch_episode, format_duration, format_pub_date
from .models import RenderOptions
from .renderer import render_cards
from .summarizer import summarize_episode
from .transcript import TranscriptError, fetch_transcript_paragraphs, load_credentials

app = typer.Typer(
    add_completion=False,
    help="将小宇宙播客单集提取为可分享的图文卡片。",
)


class ContentSource(str, Enum):
    auto = "auto"
    description = "description"
    shownotes = "shownotes"
    transcript = "transcript"


@app.command("extract")
def extract_command(
    episode: str = typer.Argument(..., help="小宇宙单集链接或 episode_id"),
    output: Path = typer.Option(Path("./output"), "--output", "-o", help="卡片输出目录"),
    source: ContentSource = typer.Option(
        ContentSource.auto,
        "--source",
        "-s",
        help="卡片内容来源：auto/description/shownotes/transcript",
    ),
    credentials: Optional[Path] = typer.Option(
        None,
        "--credentials",
        help="可选，获取逐字稿时使用的 credentials.json",
    ),
    max_chars: int = typer.Option(280, "--max-chars", help="单张卡片最大字符数"),
    metadata: bool = typer.Option(True, "--metadata/--no-metadata", help="是否保存 episode.json"),
) -> None:
    """提取单集并生成图文卡片。"""
    try:
        episode_info = fetch_episode(episode)
    except FetchError as exc:
        typer.secho(f"错误: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    transcript_paragraphs = None
    if source == ContentSource.transcript:
        if not credentials:
            typer.secho("使用 transcript 来源时必须提供 --credentials", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1)
        if not episode_info.transcript_media_id:
            typer.secho("该单集没有可用的逐字稿 media id", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1)
        try:
            creds = load_credentials(credentials)
            transcript_paragraphs = fetch_transcript_paragraphs(
                eid=episode_info.eid,
                media_id=episode_info.transcript_media_id,
                credentials=creds,
            )
        except (TranscriptError, OSError, ValueError) as exc:
            typer.secho(f"逐字稿获取失败: {exc}", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1) from exc

    options = RenderOptions(max_chars_per_card=max_chars)
    segments = build_segments_from_episode(
        episode_info,
        source=source.value,
        transcript_paragraphs=transcript_paragraphs,
        options=options,
    )
    output.mkdir(parents=True, exist_ok=True)
    saved = render_cards(episode_info, segments, output, options=options)

    if metadata:
        metadata_path = output / "episode.json"
        metadata_path.write_text(
            episode_info.model_dump_json(indent=2, exclude_none=True),
            encoding="utf-8",
        )

    typer.secho(f"已生成 {len(saved)} 张卡片，输出目录: {output.resolve()}", fg=typer.colors.GREEN)
    for path in saved:
        typer.echo(f"  - {path.name}")


@app.command("info")
def info_command(
    episode: str = typer.Argument(..., help="小宇宙单集链接或 episode_id"),
) -> None:
    """查看单集元数据，不生成卡片。"""
    try:
        episode_info = fetch_episode(episode)
    except FetchError as exc:
        typer.secho(f"错误: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"标题: {episode_info.title}")
    if episode_info.podcast:
        typer.echo(f"播客: {episode_info.podcast.title}")
    typer.echo(f"时长: {format_duration(episode_info.duration_sec)}")
    typer.echo(f"发布: {format_pub_date(episode_info.pub_date)}")
    typer.echo(f"链接: {episode_info.episode_url}")
    typer.echo(f"逐字稿: {'有' if episode_info.transcript_media_id else '无'}")


@app.command("comic")
def comic_command(
    episode: str = typer.Argument(..., help="小宇宙单集链接或 episode_id"),
    output: Path = typer.Option(Path("./output-comic"), "--output", "-o", help="漫画卡片输出目录"),
) -> None:
    """AI 摘要 + 简笔漫画风精致卡片（sketch 小人）。"""
    try:
        episode_info = fetch_episode(episode)
    except FetchError as exc:
        typer.secho(f"错误: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    summary = summarize_episode(episode_info)
    saved, _ = render_comic_cards(episode_info, output, summary=summary)

    typer.secho(
        f"已生成 {len(saved)} 张漫画卡片 · 播客: {episode_info.podcast.title if episode_info.podcast else '未知'}",
        fg=typer.colors.GREEN,
    )
    typer.echo(f"核心问题: {summary.core_question}")
    typer.echo(f"输出目录: {output.resolve()}")
    for path in saved:
        typer.echo(f"  - {path.name}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
