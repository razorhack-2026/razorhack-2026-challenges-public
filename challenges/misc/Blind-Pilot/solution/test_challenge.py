#!/usr/bin/env python3
"""Unit tests for Blind Pilot's field rules and reference planner."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "solution"))

import server
from solve import DIRS, Pilot, parse_scan


class BlindPilotTests(unittest.TestCase):
    def test_asteroid_bounces_at_field_edge(self):
        pos, velocity = server.drift((7, 2, 2), (1, 0, 0), 8)
        self.assertEqual(pos, (6, 2, 2))
        self.assertEqual(velocity, (-1, 0, 0))

    def test_radar_reports_neighbor_heading(self):
        field = server.Field(n=8, density=0)
        field.asteroids = [[1, 0, 0, (0, 1, 0)]]
        self.assertEqual(field.scan((1, 0, 0)), [(0, 1, 0)])

    def test_radar_returns_none_out_of_bounds(self):
        field = server.Field(n=8, density=0)
        self.assertIsNone(field.scan((-1, 0, 0)))

    def test_move_into_occupied_cell_costs_hull(self):
        field = server.Field(n=8, density=0, hull=5)
        field.asteroids = [[1, 0, 0, (1, 0, 0)]]
        impacts = field.move((1, 0, 0))
        self.assertEqual(impacts, 1)
        self.assertEqual(field.hull, 4)
        self.assertEqual(field.tick, 1)

    def test_scan_parser_recovers_all_reported_headings(self):
        self.assertEqual(
            parse_scan("(1,0,-1) asteroid moving left moving up"),
            [DIRS["left"], DIRS["up"]],
        )
        self.assertEqual(parse_scan("(0,1,0) empty"), [])

    def test_planner_returns_a_valid_first_move(self):
        pilot = Pilot(n=8, ship=(0, 0, 0), goal=(7, 7, 7))
        name, delta = pilot.plan()
        self.assertIn(name, DIRS)
        self.assertEqual(delta, DIRS[name])


if __name__ == "__main__":
    unittest.main()
