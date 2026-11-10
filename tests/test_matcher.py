from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import yaml

from bili_songbot.config import QueueConfig
from bili_songbot.matcher import SongMatcher
from bili_songbot.models import Song
from bili_songbot.queue_manager import QueueManager
from bili_songbot.storage import Storage


ROOT = Path(__file__).resolve().parents[1]
PREFIXES = ["点歌", "點歌", "song", "dg"]
# Independent expectations transcribed from the local video title frames.
CATALOG_CASES = [
    ("50と4つの忘れ物", "遗失物"),
    ("Beginning", "起点"),
    ("DEAD or RAP!!!", "说唱"),
    ("FLAGをはためかせろ！", "旗帜"),
    ("Never ending saga", "永无止境"),
    ("NOPE!!!!!", "诺普"),
    ("REVENGE", "复仇"),
    ("To my Dearest", "亲爱"),
    ("We are FranChouChou!", "自我介绍"),
    ("ゾンビランドDEMPA!!", "电波联动"),
    ("FANTASTIC LOVERS", "幻想恋人"),
    ("アツクナレ", "热血"),
    ("イカの魂無駄にはしない～小島食品工場株式会社社歌～", "鱿鱼"),
    ("すきっちゃん！からチュッ", "唐津"),
    ("ゼリーフィッシュ", "水母"),
    ("ドライブイン鳥(フランシュシュver.)", "烤鸡"),
    ("ぶっちゃけてフォーユー", "真心"),
    ("輝いて", "闪耀"),
    ("徒花ネクロマンシー", "招魂"),
    ("またたく宇宙（ソラ）に憧れて", "宇宙"),
    ("ヨミガエレ", "复苏"),
    ("リトルパラッポ", "帕拉波"),
    ("激昂サバイブ（Complete Edition）", "激昂"),
    ("光へ", "光明"),
    ("今を未来をありがとう", "现在与未来"),
    ("今日が歴史に残るなら", "历史"),
    ("今日はカレーだイェイイェイイェイ", "咖喱"),
    ("佐賀事変", "事变"),
    ("七福大祭典", "祭典"),
    ("宣誓！ALIVE センセーション", "宣誓"),
    ("大河よ共に泣いてくれ", "大河"),
    ("追い風トラベラーズ", "追风"),
    ("特攻DANCE ～DAWN OF THE BAD～", "特攻"),
    ("風の強い日は嫌いか？ FranChouChou cover", "风大翻唱"),
    ("風の強い日は嫌いか？", "风大"),
    ("冒険ズンドコドン!", "冒险"),
    ("夢を手に、戻れる場所もない日々を", "梦想"),
    ("命", "生命"),
    ('目覚めRETURNER (Electric Returner Type "R")', "电音R"),
    ("目覚めRETURNER (Electric Returner)", "电音"),
    ("目覚めRETURNER", "觉醒"),
    ("悠久ネバーダイ", "悠久"),
]


def load_songs() -> list[Song]:
    raw = yaml.safe_load((ROOT / "config/songs.yaml").read_text(encoding="utf-8"))
    return [Song.from_dict(song) for song in raw["songs"]]


def song(sid: str, *aliases: str, enabled: bool = True) -> Song:
    return Song(sid, sid, "unused.mp4", list(aliases), enabled=enabled)


class CatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.songs = load_songs()
        cls.matcher = SongMatcher(cls.songs, PREFIXES)

    def assert_song(self, text: str, sid: str, code: str = "exact") -> None:
        result = self.matcher.match_text(text)
        self.assertEqual(result.code, code, (text, result))
        self.assertIsNotNone(result.song)
        self.assertEqual(result.song.song_id, sid, text)

    def test_all_original_titles_and_intuitive_keywords(self) -> None:
        self.assertEqual(len(CATALOG_CASES), len(self.songs))
        for index, names in enumerate(CATALOG_CASES, 1):
            for name in names:
                for prefix in ["", "点歌 ", "點歌：", "song ", "dg "]:
                    with self.subTest(name=name, prefix=prefix):
                        self.assert_song(prefix + name, f"song_{index:03}")

    def test_every_configured_alias_display_name_and_id(self) -> None:
        for item in self.songs:
            for alias in item.aliases + [item.display_name, item.song_id]:
                for prefix in ["", "点歌 ", "song "]:
                    with self.subTest(sid=item.song_id, alias=alias, prefix=prefix):
                        self.assert_song(prefix + alias, item.song_id)

    def test_published_translations(self) -> None:
        for text, sid in [
            ("如果今天将被铭刻于历史", "song_026"),
            ("谢谢你 现在与未来", "song_025"),
            ("悠久Never Die", "song_042"),
        ]:
            with self.subTest(text=text):
                self.assert_song(text, sid)

    def test_kanji_variants_and_copy_paste(self) -> None:
        for text, sid in [
            ("歴史", "song_026"), ("歷史", "song_026"),
            ("冒険", "song_036"), ("冒險", "song_036"),
            ("佐賀事變", "song_028"), ("追風", "song_032"),
            ("　點歌：「今日が歴史に残るなら」\u200b", "song_026"),
            ("\ufeff点歌 今日が歴史に残るなら", "song_026"),
            ("ＳＯＮＧ　Ｂｅｇｉｎｎｉｎｇ", "song_002"),
            ("点歌 ﾖﾐｶﾞｴﾚ", "song_021"),
            ("特攻DANCE —DAWN OF THE BAD—", "song_033"),
            ("目覚めRETURNER（Electric Returner Type “R”）", "song_039"),
            ("点歌：历史", "song_026"), ("dg历史", "song_026"),
            ("song026", "song_026"), ("点歌 song_026", "song_026"),
        ]:
            with self.subTest(text=text):
                self.assert_song(text, sid)

    def test_versions_remain_distinct(self) -> None:
        for text, sid in [
            ("觉醒", "song_041"), ("电音", "song_040"), ("电音R", "song_039"),
            ("风大", "song_035"), ("风大翻唱", "song_034"),
        ]:
            self.assert_song(text, sid)
        result = self.matcher.match_text("return")
        self.assertEqual(result.code, "ambiguous")
        self.assertEqual(len(result.candidates), 3)
        self.assertIn("song_039", result.reason)

    def test_title_fragment_and_typo(self) -> None:
        self.assert_song("歴史に残る", "song_026", "fuzzy")
        self.assert_song("Fantastik Lovers", "song_011", "fuzzy")

    def test_chatter_unknown_ids_and_too_short_fragments(self) -> None:
        for text in [
            "今天学了历史", "我最喜欢今日が歴史に残るなら这首歌了",
            "今天的天气很好", "哈哈哈哈", "感谢主播", "谢谢", "你好",
            "佐贺", "纯子", "爱", "史", "宇", "999", "song_999", "song_0260",
            "I really love Fantastic Lovers so much", "点歌 火星未知歌曲",
        ]:
            with self.subTest(text=text):
                self.assertIsNone(self.matcher.match_text(text).song)


class MatchingRulesTests(unittest.TestCase):
    def test_ambiguity_uses_distinct_songs_and_is_order_independent(self) -> None:
        songs = [song("a", "returner alpha", "returner alpha live"), song("b", "returner beta")]
        for ordered in [songs, songs[::-1]]:
            matcher = SongMatcher(ordered, PREFIXES)
            result = matcher.match_text("returner")
            self.assertEqual(result.code, "ambiguous")
            self.assertEqual(result.candidates, ["a", "b"])

    def test_multiple_aliases_of_one_song_are_not_ambiguous(self) -> None:
        matcher = SongMatcher([song("a", "returner alpha", "returner alpha live")], PREFIXES)
        self.assertEqual(matcher.match_text("returner").song.song_id, "a")

    def test_exact_has_priority_over_versions(self) -> None:
        matcher = SongMatcher([song("a", "returner"), song("b", "returner remix")], PREFIXES)
        self.assertEqual(matcher.match_text("returner").song.song_id, "a")

    def test_duplicate_normalized_aliases_fail_fast(self) -> None:
        with self.assertRaisesRegex(ValueError, "别名冲突"):
            SongMatcher([song("a", "Type-R"), song("b", "Type R")], PREFIXES)

    def test_disabled_songs_do_not_match_or_conflict(self) -> None:
        matcher = SongMatcher([song("a", "历史"), song("b", "历史", enabled=False)], PREFIXES)
        self.assertEqual(matcher.match_text("历史").song.song_id, "a")

    def test_commands_required_when_direct_aliases_disabled(self) -> None:
        matcher = SongMatcher(load_songs(), PREFIXES, allow_direct_alias=False)
        for text in ["历史", "song_026"]:
            self.assertEqual(matcher.match_text(text).code, "no_request")
        for text in ["点歌历史", "song 历史", "dg历史", "点歌 song_026"]:
            self.assertEqual(matcher.match_text(text).song.song_id, "song_026")

    def test_english_prefix_is_not_stripped_from_a_word(self) -> None:
        matcher = SongMatcher([song("a", "bird"), song("b", "songbird")], ["song"])
        self.assertEqual(matcher.match_text("songbird").song.song_id, "b")
        self.assertEqual(matcher.extract_request_text("songbirdling"), "songbirdling")
        self.assertEqual(matcher.match_text("song bird").song.song_id, "a")

    def test_empty_prefix_does_not_hide_real_prefix(self) -> None:
        matcher = SongMatcher([song("a", "历史")], ["", "点", "点歌"])
        self.assertEqual(matcher.match_text("点歌历史").song.song_id, "a")

    def test_empty_request_and_empty_catalog(self) -> None:
        matcher = SongMatcher([], PREFIXES)
        for text in ["", " ", "点歌", "song:", "【】"]:
            self.assertEqual(matcher.match_text(text).code, "no_request")
        self.assertEqual(matcher.match_text("历史歌曲").code, "not_found")


class QueueIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.storage = Storage(Path(self.temp.name) / "test.db")
        songs = load_songs()
        self.queue = QueueManager(songs, SongMatcher(songs, PREFIXES), self.storage, QueueConfig())
        await self.queue.load()

    async def asyncTearDown(self) -> None:
        self.storage.close()
        self.temp.cleanup()

    async def test_alias_and_original_enqueue_the_same_song_with_guards(self) -> None:
        first = await self.queue.handle_danmaku("test-a", "test", "历史")
        self.assertTrue(first.accepted)
        self.assertEqual(first.song_id, "song_026")
        duplicate = await self.queue.handle_danmaku("test-b", "test", "今日が歴史に残るなら")
        self.assertEqual(duplicate.code, "duplicate")
        cooldown = await self.queue.handle_danmaku("test-a", "test", "宇宙")
        self.assertEqual(cooldown.code, "cooldown")
        self.assertEqual([item.song_id for item in self.storage.load_queue()], ["song_026"])

    async def test_ambiguous_requests_do_not_mutate_queue_or_cooldown(self) -> None:
        result = await self.queue.handle_danmaku("test-a", "test", "return")
        self.assertEqual(result.code, "ambiguous")
        self.assertIn("song_039", result.message)
        self.assertEqual(self.storage.load_queue(), [])
        self.assertEqual(self.storage.load_cooldowns(), {})


if __name__ == "__main__":
    unittest.main()
