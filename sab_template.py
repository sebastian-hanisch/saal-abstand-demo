"""Feste Sperrmatrix (nur Regel ROW): der Betreiber legt vorab fest, welche Reihe in welche Gruppenplätze zerfällt, und weist jede Gruppe dem kleinsten freien passenden Platz zu.

Die Vorlage folgt den Anteilen der Gruppenmischung (nicht stochastisch optimiert): maximiere t mit Platzzahl der Größe s ≥ t · Anteil_s, danach bei festem t die Personen (zwei ganzzahlige Programme über Muster je Reihe).
Eine optimierte Vorlage (Blom, Pendavingh, Spieksma 2020) kennt die Verteilung und wählt sie besser; dieser Vergleich ist bewusst nur die einfache Anteilsvorlage."""

from functools import lru_cache

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

import sab_constants as C
from sab_scenario import Params


@lru_cache(maxsize=None)
def patterns(L: int, d: int = 1):
    """Alle Multimengen von Gruppengrößen 1 … GMAX (Tupel der Anzahlen) mit Σ (g + d) ≤ L + d."""
    res = []

    def rec(g, left, cur):
        if g > C.GMAX:
            res.append(tuple(cur))
            return
        k = 0
        while k * (g + d) <= left:
            rec(g + 1, left - k * (g + d), cur + [k])
            k += 1

    rec(1, L + d, [])
    return res


def persons(pat) -> int:
    return sum((i + 1) * c for i, c in enumerate(pat))


def template_for(params: Params):
    """Slotgrößen je Reihe (Liste von Listen) nach den Anteilen der Mischung."""
    assert params.rule == "ROW", "die feste Sperrmatrix gibt es nur bei der Regel ROW"
    lengths = params.row_lengths
    lens = sorted(set(lengths))
    cnt = {L: lengths.count(L) for L in lens}
    cols = [(L, p) for L in lens for p in patterns(L)]
    n = len(cols)
    dist = C.DISTRIBUTIONS[params.dist]
    w = np.array([dist.get(s, 0.0) for s in range(1, C.GMAX + 1)], float)
    w /= w.sum()
    A, lo, hi = [], [], []
    for L in lens:
        A.append([1.0 if cl == L else 0.0 for cl, _ in cols] + [0.0])
        lo.append(cnt[L])
        hi.append(cnt[L])
    for s in range(C.GMAX):
        if w[s] > 0:
            A.append([float(p[s]) for _, p in cols] + [-w[s]])
            lo.append(0.0)
            hi.append(np.inf)
    res = milp(np.array([0.0] * n + [-1.0]), constraints=LinearConstraint(np.array(A), lo, hi), integrality=np.array([1] * n + [0]), bounds=Bounds(0, np.inf))
    t = -res.fun
    A2 = [r[:] for r in A] + [[0.0] * n + [1.0]]
    lo2 = list(lo) + [t * (1 - 1e-6)]          # Toleranz: HiGHS meldet t um etwa 1e-6 zu hoch, bei 1e-9 wäre das zweite Programm unlösbar
    hi2 = list(hi) + [np.inf]
    res2 = milp(np.array([-persons(p) for _, p in cols] + [0.0]), constraints=LinearConstraint(np.array(A2), lo2, hi2), integrality=np.array([1] * n + [0]), bounds=Bounds(0, np.inf))
    by_len = {}
    for i, x in enumerate(res2.x[:n]):
        if x > 0.5:
            L, p = cols[i]
            for _ in range(int(round(x))):
                slots = []
                for size, c in enumerate(p, start=1):
                    slots += [size] * c
                by_len.setdefault(L, []).append(slots)
    return [by_len[L].pop() for L in lengths]


def run_template(params: Params, seq, template):
    """Weist jede Gruppe dem kleinsten freien Slot zu, der passt; Rückgabe: gesetzte Personen."""
    slots = [[r, i, s, True] for r, sl in enumerate(template) for i, s in enumerate(sl)]
    total = 0
    for g in seq:
        best = None
        for sl in slots:
            if sl[3] and sl[2] >= g and (best is None or sl[2] < best[2]):
                best = sl
        if best is not None:
            best[3] = False
            total += g
    return total
