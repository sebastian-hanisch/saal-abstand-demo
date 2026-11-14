"""Einheitentests an Mini-Instanzen mit Handrechnung (DEMO-PLAYBOOK §1b): Saal, Abstandsregeln, Vergabeweisen, Anfragefolge, Zufallsgenerator."""

import pytest

import sab_constants as C
from sab_hall import Hall, check_placements
from sab_rng import SplitMix64
from sab_rules import run_sequence
from sab_scenario import Params, demand_of, sample_sequence


# ---------------------------------------------------------------- Saal und Regeln (Handrechnung)
def test_hall_sperrt_nachbarn_je_regel():
    h = Hall((5, 5, 5), "ROW")
    h.place(1, 2, 1)
    assert h.blocked[1, 1] and h.blocked[1, 3] and not h.blocked[0, 2] and not h.blocked[2, 2]      # seitlich gesperrt, vorn/hinten frei
    m = Hall((5, 5, 5), "MANH")
    m.place(1, 2, 1)
    assert m.blocked[0, 2] and m.blocked[2, 2] and not m.blocked[0, 1]                               # vorn/hinten gesperrt, diagonal frei
    k = Hall((5, 5, 5), "KING")
    k.place(1, 2, 1)
    assert k.blocked[0, 1] and k.blocked[2, 3]                                                       # auch diagonal gesperrt


def test_feasible_zaehlt_die_zulaessigen_starts():
    h = Hall((7,), "ROW")
    assert h.feasible(3).sum() == 5                       # Starts 0 … 4
    h.place(0, 0, 2)                                      # sperrt Platz 2
    assert [bool(x) for x in h.feasible(2)[0]] == [False, False, False, True, True, True]
    assert h.feasible(8).size == 0


@pytest.mark.parametrize("rule,erwartet", [("ROW", 6), ("MANH", 6), ("KING", 3)])
def test_first_fit_handrechnung_zwei_reihen_zu_sechs(rule, erwartet):
    """Zwei Reihen mit 6 Plätzen, Anfragen 3, 3. Die erste Gruppe sitzt auf den Plätzen 0 bis 2 der Reihe 1.
    ROW: Reihe 2 ist frei, die zweite Gruppe sitzt dort (6 Personen). MANH: vorn/hinten sind die Plätze 0 bis 2 der Reihe 2 gesperrt, die Gruppe sitzt auf 3 bis 5 (diagonal erlaubt, 6 Personen).
    KING: auch der Platz 3 der Reihe 2 ist gesperrt, es bleiben zwei Plätze: die zweite Gruppe wird abgewiesen (3 Personen)."""
    res = run_sequence(Params(rows=2, cols=6, rule=rule), [3, 3], "FF", 0)
    assert res.persons == erwartet
    assert res.placements[0] == (0, 0, 3)
    if rule == "MANH":
        assert res.placements[1] == (1, 3, 3)
    assert check_placements((6, 6), rule, res.placements)


def test_first_fit_einzelne_in_einer_reihe_jeder_zweite_platz():
    p = Params(rows=2, cols=7)
    res = run_sequence(p, [1] * 20, "FF", 0)
    assert res.persons == 8 and sorted(res.placements)[:4] == [(0, 0, 1), (0, 2, 1), (0, 4, 1), (0, 6, 1)]


def test_first_fit_gruppen_in_einer_reihe_handrechnung():
    """Reihe mit 7 Plätzen, ROW: 2, 2, dann 3 (passt nicht mehr, ein Platz bleibt); die 3 geht in Reihe 2."""
    p = Params(rows=2, cols=7)
    res = run_sequence(p, [2, 2, 3], "FF", 0)
    assert res.placements == ((0, 0, 2), (0, 3, 2), (1, 0, 3))
    assert res.accepted == (True, True, True) and res.persons == 7


def test_mitte_nimmt_mittlere_reihe_und_mitte():
    p = Params(rows=3, cols=7)
    res = run_sequence(p, [1], "MITTE", 0)
    assert res.placements == ((1, 3, 1),)


def test_best_fit_nimmt_die_engste_luecke():
    """Reihe 1 hat nach einer Gruppe einen Rest von 2 freien Plätzen, Reihe 2 ist leer (7): BF setzt eine 2er-Gruppe in den Rest, FF ebenso (erste Reihe); eine 1 danach in den Rest der engeren Lücke."""
    p = Params(rows=2, cols=7)
    res = run_sequence(p, [4, 1], "BF", 0)
    assert res.placements[0] == (0, 0, 4)
    assert res.placements[1] == (0, 5, 1)


def test_weit_e_geht_weit_weg_von_besetzten_plaetzen():
    p = Params(rows=2, cols=8)
    res = run_sequence(p, [1, 1], "WEIT_E", 0)
    (r0, s0, _), (r1, s1, _) = res.placements
    dist = ((r0 - r1) ** 2 + (s0 - s1) ** 2) ** 0.5
    assert dist >= 7.0           # die zweite Einzelperson sitzt in der entferntesten Ecke


def test_freie_wahl_ist_bei_gleichem_seed_gleich_und_bei_anderem_seed_anders():
    p = Params(rows=6, cols=12, load=1.2)
    seq = sample_sequence(p, SplitMix64(1))
    a, b, c = (run_sequence(p, seq, "FREI", s).placements for s in (5, 5, 6))
    assert a == b and a != c


# ---------------------------------------------------------------- Anfragefolge
def test_folge_erreicht_die_last_und_endet_mit_der_letzten_gruppe():
    for dist in C.DISTRIBUTIONS:
        for load in (0.5, 1.0, 1.5):
            p = Params(rows=8, cols=16, dist=dist, load=load)
            seq = sample_sequence(p, SplitMix64(11))
            target = int(load * p.seats)
            assert sum(seq) >= target and sum(seq[:-1]) < target
            assert set(seq) <= set(C.DISTRIBUTIONS[dist])


def test_folge_ist_bei_gleichem_seed_gleich():
    p = Params()
    assert sample_sequence(p, SplitMix64(9)) == sample_sequence(p, SplitMix64(9)) != sample_sequence(p, SplitMix64(10))


def test_mittlere_gruppengroesse_stimmt_mit_der_mischung_ueberein():
    for dist, probs in C.DISTRIBUTIONS.items():
        p = Params(rows=14, cols=20, dist=dist, load=2.0)
        n = total = 0
        for k in range(40):
            seq = sample_sequence(p, SplitMix64(k))
            n += len(seq)
            total += sum(seq)
        assert total / n == pytest.approx(sum(g * q for g, q in probs.items()), abs=0.08), dist


def test_nachfrage_zaehlt_je_groesse():
    assert demand_of([1, 1, 3, 6]) == [2, 0, 1, 0, 0, 1]


# ---------------------------------------------------------------- Saalform
def test_bogen_reihen_wachsen_nach_hinten():
    p = Params(rows=8, cols=16, hall="bogen")
    lengths = p.row_lengths
    assert list(lengths) == sorted(lengths) and lengths[0] == 10 and lengths[-1] == 22
    assert max(Params(rows=14, cols=20, hall="bogen").row_lengths) <= C.BOGEN_MAX_LEN
    assert Params(rows=2, cols=6, hall="bogen").row_lengths == (6, 8)
    assert Params(rows=3, cols=9).seats == 27


# ---------------------------------------------------------------- Zufallsgenerator
def test_splitmix64_ist_reproduzierbar_und_gleichverteilt():
    a, b = SplitMix64(42), SplitMix64(42)
    assert [a.below(100) for _ in range(20)] == [b.below(100) for _ in range(20)]
    rng = SplitMix64(7)
    counts = [0] * 5
    for _ in range(10000):
        counts[rng.below(5)] += 1
    assert all(abs(c - 2000) < 200 for c in counts)
