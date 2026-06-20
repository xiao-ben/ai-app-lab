from __future__ import annotations

import re
from collections import Counter

from .models import EpisodeInfo
from .parser import normalize_text
from .summarizer import ComicCardContent, EpisodeSummary, _pick_mood
from .transcript_models import TranscriptDocument

SENTENCE_SPLIT_RE = re.compile(r"(?<=[。！？!?；;])")
INSIGHT_MARKERS = (
    "其实",
    "我觉得",
    "我认为",
    "最重要的是",
    "说白了",
    "本质上",
    "换句话说",
    "关键",
    "意味着",
    "所以",
    "但是",
    "不过",
    "有一点",
    "印象",
    "感悟",
    "发现",
    "总结",
    "归根到底",
    "价值感",
    "工作",
    "意义",
)


def _split_sentences(text: str) -> list[str]:
    parts = [normalize_text(part) for part in SENTENCE_SPLIT_RE.split(text)]
    return [part for part in parts if len(part) >= 8]


def _score_sentence(sentence: str, *, position: float) -> float:
    score = 0.0
    length = len(sentence)
    if 18 <= length <= 80:
        score += 2.0
    elif length <= 120:
        score += 1.0
    score += sum(1.5 for marker in INSIGHT_MARKERS if marker in sentence)
    if "「" in sentence or "”" in sentence or '"' in sentence:
        score += 1.0
    if re.search(r"\d", sentence):
        score += 0.5
    score += max(0.0, 1.5 - position)
    return score


def _top_sentences(document: TranscriptDocument, *, limit: int = 12) -> list[str]:
    sentences = _split_sentences(document.full_text)
    if not sentences:
        return []
    scored = [
        (sentence, _score_sentence(sentence, position=index / max(len(sentences) - 1, 1)))
        for index, sentence in enumerate(sentences)
    ]
    scored.sort(key=lambda item: item[1], reverse=True)
    picked: list[str] = []
    seen: set[str] = set()
    for sentence, _ in scored:
        key = sentence[:24]
        if key in seen:
            continue
        seen.add(key)
        picked.append(sentence)
        if len(picked) >= limit:
            break
    return picked


def _topic_blocks(document: TranscriptDocument, *, block_count: int = 5) -> list[str]:
    paragraphs = document.paragraphs(group_size=10)
    if not paragraphs:
        return []
    if len(paragraphs) <= block_count:
        return paragraphs

    step = max(len(paragraphs) // block_count, 1)
    blocks: list[str] = []
    for index in range(0, len(paragraphs), step):
        chunk = "".join(paragraphs[index : index + step])
        if len(chunk) >= 40:
            blocks.append(chunk)
        if len(blocks) >= block_count:
            break
    return blocks


def _guess_core_question(episode: EpisodeInfo, sentences: list[str]) -> str:
    for sentence in sentences:
        if "？" in sentence or "?" in sentence:
            return sentence[:80]
    title = episode.title
    if "？" in title:
        return title
    return f"这期《{episode.podcast.title if episode.podcast else '播客'}》最值得记住的是什么？"


def summarize_from_transcript(
    episode: EpisodeInfo,
    document: TranscriptDocument,
    *,
    max_cards: int = 6,
) -> EpisodeSummary:
    top_sentences = _top_sentences(document, limit=10)
    topic_blocks = _topic_blocks(document, block_count=max_cards)
    core_question = _guess_core_question(episode, top_sentences)

    keywords = Counter()
    for sentence in top_sentences:
        for token in re.findall(r"[\u4e00-\u9fff]{2,6}", sentence):
            if token in {"我们", "他们", "这个", "那个", "就是", "一个", "可以", "已经", "因为", "所以"}:
                continue
            keywords[token] += 1
    takeaways = [word for word, _ in keywords.most_common(3)]
    if len(takeaways) < 3:
        takeaways.extend(top_sentences[: 3 - len(takeaways)])
    takeaways = [item[:28] + ("…" if len(item) > 28 else "") for item in takeaways[:3]]

    hook = top_sentences[0] if top_sentences else document.paragraphs(group_size=4)[:1]
    if isinstance(hook, list):
        hook = hook[0] if hook else episode.description[:120]
    if len(hook) > 120:
        hook = hook[:119] + "…"

    story_cards: list[ComicCardContent] = []
    for index, block in enumerate(topic_blocks[:max_cards], start=1):
        block_sentences = _split_sentences(block)
        scored = sorted(
            ((sentence, _score_sentence(sentence, position=0.5)) for sentence in block_sentences),
            key=lambda item: item[1],
            reverse=True,
        )
        quote = scored[0][0] if scored else block[:80]
        bullets = [sentence[:46] + ("…" if len(sentence) > 46 else "") for sentence, _ in scored[:3]]
        if not bullets:
            bullets = [block[:80] + ("…" if len(block) > 80 else "")]
        mood, pose, palette = _pick_mood(block)
        story_cards.append(
            ComicCardContent(
                title=f"逐字稿精华 {index}",
                subtitle=quote[:28] + ("…" if len(quote) > 28 else ""),
                bullets=bullets,
                quote=quote[:56] + ("…" if len(quote) > 56 else ""),
                mood=mood,
                palette=palette,
                character_pose=pose,
            )
        )

    cards: list[ComicCardContent] = [
        ComicCardContent(
            title=episode.title,
            subtitle="基于逐字稿",
            bullets=[hook],
            quote=core_question,
            mood="spark",
            palette="peach",
            character_pose="mic",
        ),
        ComicCardContent(
            title="逐字稿摘要",
            subtitle=f"共 {len(document.segments)} 句",
            bullets=top_sentences[:3],
            quote=core_question,
            mood="think",
            palette="lavender",
            character_pose="think",
        ),
        *story_cards,
        ComicCardContent(
            title="带走三句话",
            subtitle="来自口播内容",
            bullets=takeaways,
            quote=top_sentences[0][:56] if top_sentences else "这期播客值得再听一遍。",
            mood="happy",
            palette="mint",
            character_pose="cheer",
        ),
    ]
    return EpisodeSummary(hook=hook, core_question=core_question, takeaways=takeaways, cards=cards)


def render_summary_markdown(episode: EpisodeInfo, document: TranscriptDocument, summary: EpisodeSummary) -> str:
    lines = [
        f"# {episode.title}",
        "",
        f"- 播客：{episode.podcast.title if episode.podcast else '未知'}",
        f"- 链接：{episode.episode_url}",
        f"- 逐字稿句数：{len(document.segments)}",
        "",
        "## 核心问题",
        "",
        summary.core_question,
        "",
        "## 开场摘要",
        "",
        summary.hook,
        "",
        "## 精华摘录",
        "",
    ]
    for index, sentence in enumerate(_top_sentences(document, limit=8), start=1):
        lines.append(f"{index}. {sentence}")
    lines.extend(["", "## 三条 takeaway", ""])
    for item in summary.takeaways:
        lines.append(f"- {item}")
    lines.extend(["", "## 卡片内容", ""])
    for card in summary.cards:
        lines.append(f"### {card.title}")
        if card.subtitle:
            lines.append(f"_{card.subtitle}_")
        lines.append("")
        for bullet in card.bullets:
            lines.append(f"- {bullet}")
        if card.quote:
            lines.append(f"> {card.quote}")
        lines.append("")
    return "\n".join(lines)
