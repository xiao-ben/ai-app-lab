from __future__ import annotations

import json
import shutil
from pathlib import Path

from .fetcher import EpisodeInfo
from .summarizer import EpisodeSummary, summarize_episode
from .xiaohei_shots import XiaoheiShot, build_xiaohei_shots


def save_shot_list(
    shots: list[XiaoheiShot],
    output_dir: Path,
    *,
    episode: EpisodeInfo,
    summary: EpisodeSummary,
) -> Path:
    payload = {
        "episode_title": episode.title,
        "episode_url": episode.episode_url,
        "core_question": summary.core_question,
        "skill": "ian-xiaohei-illustrations",
        "shots": [
            {
                "index": shot.index,
                "slug": shot.slug,
                "theme": shot.theme,
                "structure_type": shot.structure_type,
                "core_idea": shot.core_idea,
                "composition": shot.composition,
                "elements": shot.elements,
                "labels": shot.labels,
                "filename": shot.filename,
                "prompt": shot.to_prompt(),
            }
            for shot in shots
        ],
    }
    path = output_dir / "shot-list.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def write_preview_html(shots: list[XiaoheiShot], output_dir: Path, *, title: str) -> Path:
    cards = "\n".join(
        f'''<section class="card">
  <h2>{shot.index}/8 · {shot.theme}</h2>
  <p class="meta">{shot.structure_type} · {shot.core_idea}</p>
  <img src="{shot.filename}" alt="{shot.slug}" loading="lazy" />
</section>'''
        for shot in shots
    )
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title} · 小黑配图预览</title>
  <style>
    body {{ margin:0; font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif; background:#fff; color:#111; padding:24px; }}
    header {{ max-width:960px; margin:0 auto 24px; }}
    h1 {{ font-size:1.4rem; margin-bottom:8px; }}
    .note {{ color:#666; line-height:1.6; }}
    .grid {{ display:grid; gap:28px; max-width:1100px; margin:0 auto; }}
    .card {{ border:1px solid #eee; border-radius:16px; padding:16px; }}
    .card h2 {{ margin:0 0 8px; font-size:1rem; }}
    .meta {{ margin:0 0 12px; color:#666; font-size:.9rem; line-height:1.5; }}
    .card img {{ width:100%; border-radius:12px; display:block; background:#fff; }}
  </style>
</head>
<body>
  <header>
    <h1>{title}</h1>
    <p class="note">Ian 小黑怪诞正文配图 Skill · 16:9 白底手绘 · 知行小酒馆 E234</p>
  </header>
  <div class="grid">{cards}</div>
</body>
</html>"""
    path = output_dir / "preview.html"
    path.write_text(html, encoding="utf-8")
    return path


def prepare_xiaohei_output(
    episode: EpisodeInfo,
    output_dir: str | Path,
    *,
    summary: EpisodeSummary | None = None,
    assets_source: Path | None = None,
) -> tuple[list[Path], list[XiaoheiShot]]:
    summary = summary or summarize_episode(episode)
    shots = build_xiaohei_shots(episode, summary)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    if assets_source and assets_source.exists():
        for shot in shots:
            src = assets_source / shot.filename
            if src.exists():
                shutil.copy2(src, output_path / shot.filename)

    save_shot_list(shots, output_path, episode=episode, summary=summary)
    write_preview_html(shots, output_path, title=episode.title)

    saved = [output_path / shot.filename for shot in shots if (output_path / shot.filename).exists()]
    return saved, shots
