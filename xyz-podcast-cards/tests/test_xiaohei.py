from xyz_podcast_cards.fetcher import fetch_episode
from xyz_podcast_cards.xiaohei_shots import build_xiaohei_shots


def test_build_xiaohei_shots_has_eight_items() -> None:
    episode = fetch_episode("69fd8a69e1eb34a939f868c0")
    shots = build_xiaohei_shots(episode)
    assert len(shots) == 8
    assert shots[0].slug == "value-well"
    assert "小黑" in shots[0].to_prompt()
    assert shots[-1].labels
