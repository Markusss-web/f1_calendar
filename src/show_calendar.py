"""Izdrukā kalendāru cilvēkam lasāmā formā.

Avoti:
  --source best  (noklusējums) optimums, ja ir, citādi labākais zināmais, citādi palaiž SA
  --source sa    palaiž SA ar doto seed
  --source hc    palaiž hill climbing ar doto seed

Palaišana:  python src/show_calendar.py instances/f1_k10.json [--source sa --seed 3]
            python src/show_calendar.py 24        (īsāk: tikai k)
"""

import argparse
import datetime as dt
from pathlib import Path

from hill_climbing import hill_climbing
from model import INSTANCES_DIR, load_instance, profit, revenue_total, setup_console, travel_total
from sa import simulated_annealing

MONTHS_LV = {3: "marts", 4: "aprīlis", 5: "maijs", 6: "jūnijs", 7: "jūlijs", 8: "augusts",
             9: "septembris", 10: "oktobris", 11: "novembris"}


def resolve_path(arg):
    if arg.isdigit():
        return INSTANCES_DIR / f"f1_k{arg}.json"
    return Path(arg)


def get_calendar(inst, source, seed):
    if source == "best":
        if inst.optimum:
            return inst.optimum["calendar"], "precīzs optimums (pilnā pārlase)"
        if inst.best_known:
            return inst.best_known["calendar"], f"labākais zināmais ({inst.best_known['algorithm']})"
        source = "sa"
    if source == "sa":
        return simulated_annealing(inst, seed=seed).calendar, f"simulētā rūdīšana, seed={seed}"
    res = simulated_annealing(inst, seed=seed)  # HC budžets = SA budžets
    return hill_climbing(inst, seed=seed, max_evals=res.evaluations).calendar, f"hill climbing, seed={seed}"


def print_calendar(inst, cal, title):
    dist = inst.data.get("distance_km")
    print(f"{inst.name} — {title}")
    header = (f"{'Nr':>3}  {'Datums':<10}  {'Mēnesis':<10}  {'Trase':<31}  {'Valsts':<15}  "
              f"{'Klimats':<19}  {'Ieņēm.':>7}  {'→ km':>6}  {'Ceļš':>6}")
    print(header)
    print("-" * len(header))
    for w, p in enumerate(cal):
        t, wk = inst.tracks[p], inst.weekends[w]
        date = dt.date.fromisoformat(wk["date"])
        if w < len(cal) - 1:
            q = cal[w + 1]
            km = f"{dist[p][q]:6.0f}" if dist else f"{'':6}"
            trip = f"{inst.cost[p][q]:6.2f}"
        else:
            km, trip = f"{'':6}", f"{'':6}"
        print(f"{w + 1:>3}  {date.strftime('%d.%m.%Y'):<10}  {MONTHS_LV[date.month]:<10}  "
              f"{t['name'][:31]:<31}  {t['country'][:15]:<15}  {t['climate']:<19}  "
              f"{inst.revenue[p][w]:7.2f}  {km}  {trip}")
    print("-" * len(header))
    rev, trav = revenue_total(inst, cal), travel_total(inst, cal)
    total_km = sum(dist[cal[w]][cal[w + 1]] for w in range(len(cal) - 1)) if dist else 0
    print(f"Ieņēmumi {rev:.3f} − ceļa izmaksas {trav:.3f} ({total_km:.0f} km) "
          f"= peļņa {profit(inst, cal):.3f} milj. EUR")
    if inst.optimum:
        gap = 100 * (inst.optimum["profit"] - profit(inst, cal)) / abs(inst.optimum["profit"])
        print(f"Optimums {inst.optimum['profit']:.3f}, atkāpe {gap:.3f}%")


def main():
    setup_console()
    parser = argparse.ArgumentParser(description="Kalendāra izdruka")
    parser.add_argument("instance", help="instances fails vai k (piem. 24)")
    parser.add_argument("--source", choices=("best", "sa", "hc"), default="best")
    parser.add_argument("--seed", type=int, default=1)
    args = parser.parse_args()

    inst = load_instance(resolve_path(args.instance))
    cal, title = get_calendar(inst, args.source, args.seed)
    print_calendar(inst, cal, title)


if __name__ == "__main__":
    main()
