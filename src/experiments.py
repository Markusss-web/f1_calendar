"""Eksperimenti: SA un hill climbing (HC) katram piemēram ar dažādiem random seed.

HC saņem tieši tik pat gājienu novērtējumu, cik iztērē SA (vienāds budžets).
Atsauces vērtība: precīzs optimums (no bruteforce.py, k ≤ 10) vai labākais zināmais
risinājums (tiek saglabāts instances failā laukā "best_known" un atjaunots, ja atrasts labāks).

Izvade:
  results/results.csv      – kopsavilkums (viena rinda = instance × algoritms)
  results/runs.csv         – katra atsevišķa palaišana
  results/results.md       – kopsavilkuma tabula Markdown formātā
  results/convergence.png  – konverģences grafiks lielākajai instancei (ja ir matplotlib)
  results/convergence.csv  – tie paši konverģences dati tabulas formā

Palaišana:  python src/experiments.py [--runs 20] [--seed 1] [--sizes 6 8 10 16 24]
"""

import argparse
import bisect
import csv
import statistics
import time

from bruteforce import MAX_K, solve_and_store
from hill_climbing import hill_climbing
from model import RESULTS_DIR, ROOT, list_instances, save_instance, setup_console
from sa import DEFAULTS, simulated_annealing

EPS = 1e-6
COLORS = {"SA": "#2a78d6", "HC": "#eb6834"}   # validēta kategoriskā palete (zils, oranžs)
LABELS = {"SA": "Simulētā rūdīšana", "HC": "Hill climbing ar restartiem"}


def gap_pct(value, ref):
    gap = 100.0 * (ref - value) / abs(ref)
    return 0.0 if abs(gap) < 1e-9 else gap   # bez "-0.000%" no peldošā punkta trokšņa


def reference(inst, runs):
    """Atgriež (atsauces vērtība, tips); vajadzības gadījumā atjauno best_known instances failā."""
    if inst.optimum:
        return inst.optimum["profit"], "optimums"
    best_run = max(runs, key=lambda r: r.profit)
    known = inst.best_known
    if known is None or best_run.profit > known["profit"] + EPS:
        inst.data["best_known"] = {"profit": round(best_run.profit, 6), "calendar": best_run.calendar,
                                   "algorithm": best_run.algorithm}
        save_instance(inst)
    return inst.best_known["profit"], "labākais zināmais"


def summarize(inst, algorithm, runs, ref, ref_type):
    values = [r.profit for r in runs]
    gaps = [gap_pct(v, ref) for v in values]
    return {
        "instance": inst.name,
        "k": inst.k,
        "algorithm": algorithm,
        "reference": round(ref, 4),
        "reference_type": ref_type,
        "best": round(max(values), 4),
        "mean": round(statistics.mean(values), 4),
        "worst": round(min(values), 4),
        "std": round(statistics.pstdev(values), 4),
        "mean_gap_pct": round(statistics.mean(gaps), 4),
        "max_gap_pct": round(max(gaps), 4),
        "hits": sum(1 for v in values if v >= ref - EPS),
        "runs": len(runs),
        "evaluations": runs[0].evaluations,
        "mean_time_s": round(statistics.mean(r.time_s for r in runs), 4),
    }


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path, summary, args, total_time):
    lines = [
        "# Eksperimentu rezultāti",
        "",
        f"Katram piemēram {args.runs} palaišanas ar seed {args.seed}..{args.seed + args.runs - 1}. "
        "Peļņa milj. EUR. HC saņem tādu pašu gājienu novērtējumu budžetu kā SA.",
        f"SA parametri: alpha = {args.alpha}, gājieni temperatūrā = "
        f"{args.iters_per_temp or '25·k'}, p0 = {args.p0}, T_min = T0·{args.t_min_ratio}.",
        "",
        "| k | Algoritms | Atsauce | Atsauces tips | Labākais | Vidējais | Sliktākais "
        "| Vid. atkāpe % | Maks. atkāpe % | Atrasts atsauces rez. | Gājieni | Vid. laiks, s |",
        "|---:|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary:
        lines.append(
            f"| {row['k']} | {row['algorithm']} | {row['reference']:.3f} | {row['reference_type']} "
            f"| {row['best']:.3f} | {row['mean']:.3f} | {row['worst']:.3f} "
            f"| {row['mean_gap_pct']:.3f} | {row['max_gap_pct']:.3f} | {row['hits']}/{row['runs']} "
            f"| {row['evaluations']} | {row['mean_time_s']:.3f} |")
    lines += ["", f"Kopējais eksperimentu laiks: {total_time:.1f} s.", ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def best_at(history, x):
    """Labākā vērtība pēc x novērtējumiem (vēsture ir pakāpju funkcija)."""
    idx = bisect.bisect_right([h[0] for h in history], x) - 1
    return history[max(idx, 0)][2]


def convergence(inst, runs_by_alg, ref, points=200):
    """Vidējā atkāpe % no atsauces atkarībā no novērtējumu skaita, visām palaišanām."""
    budget = max(r.evaluations for runs in runs_by_alg.values() for r in runs)
    grid = [round(budget * i / points) for i in range(points + 1)]
    curves = {alg: [statistics.mean(gap_pct(best_at(r.history, x), ref) for r in runs) for x in grid]
              for alg, runs in runs_by_alg.items()}
    return grid, curves


def plot_convergence(inst, runs_by_alg, grid, curves, path):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.ticker
    except ImportError:
        print("matplotlib nav instalēts — convergence.png netiek veidots (dati ir convergence.csv)")
        return False

    ink, muted, grid_color, base = "#0b0b0b", "#898781", "#e1e0d9", "#c3c2b7"
    plt.rcParams.update({"font.size": 10, "axes.edgecolor": base, "axes.labelcolor": "#52514e",
                         "xtick.color": muted, "ytick.color": muted, "text.color": ink})
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5), facecolor="#fcfcfb")

    # Kreisais: viena SA palaišana — pašreizējā un labākā peļņa (redzama pasliktinājumu pieņemšana)
    sa = runs_by_alg["SA"][0]
    xs = [h[0] for h in sa.history]
    ax1.plot(xs, [h[1] for h in sa.history], color=COLORS["SA"], lw=1, alpha=0.45, label="pašreizējā")
    ax1.plot(xs, [h[2] for h in sa.history], color=COLORS["SA"], lw=2, label="labākā atrastā")
    ax1.set_title(f"SA dinamika ({inst.name}, viena palaišana)", loc="left", fontsize=11)
    ax1.set_xlabel("gājienu novērtējumi")
    ax1.set_ylabel("peļņa, milj. EUR")
    ax1.legend(frameon=False, loc="lower right")

    # Labais: vidējā atkāpe no atsauces visām palaišanām
    for alg, curve in curves.items():
        ax2.plot(grid, curve, color=COLORS[alg], lw=2, label=f"{LABELS[alg]} (beigās {curve[-1]:.2f}%)")
    ax2.set_ylim(0, max(2.0, min(10.0, max(c[len(c) // 10] for c in curves.values()) * 1.1)))
    ax2.set_title(f"Vidējā atkāpe no atsauces ({len(runs_by_alg['SA'])} palaišanas)",
                  loc="left", fontsize=11)
    ax2.set_xlabel("gājienu novērtējumi")
    ax2.set_ylabel("atkāpe, %")
    ax2.legend(frameon=False, loc="upper right")

    thousands = matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}".replace(",", " "))
    for ax in (ax1, ax2):
        ax.xaxis.set_major_formatter(thousands)
        ax.set_facecolor("#fcfcfb")
        ax.grid(True, color=grid_color, lw=0.6)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=150, facecolor=fig.get_facecolor())
    plt.close(fig)
    return True


def main():
    setup_console()
    parser = argparse.ArgumentParser(description="SA un hill climbing eksperimenti")
    parser.add_argument("--runs", type=int, default=20)
    parser.add_argument("--seed", type=int, default=1, help="pirmais seed (seed, seed+1, ...)")
    parser.add_argument("--sizes", type=int, nargs="*", help="tikai šie k (pēc noklusējuma visi)")
    parser.add_argument("--alpha", type=float, default=DEFAULTS["alpha"])
    parser.add_argument("--iters-per-temp", type=int, default=None)
    parser.add_argument("--p0", type=float, default=DEFAULTS["p0"])
    parser.add_argument("--t-min-ratio", type=float, default=DEFAULTS["t_min_ratio"])
    parser.add_argument("--no-plot", action="store_true")
    args = parser.parse_args()

    insts = [i for i in list_instances() if not args.sizes or i.k in args.sizes]
    if not insts:
        raise SystemExit("Nav instanču — vispirms palaid: python src/generator.py")
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    start = time.perf_counter()
    summary, run_rows, all_runs = [], [], {}
    for inst in insts:
        if inst.k <= MAX_K and not inst.optimum:
            solve_and_store(inst)  # optimums vēl nav aprēķināts — pilnā pārlase

        runs = {"SA": [], "HC": []}
        for r in range(args.runs):
            seed = args.seed + r
            sa = simulated_annealing(inst, seed=seed, alpha=args.alpha,
                                     iters_per_temp=args.iters_per_temp, p0=args.p0,
                                     t_min_ratio=args.t_min_ratio)
            hc = hill_climbing(inst, seed=seed, max_evals=sa.evaluations)
            runs["SA"].append(sa)
            runs["HC"].append(hc)

        ref, ref_type = reference(inst, runs["SA"] + runs["HC"])
        for alg, alg_runs in runs.items():
            row = summarize(inst, alg, alg_runs, ref, ref_type)
            summary.append(row)
            for r, res in enumerate(alg_runs):
                run_rows.append({"instance": inst.name, "k": inst.k, "algorithm": alg,
                                 "seed": args.seed + r, "profit": round(res.profit, 4),
                                 "gap_pct": round(gap_pct(res.profit, ref), 4),
                                 "evaluations": res.evaluations, "time_s": round(res.time_s, 4),
                                 "calendar": " ".join(inst.tracks[p]["id"] for p in res.calendar)})
            print(f"{inst.name:7s} {alg}: labākais {row['best']:9.3f}  vidējais {row['mean']:9.3f}  "
                  f"sliktākais {row['worst']:9.3f}  atsauce {ref:9.3f} ({ref_type})  "
                  f"vid. atkāpe {row['mean_gap_pct']:.3f}%  trāpījumi {row['hits']}/{args.runs}  "
                  f"vid. laiks {row['mean_time_s']:.3f} s")
        all_runs[inst.name] = (inst, runs, ref)

    total = time.perf_counter() - start
    write_csv(RESULTS_DIR / "results.csv", summary)
    write_csv(RESULTS_DIR / "runs.csv", run_rows)
    write_markdown(RESULTS_DIR / "results.md", summary, args, total)

    # Konverģence lielākajai instancei
    inst, runs, ref = all_runs[insts[-1].name]
    grid, curves = convergence(inst, runs, ref)
    write_csv(RESULTS_DIR / "convergence.csv",
              [{"evaluations": x, **{f"{alg}_mean_gap_pct": round(c[i], 4) for alg, c in curves.items()}}
               for i, x in enumerate(grid)])
    if not args.no_plot and plot_convergence(inst, runs, grid, curves, RESULTS_DIR / "convergence.png"):
        print(f"grafiks: {(RESULTS_DIR / 'convergence.png').relative_to(ROOT)}")
    print(f"rezultāti saglabāti {RESULTS_DIR.relative_to(ROOT)}/ ({total:.1f} s)")


if __name__ == "__main__":
    main()
