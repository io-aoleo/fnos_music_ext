
"""换源只能命中同一首歌，不能拿搜索结果的第一条。"""
from proxy.app import first_same_song, same_song_identity


def test_same_song_rejects_different_title_or_artist():
    assert same_song_identity("\u6674\u5929", "\u5468\u6770\u4f26", "\u6674\u5929 (Live)", "\u5468\u6770\u4f26")
    assert not same_song_identity("\u6674\u5929", "\u5468\u6770\u4f26", "\u4e03\u91cc\u9999", "\u5468\u6770\u4f26")
    assert not same_song_identity("\u6674\u5929", "\u5468\u6770\u4f26", "\u6674\u5929", "\u6797\u4fca\u6770")


def test_first_same_song_skips_unrelated_top_hit():
    songs = [
        {"id": 1, "name": "\u4e03\u91cc\u9999", "artists": [{"name": "\u5468\u6770\u4f26"}]},
        {"id": 2, "name": "\u6674\u5929", "artists": [{"name": "\u5468\u6770\u4f26"}]},
    ]
    picked = first_same_song(
        songs, "\u6674\u5929", "\u5468\u6770\u4f26",
        title_keys=("name",), artist_keys=("artists",),
    )
    assert picked["id"] == 2
    assert first_same_song(
        songs, "\u6674\u5929", "\u9648\u5955\u8fc5",
        title_keys=("name",), artist_keys=("artists",),
    ) is None


def test_same_song_rejects_title_substring_and_artist_prefix():
    assert same_song_identity("晴天", "周杰伦", "晴天 Live", "周杰伦")
    assert same_song_identity("晴天", "周杰伦", "晴天", "周杰伦 / 方文山")
    assert not same_song_identity("晴天", "周杰伦", "晴天娃娃", "周杰伦")
    assert not same_song_identity("晴天", "周杰", "晴天", "周杰伦")
    assert not same_song_identity("go", "", "good morning", "")
