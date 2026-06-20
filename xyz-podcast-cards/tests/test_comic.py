from xyz_podcast_cards.fetcher import episode_from_payload, extract_next_data
from xyz_podcast_cards.summarizer import summarize_episode


def test_summarize_episode_extracts_five_stories() -> None:
    from pathlib import Path

    html = (Path(__file__).parent / "fixtures" / "episode_page_snippet.html").read_text(encoding="utf-8")
    payload = extract_next_data(html)
    episode = episode_from_payload(
        payload["props"]["pageProps"]["episode"],
        "https://www.xiaoyuzhoufm.com/episode/test",
    )
    summary = summarize_episode(episode)
    assert summary.core_question
    assert len(summary.cards) >= 3


def test_summarize_zhixing_hot_episode_style() -> None:
    description = """
🌈 我的一百种写法。
最近几期小酒馆，我们聊过农业，也聊过疲惫经济学。
🪡 时间轴
🟤 01 小阳
13:10 做编剧近十年后，我不再为自己创作出来的作品感到兴奋了
23:27 在家乡的初春里，和家人一起追着落日骑行
🟤 02 313
41:27 十八岁时我对自己说，要做个认真负责的大人
52:45 小猫在新家中自由打滚的那一刻，我上班受的所有窝囊气都不重要了
"""
    from xyz_podcast_cards.models import EpisodeInfo, PodcastInfo

    episode = EpisodeInfo(
        eid="test",
        pid="pid",
        title="E234 当我不再被工作定义",
        description=description,
        podcast=PodcastInfo(pid="pid", title="知行小酒馆"),
    )
    summary = summarize_episode(episode)
    story_cards = [card for card in summary.cards if card.title.startswith("故事")]
    assert len(story_cards) == 2
    assert any("小猫" in " ".join(card.bullets) for card in story_cards)
