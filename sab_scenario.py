"""Szenario: Saal mit Abstandsregel, Gruppenmischung, Last und Vergabeweise.

`Params` hat nur Schlüsselwörter (ein später eingefügtes Feld verschiebt nie still Werte)."""

from dataclasses import dataclass

import sab_constants as C
from sab_rng import SplitMix64


@dataclass(frozen=True, kw_only=True)
class Params:
    rows: int = 8               # Zahl der Reihen
    cols: int = 16              # Plätze je Reihe (bei „bogen“ die mittlere Reihenlänge)
    hall: str = "gleich"        # gleich oder bogen
    rule: str = "ROW"           # ROW, MANH oder KING
    dist: str = "paare"         # Gruppenmischung (Schlüssel von C.DISTRIBUTIONS)
    load: float = 1.0           # angefragte Personen durch Plätze
    assign: str = "FF"          # Vergabeweise

    def __post_init__(self):
        for name, lo, hi in (("rows", C.ROWS_MIN, C.ROWS_MAX), ("cols", C.COLS_MIN, C.COLS_MAX)):
            v = getattr(self, name)
            if not isinstance(v, int) or isinstance(v, bool) or not lo <= v <= hi:
                raise ValueError(f"{name} muss eine ganze Zahl von {lo} bis {hi} sein")
        if self.hall not in C.HALLS:
            raise ValueError(f"hall muss eines von {C.HALLS} sein")
        if self.rule not in C.RULES:
            raise ValueError(f"rule muss eines von {C.RULES} sein")
        if self.hall == "bogen" and self.rule != "ROW":
            raise ValueError("ein Saal mit Bogen gibt es nur bei der Regel ROW (im Raster müssen die Reihen gleich lang sein)")
        if self.dist not in C.DISTRIBUTIONS:
            raise ValueError(f"dist muss eines von {sorted(C.DISTRIBUTIONS)} sein")
        if not 0.2 <= self.load <= 2.0:
            raise ValueError("load muss zwischen 0,2 und 2,0 liegen")
        if self.assign not in C.BEHAVIOURS_ALL:
            raise ValueError(f"assign muss eines von {C.BEHAVIOURS_ALL} sein")

    @property
    def row_lengths(self) -> tuple:
        """Plätze je Reihe. Bogen: von 60 % bis 140 % der mittleren Länge (nach hinten länger), höchstens C.BOGEN_MAX_LEN und mindestens C.COLS_MIN."""
        if self.hall == "gleich" or self.rows == 1:
            return (self.cols,) * self.rows
        lo = max(C.COLS_MIN, round(0.6 * self.cols))
        hi = min(C.BOGEN_MAX_LEN, round(1.4 * self.cols))
        return tuple(round(lo + (hi - lo) * r / (self.rows - 1)) for r in range(self.rows))

    @property
    def width(self) -> int:
        return max(self.row_lengths)

    @property
    def seats(self) -> int:
        return sum(self.row_lengths)

    @property
    def mean_group(self) -> float:
        return sum(g * p for g, p in C.DISTRIBUTIONS[self.dist].items())


def sample_sequence(params: Params, rng: SplitMix64) -> list:
    """Anfragefolge: Gruppengrößen nach der Mischung, bis die angefragten Personen mindestens load · Plätze erreichen (die letzte Gruppe schließt die Folge)."""
    sizes = sorted(C.DISTRIBUTIONS[params.dist])
    probs = [C.DISTRIBUTIONS[params.dist][g] for g in sizes]
    target = int(params.load * params.seats)
    seq, total = [], 0
    while total < target:
        g = sizes[rng.choice(probs)]
        seq.append(g)
        total += g
    return seq


def demand_of(seq) -> list:
    """Zahl der Anfragen je Gruppengröße 1 … C.GMAX."""
    return [seq.count(g) for g in range(1, C.GMAX + 1)]
