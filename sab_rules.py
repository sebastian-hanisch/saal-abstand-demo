"""Vergabeweisen: wer wählt den Platz einer Gruppe, und nach welcher Regel.

Alle Weisen sehen dieselbe Anfragefolge; jede Gruppe wird sofort und unwiderruflich gesetzt oder abgewiesen.
* FF     Platzanweiser: erste zulässige Reihe, links (First-Fit).
* BF     Platzanweiser: die engste freie Lücke, in die die Gruppe passt (Best-Fit; Lücke = zusammenhängende, nicht gesperrte Plätze einer Reihe), bei Gleichstand erste Reihe, links.
* FREI   Gäste wählen frei: gleichverteilt unter ALLEN zulässigen Plätzen (Random Sequential Adsorption mit Gruppen).
* MITTE  Gäste wählen die Mitte: der zulässige Platz mit dem kleinsten Abstand zur Mittelreihe, dann zur Reihenmitte.
* WEIT_E Gäste suchen Abstand: der Platz, dessen nächster besetzter Platz (alle Reihen, euklidischer Abstand mit Reihen- und Platzabstand 1) am weitesten entfernt ist.
* WEIT_R wie WEIT_E, aber nur Plätze derselben Reihe zählen (die Wand zählt nicht). WEIT_W: wie WEIT_R, die Wand zählt wie ein besetzter Platz.
Bei Gleichstand gilt überall die erste Reihe, links."""

from dataclasses import dataclass

import numpy as np

from sab_hall import Hall
from sab_rng import SplitMix64
from sab_scenario import Params

BIG = 10 ** 6


@dataclass(frozen=True)
class RunResult:
    persons: int            # gesetzte Personen
    accepted: tuple         # je Anfrage: gesetzt?
    placements: tuple       # (Zeile, Start, Größe) der gesetzten Gruppen
    seats: int              # Plätze des Saals


class Chooser:
    """Hält den Zustand einer Vergabe (Saal und Abstandskarten) und setzt Gruppe für Gruppe."""

    def __init__(self, params: Params, behaviour: str, rng: SplitMix64):
        self.p = params
        self.behaviour = behaviour
        self.rng = rng
        self.hall = Hall(params.row_lengths, params.rule)
        R, W = self.hall.R, self.hall.C
        self.rr = np.arange(R)[:, None]
        self.xx = np.arange(W)[None, :]
        self.dmap = np.full((R, W), float(BIG))     # kleinster euklidischer Abstand zu einem besetzten Platz
        self.rowd = np.full((R, W), float(BIG))     # kleinster seitlicher Abstand zu einem besetzten Platz derselben Reihe
        if behaviour == "WEIT_W":
            for r, n in enumerate(params.row_lengths):
                for x in range(n):
                    self.rowd[r, x] = min(x + 1, n - x)

    # ----------------------------------------------------------------- Wahl
    def _window_min(self, arr, g, width):
        return np.minimum.reduce([arr[:, k:width + k] for k in range(g)])

    def _gap_lengths(self):
        """Länge der zusammenhängenden nicht gesperrten Plätze je Zelle (0 für gesperrte)."""
        free = ~self.hall.blocked
        out = np.zeros(free.shape, dtype=int)
        for r in range(free.shape[0]):
            x = 0
            while x < free.shape[1]:
                if free[r, x]:
                    y = x
                    while y < free.shape[1] and free[r, y]:
                        y += 1
                    out[r, x:y] = y - x
                    x = y
                else:
                    x += 1
        return out

    def choose(self, g: int):
        """Platz (Zeile, Start) für eine Gruppe der Größe g oder None."""
        F = self.hall.feasible(g)
        if F.size == 0 or not F.any():
            return None
        width = F.shape[1]
        flat = F.ravel()
        b = self.behaviour
        if b == "FF":
            idx = int(np.argmax(flat))
        elif b == "FREI":
            cand = np.flatnonzero(flat)
            idx = int(cand[self.rng.below(len(cand))])
        elif b == "BF":
            gaps = self._gap_lengths()
            leftover = np.full(F.shape, BIG)
            for r in range(F.shape[0]):
                for s in range(width):
                    if F[r, s]:
                        leftover[r, s] = gaps[r, s] - g
            idx = int(np.argmin(leftover.ravel()))
        elif b == "MITTE":
            rows = np.abs(np.arange(F.shape[0]) - (self.hall.R - 1) / 2.0)[:, None] * 100.0
            centre = (np.array(self.hall.lengths, dtype=float) - 1) / 2.0
            mid = np.arange(width)[None, :] + (g - 1) / 2.0
            key = np.where(F, rows + np.abs(mid - centre[:, None]), np.inf)
            idx = int(np.argmin(key.ravel()))
        else:       # WEIT_E, WEIT_R, WEIT_W: größter Mindestabstand
            arr = self.dmap if b == "WEIT_E" else self.rowd
            score = np.where(F, self._window_min(arr, g, width), -1.0)
            idx = int(np.argmax(score.ravel()))
        return idx // width, idx % width

    def place(self, r: int, s: int, g: int):
        self.hall.place(r, s, g)
        for x in range(s, s + g):
            np.minimum(self.dmap, np.hypot(self.rr - r, self.xx - x), out=self.dmap)
            self.rowd[r, :] = np.minimum(self.rowd[r, :], np.abs(self.xx[0] - x))


def run_sequence(params: Params, seq, behaviour: str = None, seed: int = 0) -> RunResult:
    """Spielt eine Anfragefolge mit der Vergabeweise `behaviour` (Standard: `params.assign`). `seed` steuert nur die freie Wahl."""
    ch = Chooser(params, behaviour or params.assign, SplitMix64(seed))
    accepted = []
    for g in seq:
        pos = ch.choose(g)
        if pos is None:
            accepted.append(False)
        else:
            ch.place(pos[0], pos[1], g)
            accepted.append(True)
    return RunResult(ch.hall.persons, tuple(accepted), tuple(ch.hall.groups), params.seats)
