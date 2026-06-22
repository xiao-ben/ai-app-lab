from __future__ import annotations

import re
from dataclasses import dataclass, field

from .models import EpisodeInfo
from .parser import normalize_text


@dataclass
class ComicCardContent:
    title: str
    subtitle: str = ""
    bullets: list[str] = field(default_factory=list)
    quote: str = ""
    mood: str = "neutral"
    palette: str = "cream"
    character_pose: str = "wave"


@dataclass
class EpisodeSummary:
    hook: str
    core_question: str
    takeaways: list[str]
    cards: list[ComicCardContent]


STORY_BLOCK_RE = re.compile(
    r"🟤\s*(\d+)\s*([^\n]+)\n(.*?)(?=\n🟤\s*\d+|\n🔗|\n🎤|\n🔍|\Z)",
    re.DOTALL,
)

TIMELINE_ITEM_RE = re.compile(r"^(\d{1,2}:\d{2})\s+(.+)$", re.MULTILINE)

MOOD_BY_KEYWORD = [
    (("猫", "狗", "小动物", "宠物", "打滚"), "warm", "hug", "mint"),
    (("财务", "危机", "杀猪盘", "坦白", "求助", "完美"), "reflect", "think", "lavender"),
    (("外婆", "家人", "妈妈", "告别", "骄傲"), "tender", "heart", "blush"),
    (("工作", "上班", "编剧", "阳光", "窝囊气"), "tired", "sigh", "peach"),
    (("骑行", "落日", "花", "初春"), "happy", "jump", "sky"),
    (("点单", "宇宙", "做主", "转行", "餐饮"), "bold", "point", "cream"),
]

PALETTES = ("cream", "mint", "blush", "lavender", "peach", "sky")


def _pick_mood(text: str) -> tuple[str, str, str]:
    for keywords, mood, pose, palette in MOOD_BY_KEYWORD:
        if any(keyword in text for keyword in keywords):
            return mood, pose, palette
    return "neutral", "wave", "cream"


def _summarize_story_block(name: str, body: str) -> ComicCardContent:
    items = [(match.group(1), normalize_text(match.group(2))) for match in TIMELINE_ITEM_RE.finditer(body)]
    merged = " ".join(text for _, text in items)
    mood, pose, palette = _pick_mood(merged)

    bullets: list[str] = []
    for _, text in items[:3]:
        short = text.split("\n")[0].strip()
        if len(short) > 46:
            short = short[:45] + "…"
        bullets.append(short)

    quote = items[-1][1].split("\n")[0].strip() if items else ""
    if len(quote) > 56:
        quote = quote[:55] + "…"

    title = f"故事 · {name.strip()}"
    if items:
        subtitle = items[0][1]
        if len(subtitle) > 28:
            subtitle = subtitle[:27] + "…"
    else:
        subtitle = "一位听友的真实分享"

    return ComicCardContent(
        title=title,
        subtitle=subtitle,
        bullets=bullets,
        quote=quote,
        mood=mood,
        palette=palette,
        character_pose=pose,
    )


def _extract_intro_points(description: str) -> tuple[str, str, list[str]]:
    text = normalize_text(description)
    hook = ""
    for paragraph in text.split("\n\n"):
        if "价值感" in paragraph or "工作" in paragraph:
            hook = paragraph
            break
    if not hook:
        hook = text.split("\n\n")[0] if text else ""

    if len(hook) > 120:
        hook = hook[:119] + "…"

    core_question = "除了工作和收入，还有什么在支撑你的价值感？"
    takeaways = [
        "价值感不必只来自头衔与 KPI",
        "陪伴、爱好与坦诚，也能撑起「我是谁」",
        "当外界评价失效时，生活细节会给出答案",
    ]
    return hook, core_question, takeaways


def summarize_episode(episode: EpisodeInfo) -> EpisodeSummary:
    description = episode.description or ""
    hook, core_question, takeaways = _extract_intro_points(description)

    story_cards: list[ComicCardContent] = []
    for match in STORY_BLOCK_RE.finditer(description):
        _, name, body = match.groups()
        story_cards.append(_summarize_story_block(name, body))

    if not story_cards:
        paragraphs = [p.strip() for p in normalize_text(description).split("\n\n") if len(p.strip()) > 20]
        for idx, paragraph in enumerate(paragraphs[:5], start=1):
            mood, pose, palette = _pick_mood(paragraph)
            story_cards.append(
                ComicCardContent(
                    title=f"要点 {idx}",
                    subtitle=paragraph[:28] + ("…" if len(paragraph) > 28 else ""),
                    bullets=[paragraph[:80] + ("…" if len(paragraph) > 80 else "")],
                    quote=paragraph,
                    mood=mood,
                    palette=palette,
                    character_pose=pose,
                )
            )

    cards: list[ComicCardContent] = [
        ComicCardContent(
            title=episode.title,
            subtitle=episode.podcast.title if episode.podcast else "小宇宙播客",
            bullets=[hook] if hook else [],
            quote=core_question,
            mood="spark",
            palette="peach",
            character_pose="mic",
        ),
        ComicCardContent(
            title="本期灵魂拷问",
            subtitle="AI 摘要",
            bullets=[
                "我们习惯用工作、收入、头衔回答「我是谁」",
                "但人生转弯时，外界评价往往会突然失灵",
                "五位听友分享了价值感重建的真实时刻",
            ],
            quote=core_question,
            mood="think",
            palette="lavender",
            character_pose="think",
        ),
        *story_cards[:5],
        ComicCardContent(
            title="带走三句话",
            subtitle="漫画小结",
            bullets=takeaways,
            quote="我不只靠工作定义自己。",
            mood="happy",
            palette="mint",
            character_pose="cheer",
        ),
    ]
    return EpisodeSummary(hook=hook, core_question=core_question, takeaways=takeaways, cards=cards)
