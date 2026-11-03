"""charts.py 单元测试：测试多排行榜歌单元数据、缓存与接口兼容。"""
import os
import tempfile
import unittest

from proxy import charts
from proxy import recommend as dailyrec


class TestCharts(unittest.TestCase):
    def test_charts_list(self):
        # 验证酷狗榜单 20 个，网易云榜单 18 个，共 38 个
        self.assertEqual(len(charts.KG_CHARTS), 20)
        self.assertEqual(len(charts.WY_CHARTS), 18)
        self.assertEqual(len(charts.ALL_CHARTS), 38)

        # 检查开关过滤
        all_enabled = charts.list_enabled_charts(True, True, True)
        self.assertEqual(len(all_enabled), 38)

        kg_only = charts.list_enabled_charts(True, True, False)
        self.assertEqual(len(kg_only), 20)

        wy_only = charts.list_enabled_charts(True, False, True)
        self.assertEqual(len(wy_only), 18)

        none_enabled = charts.list_enabled_charts(False, True, True)
        self.assertEqual(len(none_enabled), 0)

        # 检查自定义白名单过滤
        custom_enabled = charts.list_enabled_charts(True, True, True, custom_whitelist="kg_8888,wy_19723756")
        self.assertEqual(len(custom_enabled), 2)
        self.assertEqual({c["id"] for c in custom_enabled}, {"kg_8888", "wy_19723756"})

    def test_guid_helpers(self):
        guid = charts.chart_guid("kg_8888")
        self.assertEqual(guid, "online:playlist:chart:kg_8888")
        self.assertTrue(charts.is_chart_guid(guid))
        self.assertEqual(charts.chart_id_from_guid(guid), "kg_8888")
        self.assertFalse(charts.is_chart_guid("online:playlist:daily:20260927"))

        # 验证 recommend.py 中的兼容
        self.assertEqual(dailyrec.online_playlist_kind(guid), "chart")
        self.assertTrue(dailyrec.is_recommend_playlist_guid(guid))

    def test_build_record(self):
        rec = charts.build_chart_playlist_record("kg_8888", track_count=50)
        self.assertEqual(rec["name"], "TOP500")
        self.assertEqual(rec["title"], "TOP500")
        self.assertEqual(rec["trackCount"], 50)
        self.assertTrue(rec["isDaily"])
        self.assertTrue(rec["coverId"].startswith("track_"))

        rec_wy = charts.build_chart_playlist_record("wy_19723756", track_count=100)
        self.assertEqual(rec_wy["name"], "飙升榜")
        self.assertEqual(rec_wy["title"], "飙升榜")
        self.assertEqual(rec_wy["trackCount"], 100)
        self.assertTrue(rec_wy["coverId"].startswith("track_"))

    def test_cache_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old_dir = os.environ.get("FNMUSIC_RECOMMEND_DIR")
            os.environ["FNMUSIC_RECOMMEND_DIR"] = tmpdir
            try:
                test_tracks = [
                    {"id": "lx:kg:abc", "title": "测试歌曲", "artist": "测试歌手", "duration_s": 180}
                ]
                charts.save_chart_cache("kg_test", "20260927", test_tracks)
                loaded = charts.load_chart_cache("kg_test", "20260927")
                self.assertIsNotNone(loaded)
                self.assertEqual(len(loaded), 1)
                self.assertEqual(loaded[0]["title"], "测试歌曲")
            finally:
                if old_dir is not None:
                    os.environ["FNMUSIC_RECOMMEND_DIR"] = old_dir
                else:
                    os.environ.pop("FNMUSIC_RECOMMEND_DIR", None)

    def test_find_track_and_cover(self):
        sample_tracks = [
            {
                "id": "lx:wy:12345678",
                "source": "lx",
                "title": "开始懂了",
                "artist": "孙燕姿",
                "album": "我要的幸福",
                "cover_url": "https://p1.music.126.net/sample.jpg",
                "duration_s": 271,
            }
        ]
        charts.save_chart_cache("wy_5453912201", charts._today(), sample_tracks, cover_url="https://p1.music.126.net/header.jpg")
        
        # 测试根据 online guid 和原始 id 查找
        found = charts.find_track("online:lx:wy:12345678")
        self.assertIsNotNone(found)
        self.assertEqual(found["title"], "开始懂了")
        self.assertEqual(found["cover_url"], "https://p1.music.126.net/sample.jpg")

        # 测试榜单封面获取
        cover = charts.get_chart_cover("wy_5453912201")
        self.assertEqual(cover, "https://p1.music.126.net/header.jpg")

        # 测试无效 dummy 封面识别
        self.assertTrue(charts._is_dummy_cover("https://p1.music.126.net/L1m2N3o4P5q6R7s8T9u0Vw==/109951168172823456.jpg"))
        self.assertTrue(charts._is_dummy_cover("https://imge.kugou.com/mcommon/400/20230607/20230607172031123456.png"))
        self.assertFalse(charts._is_dummy_cover("https://p1.music.126.net/pcYHpMkdStnvXZTzkVa-TmA==/109951166952713766.jpg"))


    def _isolate_charts(self):
        self._saved = (
            dict(charts._MEM_CACHE),
            dict(charts._FETCH_FAIL_AT),
            dict(charts._CHART_TRACKS_BY_GUID),
            dict(charts._CHART_COVERS),
            dict(charts._FETCH_LOCKS),
        )
        charts._MEM_CACHE.clear()
        charts._FETCH_FAIL_AT.clear()
        charts._CHART_TRACKS_BY_GUID.clear()
        charts._CHART_COVERS.clear()
        charts._FETCH_LOCKS.clear()

    def _restore_charts(self):
        mem, fail, tracks, covers, locks = self._saved
        charts._MEM_CACHE.clear()
        charts._MEM_CACHE.update(mem)
        charts._FETCH_FAIL_AT.clear()
        charts._FETCH_FAIL_AT.update(fail)
        charts._CHART_TRACKS_BY_GUID.clear()
        charts._CHART_TRACKS_BY_GUID.update(tracks)
        charts._CHART_COVERS.clear()
        charts._CHART_COVERS.update(covers)
        charts._FETCH_LOCKS.clear()
        charts._FETCH_LOCKS.update(locks)

    def test_kg_title_keeps_separator_when_singer_missing(self):
        self.assertEqual(charts._clean_kg_title("周杰伦 - 晴天", ""), "周杰伦 - 晴天")
        self.assertEqual(charts._clean_kg_title("周杰伦 - 晴天", "周杰伦"), "晴天")
        self.assertEqual(charts._clean_kg_title("晴天 - 回忆版", "周杰伦"), "晴天 - 回忆版")

    def test_chart_page_does_not_repeat_tail(self):
        tracks = [{"id": str(i)} for i in range(100)]
        self.assertEqual(len(charts.chart_track_page(tracks, 1, 50)), 100)
        self.assertEqual(charts.chart_track_page(tracks, 2, 50), [])
        self.assertEqual(len(charts.chart_track_page(tracks, 2, -1)), 100)

    def test_stale_cache_does_not_block_refresh(self):
        import asyncio

        self._isolate_charts()
        old_fetch = charts.fetch_kg_chart
        calls = {"n": 0}

        async def fake_fetch(client, rankid, limit=100):
            calls["n"] += 1
            if calls["n"] == 1:
                return [], ""
            return ([{"id": "lx:kg:new", "source": "lx", "title": "新一天", "artist": "甲"}], "https://cdn.example/new.jpg")

        with tempfile.TemporaryDirectory() as tmpdir:
            old_dir = os.environ.get("FNMUSIC_RECOMMEND_DIR")
            os.environ["FNMUSIC_RECOMMEND_DIR"] = tmpdir
            charts.fetch_kg_chart = fake_fetch
            try:
                yesterday = [{"id": "lx:kg:old", "source": "lx", "title": "昨天", "artist": "乙"}]
                charts.save_chart_cache("kg_8888", "20000101", yesterday, cover_url="https://cdn.example/old.jpg")
                charts._MEM_CACHE.clear()
                self.assertIsNone(charts.load_chart_cache("kg_8888", "20991231", allow_stale=False))
                stale = charts.load_chart_cache("kg_8888", "20991231", allow_stale=True)
                self.assertEqual(stale[0]["title"], "昨天")
                self.assertNotEqual(charts._MEM_CACHE["kg_8888"][1], "20991231")

                async def run():
                    class Dummy:
                        pass
                    first = await charts.get_or_load_chart_tracks("kg_8888", client=Dummy(), limit=10)
                    self.assertEqual(first[0]["title"], "昨天")
                    charts._FETCH_FAIL_AT.clear()
                    second = await charts.get_or_load_chart_tracks("kg_8888", client=Dummy(), limit=10)
                    self.assertEqual(second[0]["title"], "新一天")
                    self.assertEqual(charts.load_chart_cache("kg_8888", charts._today(), allow_stale=False)[0]["title"], "新一天")

                asyncio.run(run())
                self.assertEqual(calls["n"], 2)
            finally:
                charts.fetch_kg_chart = old_fetch
                if old_dir is not None:
                    os.environ["FNMUSIC_RECOMMEND_DIR"] = old_dir
                else:
                    os.environ.pop("FNMUSIC_RECOMMEND_DIR", None)
                self._restore_charts()



if __name__ == "__main__":
    unittest.main()
