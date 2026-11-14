"""Orakel-Tests: jede Kernrechnung gegen eine zweite, unabhängige Umsetzung (Aufzählung, Formel, naive Schleifen).

* Offline-Optimum (ganzzahliges Programm) gegen vollständige Aufzählung aller Belegungen kleiner Säle, für alle drei Regeln.
* Reihenkapazität gleicher Gruppen: Formel g · ⌊(n + 1) / (g + 1)⌋ gegen Aufzählung.
* Freie Wahl in einer Reihe: Rekursion E(n) gegen Mittel über ALLE Reihenfolgen der Plätze (n ≤ 8) und gegen Simulation.
* Online-Vergabe First-Fit: gegen eine naive Schleifenversion ohne numpy.
* Jede Vergabe liefert eine gültige Belegung (Schleifenprüfer)."""

import itertools
import math

import pytest

import sab_constants as C
import sab_exact as X
import sab_hall as H
from sab_offline import offline_optimum
from sab_rng import SplitMix64
from sab_rules import run_sequence
from sab_scenario import Params, demand_of, sample_sequence

NEIGH = {"ROW": [(0, 1), (0, -1)], "MANH": [(0, 1), (0, -1), (1, 0), (-1, 0)],
         "KING": [(dr, dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1) if (dr, dc) != (0, 0)]}


def _conflict(a, b, rule):
    """Zwei Platzierungen (Reihe, Start, Größe) verletzen die Regel: überlappen oder berühren sich (Nachbarschaft der Regel)."""
    cells_a = [(a[0], x) for x in range(a[1], a[1] + a[2])]
    cells_b = {(b[0], x) for x in range(b[1], b[1] + b[2])}
    for (r, x) in cells_a:
        if (r, x) in cells_b:
            return True
        for dr, dc in NEIGH[rule]:
            if (r + dr, x + dc) in cells_b:
                return True
    return False


def brute_force_persons(lengths, rule, sizes):
    """Größte Personenzahl: alle Teilmengen der Anfragen, alle Platzierungen, rekursiv mit Rücknahme."""
    best = 0
    items = list(sizes)

    def rec(i, placed, persons):
        nonlocal best
        best = max(best, persons)
        if i == len(items):
            return
        if persons + sum(items[i:]) <= best:
            return
        g = items[i]
        for r, n in enumerate(lengths):
            for s in range(n - g + 1):
                p = (r, s, g)
                if all(not _conflict(p, q, rule) for q in placed):
                    rec(i + 1, placed + [p], persons + g)
        rec(i + 1, placed, persons)

    rec(0, [], 0)
    return best


def _params_for(lengths, rule):
    """Params mit gleich langen Reihen (die Aufzählung nutzt gleich lange Säle)."""
    return Params(rows=len(lengths), cols=lengths[0], rule=rule)


@pytest.mark.parametrize("rule", C.RULES)
@pytest.mark.parametrize("rows,cols,sizes", [
    (2, 6, (1, 2, 2, 3)),
    (3, 6, (2, 2, 3, 1)),
    (2, 7, (3, 3, 1, 1, 2)),
    (3, 6, (1, 1, 1, 1, 1, 1)),
    (2, 6, (4, 2, 1)),
])
def test_offline_optimum_gleich_aufzaehlung(rule, rows, cols, sizes):
    p = Params(rows=rows, cols=cols, rule=rule)
    demand = [sizes.count(g) for g in range(1, C.GMAX + 1)]
    res = offline_optimum(p, demand, 20.0)
    assert res.status == 0
    assert res.persons == brute_force_persons(p.row_lengths, rule, sizes)


def test_offline_optimum_im_bogensaal_gleich_aufzaehlung():
    p = Params(rows=3, cols=8, hall="bogen")
    lengths = p.row_lengths
    assert len(set(lengths)) > 1
    sizes = (2, 3, 1, 2, 4)
    res = offline_optimum(p, [sizes.count(g) for g in range(1, C.GMAX + 1)], 20.0)
    assert res.persons == brute_force_persons(lengths, "ROW", sizes)


@pytest.mark.parametrize("n", range(1, 13))
@pytest.mark.parametrize("g", range(1, 5))
def test_reihenkapazitaet_gleich_aufzaehlung(n, g):
    best = 0
    for k in range(0, n // g + 2):
        # k Gruppen der Größe g passen, wenn k · g + (k − 1) ≤ n
        if k * g + max(k - 1, 0) <= n:
            best = max(best, k * g)
    assert X.row_capacity(n, g) == best


@pytest.mark.parametrize("n", range(1, 9))
def test_freie_wahl_rekursion_gleich_mittel_ueber_alle_reihenfolgen(n):
    total = 0
    for order in itertools.permutations(range(n)):
        taken = []
        for p in order:
            if all(abs(p - q) > 1 for q in taken):
                taken.append(p)
        total += len(taken)
    assert X.rsa_expected(n) == pytest.approx(total / math.factorial(n), abs=1e-12)


@pytest.mark.parametrize("n", [10, 16, 30])
def test_freie_wahl_rekursion_gleich_simulation(n):
    m, se = X.rsa_simulate_row(n, 20000, 777)
    assert abs(m - X.rsa_expected(n)) < 4 * se + 1e-9


def test_freie_wahl_grenzwert_der_reihe_ist_ein_minus_e_hoch_minus_zwei_halbe():
    assert X.rsa_expected(2000) / 2000 == pytest.approx((1 - math.exp(-2)) / 2, abs=1e-3)


def test_einzelne_kapazitaet_ist_jeder_zweite_platz():
    for n in range(1, 30):
        assert X.singles_capacity(n) == math.ceil(n / 2)


def naive_first_fit(lengths, rule, seq):
    """First-Fit mit reinen Schleifen: erste Reihe, links, die zulässig ist."""
    placed = []
    accepted = []
    for g in seq:
        done = False
        for r, n in enumerate(lengths):
            for s in range(n - g + 1):
                p = (r, s, g)
                if all(not _conflict(p, q, rule) for q in placed):
                    placed.append(p)
                    done = True
                    break
            if done:
                break
        accepted.append(done)
    return placed, accepted


@pytest.mark.parametrize("rule", C.RULES)
@pytest.mark.parametrize("seed", range(6))
def test_first_fit_gleich_naive_schleifen(rule, seed):
    p = Params(rows=5, cols=9, rule=rule, load=1.3)
    seq = sample_sequence(p, SplitMix64(seed))
    res = run_sequence(p, seq, "FF", 1)
    placed, accepted = naive_first_fit(p.row_lengths, rule, seq)
    assert sorted(res.placements) == sorted(placed)
    assert list(res.accepted) == accepted


@pytest.mark.parametrize("behaviour", C.BEHAVIOURS_ALL)
@pytest.mark.parametrize("rule", C.RULES)
def test_jede_vergabe_liefert_gueltige_belegungen(behaviour, rule):
    for seed in range(4):
        p = Params(rows=6, cols=10, rule=rule, load=1.4, dist="familie")
        seq = sample_sequence(p, SplitMix64(seed))
        res = run_sequence(p, seq, behaviour, seed + 1)
        assert H.check_placements(p.row_lengths, rule, res.placements)
        assert res.persons == sum(g for _r, _s, g in res.placements)


def test_bogensaal_vergaben_sind_gueltig():
    p = Params(rows=7, cols=12, hall="bogen", dist="paare", load=1.2)
    for b in C.BEHAVIOURS_ALL:
        seq = sample_sequence(p, SplitMix64(3))
        assert H.check_placements(p.row_lengths, "ROW", run_sequence(p, seq, b, 4).placements)


def test_online_nie_besser_als_offline():
    for rule in C.RULES:
        for seed in range(5):
            p = Params(rows=5, cols=8, rule=rule, load=1.2)
            seq = sample_sequence(p, SplitMix64(seed))
            off = offline_optimum(p, demand_of(seq), 20.0)
            assert off.status == 0
            for b in C.ASSIGNS:
                assert run_sequence(p, seq, b, seed + 1).persons <= off.persons


def test_pruefer_erkennt_verletzungen():
    assert H.check_placements((6,), "ROW", [(0, 0, 2), (0, 3, 2)])
    assert not H.check_placements((6,), "ROW", [(0, 0, 2), (0, 2, 2)])           # berühren sich
    assert not H.check_placements((6,), "ROW", [(0, 0, 3), (0, 2, 2)])           # überlappen
    assert not H.check_placements((6,), "ROW", [(0, 5, 2)])                      # ragt über die Reihe
    assert H.check_placements((4, 4), "ROW", [(0, 0, 2), (1, 0, 2)])
    assert not H.check_placements((4, 4), "MANH", [(0, 0, 2), (1, 0, 2)])        # vorn/hinten benachbart
    assert H.check_placements((4, 4), "MANH", [(0, 0, 2), (1, 2, 2)])            # nur diagonal berührt: bei MANH erlaubt
    assert H.check_placements((4, 4), "MANH", [(0, 0, 1), (1, 1, 1)])            # diagonal ist bei MANH erlaubt
    assert not H.check_placements((4, 4), "KING", [(0, 0, 1), (1, 1, 1)])        # diagonal ist bei KING gesperrt
