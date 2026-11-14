"""Jede Zahl der README-Tabelle „Befunde“ wird hier gezählt (DEMO-PLAYBOOK 11a): über die ganze Messdatei `data/sab_results.json`;
einige Zeilen rechnen die Tests außerdem neu (Rekursion, Gruppenkapazitäten per ganzzahligem Programm, freie Wahl in einer Reihe) und prüfen so, dass die Datei zum Code passt."""

import math

import pytest

import sab_constants as C
import sab_evaluation as ev
import sab_exact as X
from sab_offline import offline_optimum
from sab_rng import SplitMix64
from sab_rules import run_sequence
from sab_scenario import Params, sample_sequence

DATA = ev.load_results()
V = DATA["verhalten"]
VG = [r for r in V if r["dist"] != "einzel"]          # die 12 Zellen mit Gruppen
R = DATA["raster"]
FIVE = ("FF", "BF", "FREI", "MITTE", "WEIT_E")


def sh(r, b):
    return 100.0 * r["behaviours"][b]["share"]


def cell(hall, dist, load):
    return next(r for r in V if (r["hall"], r["dist"], r["load"]) == (hall, dist, load))


def rcell(rule, dist, load):
    return next(r for r in R if (r["rule"], r["dist"], r["load"]) == (rule, dist, load))


def test_messreihe_hat_die_erwartete_form():
    m = DATA["meta"]
    assert m["sweep_seeds"] == [C.SWEEP_SEEDS[0], C.SWEEP_SEEDS[-1]] == [100000, 100099] and len(C.SWEEP_SEEDS) == 100 and m["sub_seed_stride"] == C.SUBSEED_STRIDE == 1000
    assert len(V) == 16 and len(VG) == 12 and len(R) == 18 and len(DATA["vorlage"]) == 6 and len(DATA["gruppen"]) == 18
    assert all(r["n"] == 100 for r in V) and all(r["n"] == (100 if r["dist"] == "einzel" else 40) for r in R)
    assert all(r["offline_optimal"] == r["n"] for r in V + R)            # das Offline-Optimum war in jeder Zelle bewiesen
    assert all(g["status"] == 0 for g in DATA["gruppen"])


def test_wer_vergibt_bei_last_1_0():
    """Befund 1: Anteile am Offline-Optimum der fünf Vergabeweisen, Saal 8 × 16 mit gleich langen Reihen."""
    rows = {d: cell("gleich", d, 1.0) for d in ("paare", "familie", "gleich")}
    assert [round(sh(rows[d], "FF"), 1) for d in rows] == [92.4, 93.5, 92.9]
    assert [round(sh(rows[d], "FREI"), 1) for d in rows] == [81.5, 80.1, 78.2]
    assert [round(sh(rows[d], "MITTE"), 1) for d in rows] == [89.0, 88.3, 86.3]
    assert [round(sh(rows[d], "WEIT_E"), 1) for d in rows] == [85.9, 88.3, 87.4]


def test_wer_vergibt_platzanweiser_vorn_und_freie_wahl_hinten_in_allen_12_zellen():
    assert len(VG) == 12
    assert all(sh(r, "FF") > max(sh(r, b) for b in ("FREI", "MITTE", "WEIT_E")) for r in VG)
    assert round(min(sh(r, "FF") - max(sh(r, b) for b in ("FREI", "MITTE", "WEIT_E")) for r in VG), 1) == 1.3
    assert all(sh(r, "FREI") == min(sh(r, b) for b in FIVE) for r in VG)


def test_last_freie_wahl_verliert_schon_bei_70_prozent_last():
    loss = lambda r, b: 100.0 - sh(r, b)      # noqa: E731
    lo = [r for r in VG if r["load"] == 0.7]
    hi = [r for r in VG if r["load"] == 1.0]
    assert len(lo) == len(hi) == 6
    assert (round(min(loss(r, "FREI") for r in lo), 1), round(max(loss(r, "FREI") for r in lo), 1)) == (11.5, 15.5)
    assert (round(min(loss(r, "FREI") for r in hi), 1), round(max(loss(r, "FREI") for r in hi), 1)) == (18.5, 21.8)
    assert round(max(loss(r, "FF") for r in lo), 1) == 0.7
    assert (round(min(loss(r, "FF") for r in hi), 1), round(max(loss(r, "FF") for r in hi), 1)) == (6.5, 7.7)


def test_freie_wahl_reihe_exakt_gegen_simulation_und_grenzwert():
    rows = {r["n"]: r for r in DATA["rsa"]["reihe"]}
    assert [round(rows[n]["exact"], 3) for n in (10, 20, 50, 100)] == [4.620, 8.944, 21.914, 43.530]
    assert [round(100 * rows[n]["exact"] / rows[n]["capacity"], 1) for n in (10, 20, 50, 100)] == [92.4, 89.4, 87.7, 87.1]
    assert rows[100]["capacity"] == 50 and round(rows[100]["sim"], 3) == 43.533 and round(rows[100]["sim_se"], 3) == 0.010
    assert all(abs(r["sim"] - r["exact"]) < 4 * r["sim_se"] for r in rows.values())
    assert round((1 - math.exp(-2)) / 2, 4) == 0.4323 and round(100 * (1 - math.exp(-2)), 1) == 86.5
    assert all(X.rsa_expected(n) == pytest.approx(rows[n]["exact"]) for n in rows)


def test_freie_wahl_reihe_neu_simuliert():
    m, se = X.rsa_simulate_row(20, 20000, 99)
    assert abs(m - 8.944) < 4 * se + 0.005


def test_freie_wahl_raster_einzelne():
    rows = {r["rule"]: r for r in DATA["rsa"]["raster"]}
    assert [round(rows[k]["free"], 1) for k in C.RULES] == [72.2, 60.6, 33.5]
    assert [rows[k]["capacity"] for k in C.RULES] == [80, 80, 40] and all(rows[k]["ff"] == rows[k]["capacity"] for k in C.RULES) and all(rows[k]["n"] == 200 for k in C.RULES)
    assert [round(100 * rows[k]["free"] / rows[k]["capacity"], 1) for k in C.RULES] == [90.2, 75.7, 83.7]
    assert round(10 * X.rsa_expected(16), 2) == 72.14 and abs(rows["ROW"]["free"] - 10 * X.rsa_expected(16)) < 4 * rows["ROW"]["free_se"]       # ROW: zehn unabhängige Reihen


def test_freie_wahl_raster_neu_gerechnet_fuer_row():
    p = Params(rows=10, cols=16, dist="einzel", load=1.5)
    free = [run_sequence(p, sample_sequence(p, SplitMix64(k)), "FREI", k + 1).persons for k in range(60)]
    assert abs(sum(free) / len(free) - 10 * X.rsa_expected(16)) < 1.0


def test_abstand_suchen_definitionen_und_vergleich_mit_freier_wahl():
    c = cell("gleich", "paare", 1.0)
    assert [round(sh(c, b), 1) for b in ("WEIT_E", "WEIT_R", "WEIT_W")] == [85.9, 82.9, 76.0]
    assert all(sh(r, "WEIT_E") > sh(r, "WEIT_R") > sh(r, "WEIT_W") for r in VG)
    assert all(sh(r, "WEIT_E") > sh(r, "FREI") for r in VG) and round(min(sh(r, "WEIT_E") - sh(r, "FREI") for r in VG), 1) == 4.4
    assert (round(sh(cell("gleich", "einzel", 1.0), "WEIT_E"), 1), round(sh(cell("gleich", "einzel", 1.0), "FREI"), 1)) == (82.8, 90.4)
    assert (round(sh(cell("bogen", "einzel", 1.0), "WEIT_E"), 1), round(sh(cell("bogen", "einzel", 1.0), "FREI"), 1)) == (92.4, 87.4)
    manh = [rcell("MANH", d, ld) for d in ("paare", "familie") for ld in (1.0, 1.5)]
    assert [round(sh(r, "WEIT_E") - sh(r, "FREI"), 1) for r in manh] == [-3.0, -2.7, 0.2, 0.0]


def test_best_fit_gegen_first_fit():
    assert len(V) == 16 and round(max(abs(sh(r, "FF") - sh(r, "BF")) for r in V), 2) == 0.04
    for rule in ("ROW", "KING"):
        assert round(max(abs(sh(r, "FF") - sh(r, "BF")) for r in R if r["rule"] == rule), 2) == 0.07
    paare = [rcell("MANH", "paare", ld) for ld in (1.0, 1.5)]
    familie = [rcell("MANH", "familie", ld) for ld in (1.0, 1.5)]
    assert [round(sh(r, "BF") - sh(r, "FF"), 1) for r in paare] == [1.8, 1.8]
    assert [round(sh(r, "FF") - sh(r, "BF"), 1) for r in familie] == [0.2, 0.0]


def test_raster_rangfolge():
    cells = [r for r in R if r["dist"] != "einzel"]
    assert len(cells) == 12
    assert (round(min(sh(r, "FF") for r in cells), 1), round(max(sh(r, "FF") for r in cells), 1)) == (86.8, 93.5)
    frei = {k: [sh(r, "FREI") for r in cells if r["rule"] == k] for k in C.RULES}
    assert [(round(min(frei[k]), 1), round(max(frei[k]), 1)) for k in C.RULES] == [(79.6, 81.5), (76.8, 80.8), (73.2, 75.9)]
    assert all(sh(r, "FF") > sh(r, "FREI") for r in cells)
    manh = [r for r in cells if r["rule"] == "MANH"]
    assert all(sh(r, "MITTE") > sh(r, "FF") for r in manh)
    gaps = sorted(round(sh(r, "MITTE") - sh(r, "FF"), 1) for r in manh)
    assert (gaps[0], gaps[-1]) == (1.8, 3.7)
    other = [round(sh(r, "FF") - sh(r, "MITTE"), 1) for r in cells if r["rule"] != "MANH"]
    assert (min(other), max(other)) == (3.1, 5.4)


def test_gruppen_regelgeometrie():
    g = {(r["rule"], r["g"]): r["persons"] for r in DATA["gruppen"]}
    assert [g["ROW", k] for k in range(1, 7)] == [80, 100, 120, 120, 100, 120]
    assert [g["MANH", k] for k in range(1, 7)] == [80, 80, 75, 80, 75, 60]
    assert [g["KING", k] for k in range(1, 7)] == [40, 50, 60, 60, 50, 60]
    assert all(g["ROW", k] == 10 * X.row_capacity(16, k) for k in range(1, 7))
    assert all(r["formula"] == r["persons"] for r in DATA["gruppen"] if r["rule"] == "ROW")


@pytest.mark.parametrize("rule,g,expected", [("ROW", 3, 120), ("MANH", 6, 60), ("KING", 2, 50)])
def test_gruppen_neu_gerechnet(rule, g, expected):
    p = Params(rows=10, cols=16, rule=rule)
    demand = [0] * C.GMAX
    demand[g - 1] = 500
    res = offline_optimum(p, demand, 20.0)
    assert res.status == 0 and res.persons == expected


def test_sperrmatrix_gegen_platzanweiser():
    rows = DATA["vorlage"]
    assert len(rows) == 6 and all(r["hall"] == "gleich" for r in rows)
    gaps = [100 * (r["ff_share"] - r["template_share"]) for r in rows]
    assert all(x > 0 for x in gaps) and (round(min(gaps), 1), round(max(gaps), 1)) == (3.2, 5.7)
