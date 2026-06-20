from __future__ import annotations

import re

from bs4 import BeautifulSoup

SECTION_MARKERS = (
    "🕰️",
    "🎺",
    "💿",
    "节目简介",
    "本期嘉宾",
    "时间轴",
    "Shownotes",
)


def html_to_text(html: str) -> str:
    if not html.strip():
        return ""
    soup = BeautifulSoup(html, "html.parser")
    for br in soup.find_all("br"):
        br.replace_with("\n")
    for tag in soup.find_all(["p", "li", "h1", "h2", "h3", "h4"]):
        tag.insert_after("\n")
    text = soup.get_text("\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    return text.strip()


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_sections(text: str) -> list[tuple[str, str]]:
    text = normalize_text(text)
    if not text:
        return []

    pattern = "|".join(re.escape(marker) for marker in SECTION_MARKERS)
    parts = re.split(rf"(?=(?:{pattern}))", text)
    sections: list[tuple[str, str]] = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        lines = part.split("\n", 1)
        title = lines[0].strip()
        body = lines[1].strip() if len(lines) > 1 else part
        if title == part and len(part) < 40:
            sections.append((title, ""))
        else:
            sections.append((title, body or part))
    return sections


def merge_description_and_shownotes(description: str, shownotes_html: str) -> str:
    shownotes_text = html_to_text(shownotes_html)
    description = normalize_text(description)
    if description and shownotes_text:
        if shownotes_text in description or description in shownotes_text:
            return description if len(description) >= len(shownotes_text) else shownotes_text
        return f"{description}\n\n{shownotes_text}"
    return description or shownotes_text
