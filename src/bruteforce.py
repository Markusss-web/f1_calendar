"""Pilnā pārlase precīzam optimumam (k ≤ 10).

Rekursīvi piešķir posmus nedēļas nogalēm 0, 1, ..., k−1 un peļņu skaita inkrementāli,
tāpēc katra permutācija izmaksā O(1) papildu darba. Pēc noklusējuma tiek apskatītas visas
k! permutācijas; ar --bnb papildus izmanto zaru un robežu (branch and bound) nogriešanu —
arī tā dod precīzu optimumu, tikai ātrāk.

Rezultāts tiek saglabāts instances failā laukā "optimum" un netiek rēķināts atkārtoti
(ja vien nav norādīts --force).

Palaišana:  python src/bruteforce.py [instances/f1_k8.json ...] [--max-k 10] [--bnb] [--force]
"""

import argparse
import math
import time

from model import list_instances, load_instance, profit, save_instance, setup_console

MAX_K = 10


def brute_force(inst, use_bound=False):
    """Atgriež (best_profit, best_calendar, visited_leaves)."""
    n = inst.k
    rev, cost = inst.revenue, inst.cost
    used = [False] * n
    cal = [0] * n
    best = [-math.inf, None]
    leaves = [0]

    # Augšējā robeža atlikušajiem posmiem: katram max ieņēmumi atlikušajās nogalēs, ceļš ≥ 0
    suffix_max = [[max(rev[p][w:]) for w in range(n)] for p in range(n)]

    def dfs(pos, prev, acc):
        if pos == n:
            leaves[0] += 1
            if acc > best[0]:
                best[0], best[1] = acc, cal[:]
            return
        if use_bound:
            bound = acc + sum(suffix_max[p][pos] for p in range(n) if not used[p])
            if bound <= best[0]:
                return
        rev_pos = [rev[p][pos] for p in range(n)]
        cost_prev = cost[prev] if pos > 0 else [0.0] * n
        for p in range(n):
            if not used[p]:
                used[p] = True
                cal[pos] = p
                dfs(pos + 1, p, acc + rev_pos[p] - cost_prev[p])
                used[p] = False

    dfs(0, 0, 0.0)
    best_cal = best[1]
    return profit(inst, best_cal), best_cal, leaves[0]


def solve_and_store(inst, use_bound=False, force=False):
    if inst.optimum and not force:
        print(f"{inst.name}: optimums jau saglabāts = {inst.optimum['profit']:.4f} (izlaižu)")
        return inst.optimum
    start = time.perf_counter()
    best, cal, leaves = brute_force(inst, use_bound)
    elapsed = time.perf_counter() - start
    inst.data["optimum"] = {
        "profit": round(best, 6),
        "calendar": cal,
        "method": "branch and bound" if use_bound else "full enumeration",
        "leaves": leaves,
        "time_s": round(elapsed, 2),
    }
    save_instance(inst)
    print(f"{inst.name}: optimums = {best:.4f}, apskatītas {leaves} permutācijas "
          f"({math.factorial(inst.k)} kopā), {elapsed:.1f} s")
    return inst.data["optimum"]


def main():
    setup_console()
    parser = argparse.ArgumentParser(description="Pilnā pārlase precīzam optimumam")
    parser.add_argument("instances", nargs="*", help="instanču faili (pēc noklusējuma visi ar k ≤ max-k)")
    parser.add_argument("--max-k", type=int, default=MAX_K)
    parser.add_argument("--bnb", action="store_true", help="izmantot branch and bound nogriešanu")
    parser.add_argument("--force", action="store_true", help="pārrēķināt arī saglabātos")
    args = parser.parse_args()

    insts = [load_instance(p) for p in args.instances] if args.instances else list_instances()
    for inst in insts:
        if inst.k > args.max_k:
            print(f"{inst.name}: k={inst.k} > {args.max_k}, pilnā pārlase netiek veikta")
            continue
        solve_and_store(inst, use_bound=args.bnb, force=args.force)


if __name__ == "__main__":
    main()
