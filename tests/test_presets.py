"""Presets: Vollständigkeit, gültige Werte, Standard-Preset = Standardeinstellungen; Permalink-Spezifikation."""

import dataclasses

import sab_constants as C
import sab_presets as P
from sab_scenario import Params


def test_jedes_preset_hat_hilfetext_und_nur_bekannte_felder():
    assert set(C.PRESETS) == set(C.PRESET_HELP)
    felder = {f.name for f in dataclasses.fields(Params)}
    for name, preset in C.PRESETS.items():
        assert set(preset) <= felder, name
        assert C.PRESET_HELP[name]
        Params(**preset)            # jedes Preset ist gültig


def test_das_erste_preset_ist_der_standard():
    assert Params(**C.PRESETS[next(iter(C.PRESETS))]) == Params()


def test_jeder_regler_hat_eine_url_und_ein_params_feld():
    urls = [spec.url_param for spec in P.SETTING_SPECS.values()]
    assert len(urls) == len(set(urls))
    felder = {f.name for f in dataclasses.fields(Params)} | {"seed"}
    assert {spec.param for spec in P.SETTING_SPECS.values()} == felder


def test_standardwerte_der_regler_sind_die_der_params():
    d = Params()
    for key, spec in P.SETTING_SPECS.items():
        if spec.param != "seed":
            assert spec.default == getattr(d, spec.param), key


def test_auswahlfelder_nennen_alle_gueltigen_werte():
    spec = P.SETTING_SPECS
    assert spec["rule_select"].choices == C.RULES and spec["hall_select"].choices == C.HALLS
    assert spec["assign_select"].choices == C.ASSIGNS and set(spec["dist_select"].choices) == set(C.DISTRIBUTIONS)
    assert all(k in C.RULE_LABELS for k in C.RULES) and all(k in C.ASSIGN_LABELS for k in C.ASSIGNS) and all(k in C.DIST_LABELS for k in C.DISTRIBUTIONS)


def test_verteilungsnamen_nennen_mittlere_gruppengroesse():
    """Die Anzeigenamen nennen die mittlere Gruppengröße (kaufmännisch gerundet, deutsches Komma)."""
    from decimal import ROUND_HALF_UP, Decimal
    for key, probs in C.DISTRIBUTIONS.items():
        assert abs(sum(probs.values()) - 1.0) < 1e-12, key
        mean = sum(g * q for g, q in probs.items())
        digits = "0.01" if key == "paare" else "0.1"            # Ø 2,15 steht mit zwei Stellen, weil 2,2 den Wert verfälscht
        text = str(Decimal(str(round(mean, 10))).quantize(Decimal(digits), rounding=ROUND_HALF_UP)).replace(".", ",")
        if text.endswith(",0"):
            text = text[:-2]
        if text.endswith(",00"):
            text = text[:-3]
        assert f"Ø {text}" in C.DIST_LABELS[key], (key, text, C.DIST_LABELS[key])


def test_preset_familien_hilfetext_nennt_die_mittlere_gruppengroesse_der_familienmischung():
    mean = sum(g * q for g, q in C.DISTRIBUTIONS["familie"].items())
    assert round(mean, 1) == 3.2 and "Ø 3,2" in C.PRESET_HELP["Fast voller Saal mit Familien"]
    assert C.PRESETS["Fast voller Saal mit Familien"]["load"] == 1.2 and "20 % mehr Anfragen" in C.PRESET_HELP["Fast voller Saal mit Familien"]
