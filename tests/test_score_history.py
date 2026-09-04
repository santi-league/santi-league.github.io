import json
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from generate_website import extract_recent_games
from s_league.content import _compute_running_score_totals


class ScoreHistoryTest(unittest.TestCase):
    def test_running_total_accumulates_before_rounding_for_multiway_ties(self):
        average_uma = (45000 + 5000 - 15000) / 3
        summary = {
            "summary": [
                {
                    "name": "tied_player",
                    "rank": 1,
                    "final_points": 25000,
                    "avg_uma": average_uma,
                }
            ]
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            files = []
            for index, hour in enumerate((1, 2), start=1):
                path = Path(temp_dir) / f"game_{index}.json"
                path.write_text(
                    json.dumps({
                        "title": ["test", f"01/01/2026, {hour:02d}:00:00 AM"],
                    }),
                    encoding="utf-8",
                )
                files.append(str(path))

            recent_games = extract_recent_games(files, [summary, summary], count=2)

        score_change = recent_games[0]["players_detail"][0]["score_change"]
        self.assertAlmostEqual(score_change, 35 / 3)

        _compute_running_score_totals(recent_games)
        latest_score = recent_games[0]["players_detail"][0]["score_after"]
        self.assertEqual(latest_score, 23.3)


if __name__ == "__main__":
    unittest.main()
