"""Konstanten: Regler-Grenzen, feste Annahmen, Farben und Presets."""

SEED_MAX, DEFAULT_SEED = 999999, 35
SWEEP_SEEDS = tuple(range(100000, 100100))   # feste Zufalls-Seeds der vorgerechneten Messreihen (je Zelle 100 Folgen): nie ein einzelner Seed als Befund
SUBSEED_STRIDE = 1000                        # Folge k der Live-Rechnung: Zufalls-Seed seed * SUBSEED_STRIDE + k
LIVE_SEQS = 8                                # Anfragefolgen der Live-Rechnung
OFFLINE_TLIMIT = 6.0                         # Zeitgrenze (Sekunden) je exaktem Offline-Optimum in der Live-Rechnung

ROWS_MIN, ROWS_MAX = 2, 14
COLS_MIN, COLS_MAX = 6, 20
BOGEN_MAX_LEN = 28                           # längste Reihe im Saal mit Bogen
GMAX = 6                                     # größte Gruppe

# Gruppengrößen-Mischungen (Annahmen): Anteil der Gruppen mit 1, 2, … Personen
DISTRIBUTIONS = {
    "einzel": {1: 1.0},
    "paare": {1: 0.25, 2: 0.50, 3: 0.10, 4: 0.15},
    "familie": {1: 0.10, 2: 0.25, 3: 0.20, 4: 0.30, 5: 0.10, 6: 0.05},
    "gleich": {g: 1 / 6 for g in range(1, 7)},
}
DIST_LABELS = {
    "einzel": "Nur Einzelne (Ø 1 Person)",
    "paare": "Viele Paare (Ø 2,15 Personen)",
    "familie": "Familien (Ø 3,2 Personen)",
    "gleich": "Gleichmäßig 1 bis 6 (Ø 3,5 Personen)",
}
RULES = ("ROW", "MANH", "KING")
RULE_LABELS = {
    "ROW": "Nur seitlich: eine Lücke in der Reihe",
    "MANH": "Schachbrett: auch vorn und hinten gesperrt",
    "KING": "Streng: auch diagonal gesperrt",
}
HALLS = ("gleich", "bogen")
HALL_LABELS = {"gleich": "Gleich lange Reihen", "bogen": "Saal mit Bogen (Reihen werden nach hinten länger)"}

# Vergabeweisen: Platzanweiser (FF, BF), Gäste wählen frei (FREI), die Mitte (MITTE), Gäste suchen Abstand (WEIT_E)
ASSIGNS = ("FF", "BF", "FREI", "MITTE", "WEIT_E")
ASSIGN_LABELS = {
    "FF": "Platzanweiser links (First-Fit)",
    "BF": "Platzanweiser engste Lücke (Best-Fit)",
    "FREI": "Gäste wählen frei",
    "MITTE": "Gäste wählen die Mitte",
    "WEIT_E": "Gäste suchen Abstand (zu allen Gästen)",
}
# weitere Definitionen von „Abstand suchen“, nur in den vorgerechneten Experimenten
EXTRA_BEHAVIOURS = ("WEIT_R", "WEIT_W")
BEHAVIOUR_LABELS = dict(ASSIGN_LABELS, WEIT_R="Abstand suchen: nur in der Reihe", WEIT_W="Abstand suchen: nur in der Reihe, Wand zählt mit")

COLOR_GOOD = "#2F6B65"
COLOR_BAD = "#c0504d"
COLOR_NEUTRAL = "#4c78a8"
COLOR_GRAY = "rgba(150,150,150,0.55)"
COLOR_GROUP = {1: "#9ecae1", 2: "#6baed6", 3: "#4292c6", 4: "#2171b5", 5: "#2F6B65", 6: "#1b4a45"}

PRESETS = {
    "Platzanweiser": {},
    "Gäste wählen frei": {"assign": "FREI"},
    "Gäste suchen Abstand": {"assign": "WEIT_E"},
    "Fast voller Saal mit Familien": {"dist": "familie", "load": 1.2, "assign": "FREI"},
    "Nur Einzelne": {"dist": "einzel", "assign": "FREI"},
    "Saal mit Bogen": {"hall": "bogen", "assign": "FREI"},
}
PRESET_HELP = {
    "Platzanweiser": "8 Reihen zu je 16 Plätzen, Regel „nur seitlich“, viele Paare, Saal ausgelastet: ein Platzanweiser setzt jede Gruppe in die erste freie Lücke links.",
    "Gäste wählen frei": "Derselbe Saal, aber jede Gruppe wählt gleichverteilt unter allen zulässigen Plätzen: die Reihen zerfallen vermutlich in Reste, in die größere Gruppen nicht mehr passen (nicht gemessen).",
    "Gäste suchen Abstand": "Jede Gruppe setzt sich auf den Platz mit dem größten Abstand zu allen anderen Gästen, auch in anderen Reihen. Vergleichen Sie das Ergebnis mit freier Wahl und mit dem Platzanweiser.",
    "Fast voller Saal mit Familien": "Familien (Ø 3,2 Personen) und 20 % mehr Anfragen als Plätze, Gäste wählen frei. Vergleichen Sie die Rangfolge der fünf Vergabeweisen mit der bei Paaren.",
    "Nur Einzelne": "Nur Einzelgäste: ein Platzanweiser besetzt jeden zweiten Platz (das Optimum), freie Wahl bleibt darunter (in einer Reihe exakt gerechnet, siehe Kernfrage 2).",
    "Saal mit Bogen": "Reihen, die nach hinten länger werden (Saal mit Bogen), Gäste wählen frei. Best-Fit und First-Fit unterscheiden sich kaum (Experiment 3).",
}

BEHAVIOURS_ALL = ASSIGNS + EXTRA_BEHAVIOURS
