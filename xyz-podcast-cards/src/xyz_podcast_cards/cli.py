from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Optional

import typer

from .comic_renderer import render_comic_cards
from .content import build_segments_from_episode
from .fetcher import FetchError, fetch_episode, format_duration, format_pub_date
from .models import RenderOptions
from .pipeline import resolve_credentials, run_asr_pipeline, run_public_pipeline, run_transcript_pipeline
from .public_script import PublicScriptError, build_public_script_document
from .renderer import render_cards
from .summarizer import summarize_episode
from .transcript import TranscriptError, fetch_transcript_document, load_credentials
from .audio_downloader import AudioDownloadError, download_episode_audio
from .asr import AsrError, transcribe_audio_file
from .xiaohei_renderer import prepare_xiaohei_output
from .xiaohei_shots import build_xiaohei_shots

app = typer.Typer(
    add_completion=False,
    help="将小宇宙播客单集提取为可分享的图文卡片。",
)


class ContentSource(str, Enum):
    auto = "auto"
    description = "description"
    shownotes = "shownotes"
    transcript = "transcript"


class CardStyle(str, Enum):
    extract = "extract"
    comic = "comic"
    both = "both"


@app.command("transcript")
def transcript_command(
    episode: str = typer.Argument(..., help="小宇宙单集链接或 episode_id"),
    output: Path = typer.Option(Path("./output-transcript"), "--output", "-o", help="逐字稿输出目录"),
    credentials: Optional[Path] = typer.Option(None, "--credentials", help="小宇宙 credentials.json"),
    public: bool = typer.Option(
        False,
        "--public",
        help="免登录模式：从公开页 ShowNotes/时间轴提取文稿（xyz-dl 同款方案）",
    ),
) -> None:
    """下载并解析逐字稿/节目文稿（txt / json / srt）。"""
    try:
        episode_info = fetch_episode(episode)
    except FetchError as exc:
        typer.secho(f"错误: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    from .pipeline import save_transcript_files

    output.mkdir(parents=True, exist_ok=True)

    if public:
        try:
            document = build_public_script_document(episode_info)
        except PublicScriptError as exc:
            typer.secho(f"公开文稿获取失败: {exc}", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1) from exc
        paths = save_transcript_files(document, output)
        typer.secho(
            f"已保存公开节目文稿（ShowNotes/时间轴），共 {len(document.segments)} 段",
            fg=typer.colors.GREEN,
        )
        typer.echo("说明：这不是口播 ASR 逐字稿；如需官方逐字稿请去掉 --public 并提供 credentials。")
        for name, path in paths.items():
            typer.echo(f"  - {name}: {path.name}")
        return

    try:
        cred_path = resolve_credentials(credentials)
        creds = load_credentials(cred_path)
    except (FileNotFoundError, OSError, ValueError) as exc:
        typer.secho(f"错误: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    if not episode_info.transcript_media_id:
        typer.secho("该单集没有可用的官方逐字稿", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    try:
        document = fetch_transcript_document(
            eid=episode_info.eid,
            media_id=episode_info.transcript_media_id,
            title=episode_info.title,
            credentials=creds,
        )
    except TranscriptError as exc:
        typer.secho(f"逐字稿获取失败: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    paths = save_transcript_files(document, output)
    typer.secho(f"已保存官方逐字稿，共 {len(document.segments)} 句", fg=typer.colors.GREEN)
    for name, path in paths.items():
        typer.echo(f"  - {name}: {path.name}")


@app.command("pipeline-public")
def pipeline_public_command(
    episode: str = typer.Argument(..., help="小宇宙单集链接或 episode_id"),
    output: Path = typer.Option(Path("./output-public"), "--output", "-o", help="输出目录"),
    style: CardStyle = typer.Option(CardStyle.both, "--style", help="生成卡片类型：extract/comic/both"),
    max_chars: int = typer.Option(280, "--max-chars", help="单张卡片最大字符数"),
) -> None:
    """免登录流水线：公开页文稿 → 文本摘要 → 卡片（xyz-dl 同款 __NEXT_DATA__ 方案）。"""
    try:
        episode_info = fetch_episode(episode)
        result = run_public_pipeline(
            episode_info,
            output_dir=output,
            card_style=style.value,
            max_chars=max_chars,
        )
    except (FetchError, PublicScriptError) as exc:
        typer.secho(f"流水线失败: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    summary = result["summary"]
    typer.secho("免登录流水线完成", fg=typer.colors.GREEN)
    typer.echo("文稿来源: 公开页 ShowNotes / 时间轴（非口播 ASR）")
    typer.echo(f"核心问题: {summary.core_question}")
    typer.echo(f"输出目录: {output.resolve()}")
    typer.echo("  - transcript.txt / summary.md")
    cards = result.get("cards", {})
    if "extract" in cards:
        typer.echo(f"  - cards-extract/ ({len(cards['extract'])} 张)")
    if "comic" in cards:
        typer.echo(f"  - cards-comic/ ({len(cards['comic'])} 张)")


@app.command("pipeline")
def pipeline_command(
    episode: str = typer.Argument(..., help="小宇宙单集链接或 episode_id"),
    output: Path = typer.Option(Path("./output-pipeline"), "--output", "-o", help="输出目录"),
    credentials: Optional[Path] = typer.Option(None, "--credentials", help="小宇宙 credentials.json"),
    style: CardStyle = typer.Option(CardStyle.both, "--style", help="生成卡片类型：extract/comic/both"),
    max_chars: int = typer.Option(280, "--max-chars", help="单张卡片最大字符数"),
) -> None:
    """逐字稿 → 文本摘要 → 图文/漫画卡片 一键流水线。"""
    try:
        episode_info = fetch_episode(episode)
        cred_path = resolve_credentials(credentials)
        creds = load_credentials(cred_path)
    except (FetchError, FileNotFoundError, OSError, ValueError) as exc:
        typer.secho(f"错误: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    if not episode_info.transcript_media_id:
        typer.secho("该单集没有可用的官方逐字稿", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    try:
        result = run_transcript_pipeline(
            episode_info,
            credentials=creds,
            output_dir=output,
            card_style=style.value,
            max_chars=max_chars,
        )
    except TranscriptError as exc:
        typer.secho(f"流水线失败: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    summary = result["summary"]
    typer.secho("流水线完成", fg=typer.colors.GREEN)
    typer.echo(f"核心问题: {summary.core_question}")
    typer.echo(f"输出目录: {output.resolve()}")
    typer.echo("  - transcript.txt / transcript.json / transcript.srt")
    typer.echo("  - summary.md / summary.json")
    cards = result.get("cards", {})
    if "extract" in cards:
        typer.echo(f"  - cards-extract/ ({len(cards['extract'])} 张)")
    if "comic" in cards:
        typer.echo(f"  - cards-comic/ ({len(cards['comic'])} 张)")


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
            cred_path = resolve_credentials(credentials)
            creds = load_credentials(cred_path)
            from .transcript import fetch_transcript_paragraphs

            transcript_paragraphs = fetch_transcript_paragraphs(
                eid=episode_info.eid,
                media_id=episode_info.transcript_media_id,
                credentials=creds,
            )
        except (TranscriptError, FileNotFoundError, OSError, ValueError) as exc:
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


@app.command("xiaohei")
def xiaohei_command(
    episode: str = typer.Argument(..., help="小宇宙单集链接或 episode_id"),
    output: Path = typer.Option(Path("./output-xiaohei"), "--output", "-o", help="小黑配图输出目录"),
    prompts_only: bool = typer.Option(False, "--prompts-only", help="仅输出 shot list 与提示词，不生图"),
    assets: Optional[Path] = typer.Option(
        None,
        "--assets",
        help="已生成图片目录（按 shot 文件名复制到 output）",
    ),
) -> None:
    """Ian 小黑怪诞正文配图 Skill：AI 摘要 + 16:9 白底手绘配图。"""
    try:
        episode_info = fetch_episode(episode)
    except FetchError as exc:
        typer.secho(f"错误: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    summary = summarize_episode(episode_info)
    shots = build_xiaohei_shots(episode_info, summary)
    output.mkdir(parents=True, exist_ok=True)

    if prompts_only:
        from .xiaohei_renderer import save_shot_list, write_preview_html

        save_shot_list(shots, output, episode=episode_info, summary=summary)
        write_preview_html(shots, output, title=episode_info.title)
        typer.secho(f"已输出 {len(shots)} 条 shot list → {output.resolve()}", fg=typer.colors.GREEN)
        typer.echo("请使用图像模型按 shot-list.json 中的 prompt 逐张生成。")
        return

    saved, _ = prepare_xiaohei_output(
        episode_info,
        output,
        summary=summary,
        assets_source=assets,
    )
    if not saved:
        typer.secho(
            "未找到已生成图片。请先使用图像模型生成，或通过 --assets 指定图片目录。",
            fg=typer.colors.YELLOW,
        )
        typer.echo(f"已写入 shot-list.json 与 preview.html → {output.resolve()}")
        return

    typer.secho(
        f"已准备 {len(saved)} 张小黑配图 · 播客: {episode_info.podcast.title if episode_info.podcast else '未知'}",
        fg=typer.colors.GREEN,
    )
    typer.echo(f"核心问题: {summary.core_question}")
    typer.echo(f"输出目录: {output.resolve()}")
    for path in saved:
        typer.echo(f"  - {path.name}")


@app.command("download-audio")
def download_audio_command(
    episode: str = typer.Argument(..., help="小宇宙单集链接或 episode_id"),
    output: Path = typer.Option(Path("./output-audio"), "--output", "-o", help="音频输出目录"),
) -> None:
    """免登录下载单集音频（多为 m4a，参考 casts_down / xyz-dl 公开页方案）。"""
    try:
        episode_info = fetch_episode(episode)
        audio_path = download_episode_audio(episode_info, output)
    except (FetchError, AudioDownloadError) as exc:
        typer.secho(f"错误: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    typer.secho(f"已下载音频: {audio_path.resolve()}", fg=typer.colors.GREEN)
    typer.echo(f"时长: {format_duration(episode_info.duration_sec)}")


@app.command("asr")
def asr_command(
    target: str = typer.Argument(..., help="小宇宙单集链接/episode_id，或本地音频文件路径"),
    output: Path = typer.Option(Path("./output-asr"), "--output", "-o", help="转写输出目录"),
    model: str = typer.Option("small", "--model", help="faster-whisper 模型：tiny/base/small/medium/large-v3"),
    device: str = typer.Option("auto", "--device", help="推理设备：auto/cpu/cuda"),
    language: str = typer.Option("zh", "--language", help="语言代码"),
) -> None:
    """使用 faster-whisper 本地转写音频为逐字稿（参考 casts_down）。"""
    from .pipeline import save_transcript_files

    audio_path: Path
    eid = ""
    title = ""

    candidate = Path(target)
    if candidate.exists() and candidate.is_file():
        audio_path = candidate
        eid = candidate.stem
        title = candidate.stem
    else:
        try:
            episode_info = fetch_episode(target)
        except FetchError as exc:
            typer.secho(f"错误: {exc}", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1) from exc
        try:
            audio_path = download_episode_audio(episode_info, output / "audio")
        except AudioDownloadError as exc:
            typer.secho(f"音频下载失败: {exc}", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1) from exc
        eid = episode_info.eid
        title = episode_info.title

    try:
        document = transcribe_audio_file(
            audio_path,
            eid=eid,
            title=title,
            model_name=model,
            device=device,
            language=language,
        )
    except AsrError as exc:
        typer.secho(f"转写失败: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    output.mkdir(parents=True, exist_ok=True)
    paths = save_transcript_files(document, output)
    typer.secho(f"转写完成，共 {len(document.segments)} 段", fg=typer.colors.GREEN)
    typer.echo(f"来源: faster-whisper ({model})")
    for name, path in paths.items():
        typer.echo(f"  - {name}: {path.name}")


@app.command("pipeline-asr")
def pipeline_asr_command(
    episode: str = typer.Argument(..., help="小宇宙单集链接或 episode_id"),
    output: Path = typer.Option(Path("./output-asr"), "--output", "-o", help="输出目录"),
    style: CardStyle = typer.Option(CardStyle.both, "--style", help="生成卡片类型：extract/comic/both"),
    max_chars: int = typer.Option(280, "--max-chars", help="单张卡片最大字符数"),
    model: str = typer.Option("small", "--model", help="faster-whisper 模型"),
    device: str = typer.Option("auto", "--device", help="推理设备：auto/cpu/cuda"),
    language: str = typer.Option("zh", "--language", help="语言代码"),
    keep_audio: bool = typer.Option(True, "--keep-audio/--no-keep-audio", help="转写后是否保留音频文件"),
) -> None:
    """免登录流水线：下载音频 → whisper 转写 → 摘要 → 卡片。"""
    try:
        episode_info = fetch_episode(episode)
        result = run_asr_pipeline(
            episode_info,
            output_dir=output,
            card_style=style.value,
            max_chars=max_chars,
            model_name=model,
            device=device,
            language=language,
            keep_audio=keep_audio,
        )
    except (FetchError, AudioDownloadError, AsrError) as exc:
        typer.secho(f"流水线失败: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    summary = result["summary"]
    typer.secho("ASR 流水线完成", fg=typer.colors.GREEN)
    typer.echo("文稿来源: faster-whisper 本地转写（口播 ASR，非官方逐字稿）")
    typer.echo(f"核心问题: {summary.core_question}")
    typer.echo(f"输出目录: {output.resolve()}")
    if keep_audio:
        typer.echo(f"  - audio/{result['audio'].name}")
    typer.echo("  - transcript.txt / transcript.json / transcript.srt")
    typer.echo("  - summary.md / summary.json")
    cards = result.get("cards", {})
    if "extract" in cards:
        typer.echo(f"  - cards-extract/ ({len(cards['extract'])} 张)")
    if "comic" in cards:
        typer.echo(f"  - cards-comic/ ({len(cards['comic'])} 张)")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
