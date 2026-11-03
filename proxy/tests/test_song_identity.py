
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


import asyncio

import httpx


def test_best_effort_kg_meta_without_cached_title(monkeypatch):
    """曲名缓存是空的时候，酷狗收藏不能在下载歌词前崩掉。"""
    import proxy.app as appmod

    async def no_info(request, guid, include_lyric=True):
        return None

    async def kg_meta(hash_val):
        return {
            "title": "晴天",
            "artist": "周杰伦",
            "album": "",
            "duration_s": 269.792,
            "kg_lyric_id": "1",
            "kg_accesskey": "key",
        }

    async def lyric(lyric_id, access_key):
        return "[00:01.00]晴天"

    saved = {}
    monkeypatch.setattr(appmod, "_online_info", no_info)
    monkeypatch.setattr(appmod, "_resolve_kg_hash_meta", kg_meta)
    monkeypatch.setattr(appmod, "_download_kg_krcs_lyric", lyric)
    monkeypatch.setattr(appmod, "read_lyric_cache", lambda guid: "")
    monkeypatch.setattr(appmod, "find_cache_file", lambda guid: None)
    monkeypatch.setattr(
        appmod, "write_lyric_cache",
        lambda guid, text, title="", artist="": saved.update(text=text, title=title),
    )

    info = asyncio.run(appmod._best_effort_online_info(None, "online:lx:kg:ABCDEF"))
    assert info["title"] == "晴天"
    assert info["artist"] == "周杰伦"
    assert info["duration_s"] == 269.792
    assert "晴天" in info["lyric"]
    assert saved["title"] == "晴天"


def test_lx_placeholder_info_is_not_cached():
    import proxy.app as appmod

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True, "data": {
            "id": "lx:kg:abc", "title": "", "artist": "", "duration_s": 0,
        }})

    appmod.app.state.lx_client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="http://127.0.0.1:8772",
    )

    class Request:
        app = appmod.app

    data = asyncio.run(appmod._fetch_online_info(Request(), "online:lx:kg:abc", include_lyric=False))
    assert data is None
