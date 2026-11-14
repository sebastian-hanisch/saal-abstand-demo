"""Geschlossene Rechnungen: erwartete Besetzung einer Reihe bei freier Wahl (Random Sequential Adsorption mit Einzelgästen) und Kapazität gleicher Gruppen in einer Reihe.

* `rsa_expected(n)`: Einzelne Gäste wählen gleichverteilt unter den zulässigen Plätzen einer Reihe mit n Plätzen (eine Lücke zwischen Gästen). Rekursion: der gewählte Platz i
  teilt die Reihe in zwei freie Stücke mit i − 2 und n − i − 1 Plätzen; E(n) = 1/n · Σ_i (1 + E(i − 2) + E(n − i − 1)), E(n) = 0 für n ≤ 0.
* `row_capacity(n, g)`: Gruppen der Größe g mit einer Lücke in einer Reihe mit n Plätzen: g · ⌊(n + 1) / (g + 1)⌋ Personen (Bin-Packing mit Behältern der Länge n + 1 und Gegenständen g + 1).
* `rsa_simulate_row`: Simulation derselben freien Wahl (Gegenprobe der Rekursion)."""

from functools import lru_cache
from math import sqrt

from sab_rng import SplitMix64


@lru_cache(maxsize=None)
def _table(n: int) -> tuple:
    """E(0) … E(n) von unten nach oben (keine Rekursionstiefe)."""
    e = [0.0] * (n + 1)
    for m in range(1, n + 1):
        e[m] = sum(1.0 + e[max(i - 2, 0)] + e[max(m - i - 1, 0)] for i in range(1, m + 1)) / m
    return tuple(e)


def rsa_expected(n: int) -> float:
    """Erwartete Zahl besetzter Plätze einer Reihe mit n Plätzen bei freier Wahl von Einzelnen (exakt)."""
    return _table(n)[n] if n > 0 else 0.0


def row_capacity(n: int, g: int) -> int:
    return g * ((n + 1) // (g + 1))


def singles_capacity(n: int) -> int:
    """Größte Zahl Einzelner in einer Reihe mit n Plätzen: jeder zweite Platz."""
    return (n + 1) // 2


def rsa_simulate_row(n: int, runs: int, seed: int) -> tuple:
    """Mittel und Standardfehler der besetzten Plätze bei freier Wahl von Einzelnen in einer Reihe mit n Plätzen (gleichverteilte Reihenfolge der Plätze = gleichverteilte Wahl unter den zulässigen)."""
    rng = SplitMix64(seed)
    counts = []
    for _ in range(runs):
        order = list(range(n))
        rng.shuffle(order)
        blocked = [False] * n
        c = 0
        for p in order:
            if not blocked[p]:
                c += 1
                for q in (p - 1, p, p + 1):
                    if 0 <= q < n:
                        blocked[q] = True
        counts.append(c)
    mean = sum(counts) / runs
    var = sum((x - mean) ** 2 for x in counts) / (runs - 1)
    return mean, sqrt(var / runs)
