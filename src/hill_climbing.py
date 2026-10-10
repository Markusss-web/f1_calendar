"""Hill climbing ar nejaušiem restartiem (bāzes salīdzinājums SA).

Katrs kāpiens: first-improvement pa pilnu apkārtni (swap + reverse + insert) nejaušā secībā;
ja neviens kaimiņš neuzlabo — lokālais optimums, restartē no jauna nejauša kalendāra.
Darbs beidzas, kad iztērēts gājienu novērtējumu budžets max_evals.

Palaišana:  python src/hill_climbing.py instances/f1_k10.json [--seed 1] [--max-evals 50000]
"""

import argparse
import random
import time

from model import RunResult, all_moves, apply_move, delta, load_instance, profit, setup_console


def hill_climbing(inst, seed=None, max_evals=50_000):
    rng = random.Random(seed)
    k = inst.k
    moves = all_moves(k)
    start = time.perf_counter()

    best, best_cal = float("-inf"), None
    evaluations = restarts = 0
    history = []

    while evaluations < max_evals:
        cal = list(range(k))
        rng.shuffle(cal)
        current = profit(inst, cal)
        restarts += 1
        new_best = current > best + 1e-9
        if new_best:
            best = current
        history.append((evaluations, current, best))

        improved = True
        while improved and evaluations < max_evals:
            improved = False
            rng.shuffle(moves)
            for move in moves:
                d = delta(inst, cal, move)
                evaluations += 1
                if d > 1e-9:
                    apply_move(cal, move)
                    current += d
                    improved = True
                    if current > best + 1e-9:   # kāpiena laikā peļņa tikai aug
                        best, new_best = current, True
                        history.append((evaluations, current, best))
                    break
                if evaluations >= max_evals:
                    break

        if new_best:  # kāpiena beigu kalendārs ir šī kāpiena labākais
            best_cal = cal[:]

    best = profit(inst, best_cal)
    return RunResult("HC", best_cal, best, time.perf_counter() - start, evaluations, history,
                     {"restarts": restarts})


def main():
    setup_console()
    parser = argparse.ArgumentParser(description="Hill climbing ar restartiem vienai instancei")
    parser.add_argument("instance")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--max-evals", type=int, default=50_000)
    args = parser.parse_args()

    inst = load_instance(args.instance)
    res = hill_climbing(inst, seed=args.seed, max_evals=args.max_evals)
    print(f"{inst.name}: peļņa = {res.profit:.3f}, laiks = {res.time_s:.2f} s, "
          f"restarti = {res.info['restarts']}")
    if inst.optimum:
        print(f"optimums = {inst.optimum['profit']:.3f}")
    print("kalendārs:", " ".join(inst.tracks[p]["id"] for p in res.calendar))


if __name__ == "__main__":
    main()
