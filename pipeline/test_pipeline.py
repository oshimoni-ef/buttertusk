"""Offline tests: python -m unittest discover pipeline"""
import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build  # noqa: E402
import schema  # noqa: E402
from providers import internationalshowtimes, seed  # noqa: E402


class SeedTest(unittest.TestCase):
    def test_snapshot_is_valid(self):
        schema.validate(seed.fetch({}))

    def test_build_inlines_data(self):
        with tempfile.TemporaryDirectory() as d:
            data = build.build("seed", dist=Path(d))
            page = (Path(d) / "index.html").read_text(encoding="utf-8")
            self.assertNotIn(build.SLOT, page)
            self.assertIn('"generated_at"', page)
            self.assertEqual(json.loads((Path(d) / "showtimes.json").read_text(encoding="utf-8"))["meta"]["source"], data["meta"]["source"])


class InternationalShowtimesTest(unittest.TestCase):
    RAW = {
        "cinemas": [{"id": 7, "name": "AMC Framingham 16", "website": "https://amc.example",
                     "location": {"lat": 42.3, "lon": -71.39, "address": {"city": "Framingham"}}}],
        "movies": [{"id": 3, "title": "Clayface", "runtime": 108, "age_limits": {"US": "R"}, "genres": [{"name": "Horror"}]}],
        "showtimes": [
            {"cinema_id": 7, "movie_id": 3, "start_at": "2026-10-26T19:00:00-04:00", "is_imax": True, "booking_link": "https://buy.example/1"},
            {"cinema_id": 7, "movie_id": 3, "start_at": "2026-10-27T00:30:00-04:00", "language": "es"},
            {"cinema_id": 7, "movie_id": 3, "start_at": "2026-10-26T19:00:00-04:00", "is_imax": True},   # duplicate
            {"cinema_id": 99, "movie_id": 3, "start_at": "2026-10-26T20:00:00-04:00"},                     # unknown cinema
        ],
    }

    def test_normalize(self):
        d = internationalshowtimes.normalize(self.RAW, date(2026, 10, 26), 7)
        d["zips"] = {"01701": [42.3, -71.4]}
        schema.validate(d)
        self.assertEqual(d["films"][0], {"title": "Clayface", "rating": "R", "runtime": 108, "genres": ["Horror"]})
        self.assertEqual(d["showings"][0], ["2026-10-26", 0, 0, 1140, "IMAX", "https://buy.example/1", ""])
        # 12:30 AM belongs to the evening before, shown as 24:30
        self.assertEqual(d["showings"][1][:5], ["2026-10-26", 0, 0, 1470, "Spanish"])
        self.assertEqual(len(d["showings"]), 2)


class SchemaTest(unittest.TestCase):
    def test_rejects_out_of_range(self):
        with self.assertRaises(schema.SchemaError):
            schema.validate({"meta": {}, "dates": ["2026-10-26"], "cinemas": [{"name": "A", "lat": 1, "lng": 1}],
                             "films": [{"title": "F"}], "showings": [["2026-10-26", 5, 0, 600, "", "", ""]]})


if __name__ == "__main__":
    unittest.main()
