"""Saal als Raster: belegte und gesperrte Plätze, zulässige Plätze für eine Gruppe, Prüfung einer Belegung.

Eine Gruppe der Größe g sitzt zusammenhängend in einer Reihe. Zellen verschiedener Gruppen dürfen nicht benachbart sein:
ROW: seitlich benachbart (eine Lücke in der Reihe), MANH: auch vorn und hinten (4-Nachbarschaft, Schachbrettregel), KING: auch diagonal (8-Nachbarschaft)."""

import numpy as np

NEIGHBOURS = {
    "ROW": [(0, 1), (0, -1)],
    "MANH": [(0, 1), (0, -1), (1, 0), (-1, 0)],
    "KING": [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)],
}


class Hall:
    """Zustand eines Saals. `lengths`: Plätze je Reihe; Zellen hinter dem Ende einer Reihe gibt es nicht."""

    def __init__(self, lengths, rule: str):
        self.lengths = tuple(lengths)
        self.rule = rule
        self.R = len(self.lengths)
        self.C = max(self.lengths)
        self.valid = np.zeros((self.R, self.C), dtype=bool)
        for r, n in enumerate(self.lengths):
            self.valid[r, :n] = True
        self.occ = np.zeros((self.R, self.C), dtype=int)        # 0 frei, sonst Nummer der Gruppe
        self.blocked = ~self.valid                              # belegt, gesperrt oder nicht vorhanden
        self.groups = []                                        # (Zeile, Start, Größe) je Nummer - 1 (Nummern ab 1)

    def feasible(self, g: int):
        """Boolesche Matrix F[r, s]: Gruppe der Größe g darf auf den Plätzen s … s + g − 1 der Reihe r sitzen."""
        width = self.C - g + 1
        if width <= 0:
            return np.zeros((self.R, 0), dtype=bool)
        ok = np.ones((self.R, width), dtype=bool)
        for k in range(g):
            ok &= ~self.blocked[:, k:width + k]
        return ok

    def place(self, r: int, s: int, g: int) -> int:
        gid = len(self.groups) + 1
        self.groups.append((r, s, g))
        self.occ[r, s:s + g] = gid
        for x in range(s, s + g):
            self.blocked[r, x] = True
            for dr, dx in NEIGHBOURS[self.rule]:
                r2, x2 = r + dr, x + dx
                if 0 <= r2 < self.R and 0 <= x2 < self.C:
                    self.blocked[r2, x2] = True
        return gid

    @property
    def persons(self) -> int:
        return int(sum(g for _r, _s, g in self.groups))


def check_placements(lengths, rule: str, placements) -> bool:
    """Unabhängige Prüfung einer Belegung (Liste (Zeile, Start, Größe)): alle Plätze existieren, keine Zelle doppelt, Zellen verschiedener Gruppen nie benachbart. Reine Schleifen, kein Gemeinsames mit Hall."""
    cell = {}
    for gid, (r, s, g) in enumerate(placements):
        if not (0 <= r < len(lengths)) or s < 0 or s + g > lengths[r]:
            return False
        for x in range(s, s + g):
            if (r, x) in cell:
                return False
            cell[(r, x)] = gid
    for (r, x), gid in cell.items():
        for dr, dx in NEIGHBOURS[rule]:
            other = cell.get((r + dr, x + dx))
            if other is not None and other != gid:
                return False
    return True
