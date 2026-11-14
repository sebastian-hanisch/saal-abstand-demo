"""AppTest der Demo selbst: Standardsaal, Presets, Permalink, Kernfragen, Exakt-Reiter, Regeln, Saal mit Bogen, Grenzfälle."""

import os

import pytest
from streamlit.testing.v1 import AppTest

import sab_constants as C

APP_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")
TIMEOUT = int(os.environ.get("APPTEST_TIMEOUT", "300"))


def _app() -> AppTest:
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=TIMEOUT)
    assert not at.exception, [str(e) for e in at.exception]
    return at


def _texts(at):
    return " ".join(x.value for x in list(at.success) + list(at.info) + list(at.warning) + list(at.error))


def _headings(at):
    return " ".join(m.value for m in at.markdown if m.value.startswith("## "))


def _metric(at, label):
    return next(m.value for m in at.metric if m.label == label)


def _num(text):
    return float(text.replace(" %", "").replace(",", "."))


def test_standardsaal_zeigt_fuenf_kennzahlen_und_alle_abschnitte():
    at = _app()
    assert [m.label for m in at.metric[:5]] == ["Gesetzte Personen", "Besetzte Plätze", "Anteil am Offline-Optimum", "Offline-Optimum", "Abgewiesene Gruppen"]
    h = _headings(at)
    for wort in ("Ergebnis", "Kernfrage 1", "Kernfrage 2", "Kernfrage 3", "Experimente"):
        assert wort in h
    assert 0 < _num(_metric(at, "Anteil am Offline-Optimum")) <= 100 and _num(_metric(at, "Offline-Optimum")) > _num(_metric(at, "Gesetzte Personen")) * 0.99
    assert "Vergleichsgröße" in _texts(at) and "Reihenfolge" in _texts(at)


@pytest.mark.parametrize("name", list(C.PRESETS))
def test_jedes_preset_laeuft_und_zeigt_die_verdikte(name):
    at = _app()
    at.sidebar.button(key=f"preset_{name}").click().run(timeout=TIMEOUT)
    assert not at.exception, [str(e) for e in at.exception]
    text = _texts(at)
    assert "Offline-Optimums" in text and "Reihenfolge" in text and "Gäste, die frei wählen" in text and "passen" in text


def test_preset_gaeste_waehlen_frei_senkt_den_anteil_gegen_den_platzanweiser():
    at = _app()
    standard = _num(_metric(at, "Anteil am Offline-Optimum"))
    at.sidebar.button(key="preset_Gäste wählen frei").click().run(timeout=TIMEOUT)
    assert _num(_metric(at, "Anteil am Offline-Optimum")) < standard - 5.0


def test_nur_einzelne_der_platzanweiser_erreicht_das_optimum():
    at = _app()
    at.sidebar.selectbox(key="dist_select").set_value("einzel").run(timeout=TIMEOUT)
    assert not at.exception and _num(_metric(at, "Anteil am Offline-Optimum")) == pytest.approx(100.0, abs=0.05)


@pytest.mark.parametrize("rule", C.RULES)
def test_jede_regel_laeuft_und_nennt_sich_in_kernfrage_2_und_3(rule):
    at = _app()
    at.sidebar.selectbox(key="rule_select").set_value(rule).run(timeout=TIMEOUT)
    assert not at.exception and f"Regel {rule}" in _texts(at)


def test_saal_mit_bogen_nur_bei_der_regel_nur_seitlich():
    at = _app()
    at.sidebar.selectbox(key="hall_select").set_value("bogen").run(timeout=TIMEOUT)
    assert not at.exception
    at.sidebar.selectbox(key="rule_select").set_value("MANH").run(timeout=TIMEOUT)
    assert not at.exception and any("Saal mit Bogen gibt es nur bei der Regel" in c.value for c in at.sidebar.caption)


def test_exakt_reiter_rechnet_das_optimum_der_ersten_folge():
    at = _app()
    at.button(key="offline_run").click().run(timeout=TIMEOUT)
    assert not at.exception
    assert _num(next(m.value for m in at.metric if m.label == "Offline-Optimum der ersten Folge")) > 0
    at.sidebar.slider(key="rows_slider").set_value(5).run(timeout=TIMEOUT)
    assert not at.exception and any("erneut" in c.value for c in at.caption)


def test_permalink_uebernimmt_werte_und_begrenzt_sie():
    at = AppTest.from_file(APP_PATH)
    at.query_params["rows"] = "6"
    at.query_params["cols"] = "99"
    at.query_params["dist"] = "familie"
    at.query_params["rule"] = "unsinn"
    at.query_params["load"] = "1.2"
    at.run(timeout=TIMEOUT)
    assert not at.exception
    assert at.sidebar.slider(key="rows_slider").value == 6 and at.sidebar.slider(key="cols_slider").value == C.COLS_MAX
    assert at.sidebar.selectbox(key="dist_select").value == "familie" and at.sidebar.selectbox(key="rule_select").value == "ROW"
    assert at.sidebar.slider(key="load_slider").value == pytest.approx(1.2)


def test_die_sechs_experimente_stehen_als_tabellen_da():
    at = _app()
    subs = [s.value for s in at.subheader if s.value.startswith("🔬")]
    assert len(subs) == 6
    assert len(at.dataframe) == 1 + 6      # Tabelle der Kernfrage 1 und die Tabellen der Experimente 1 bis 6
