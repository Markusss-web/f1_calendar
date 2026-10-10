"""Testa piemēru ģenerators F1 kalendāra plānošanas uzdevumam.

Ģenerē instances/f1_k{k}.json failus no data/tracks.json:
  * cost[a][b]    = haversine(a, b) km × (loģistikas €/km + CO2 t/km × CO2 cena €/t), milj. EUR
  * revenue[p][w] = bāzes ieņēmumi × sezonalitāte(klimats, mēnesis) × (1 ± troksnis), milj. EUR
  * k nedēļas nogales vienmērīgi sadalītas no marta pirmās līdz novembra pēdējai svētdienai

Palaišana:  python src/generator.py [--seed 2026] [--sizes 6 8 10 16 24]
"""

import argparse
import datetime as dt
import json
import math
import random
from pathlib import Path

from model import save_json, setup_console

ROOT = Path(__file__).resolve().parent.parent
TRACKS_FILE = ROOT / "data" / "tracks.json"
INSTANCES_DIR = ROOT / "instances"

DEFAULT_SIZES = [6, 8, 10, 16, 24]
SEASON_YEAR = 2026

# Sezonalitātes koeficienti pēc klimata tipa mēnešiem 3..11 (marts..novembris)
SEASONALITY = {
    #                     Mar   Apr   Mai   Jūn   Jūl   Aug   Sep   Okt   Nov
    "desert":            [1.00, 0.90, 0.60, 0.30, 0.20, 0.20, 0.40, 0.80, 1.00],
    "temperate":         [0.45, 0.65, 0.85, 1.00, 1.00, 0.95, 0.85, 0.60, 0.40],
    "mediterranean":     [0.60, 0.80, 1.00, 1.00, 0.85, 0.80, 0.95, 0.80, 0.55],
    "subtropical":       [0.90, 1.00, 0.90, 0.60, 0.50, 0.50, 0.70, 1.00, 0.95],
    "tropical":          [0.85, 0.85, 0.80, 0.75, 0.75, 0.80, 0.90, 0.95, 0.90],
    "southern_hemisphere": [1.00, 0.90, 0.70, 0.50, 0.45, 0.50, 0.70, 0.90, 1.00],
}

# Izmaksu parametri
COST_PARAMS = {
    "logistics_eur_per_km": 2000.0,   # kravas un komandu pārvadājumi
    "co2_t_per_km": 4.0,              # emisijas uz km (aviopārvadājumi)
    "co2_price_eur_per_t": 150.0,     # emisiju cena
    "road_threshold_km": 1500.0,      # īsus pārbraucienus veic ar kravas auto ...
    "road_factor": 0.6,               # ... kas ir lētāk un ar mazākām emisijām
}
REVENUE_NOISE = 0.05                  # ±5% nejaušs troksnis ieņēmumiem


def haversine_km(lat1, lon1, lat2, lon2):
    """Lielā riņķa attālums starp diviem punktiem km."""
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = phi2 - phi1
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def travel_cost(dist_km, params=COST_PARAMS):
    """Pārbrauciena izmaksas milj. EUR (loģistika + emisijas)."""
    eur_per_km = params["logistics_eur_per_km"] + params["co2_t_per_km"] * params["co2_price_eur_per_t"]
    cost = dist_km * eur_per_km / 1e6
    if dist_km < params["road_threshold_km"]:
        cost *= params["road_factor"]
    return cost


def season_weekends(k, year=SEASON_YEAR):
    """k svētdienas, vienmērīgi sadalītas no marta pirmās līdz novembra pēdējai svētdienai."""
    first = dt.date(year, 3, 1)
    first += dt.timedelta(days=(6 - first.weekday()) % 7)      # pirmā svētdiena martā
    last = dt.date(year, 11, 30)
    last -= dt.timedelta(days=(last.weekday() - 6) % 7)         # pēdējā svētdiena novembrī
    total_weeks = (last - first).days // 7
    weekends = []
    for i in range(k):
        week = round(i * total_weeks / (k - 1)) if k > 1 else 0
        date = first + dt.timedelta(weeks=week)
        weekends.append({"index": i, "date": date.isoformat(), "month": date.month})
    return weekends


def generate_instance(all_tracks, k, seed):
    """Izveido vienu piemēru ar k posmiem."""
    rng = random.Random(seed)
    if k < len(all_tracks):
        chosen = sorted(rng.sample(range(len(all_tracks)), k))   # trašu apakškopa
        tracks = [all_tracks[i] for i in chosen]
    else:
        tracks = list(all_tracks[:k])

    weekends = season_weekends(k)

    # Attālumu un izmaksu matricas (simetriskas)
    dist = [[0.0] * k for _ in range(k)]
    cost = [[0.0] * k for _ in range(k)]
    for a in range(k):
        for b in range(a + 1, k):
            d = haversine_km(tracks[a]["lat"], tracks[a]["lon"], tracks[b]["lat"], tracks[b]["lon"])
            dist[a][b] = dist[b][a] = round(d, 1)
            cost[a][b] = cost[b][a] = round(travel_cost(d), 4)

    # Ieņēmumu matrica: rinda = posms, kolonna = nedēļas nogale
    revenue = []
    for t in tracks:
        row = []
        for w in weekends:
            factor = SEASONALITY[t["climate"]][w["month"] - 3]
            noise = 1.0 + rng.uniform(-REVENUE_NOISE, REVENUE_NOISE)
            row.append(round(t["base_revenue"] * factor * noise, 4))
        revenue.append(row)

    return {
        "name": f"f1_k{k}",
        "k": k,
        "seed": seed,
        "units": "milj. EUR",
        "params": {"season_year": SEASON_YEAR, "revenue_noise": REVENUE_NOISE, **COST_PARAMS},
        "tracks": [{key: t[key] for key in ("id", "name", "country", "climate", "lat", "lon")} for t in tracks],
        "weekends": weekends,
        "revenue": revenue,
        "cost": cost,
        "distance_km": dist,
    }


def main():
    setup_console()
    parser = argparse.ArgumentParser(description="F1 kalendāra testa piemēru ģenerators")
    parser.add_argument("--seed", type=int, default=2026, help="bāzes random seed")
    parser.add_argument("--sizes", type=int, nargs="+", default=DEFAULT_SIZES, help="posmu skaiti k")
    args = parser.parse_args()

    all_tracks = json.loads(TRACKS_FILE.read_text(encoding="utf-8"))["tracks"]
    INSTANCES_DIR.mkdir(parents=True, exist_ok=True)

    for k in args.sizes:
        if not 2 <= k <= len(all_tracks):
            raise SystemExit(f"k={k} jābūt robežās 2..{len(all_tracks)}")
        inst = generate_instance(all_tracks, k, seed=args.seed * 1000 + k)
        path = INSTANCES_DIR / f"{inst['name']}.json"

        # Ja dati nav mainījušies, saglabā iepriekš aprēķināto optimumu / labāko zināmo
        if path.exists():
            old = json.loads(path.read_text(encoding="utf-8"))
            if old.get("revenue") == inst["revenue"] and old.get("cost") == inst["cost"]:
                for key in ("optimum", "best_known"):
                    if key in old:
                        inst[key] = old[key]

        save_json(path, inst)
        names = ", ".join(t["id"] for t in inst["tracks"])
        print(f"{path.relative_to(ROOT)}: k={k} [{names}]")


if __name__ == "__main__":
    main()
