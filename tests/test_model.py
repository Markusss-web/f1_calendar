"""Pārbauda delta novērtējumu pret pilnu pārrēķinu un algoritmus uz maza piemēra.

Palaišana:  python -m unittest discover tests
"""

import itertools
import json
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from bruteforce import brute_force                           # noqa: E402
from generator import TRACKS_FILE, generate_instance         # noqa: E402
from hill_climbing import hill_climbing                      # noqa: E402
from model import (Instance, all_moves, apply_move, cumulative, delta, profit,  # noqa: E402
                   random_move)
from sa import simulated_annealing                           # noqa: E402


def make_instance(k, seed=1, symmetric=True):
    tracks = json.loads(TRACKS_FILE.read_text(encoding="utf-8"))["tracks"]
    data = generate_instance(tracks, k, seed)
    cost = data["cost"]
    if not symmetric:  # izkropļo matricu, lai pārbaudītu arī nesimetrisko gadījumu
        rng = random.Random(seed)
        cost = [[v * rng.uniform(0.5, 1.5) for v in row] for row in cost]
    return Instance(data["name"], k, data["revenue"], cost, data["tracks"], data["weekends"],
                    data, None, symmetric)


class DeltaTest(unittest.TestCase):
    def check_all_moves(self, inst):
        rng = random.Random(7)
        for _ in range(20):
            cal = list(range(inst.k))
            rng.shuffle(cal)
            base = profit(inst, cal)
            for move in all_moves(inst.k) + [("insert", i, i + 1) for i in range(inst.k - 1)]:
                new = cal[:]
                apply_move(new, move)
                self.assertEqual(sorted(new), list(range(inst.k)))
                self.assertAlmostEqual(delta(inst, cal, move), profit(inst, new) - base, places=7,
                                       msg=str(move))

    def test_symmetric(self):
        for k in (2, 3, 6, 11):
            self.check_all_moves(make_instance(k))

    def test_asymmetric(self):
        self.check_all_moves(make_instance(9, symmetric=False))

    def test_random_moves_valid(self):
        rng = random.Random(3)
        cum = cumulative((0.4, 0.3, 0.3))
        for _ in range(2000):
            kind, i, j = random_move(8, rng, cum)
            self.assertNotEqual(i, j)
            if kind != "insert":
                self.assertLess(i, j)


class AlgorithmTest(unittest.TestCase):
    def test_bruteforce_matches_itertools(self):
        inst = make_instance(6, seed=5)
        expected = max(profit(inst, list(p)) for p in itertools.permutations(range(6)))
        best, cal, leaves = brute_force(inst)
        self.assertAlmostEqual(best, expected, places=9)
        self.assertEqual(leaves, 720)
        best_bnb, _, _ = brute_force(inst, use_bound=True)
        self.assertAlmostEqual(best_bnb, expected, places=9)

    def test_sa_and_hc_reach_optimum_small(self):
        inst = make_instance(7, seed=9)
        opt, _, _ = brute_force(inst, use_bound=True)
        sa = simulated_annealing(inst, seed=1)
        hc = hill_climbing(inst, seed=1, max_evals=20_000)
        self.assertAlmostEqual(sa.profit, profit(inst, sa.calendar), places=9)
        self.assertAlmostEqual(sa.profit, opt, places=6)
        self.assertLessEqual(hc.profit, opt + 1e-9)

    def test_reproducible(self):
        inst = make_instance(10, seed=2)
        a = simulated_annealing(inst, seed=42)
        b = simulated_annealing(inst, seed=42)
        self.assertEqual(a.calendar, b.calendar)
        self.assertEqual(a.history, b.history)


if __name__ == "__main__":
    unittest.main()
