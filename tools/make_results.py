"""Erzeugt `data/sab_results.json`: vorgerechnete Messreihen (Simulationen mit festen Zufalls-Seeds, exaktes Offline-Optimum).

    python tools/make_results.py <teil> [<teil> ...]      Teile: verhalten raster gruppen rsa vorlage

Jeder Teil schreibt seinen Abschnitt und lässt die übrigen stehen. Folge k einer Zelle hat den Zufalls-Seed `C.SWEEP_SEEDS[k] * 1000` (Anfragefolge) und `... + 1` (freie Wahl)."""
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import sab_constants as C  # noqa: E402
import sab_exact as X  # noqa: E402
import sab_template as T  # noqa: E402
from sab_offline import offline_optimum  # noqa: E402
from sab_rng import SplitMix64  # noqa: E402
from sab_rules import run_sequence  # noqa: E402
from sab_scenario import Params, demand_of, sample_sequence  # noqa: E402

OUT = ROOT / "data" / "sab_results.json"
TLIMIT = 20.0


def load() -> dict:
    return json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}


def save(data: dict):
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_bytes((json.dumps(data, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))   # LF auch unter Windows


def mean_se(values):
    n = len(values)
    m = sum(values) / n
    se = math.sqrt(sum((v - m) ** 2 for v in values) / (n - 1) / n) if n > 1 else 0.0
    return m, se


def cell(params: Params, behaviours, n_seq: int):
    """Eine Zelle: n_seq Folgen, je Folge Offline-Optimum und alle Vergabeweisen. Rückgabe: Mittel und Standardfehler der gesetzten Personen und ihres Anteils am Offline-Optimum."""
    offs, pers, status = [], {b: [] for b in behaviours}, []
    for k in range(n_seq):
        seed = C.SWEEP_SEEDS[k] * C.SUBSEED_STRIDE
        seq = sample_sequence(params, SplitMix64(seed))
        off = offline_optimum(params, demand_of(seq), TLIMIT)
        offs.append(off.persons)
        status.append(off.status)
        for b in behaviours:
            pers[b].append(run_sequence(params, seq, b, seed + 1).persons)
    out = {"offline_mean": sum(offs) / n_seq, "offline_optimal": sum(1 for s in status if s == 0), "n": n_seq, "behaviours": {}}
    for b in behaviours:
        m, se = mean_se([p / o for p, o in zip(pers[b], offs)])
        pm, pse = mean_se(pers[b])
        out["behaviours"][b] = {"persons": pm, "persons_se": pse, "share": m, "share_se": se}
    return out


def part_verhalten(data):
    rows = []
    for hn, hall in (("gleich", "gleich"), ("bogen", "bogen")):
        for dist in ("einzel", "paare", "familie", "gleich"):
            for load in (0.7, 1.0):
                p = Params(rows=8, cols=16, hall=hall, dist=dist, load=load)
                c = cell(p, C.BEHAVIOURS_ALL, len(C.SWEEP_SEEDS))
                rows.append({"hall": hn, "dist": dist, "load": load, "seats": p.seats, **c})
                print("verhalten", hn, dist, load, {b: round(100 * v["share"], 1) for b, v in c["behaviours"].items()}, flush=True)
    data["verhalten"] = rows


def part_raster(data):
    rows = []
    for rule in C.RULES:
        for dist in ("einzel", "paare", "familie"):
            for load in (1.0, 1.5):
                p = Params(rows=10, cols=16, rule=rule, dist=dist, load=load)
                n = 100 if dist == "einzel" else 40
                c = cell(p, C.ASSIGNS, n)
                rows.append({"rule": rule, "dist": dist, "load": load, "seats": p.seats, **c})
                print("raster", rule, dist, load, {b: round(100 * v["share"], 1) for b, v in c["behaviours"].items()}, c["offline_optimal"], "/", n, flush=True)
    data["raster"] = rows


def part_gruppen(data):
    rows = []
    for rule in C.RULES:
        p = Params(rows=10, cols=16, rule=rule)
        for g in range(1, C.GMAX + 1):
            demand = [0] * C.GMAX
            demand[g - 1] = 500
            off = offline_optimum(p, demand, TLIMIT)
            rows.append({"rule": rule, "g": g, "persons": off.persons, "status": off.status, "seats": p.seats, "formula": 10 * X.row_capacity(16, g) if rule == "ROW" else None})
            print("gruppen", rule, g, off.persons, off.status, flush=True)
    data["gruppen"] = rows


def part_rsa(data):
    rsa = {"reihe": [], "raster": []}
    for n in (6, 10, 16, 20, 50, 100):
        m, se = X.rsa_simulate_row(n, 20000, 4242)
        rsa["reihe"].append({"n": n, "exact": X.rsa_expected(n), "sim": m, "sim_se": se, "capacity": X.singles_capacity(n)})
        print("rsa", n, X.rsa_expected(n), m, se, flush=True)
    for rule in C.RULES:
        p = Params(rows=10, cols=16, rule=rule, dist="einzel", load=1.5)
        free, ff = [], []
        for k in range(200):
            seed = C.SWEEP_SEEDS[k % 100] * C.SUBSEED_STRIDE + (k // 100) * 7
            seq = sample_sequence(p, SplitMix64(seed))
            free.append(run_sequence(p, seq, "FREI", seed + 1).persons)
            ff.append(run_sequence(p, seq, "FF", seed + 1).persons)
        demand = [0] * C.GMAX
        demand[0] = 500
        cap = offline_optimum(p, demand, TLIMIT).persons
        fm, fse = mean_se(free)
        rsa["raster"].append({"rule": rule, "seats": p.seats, "capacity": cap, "free": fm, "free_se": fse, "ff": sum(ff) / len(ff), "n": len(free)})
        print("rsa raster", rule, cap, fm, fse, sum(ff) / len(ff), flush=True)
    data["rsa"] = rsa


def part_vorlage(data):
    rows = []
    for hn in ("gleich",):      # im Saal mit Bogen hat jede Reihe eine andere Länge (über 2000 Muster): das ganzzahlige Programm der Vorlage ist dort nicht in vertretbarer Zeit lösbar
        for dist in ("paare", "familie", "gleich"):
            template = T.template_for(Params(rows=8, cols=16, hall=hn, dist=dist))
            for load in (0.7, 1.0):
                p = Params(rows=8, cols=16, hall=hn, dist=dist, load=load)
                ff, vo = [], []
                for k in range(len(C.SWEEP_SEEDS)):
                    seed = C.SWEEP_SEEDS[k] * C.SUBSEED_STRIDE
                    seq = sample_sequence(p, SplitMix64(seed))
                    off = offline_optimum(p, demand_of(seq), TLIMIT).persons
                    ff.append(run_sequence(p, seq, "FF", seed + 1).persons / off)
                    vo.append(T.run_template(p, seq, template) / off)
                (fm, fse), (vm, vse) = mean_se(ff), mean_se(vo)
                rows.append({"hall": hn, "dist": dist, "load": load, "n": len(ff), "ff_share": fm, "ff_se": fse, "template_share": vm, "template_se": vse})
                print("vorlage", hn, dist, load, round(100 * fm, 1), round(100 * vm, 1), flush=True)
    data["vorlage"] = rows


PARTS = {"verhalten": part_verhalten, "raster": part_raster, "gruppen": part_gruppen, "rsa": part_rsa, "vorlage": part_vorlage}


def main(argv):
    if not argv or any(a not in PARTS for a in argv):
        raise SystemExit(__doc__)
    data = load()
    data.setdefault("meta", {})
    data["meta"].update({"sweep_seeds": [C.SWEEP_SEEDS[0], C.SWEEP_SEEDS[-1]], "sub_seed_stride": C.SUBSEED_STRIDE, "tlimit": TLIMIT})
    for part in argv:
        PARTS[part](data)
        current = load()                   # nur den eigenen Abschnitt schreiben: parallele Läufe anderer Teile bleiben erhalten
        current.setdefault("meta", {}).update(data["meta"])
        current[part] = data[part]
        save(current)
        print("fertig:", part, flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
