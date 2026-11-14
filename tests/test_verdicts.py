"""Verdikte (reine Funktionen in sab_evaluation.py) an handgesetzten Werten: Schwellen und jede Zahl im Text; dazu die erwartete Verdikt-Stufe je Preset (DEMO-PLAYBOOK 11a Punkt 7)."""

import pytest

import sab_constants as C
import sab_evaluation as ev
from sab_rules import RunResult
from sab_scenario import Params


def _stat(share, persons=90.0, rej=5.0, occ=0.7, se=0.004):
    return ev.Stat(persons, 1.0, share, se, rej, occ)


def _analysis(params=Params(), shares=None, proven=8, offline=100.0):
    base = {"FF": 0.93, "BF": 0.93, "FREI": 0.81, "MITTE": 0.89, "WEIT_E": 0.86}
    base.update(shares or {})
    stats = {k: _stat(v, persons=v * offline) for k, v in base.items()}
    ex = RunResult(10, (True,), ((0, 0, 2),), params.seats)
    return ev.Analysis(ev.Settings(params=params), 8, offline, proven, stats, ex, (2,))


def test_verdikt_vergabe_platzanweiser_ist_die_vergleichsgroesse():
    kind, text = ev.verdict_assign(_analysis())
    assert kind == "success" and "93,0 %" in text and "ist hier die Vergleichsgröße" in text and "mit dem Platzanweiser links" not in text
    kind, _ = ev.verdict_assign(_analysis(shares={"FF": 0.85, "BF": 0.85}))
    assert kind == "info"


def test_verdikt_vergabe_drei_stufen_mit_zahlen():
    p = Params(assign="FREI")
    kind, text = ev.verdict_assign(_analysis(p))                          # 93,0 gegen 81,0: 12 Punkte
    assert kind == "warning" and "81,0 %" in text and "12,0 Prozentpunkte zugunsten von „Platzanweiser links (First-Fit)“" in text and "Standardfehler 0,4" in text
    kind, text = ev.verdict_assign(_analysis(p, shares={"FREI": 0.915}))   # 1,5 Punkte
    assert kind == "info" and "1,5 Prozentpunkte zugunsten von „Platzanweiser links (First-Fit)“" in text
    kind, text = ev.verdict_assign(_analysis(p, shares={"FREI": 0.925}))   # 0,5 Punkte
    assert kind == "success"
    kind, text = ev.verdict_assign(_analysis(p, shares={"FREI": 0.95}))    # besser als der Platzanweiser
    assert kind == "success" and "2,0 Prozentpunkte zugunsten dieser Vergabe" in text


def test_verdikt_vergabe_nennt_unbewiesene_optima():
    _, text = ev.verdict_assign(_analysis(Params(assign="FREI"), proven=5))
    assert "nur in 5 von 8 Folgen bewiesen" in text


def test_verdikt_rangfolge_nennt_beste_und_schlechteste_vergabe():
    kind, text = ev.verdict_ranking(_analysis())
    assert kind == "info" and "„Platzanweiser links (First-Fit)“ vorn (93,0 %" in text and "hinten (81,0 %" in text
    assert "FF 93 %, BF 93 %, MITTE 89 %, WEIT_E 86 %, FREI 81 %" in text
    kind, _ = ev.verdict_ranking(_analysis(shares={k: 0.9 for k in ("FF", "BF", "FREI", "MITTE", "WEIT_E")}))
    assert kind == "success"


def test_verdikt_freie_wahl_nennt_reihe_und_saal():
    hall = {"capacity": 80, "free": 70.0, "free_se": 0.13, "ff": 80.0, "runs": 40}
    kind, text = ev.verdict_free(16, hall, "ROW")
    assert kind == "warning" and "in einer Reihe mit 16 Plätzen im Mittel" in text and "von 8 möglichen" in text and "Regel ROW sind es 70,0 von 80 (87,5 %" in text
    assert "ein Platzanweiser erreicht 100,0 %" in text
    kind, _ = ev.verdict_free(16, {**hall, "free": 76.0}, "ROW")
    assert kind == "info"


def test_verdikt_gruppen_hebt_oder_hebt_nicht():
    rows = [{"g": g, "persons": v, "share": v / 100} for g, v in zip(range(1, 7), (50, 60, 70, 72, 60, 48))]
    kind, text = ev.verdict_groups(rows, "ROW")
    assert kind == "success" and "Gruppen der Größe 4 schaffen 72" in text and "am wenigsten die Größe 6 mit 48" in text and "1 von 5 Gruppengrößen liegen unter den Einzelnen" in text and "heben hier die Kapazität." in text
    rows = [{"g": g, "persons": v, "share": v / 100} for g, v in zip(range(1, 7), (50, 45, 40, 44, 30, 20))]
    kind, text = ev.verdict_groups(rows, "KING")
    assert kind == "info" and "nicht" in text and "5 von 5" in text


def test_verdikt_vergabe_je_preset():
    erwartet = {"Platzanweiser": "success", "Gäste wählen frei": "warning", "Gäste suchen Abstand": "warning", "Fast voller Saal mit Familien": "warning", "Nur Einzelne": "warning", "Saal mit Bogen": "warning"}
    assert set(erwartet) == set(C.PRESETS)
    for name, kind in erwartet.items():
        a = ev.analyse(ev.Settings(params=Params(**C.PRESETS[name])))
        assert ev.verdict_assign(a)[0] == kind, (name, ev.verdict_assign(a)[1])


def test_analyse_hat_alle_vergaben_und_stimmt_im_zweiten_aufruf_ueberein():
    a = ev.analyse(ev.Settings(params=Params(rows=4, cols=8), seed=1))
    assert set(a.stats) == set(C.ASSIGNS) and a.offline_proven == a.n == C.LIVE_SEQS


def test_luecke_zum_optimum_in_prozent():
    cell = {"behaviours": {"FF": {"share": 0.925}}}
    assert ev.gap_pct(cell, "FF") == pytest.approx(7.5)


def test_nicht_bewiesenes_optimum_gibt_nie_mehr_als_100_prozent(monkeypatch):
    """Bei Erreichen der Zeitgrenze ist die gefundene Lösung nur eine untere Schranke: der Bezugswert ist dann mindestens die beste Online-Belegung, der Anteil höchstens 100 %."""
    from sab_offline import OfflineResult
    monkeypatch.setattr(ev, "offline_optimum", lambda p, d, tl=None: OfflineResult(8, 1, 6.0, 100))
    a = ev.analyse(ev.Settings(params=Params(rows=4, cols=8), seed=2))
    assert a.offline_proven == 0 and all(s.share <= 1.0 + 1e-12 for s in a.stats.values())
    kind, text = ev.verdict_assign(a)
    assert "nur in 0 von 8 Folgen bewiesen" in text and "untere Schranke" in text          # auch beim Platzanweiser links
    kind, text = ev.verdict_assign(ev.analyse(ev.Settings(params=Params(rows=4, cols=8, assign="FREI"), seed=2)))
    assert "untere Schranke" in text


def test_verdikt_vergabe_gleichstand_und_best_fit_wortlaut():
    kind, text = ev.verdict_assign(_analysis(Params(assign="BF")))
    assert "Kein Unterschied zum Platzanweiser links" in text
    kind, text = ev.verdict_assign(_analysis(Params(assign="BF"), shares={"BF": 0.90}))
    assert "zugunsten von „Platzanweiser links (First-Fit)“" in text
