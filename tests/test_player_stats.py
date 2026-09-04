import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from player_stats import calculate_player_stats


class CalculatePlayerStatsTest(unittest.TestCase):
    def test_total_score_uses_split_uma_for_tied_players(self):
        summary = [
            {"name": "first", "rank": 1, "final_points": 39300, "avg_uma": 45000},
            {"name": "tied_a", "rank": 3, "final_points": 17200, "avg_uma": -25000.0},
            {"name": "tied_b", "rank": 3, "final_points": 17200, "avg_uma": -25000.0},
            {"name": "second", "rank": 2, "final_points": 26300, "avg_uma": 5000},
        ]

        stats = calculate_player_stats([{"summary": summary}], [1])

        self.assertEqual(stats["tied_a"]["total_score"], -32800.0)
        self.assertEqual(stats["tied_b"]["total_score"], -32800.0)
        self.assertEqual(
            sum(player["total_score"] for player in stats.values()),
            0,
        )

    def test_total_score_falls_back_to_rank_uma_for_legacy_summary(self):
        summary = [
            {"name": "first", "rank": 1, "final_points": 40000},
            {"name": "second", "rank": 2, "final_points": 30000},
            {"name": "third", "rank": 3, "final_points": 20000},
            {"name": "fourth", "rank": 4, "final_points": 10000},
        ]

        stats = calculate_player_stats([{"summary": summary}], [1])

        self.assertEqual(stats["first"]["total_score"], 60000)
        self.assertEqual(stats["second"]["total_score"], 10000)
        self.assertEqual(stats["third"]["total_score"], -20000)
        self.assertEqual(stats["fourth"]["total_score"], -50000)

    def test_head_to_head_score_diff_uses_split_uma(self):
        summary = [
            {"name": "first", "rank": 1, "final_points": 39300, "avg_uma": 45000},
            {"name": "tied_a", "rank": 3, "final_points": 17200, "avg_uma": -25000.0},
            {"name": "tied_b", "rank": 3, "final_points": 17200, "avg_uma": -25000.0},
            {"name": "second", "rank": 2, "final_points": 26300, "avg_uma": 5000},
        ]

        stats = calculate_player_stats([{"summary": summary}], [1])

        self.assertEqual(stats["tied_a"]["vs_players"]["tied_b"]["score_diff"], 0)
        self.assertEqual(stats["tied_b"]["vs_players"]["tied_a"]["score_diff"], 0)
        self.assertEqual(stats["tied_a"]["vs_players"]["first"]["score_diff"], -92100.0)
        self.assertEqual(stats["first"]["vs_players"]["tied_a"]["score_diff"], 92100.0)

    def test_league_average_includes_players_with_exactly_ten_games(self):
        games = []
        for _ in range(10):
            games.append({
                "summary": [
                    {"name": "first", "rank": 1, "final_points": 40000},
                    {"name": "second", "rank": 2, "final_points": 30000},
                    {"name": "third", "rank": 3, "final_points": 20000},
                    {"name": "fourth", "rank": 4, "final_points": 10000},
                ]
            })

        stats = calculate_player_stats(games, [1] * len(games))

        self.assertIn("_league_average", stats)
        self.assertEqual(stats["_league_average"]["avg_rank"], 2.5)


if __name__ == "__main__":
    unittest.main()
