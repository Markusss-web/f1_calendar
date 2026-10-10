"""Uzdevuma modelis: instances ielāde/saglabāšana, mērķa funkcija un gājienu delta novērtēšana.

Kalendārs ir permutācija `cal`, kur cal[w] = posma (trases) indekss nedēļas nogalē w.
    profit(cal) = Σ_w revenue[cal[w]][w] − Σ_w cost[cal[w]][cal[w+1]]

Gājieni (move = (kind, i, j)):
    "swap"    – samaina posmus pozīcijās i un j
    "reverse" – apgriež segmentu cal[i..j] (i < j)
    "insert"  – izņem posmu no pozīcijas i un ievieto pozīcijā j
delta_*() atgriež new_profit − old_profit (pozitīvs = uzlabojums), nepārrēķinot visu kalendāru.
"""

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INSTANCES_DIR = ROOT / "instances"
RESULTS_DIR = ROOT / "results"

MOVE_KINDS = ("swap", "reverse", "insert")


def setup_console():
    """Lai latviešu burti nesalauž izvadi Windows konsolē vai pāradresējot uz failu."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


# ---------------------------------------------------------------- instances

@dataclass
class Instance:
    name: str
    k: int
    revenue: list          # revenue[p][w]
    cost: list             # cost[a][b]
    tracks: list
    weekends: list
    data: dict             # pilns JSON saturs (lai var saglabāt atpakaļ)
    path: Path = None
    symmetric: bool = True

    @property
    def optimum(self):
        return self.data.get("optimum")

    @property
    def best_known(self):
        return self.data.get("best_known")


def load_instance(path):
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    cost = data["cost"]
    k = data["k"]
    symmetric = all(cost[a][b] == cost[b][a] for a in range(k) for b in range(a + 1, k))
    return Instance(data["name"], k, data["revenue"], cost, data["tracks"], data["weekends"],
                    data, path, symmetric)


def list_instances(directory=INSTANCES_DIR):
    """Visas instances, sakārtotas pēc k."""
    return sorted((load_instance(p) for p in Path(directory).glob("*.json")), key=lambda x: x.k)


def save_json(path, data):
    """JSON ar matricas rindām vienā rindā (kompaktāk un lasāmāk nekā indent=…)."""
    def fmt(value, level):
        pad = " " * level
        if isinstance(value, dict):
            items = [f'{pad} {json.dumps(key)}: {fmt(v, level + 1)}' for key, v in value.items()]
            return "{\n" + ",\n".join(items) + "\n" + pad + "}"
        if isinstance(value, list) and value and isinstance(value[0], (list, dict)):
            items = [pad + " " + (json.dumps(v, ensure_ascii=False) if isinstance(v, dict)
                                  else fmt(v, level + 1)) for v in value]
            return "[\n" + ",\n".join(items) + "\n" + pad + "]"
        return json.dumps(value, ensure_ascii=False)

    Path(path).write_text(fmt(data, 0) + "\n", encoding="utf-8")


def save_instance(inst):
    save_json(inst.path, inst.data)


# ---------------------------------------------------------------- mērķa funkcija

def revenue_total(inst, cal):
    rev = inst.revenue
    return sum(rev[p][w] for w, p in enumerate(cal))


def travel_total(inst, cal):
    cost = inst.cost
    return sum(cost[cal[w]][cal[w + 1]] for w in range(len(cal) - 1))


def profit(inst, cal):
    return revenue_total(inst, cal) - travel_total(inst, cal)


def is_permutation(cal, k):
    return sorted(cal) == list(range(k))


# ---------------------------------------------------------------- gājieni

def random_move(k, rng, cum_probs):
    """Nejaušs gājiens; cum_probs = kumulatīvās varbūtības (swap, reverse, insert)."""
    r = rng.random()
    kind = "swap" if r < cum_probs[0] else ("reverse" if r < cum_probs[1] else "insert")
    i = rng.randrange(k)
    j = rng.randrange(k - 1)
    if j >= i:
        j += 1
    if kind != "insert" and i > j:
        i, j = j, i
    return kind, i, j


def all_moves(k):
    """Pilna apkārtne bez dublikātiem (blakus elementu reverse/insert = swap)."""
    moves = [("swap", i, j) for i in range(k) for j in range(i + 1, k)]
    moves += [("reverse", i, j) for i in range(k) for j in range(i + 2, k)]
    moves += [("insert", i, j) for i in range(k) for j in range(k) if abs(i - j) > 1]
    return moves


def cumulative(probs):
    total = sum(probs)
    c0 = probs[0] / total
    return (c0, c0 + probs[1] / total)


def delta_swap(inst, cal, i, j):
    """Δ, samainot pozīcijas i < j. O(1)."""
    rev, c, n = inst.revenue, inst.cost, len(cal)
    a, b = cal[i], cal[j]
    d = rev[b][i] + rev[a][j] - rev[a][i] - rev[b][j]
    if j == i + 1:
        if i > 0:
            p = cal[i - 1]
            d += c[p][a] - c[p][b]
        d += c[a][b] - c[b][a]
        if j < n - 1:
            q = cal[j + 1]
            d += c[b][q] - c[a][q]
    else:
        ai, bi = cal[i + 1], cal[j - 1]
        if i > 0:
            p = cal[i - 1]
            d += c[p][a] - c[p][b]
        d += c[a][ai] - c[b][ai] + c[bi][b] - c[bi][a]
        if j < n - 1:
            q = cal[j + 1]
            d += c[b][q] - c[a][q]
    return d


def delta_reverse(inst, cal, i, j):
    """Δ, apgriežot segmentu cal[i..j], i < j. Ieņēmumi O(j−i), ceļš O(1) simetriskām izmaksām."""
    rev, c, n = inst.revenue, inst.cost, len(cal)
    d = 0.0
    for t in range(i, j + 1):
        d += rev[cal[i + j - t]][t] - rev[cal[t]][t]
    a, b = cal[i], cal[j]
    if i > 0:
        p = cal[i - 1]
        d += c[p][a] - c[p][b]
    if j < n - 1:
        q = cal[j + 1]
        d += c[b][q] - c[a][q]
    if not inst.symmetric:  # nesimetriskām izmaksām mainās arī segmenta iekšējās šķautnes
        for t in range(i, j):
            d += c[cal[t]][cal[t + 1]] - c[cal[t + 1]][cal[t]]
    return d


def delta_insert(inst, cal, i, j):
    """Δ, pārvietojot posmu no pozīcijas i uz j. Ieņēmumi O(|i−j|), ceļš O(1)."""
    rev, c, n = inst.revenue, inst.cost, len(cal)
    x = cal[i]
    d = 0.0
    if i < j:
        # cal[i+1..j] nobīdās par vienu pa kreisi, x nonāk pozīcijā j
        for t in range(i, j):
            d += rev[cal[t + 1]][t] - rev[cal[t]][t]
        d += rev[x][j] - rev[cal[j]][j]
        y = cal[j]
        if i > 0:
            p = cal[i - 1]
            d += c[p][x] - c[p][cal[i + 1]]
        d += c[x][cal[i + 1]] - c[y][x]
        if j < n - 1:
            q = cal[j + 1]
            d += c[y][q] - c[x][q]
    else:
        # cal[j..i-1] nobīdās par vienu pa labi, x nonāk pozīcijā j
        for t in range(j + 1, i + 1):
            d += rev[cal[t - 1]][t] - rev[cal[t]][t]
        d += rev[x][j] - rev[cal[j]][j]
        y = cal[j]
        if j > 0:
            p = cal[j - 1]
            d += c[p][y] - c[p][x]
        d += c[cal[i - 1]][x] - c[x][y]
        if i < n - 1:
            q = cal[i + 1]
            d += c[x][q] - c[cal[i - 1]][q]
    return d


_DELTA = {"swap": delta_swap, "reverse": delta_reverse, "insert": delta_insert}


def delta(inst, cal, move):
    kind, i, j = move
    return _DELTA[kind](inst, cal, i, j)


def apply_move(cal, move):
    """Izpilda gājienu uz vietas."""
    kind, i, j = move
    if kind == "swap":
        cal[i], cal[j] = cal[j], cal[i]
    elif kind == "reverse":
        cal[i:j + 1] = cal[i:j + 1][::-1]
    else:
        cal.insert(j, cal.pop(i))


# ---------------------------------------------------------------- rezultāts

@dataclass
class RunResult:
    algorithm: str
    calendar: list
    profit: float
    time_s: float
    evaluations: int                              # novērtēto gājienu skaits
    history: list = field(default_factory=list)   # [(evaluations, current, best), ...]
    info: dict = field(default_factory=dict)
