import unittest

from tvshows_torrenter.tvshows import TvShow


class TestParsing(unittest.TestCase):
    def test_parse_imdb_marker(self):
        marker = "American.Horror.Story.S01E01.Pilot.HDTV.XviD-FQM.VTV.imdb.1844624"
        tv = TvShow.parse_imdb_marker(marker)
        self.assertIsNotNone(tv)
        assert tv is not None
        self.assertEqual(tv.imdb_id, "1844624")
        self.assertEqual(tv.name, "American Horror Story")
        self.assertEqual(tv.season, 1)
        self.assertEqual(tv.episode, 1)

    def test_parse_episode_from_video_regex(self):
        video = "American.Horror.Story.S03E21.720p.WEB-DL.mkv"
        tv = TvShow.parse_episode_from_video(video)
        self.assertIsNotNone(tv)
        assert tv is not None
        self.assertEqual(tv.name, "American Horror Story")
        self.assertEqual(tv.season, 3)
        self.assertEqual(tv.episode, 21)

    def test_parse_episode_from_video_x_format(self):
        video = "American.Horror.Story.3x21.720p.WEB-DL.mkv"
        tv = TvShow.parse_episode_from_video(video)
        self.assertIsNotNone(tv)
        assert tv is not None
        self.assertEqual(tv.name, "American Horror Story")
        self.assertEqual(tv.season, 3)
        self.assertEqual(tv.episode, 21)


if __name__ == "__main__":
    unittest.main()

