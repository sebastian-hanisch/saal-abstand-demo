"""Offline-Optimum: die größte Personenzahl, wenn jemand die ganze Anfragefolge kennt und frei auswählt, welche Gruppen er setzt (ganzzahliges Programm, HiGHS über scipy.optimize.milp).

Modell: eine 0/1-Variable je waagerechter Platzierung (Reihe, Start, Größe); je Größe höchstens so viele Platzierungen wie Anfragen.
Seitlich (alle Regeln): je Zelle höchstens eine virtuelle Strecke [s, s + g + 1) (Intervallgraph, exakt; die Strecke endet an der Reihenwand im Gedachten, sodass dort keine Lücke nötig ist).
Vorn/hinten (MANH, KING) und diagonal (KING): je Paar benachbarter Zellen verschiedener Reihen `o_c + o_c' <= 1` (Zellen verschiedener Reihen gehören nie zur selben Gruppe)."""

import time
from dataclasses import dataclass

import numpy as np
import scipy.sparse as sp
from scipy.optimize import Bounds, LinearConstraint, milp

import sab_constants as C
from sab_scenario import Params


@dataclass(frozen=True)
class OfflineResult:
    persons: int | None        # beste gefundene Personenzahl (bei status 0 das Optimum)
    status: int                # 0 bewiesen optimal, 1 Zeitgrenze erreicht (Lösung bekannt, nicht bewiesen), 2 sonst
    seconds: float
    variables: int


def offline_optimum(params: Params, demand, tlimit: float = C.OFFLINE_TLIMIT) -> OfflineResult:
    lengths = params.row_lengths
    R, W = len(lengths), max(lengths)
    pl = [(r, s, g) for g in range(1, C.GMAX + 1) if demand[g - 1] > 0 for r in range(R) for s in range(lengths[r] - g + 1)]
    n = len(pl)
    if n == 0:
        return OfflineResult(0, 0, 0.0, 0)
    rows, cols, ub = [], [], []
    k = 0

    def add(idx, bound=1.0):
        nonlocal k
        for j in idx:
            rows.append(k)
            cols.append(j)
        ub.append(bound)
        k += 1

    for g in range(1, C.GMAX + 1):
        idx = [j for j, p in enumerate(pl) if p[2] == g]
        if idx:
            add(idx, float(demand[g - 1]))
    for r in range(R):
        for c in range(lengths[r] + 1):
            idx = [j for j, p in enumerate(pl) if p[0] == r and p[1] <= c < p[1] + p[2] + 1]
            if len(idx) > 1:
                add(idx)
    cover = {}
    for j, (r, s, g) in enumerate(pl):
        for x in range(s, s + g):
            cover.setdefault((r, x), []).append(j)
    pairs = []
    if params.rule in ("MANH", "KING"):
        pairs += [((r, x), (r + 1, x)) for r in range(R - 1) for x in range(W)]
    if params.rule == "KING":
        pairs += [((r, x), (r + 1, x + 1)) for r in range(R - 1) for x in range(W - 1)]
        pairs += [((r, x), (r + 1, x - 1)) for r in range(R - 1) for x in range(1, W)]
    for a, b in pairs:
        idx = cover.get(a, []) + cover.get(b, [])
        if idx:
            add(idx)
    A = sp.csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(k, n))
    c_obj = -np.array([p[2] for p in pl], dtype=float)
    t = time.time()
    res = milp(c_obj, constraints=LinearConstraint(A, -np.inf, np.array(ub)), integrality=np.ones(n), bounds=Bounds(0, 1), options={"mip_rel_gap": 0.0, "time_limit": tlimit, "disp": False})
    seconds = time.time() - t
    if res.x is None:
        return OfflineResult(None, 2, seconds, n)
    return OfflineResult(int(round(-res.fun)), 0 if res.status == 0 else 1, seconds, n)
