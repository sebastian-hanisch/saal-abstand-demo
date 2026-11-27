"""Kennzahlen, Verdikte (reine Funktionen) und Zugriff auf die vorgerechneten Messreihen."""

import json
import math
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path

import sab_constants as C
import sab_exact as X
from sab_offline import offline_optimum
from sab_rng import SplitMix64
from sab_rules import RunResult, run_sequence
from sab_scenario import Params, demand_of, sample_sequence

RESULTS_PATH = Path(__file__).resolve().parent / "data" / "sab_results.json"


@dataclass(frozen=True, kw_only=True)
class Settings:
    params: Params = Params()
    seed: int = C.DEFAULT_SEED


@dataclass(frozen=True)
class Stat:
    persons: float             # gesetzte Personen im Mittel über die Folgen
    persons_se: float
    share: float               # Anteil am Offline-Optimum (Mittel der Anteile je Folge)
    share_se: float
    rejected: float            # abgewiesene Gruppen im Mittel
    occupancy: float           # gesetzte Personen durch Plätze


@dataclass(frozen=True)
class Analysis:
    settings: Settings
    n: int                     # Zahl der Anfragefolgen
    offline_mean: float        # Offline-Optimum im Mittel (Personen)
    offline_proven: int        # Folgen, bei denen das Optimum bewiesen wurde
    stats: dict                # Vergabeweise -> Stat
    example: RunResult         # eine Folge (die erste) mit der eingestellten Vergabeweise
    example_requests: tuple    # ihre Anfragefolge


def _mean_se(values):
    n = len(values)
    m = sum(values) / n
    se = math.sqrt(sum((v - m) ** 2 for v in values) / (n - 1) / n) if n > 1 else 0.0
    return m, se


def analyse(settings: Settings) -> Analysis:
    """Live-Rechnung: C.LIVE_SEQS Anfragefolgen (Zufalls-Seed seed · 1000 + k), je Folge das exakte Offline-Optimum und alle Vergabeweisen."""
    p, seed = settings.params, settings.seed
    offs, proven = [], 0
    runs = {a: [] for a in C.ASSIGNS}
    best_online = []
    example = example_seq = None
    for k in range(C.LIVE_SEQS):
        s = seed * C.SUBSEED_STRIDE + k
        seq = sample_sequence(p, SplitMix64(s))
        off = offline_optimum(p, demand_of(seq))
        offs.append(max(off.persons or 0, 1))
        proven += 1 if off.status == 0 else 0
        best = 0
        for a in C.ASSIGNS:
            r = run_sequence(p, seq, a, s + 1)
            best = max(best, r.persons)
            runs[a].append((r, len(seq)))
            if k == 0 and a == p.assign:
                example, example_seq = r, tuple(seq)
        best_online.append(best)
        if off.status != 0:          # Zeitgrenze: die gefundene Lösung ist nur eine untere Schranke des Optimums; jede Online-Belegung ist ebenfalls zulässig, also ist ihr Maximum eine zweite untere Schranke
            offs[-1] = max(offs[-1], best)
    if example is None:      # eingestellte Vergabeweise gehört nicht zu C.ASSIGNS (nur Tests)
        s = seed * C.SUBSEED_STRIDE
        example_seq = tuple(sample_sequence(p, SplitMix64(s)))
        example = run_sequence(p, list(example_seq), p.assign, s + 1)
    stats = {}
    for a in C.ASSIGNS:
        persons = [r.persons for r, _n in runs[a]]
        shares = [pe / o for pe, o in zip(persons, offs)]
        rej = [sum(1 for f in r.accepted if not f) for r, _n in runs[a]]
        pm, pse = _mean_se(persons)
        sm, sse = _mean_se(shares)
        stats[a] = Stat(pm, pse, sm, sse, sum(rej) / len(rej), pm / p.seats)
    return Analysis(settings, C.LIVE_SEQS, sum(offs) / len(offs), proven, stats, example, example_seq)


def singles_capacity(params: Params) -> int:
    """Größte Zahl Einzelner im Saal (exakt)."""
    demand = [500] + [0] * (C.GMAX - 1)
    off = offline_optimum(params, demand, C.OFFLINE_TLIMIT)
    if off.status != 0:
        raise RuntimeError("Größte Zahl Einzelner innerhalb der Zeitgrenze nicht bewiesen")
    return off.persons


def free_singles(params: Params, runs: int, seed: int) -> dict:
    """Einzelne Gäste im Saal: freie Wahl gegen Platzanweiser (First-Fit) und gegen die Obergrenze (exakt). Anfragefolgen: Einzelne mit Last 1,5."""
    p = replace(params, dist="einzel", load=1.5)
    free, ff = [], []
    for k in range(runs):
        s = seed * C.SUBSEED_STRIDE + k
        seq = sample_sequence(p, SplitMix64(s))
        free.append(run_sequence(p, seq, "FREI", s + 1).persons)
        ff.append(run_sequence(p, seq, "FF", s + 1).persons)
    cap = singles_capacity(p)
    fm, fse = _mean_se(free)
    return {"capacity": cap, "free": fm, "free_se": fse, "ff": sum(ff) / len(ff), "runs": runs}


def group_capacity(params: Params) -> list:
    """Größte Personenzahl, wenn nur Gruppen EINER Größe g kommen (g = 1 … 6), im eingestellten Saal und mit der eingestellten Regel (exakt)."""
    out = []
    for g in range(1, C.GMAX + 1):
        demand = [0] * C.GMAX
        demand[g - 1] = 500
        off = offline_optimum(params, demand, C.OFFLINE_TLIMIT)
        out.append({"g": g, "persons": off.persons, "share": off.persons / params.seats, "status": off.status})
    return out


@lru_cache(maxsize=1)
def load_results() -> dict:
    return json.loads(RESULTS_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------------------------- Auswertung der Messreihen
def verhalten_cell(data: dict, hall: str, dist: str, load: float) -> dict:
    for r in data["verhalten"]:
        if (r["hall"], r["dist"], r["load"]) == (hall, dist, load):
            return r
    raise KeyError((hall, dist, load))


def gap_pct(cell: dict, behaviour: str) -> float:
    """Lücke zum Offline-Optimum in Prozent der Personen: 100 · (1 − Anteil)."""
    return 100.0 * (1.0 - cell["behaviours"][behaviour]["share"])


# ---------------------------------------------------------------------------------------------- Verdikte
def _pct(x: float, digits: int = 1) -> str:
    return f"{x:.{digits}f}".replace(".", ",") + " %"


def _num(x: float, digits: int = 1) -> str:
    return f"{x:.{digits}f}".replace(".", ",")


def verdict_assign(a: Analysis) -> tuple:
    """Die eingestellte Vergabeweise gegen den Platzanweiser (First-Fit) auf denselben Folgen."""
    p = a.settings.params
    s, ff = a.stats[p.assign], a.stats["FF"]
    diff = 100.0 * (ff.share - s.share)
    text = (f"Mit „{C.ASSIGN_LABELS[p.assign]}“ werden im Mittel über {a.n} Folgen {_pct(100 * s.share)} des Offline-Optimums erreicht ({_num(s.persons)} von {_num(a.offline_mean)} Personen, "
            f"Standardfehler {_num(100 * s.share_se)} Prozentpunkte)")
    note = ""
    if a.offline_proven < a.n:
        note = (f" Das Optimum wurde nur in {a.offline_proven} von {a.n} Folgen bewiesen (Zeitgrenze); in den übrigen ist der Bezugswert eine untere Schranke des Optimums (die beste gefundene Lösung, mindestens die beste Online-Belegung), "
                "der Anteil also eher zu hoch.")
    if p.assign == "FF":
        return ("success" if s.share >= 0.9 else "info"), text + ". Der Platzanweiser ist hier die Vergleichsgröße." + note
    text += f", mit dem Platzanweiser links {_pct(100 * ff.share)}."
    if abs(diff) < 0.05:
        text += " Kein Unterschied zum Platzanweiser links."
    elif diff > 0:
        text += f" Unterschied: {_num(diff)} Prozentpunkte zugunsten von „{C.ASSIGN_LABELS['FF']}“."
    else:
        text += f" Unterschied: {_num(-diff)} Prozentpunkte zugunsten dieser Vergabe."
    text += note
    if diff >= 5.0:
        return "warning", text
    if diff >= 1.0:
        return "info", text
    return "success", text


def verdict_ranking(a: Analysis) -> tuple:
    order = sorted(a.stats, key=lambda k: -a.stats[k].share)
    best, worst = order[0], order[-1]
    text = (f"Auf denselben {a.n} Anfragefolgen liegt „{C.ASSIGN_LABELS[best]}“ vorn ({_pct(100 * a.stats[best].share)} des Offline-Optimums) und „{C.ASSIGN_LABELS[worst]}“ hinten "
            f"({_pct(100 * a.stats[worst].share)}). Reihenfolge: " + ", ".join(f"{k} {_pct(100 * a.stats[k].share, 0)}" for k in order) + ".")
    spread = 100 * (a.stats[best].share - a.stats[worst].share)
    return ("info" if spread >= 1.0 else "success"), text


def verdict_free(row_n: int, hall: dict, rule: str) -> tuple:
    """Kernfrage 2: Was kostet freie Wahl? `hall`: Ergebnis von free_singles."""
    exact = X.rsa_expected(row_n)
    cap_row = X.singles_capacity(row_n)
    text = (f"Einzelne Gäste, die frei wählen, besetzen in einer Reihe mit {row_n} Plätzen im Mittel {_num(exact, 2)} von {cap_row} möglichen ({_pct(100 * exact / cap_row)}, exakt). "
            f"Im Saal mit der Regel {rule} sind es {_num(hall['free'])} von {hall['capacity']} ({_pct(100 * hall['free'] / hall['capacity'])}, Mittel über {hall['runs']} Läufe, "
            f"Standardfehler {_num(hall['free_se'], 2)}); ein Platzanweiser erreicht {_pct(100 * hall['ff'] / hall['capacity'])}.")
    return ("warning" if hall["free"] / hall["capacity"] < 0.9 else "info"), text


def verdict_groups(rows: list, rule: str) -> tuple:
    """Kernfrage 3: Heben Gruppen die Kapazität gegenüber Einzelnen? `rows`: Ergebnis von group_capacity."""
    single = rows[0]["persons"]
    best = max(rows, key=lambda r: (r["persons"], -r["g"]))
    worst_multi = min(rows[1:], key=lambda r: r["persons"])
    below = sum(1 for r in rows[1:] if r["persons"] < single)
    text = (f"Bei der Regel {rule} passen {single} Personen in den Saal, wenn nur Einzelne kommen ({_pct(100 * rows[0]['share'])} der Plätze). Gruppen der Größe {best['g']} schaffen {best['persons']} "
            f"({_pct(100 * best['share'])}), unter den Gruppengrößen ab 2 Personen am wenigsten die Größe {worst_multi['g']} mit {worst_multi['persons']}; {below} von 5 Gruppengrößen liegen unter den Einzelnen.")
    if best["persons"] > single:
        return "success", text + " Gruppen heben hier die Kapazität."
    return "info", text + " Gruppen heben hier die Kapazität nicht."
