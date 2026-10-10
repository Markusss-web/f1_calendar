"""Simulētā rūdīšana (SA) F1 kalendāra plānošanai (maksimizācija).

Palaišana vienai instancei:  python src/sa.py instances/f1_k10.json [--seed 1] [--alpha 0.95]
"""

import argparse
import math
import random
import time

from model import (RunResult, apply_move, cumulative, delta, load_instance, profit,
                   random_move, setup_console)

DEFAULTS = {
    "alpha": 0.99,              # ģeometriskā dzesēšana: T ← alpha·T
    "iters_per_temp": None,     # gājieni vienā temperatūras līmenī (None → 25·k)
    "p0": 0.8,                  # vēlamā sākotnējā pasliktinājumu pieņemšanas varbūtība
    "t_min_ratio": 1e-3,        # apstājas, kad T < T0·t_min_ratio
    "move_probs": (0.4, 0.3, 0.3),  # swap, reverse, insert
    "t0_samples": 200,          # nejaušo gājienu skaits T0 noteikšanai
}


def initial_temperature(inst, rng, cum_probs, p0, samples):
    """T0 tā, lai vidēja pasliktinājuma pieņemšanas varbūtība būtu p0: exp(−mean|Δ|/T0) = p0."""
    cal = list(range(inst.k))
    rng.shuffle(cal)
    worse = []
    for _ in range(samples):
        move = random_move(inst.k, rng, cum_probs)
        d = delta(inst, cal, move)
        if d < 0:
            worse.append(-d)
        apply_move(cal, move)          # nejaušā pastaiga, lai paraugi nebūtu no viena punkta
    mean_abs = sum(worse) / len(worse) if worse else 1.0
    return -mean_abs / math.log(p0)


def simulated_annealing(inst, seed=None, alpha=DEFAULTS["alpha"],
                        iters_per_temp=DEFAULTS["iters_per_temp"], p0=DEFAULTS["p0"],
                        t_min_ratio=DEFAULTS["t_min_ratio"], move_probs=DEFAULTS["move_probs"],
                        t0_samples=DEFAULTS["t0_samples"]):
    rng = random.Random(seed)
    k = inst.k
    cum_probs = cumulative(move_probs)
    length = iters_per_temp or 25 * k
    start = time.perf_counter()

    t0 = initial_temperature(inst, rng, cum_probs, p0, t0_samples)
    t_min = t0 * t_min_ratio

    # Nejaušs sākuma risinājums
    cal = list(range(k))
    rng.shuffle(cal)
    current = profit(inst, cal)
    best, best_cal = current, cal[:]

    temp = t0
    evaluations = accepted = 0
    history = [(0, current, best)]
    rand, exp = rng.random, math.exp

    while temp > t_min:
        for _ in range(length):
            move = random_move(k, rng, cum_probs)
            d = delta(inst, cal, move)
            evaluations += 1
            # Uzlabojumu pieņem vienmēr, pasliktinājumu ar varbūtību exp(−|Δ|/T)
            if d >= 0 or rand() < exp(d / temp):
                apply_move(cal, move)
                current += d
                accepted += 1
                if current > best + 1e-9:
                    best, best_cal = current, cal[:]
        history.append((evaluations, current, best))
        temp *= alpha

    best = profit(inst, best_cal)  # precīza vērtība (bez uzkrātās peldošā punkta kļūdas)
    return RunResult("SA", best_cal, best, time.perf_counter() - start, evaluations, history,
                     {"t0": t0, "levels": len(history) - 1, "iters_per_temp": length,
                      "acceptance_rate": accepted / max(evaluations, 1)})


def main():
    setup_console()
    parser = argparse.ArgumentParser(description="Simulētā rūdīšana vienai instancei")
    parser.add_argument("instance")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--alpha", type=float, default=DEFAULTS["alpha"])
    parser.add_argument("--iters-per-temp", type=int, default=None)
    parser.add_argument("--p0", type=float, default=DEFAULTS["p0"])
    parser.add_argument("--t-min-ratio", type=float, default=DEFAULTS["t_min_ratio"])
    parser.add_argument("--move-probs", type=float, nargs=3, default=DEFAULTS["move_probs"],
                        metavar=("SWAP", "REVERSE", "INSERT"))
    args = parser.parse_args()

    inst = load_instance(args.instance)
    res = simulated_annealing(inst, seed=args.seed, alpha=args.alpha,
                              iters_per_temp=args.iters_per_temp, p0=args.p0,
                              t_min_ratio=args.t_min_ratio, move_probs=args.move_probs)
    print(f"{inst.name}: peļņa = {res.profit:.3f}, laiks = {res.time_s:.2f} s, "
          f"gājieni = {res.evaluations}, T0 = {res.info['t0']:.3f}, "
          f"pieņemti = {res.info['acceptance_rate']:.1%}")
    if inst.optimum:
        print(f"optimums = {inst.optimum['profit']:.3f}")
    print("kalendārs:", " ".join(inst.tracks[p]["id"] for p in res.calendar))


if __name__ == "__main__":
    main()
