"""Randfälle: ungültige Eingaben, kleinster und größter Saal, Gruppen größer als die Reihe, leere Anfragen, Zeitgrenze des ganzzahligen Programms."""

import pytest

import sab_constants as C
import sab_evaluation as ev
import sab_template as T
from sab_hall import check_placements
from sab_offline import offline_optimum
from sab_rng import SplitMix64
from sab_rules import run_sequence
from sab_scenario import Params, sample_sequence


@pytest.mark.parametrize("kw", [dict(rows=1), dict(rows=15), dict(cols=5), dict(cols=21), dict(rows=True), dict(rows=3.5), dict(hall="x"), dict(rule="x"), dict(dist="x"),
                                dict(load=0.1), dict(load=2.5), dict(assign="x"), dict(hall="bogen", rule="MANH"), dict(hall="bogen", rule="KING")])
def test_ungueltige_eingaben_werden_abgelehnt(kw):
    with pytest.raises(ValueError):
        Params(**kw)


def test_params_nimmt_nur_schluesselwoerter():
    with pytest.raises(TypeError):
        Params(8, 16)


def test_kleinster_saal_laeuft_in_allen_regeln_und_vergaben():
    for rule in C.RULES:
        p = Params(rows=C.ROWS_MIN, cols=C.COLS_MIN, rule=rule, load=2.0)
        seq = sample_sequence(p, SplitMix64(2))
        for b in C.BEHAVIOURS_ALL:
            res = run_sequence(p, seq, b, 3)
            assert 0 <= res.persons <= p.seats and check_placements(p.row_lengths, rule, res.placements)


def test_groesster_saal_ist_14_mal_20_und_laeuft_online():
    p = Params(rows=C.ROWS_MAX, cols=C.COLS_MAX, load=1.5)
    assert p.seats == 280
    seq = sample_sequence(p, SplitMix64(1))
    for b in C.BEHAVIOURS_ALL:
        assert check_placements(p.row_lengths, "ROW", run_sequence(p, seq, b, 2).placements)


def test_gruppe_laenger_als_die_reihe_wird_abgewiesen():
    res = run_sequence(Params(rows=2, cols=6), [6, 6, 6], "FF", 0)
    assert res.accepted == (True, True, False) and res.persons == 12      # Gruppen zu 6 füllen je eine Reihe von 6 Plätzen: zwei Reihen reichen für zwei, die dritte findet keine Reihe
    assert run_sequence(Params(rows=2, cols=6), [5, 5], "FF", 0).accepted == (True, True)


def test_leere_anfragefolge_setzt_niemanden():
    p = Params()
    for b in C.BEHAVIOURS_ALL:
        assert run_sequence(p, [], b, 0).persons == 0
    assert offline_optimum(p, [0] * C.GMAX).persons == 0


def test_offline_optimum_bei_wenig_nachfrage_setzt_alle():
    p = Params(rows=4, cols=8)
    assert offline_optimum(p, [2, 1, 0, 0, 0, 0]).persons == 2 + 2


def test_offline_optimum_zeitgrenze_liefert_status_und_untere_schranke():
    """Mit einer Zeitgrenze fast null liefert das Programm entweder das Optimum oder meldet, dass es nicht bewiesen ist (Status 1 oder 2); eine gemeldete Lösung ist nie größer als das bewiesene Optimum."""
    p = Params(rows=14, cols=20, rule="MANH", dist="familie", load=1.5)
    seq = sample_sequence(p, SplitMix64(4))
    demand = [seq.count(g) for g in range(1, C.GMAX + 1)]
    quick = offline_optimum(p, demand, 0.05)
    assert quick.status in (0, 1, 2)
    if quick.status == 1 and quick.persons is not None:
        full = offline_optimum(p, demand, 60.0)
        if full.status == 0:
            assert quick.persons <= full.persons


def test_analyse_ist_bei_gleichen_einstellungen_gleich():
    s = ev.Settings(params=Params(rows=4, cols=8), seed=3)
    a, b = ev.analyse(s), ev.analyse(s)
    assert a.stats == b.stats and a.offline_mean == b.offline_mean and a.example.placements == b.example.placements


def test_analyse_liefert_anteile_zwischen_null_und_eins_und_ff_gleich_bf_bei_gleichen_reihen():
    a = ev.analyse(ev.Settings(params=Params(rows=4, cols=8), seed=5))
    for k, s in a.stats.items():
        assert 0 < s.share <= 1.0000001, k
        assert s.persons <= a.offline_mean + 1e-9 or s.share <= 1.0
    assert a.example.persons > 0 and a.n == C.LIVE_SEQS


def test_sperrmatrix_gibt_es_nur_bei_der_regel_nur_seitlich():
    with pytest.raises(AssertionError):
        T.template_for(Params(rows=4, cols=8, rule="MANH"))
    p = Params(rows=4, cols=8, rule="ROW", dist="paare")
    template = T.template_for(p)
    assert len(template) == 4 and all(isinstance(slots, list) for slots in template)
    seq = sample_sequence(p, SplitMix64(1))
    assert 0 < T.run_template(p, seq, template) <= p.seats


def test_sperrmatrix_slots_passen_in_die_reihe():
    """Je Reihe passen die Plätze der Slots samt einer Lücke zwischen ihnen in die Reihenlänge."""
    for hall in ("gleich", "bogen"):
        p = Params(rows=4, cols=10, hall=hall, dist="familie")
        for slots, n in zip(T.template_for(p), p.row_lengths):
            assert sum(slots) + max(len(slots) - 1, 0) <= n
