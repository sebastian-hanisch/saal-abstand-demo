"""Saal mit Abstand: Wer vergibt die Plätze? - interaktive Fall-Demo
Sebastian Hanisch - Operations Research und Machine Learning

Ein Saal (Kino, Hörsaal, Theater) mit Abstandsregel: zwischen fremden Gruppen muss ein Platz frei bleiben. Die Demo vergleicht Vergabeweisen auf denselben Anfragefolgen: ein Platzanweiser,
Gäste, die frei wählen, die Mitte nehmen oder Abstand suchen, und misst sie am exakten Offline-Optimum.

Lauffähig mit: streamlit run app.py
"""

import time

import pandas  # noqa: F401  (früh importiert, Vorsichtsmaßnahme gegen einen Importfehler beim Kaltstart der Cloud-App)
import streamlit as st

import sab_constants as C
from sab_evaluation import (
    Settings,
    analyse,
    free_singles,
    group_capacity,
    load_results,
    verdict_assign,
    verdict_free,
    verdict_groups,
    verdict_ranking,
)
from sab_layout import dunkles_design, kopf_css
from sab_offline import offline_optimum
from sab_presets import (
    bounds,
    init_session_state_defaults,
    load_permalink_settings,
    randomize_seed,
    sidebar_presets,
    sync_query_params,
)
from sab_rng import SplitMix64
from sab_scenario import Params, demand_of, sample_sequence
from sab_visualization import build_free_row, build_groups, build_hall, build_shares

st.set_page_config(page_title="Saal mit Abstand – Sebastian Hanisch", layout="wide")

DATA = load_results()


@st.cache_data(show_spinner=False)
def _analysis(settings):
    return analyse(settings)


@st.cache_data(show_spinner=False)
def _free_singles(params, seed):
    return free_singles(params, 40, seed)


@st.cache_data(show_spinner=False)
def _groups(params):
    return group_capacity(params)


def _show(verdict):
    kind, text = verdict
    {"success": st.success, "warning": st.warning, "info": st.info}[kind](text)


def _num(x, digits=1):
    return f"{x:.{digits}f}".replace(".", ",")


ASSUMPTIONS_MARKDOWN = """
| Annahme | Wer setzt an |
|---|---|
| Gruppen mit 1 bis 6 Personen kommen nacheinander, nach einer von vier Mischungen (gesetzt, nicht aus Daten); jede wird sofort und unwiderruflich gesetzt oder abgewiesen | Regler, Modell |
| Abstandsregel: Zellen verschiedener Gruppen dürfen nicht benachbart sein (seitlich; zusätzlich vorn und hinten; zusätzlich diagonal); Gruppen sitzen zusammenhängend in einer Reihe | Regler |
| Last = angefragte Personen durch Plätze; die Folge endet, sobald die angefragten Personen die Last erreichen | Regler |
| Der Platzanweiser (First-Fit, Best-Fit) kennt die Regel und setzt nach fester Vorschrift; er kennt die künftigen Anfragen nicht | Modell |
| Das Verhalten der Gäste (frei, Mitte, Abstand suchen) ist ein gesetztes Modell, keine Beobachtung echter Gäste | Modell |
| Das Offline-Optimum kennt die ganze Folge und wählt frei aus, welche Gruppen es setzt: es ist ein Maßstab, kein erreichbarer Wert | Modell |
| Reihenregel: Saal mit Bogen (längere Reihen nach hinten) nur bei der Regel „nur seitlich“; Raster höchstens 14 Reihen mit 20 Plätzen | Regler |
| Keine Gänge, keine Plätze am Rand, keine Wegezeiten, keine Warteliste, keine Haushalte, die sich trennen lassen | Nicht umgesetzt |
"""

# Fester Kopf: nur der Titel bleibt beim Scrollen oben (Stylesheet in sab_layout.py).
st.html(kopf_css(dunkles_design()))
with st.container(key="kopf"):
    st.title("🎭 Saal mit Abstand: Wer vergibt die Plätze?")
st.markdown(
    """
In einem **Saal mit Abstandsregel** (zwischen fremden Gruppen bleibt ein Platz frei) kommen Gruppen von einer bis sechs Personen nacheinander und werden sofort gesetzt oder abgewiesen. Die Demo fragt:
**Wer soll die Plätze vergeben**, ein **Platzanweiser** oder die **Gäste** selbst, und wie wählen die Gäste, wenn sie **frei** wählen, die **Mitte** nehmen oder **Abstand suchen**? Als Maßstab dient das
**exakte Offline-Optimum**, das die ganze Folge kennt. Dazu kommen drei **Abstandsregeln** (seitlich, Schachbrett, streng), ein **Saal mit Bogen** und eine **feste Sperrmatrix**.

Alle Annahmen (Gruppenmischungen, Gästeverhalten, Regeln) sind Regler oder gesetzt, keine Messdaten. Weiter unten: der **Saalplan** einer Folge, drei **Kernfragen**, sechs **Experimente** mit vorgerechneten
Messreihen und die Expander **🔧 Wie wir das erreichen – vollständiger Methodenvergleich**, **📐 Mathematische Formulierung** und **🚧 Wo die Annahmen enden**.
"""
)
st.caption("🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, um ein Szenario zu teilen.")

load_permalink_settings()
init_session_state_defaults()

with st.sidebar:
    sidebar_presets()  # Schnellstart oben, das aktive Preset ist hervorgehoben
    st.header("🎭 Saal")
    rows = st.slider("Reihen", *bounds("rows_slider"), key="rows_slider", help="Zahl der Reihen (Reihe 1 liegt vorn).")
    cols = st.slider("Plätze je Reihe", *bounds("cols_slider"), key="cols_slider", help="Plätze je Reihe; im Saal mit Bogen die mittlere Länge (von 60 % vorn bis 140 % hinten).")
    rule = st.selectbox("Abstandsregel", list(C.RULES), key="rule_select", format_func=lambda k: C.RULE_LABELS[k],
                        help="Zellen verschiedener Gruppen dürfen nicht benachbart sein: seitlich; zusätzlich vorn und hinten (Schachbrett); zusätzlich diagonal (streng).")
    hall = st.selectbox("Saalform", list(C.HALLS), key="hall_select", format_func=lambda k: C.HALL_LABELS[k], help="Gleich lange Reihen oder ein Saal mit Bogen (nur bei der Regel „nur seitlich“).")
    if rule != "ROW" and hall == "bogen":
        st.caption("Ein Saal mit Bogen gibt es nur bei der Regel „nur seitlich“: gerechnet wird mit gleich langen Reihen.")
        hall = "gleich"
    st.header("👥 Gäste")
    dist = st.selectbox("Gruppenmischung", list(C.DISTRIBUTIONS), key="dist_select", format_func=lambda k: C.DIST_LABELS[k], help="Anteile der Gruppengrößen 1 bis 6 (gesetzt, nicht aus Daten).")
    load = st.slider("Last", *bounds("load_slider"), key="load_slider", step=0.1, format="%.1f",
                     help="Angefragte Personen durch Plätze. Wegen der Lücken passt nicht immer alles hinein: bei lauter Einzelnen schon ab Last 0,5 nicht mehr, bei Paaren ab etwa 0,8; bei kleiner Last passt offline alles.")
    st.header("🪑 Vergabe")
    assign = st.selectbox("Wer wählt den Platz?", list(C.ASSIGNS), key="assign_select", format_func=lambda k: C.ASSIGN_LABELS[k],
                          help="Platzanweiser links, Platzanweiser engste Lücke, Gäste wählen frei (gleichverteilt unter allen zulässigen Plätzen), die Mitte nehmen oder Abstand zu allen Gästen suchen.")
    st.header("🎲 Zufall")
    seed = st.number_input("Zufalls-Seed", *bounds("seed_input"), key="seed_input", help="Gleicher Seed, gleiche Anfragefolgen (eigener Zufallsgenerator).")
    st.button("🎲 Neuen Zufalls-Seed würfeln", on_click=randomize_seed)

params = Params(rows=rows, cols=cols, hall=hall, rule=rule, dist=dist, load=load, assign=assign)
settings = Settings(params=params, seed=int(seed))
sync_query_params({"rows_slider": rows, "cols_slider": cols, "hall_select": st.session_state["hall_select"], "rule_select": rule, "dist_select": dist, "load_slider": load,
                   "assign_select": assign, "seed_input": int(seed)})

t0 = time.perf_counter()
with st.spinner("Der Saal wird gefüllt und das Offline-Optimum gerechnet …"):
    a = _analysis(settings)
elapsed = time.perf_counter() - t0
s = a.stats[assign]

# ---------------------------------------------------------------------------------------------- Ergebnis und Saalplan
st.markdown("## Ergebnis des eingestellten Saals")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Gesetzte Personen", _num(s.persons), help=f"Mittel über {a.n} Anfragefolgen, Standardfehler {_num(s.persons_se)}.")
c2.metric("Besetzte Plätze", f"{100 * s.occupancy:.0f} %".replace(".", ","), help=f"Gesetzte Personen durch die {params.seats} Plätze des Saals.")
c3.metric("Anteil am Offline-Optimum", f"{100 * s.share:.1f} %".replace(".", ","), help="Mittel der Anteile je Folge: gesetzte Personen durch die Personen des exakten Offline-Optimums.")
c4.metric("Offline-Optimum", _num(a.offline_mean), help=f"Größte Personenzahl, wenn die ganze Folge bekannt ist (im Mittel; bewiesen in {a.offline_proven} von {a.n} Folgen).")
c5.metric("Abgewiesene Gruppen", _num(s.rejected), help="Gruppen, die keinen zulässigen Platz fanden (Mittel je Folge).")
st.caption(f"Rechenzeit der Live-Rechnung: {elapsed:.1f} s ({a.n} Folgen mit Zufalls-Seeds {int(seed)} · 1000 + k, wiederholte Einstellungen kommen aus dem Zwischenspeicher).")

st.markdown("**Saalplan der ersten Folge** (Zahl = Größe der Gruppe, hellgrün = freier Platz, Reihe 1 vorn)")
requested = sum(a.example_requests)
st.plotly_chart(build_hall(params.row_lengths, a.example.placements), width="stretch", config={"displayModeBar": False})
st.caption(f"Erste Folge: {len(a.example_requests)} Gruppen mit {requested} Personen angefragt, {a.example.persons} Personen gesetzt, {sum(1 for f in a.example.accepted if not f)} Gruppen abgewiesen.")

# ---------------------------------------------------------------------------------------------- Kernfrage 1
st.markdown("## Kernfrage 1: Wer soll die Plätze vergeben?")
_show(verdict_assign(a))
_show(verdict_ranking(a))
st.plotly_chart(build_shares(a.stats, assign), width="stretch", config={"displayModeBar": False})
st.dataframe([{"Vergabe": C.ASSIGN_LABELS[k], "Personen": _num(v.persons), "Anteil am Optimum": _num(100 * v.share) + " %", "Standardfehler": _num(100 * v.share_se, 2) + " Punkte", "abgewiesene Gruppen": _num(v.rejected)}
              for k, v in a.stats.items()], hide_index=True, width="stretch")

# ---------------------------------------------------------------------------------------------- Kernfrage 2
st.markdown("## Kernfrage 2: Was kostet freie Wahl?")
st.caption("Einzelne Gäste, gleichverteilte Wahl unter allen zulässigen Plätzen (Random Sequential Adsorption): exakt in einer Reihe, simuliert im eingestellten Saal.")
free_hall = _free_singles(params, int(seed))
_show(verdict_free(cols, free_hall, rule))
st.plotly_chart(build_free_row(DATA["rsa"]["reihe"]), width="stretch", config={"displayModeBar": False})
st.caption("Die erwartete Besetzung einer Reihe bei freier Wahl nähert sich mit wachsender Länge dem Grenzwert (1 − e⁻²)/2 ≈ 0,4323 der Plätze, also 86,5 % der Obergrenze von 0,5.")

# ---------------------------------------------------------------------------------------------- Kernfrage 3
st.markdown("## Kernfrage 3: Heben Gruppen die Kapazität?")
with st.spinner("Die Kapazität gleicher Gruppen wird gerechnet …"):
    caps = _groups(params)
_show(verdict_groups(caps, rule))
st.plotly_chart(build_groups(caps, rule), width="stretch", config={"displayModeBar": False})
st.caption("Exakt gerechnet für den eingestellten Saal (ein ganzzahliges Programm je Gruppengröße); alle drei Regeln im Raster 10 × 16 stehen im Experiment 5.")

# ---------------------------------------------------------------------------------------------- Experimente
st.markdown("## Experimente (vorgerechnet)")
st.caption("Simulationen mit festen Zufalls-Seeds und exaktem Offline-Optimum (`tools/make_results.py`); nichts davon rechnet beim Öffnen der Seite.")

HALL_NAME = {"gleich": "8 × 16 gleich lang", "bogen": "8 Reihen mit Bogen"}
BEHAVIOUR_COLS = ["FF", "BF", "FREI", "MITTE", "WEIT_E", "WEIT_R", "WEIT_W"]

st.subheader("🔬 1 · Wer wählt, entscheidet: Rangfolge der Vergabeweisen")
st.dataframe([{"Saal": HALL_NAME[r["hall"]], "Mischung": C.DIST_LABELS[r["dist"]], "Last": _num(r["load"]), **{C.BEHAVIOUR_LABELS[b]: _num(100 * r["behaviours"][b]["share"]) + " %" for b in BEHAVIOUR_COLS}}
              for r in DATA["verhalten"]], hide_index=True, width="stretch")
st.caption("Anteil am Offline-Optimum in Prozent, Mittel über 100 Folgen je Zeile; Regel „nur seitlich“. „Abstand suchen“ gibt es in drei Definitionen: zu allen Gästen (auch in anderen Reihen), nur in der Reihe, nur in der Reihe mit der Wand.")

st.subheader("🔬 2 · Last: schon bei 70 % Last gehen bei freier Wahl Gäste verloren")
rows2 = []
for r in DATA["verhalten"]:
    if r["hall"] == "gleich" and r["dist"] in ("paare", "familie", "gleich"):
        rows2.append({"Mischung": C.DIST_LABELS[r["dist"]], "Last": _num(r["load"]), "Platzanweiser": _num(100 * r["behaviours"]["FF"]["share"]) + " %", "Gäste wählen frei": _num(100 * r["behaviours"]["FREI"]["share"]) + " %",
                      "Unterschied": _num(100 * (r["behaviours"]["FF"]["share"] - r["behaviours"]["FREI"]["share"])) + " Punkte"})
st.dataframe(rows2, hide_index=True, width="stretch")
st.caption("Anteil am Offline-Optimum, Saal 8 × 16 mit gleich langen Reihen, Regel „nur seitlich“; Last 0,7 heißt: angefragt werden 70 % der Plätze. Der Platzanweiser setzt dann fast alle Gäste, bei freier Wahl bleibt ein Teil der Anfragen ohne Platz.")

st.subheader("🔬 3 · Saal mit Bogen: Best-Fit und First-Fit")
rows3 = []
for r in DATA["verhalten"]:
    if r["hall"] == "bogen" and r["dist"] != "einzel":
        rows3.append({"Mischung": C.DIST_LABELS[r["dist"]], "Last": _num(r["load"]), "First-Fit": _num(100 * r["behaviours"]["FF"]["share"], 2) + " %", "Best-Fit": _num(100 * r["behaviours"]["BF"]["share"], 2) + " %",
                      "Unterschied": _num(100 * (r["behaviours"]["BF"]["share"] - r["behaviours"]["FF"]["share"]), 2) + " Punkte"})
st.dataframe(rows3, hide_index=True, width="stretch")

st.subheader("🔬 4 · Raster: freie Wahl gegen Platzanweiser")
st.dataframe([{"Regel": r["rule"], "Mischung": C.DIST_LABELS[r["dist"]], "Last": _num(r["load"]), "Folgen": r["n"], "Platzanweiser": _num(100 * r["behaviours"]["FF"]["share"]) + " %",
               "Gäste wählen frei": _num(100 * r["behaviours"]["FREI"]["share"]) + " %", "Mitte": _num(100 * r["behaviours"]["MITTE"]["share"]) + " %", "Abstand suchen": _num(100 * r["behaviours"]["WEIT_E"]["share"]) + " %"}
              for r in DATA["raster"]], hide_index=True, width="stretch")
st.caption("Raster 10 Reihen × 16 Plätze; Anteil am Offline-Optimum (exakt, ganzzahliges Programm).")

st.subheader("🔬 5 · Regelgeometrie und Gruppengröße")
tab_rows = []
for g in range(1, C.GMAX + 1):
    row = {"Gruppengröße": str(g)}
    for rl in C.RULES:
        v = next(x for x in DATA["gruppen"] if x["rule"] == rl and x["g"] == g)
        row[rl] = f"{v['persons']} ({_num(100 * v['persons'] / v['seats'], 0)} %)"
    tab_rows.append(row)
st.dataframe(tab_rows, hide_index=True, width="stretch")
st.caption("Größte Personenzahl bei lauter gleich großen Gruppen im Raster 10 × 16 (160 Plätze), exakt. Nur seitlich (ROW), Schachbrett (MANH), streng (KING).")

st.subheader("🔬 6 · Feste Sperrmatrix statt Vergabe nach Bedarf")
st.dataframe([{"Saal": HALL_NAME[r["hall"]], "Mischung": C.DIST_LABELS[r["dist"]], "Last": _num(r["load"]), "Platzanweiser": _num(100 * r["ff_share"]) + " %", "feste Sperrmatrix": _num(100 * r["template_share"]) + " %"}
              for r in DATA["vorlage"]], hide_index=True, width="stretch")
st.caption("Saal 8 × 16 mit gleich langen Reihen, Regel „nur seitlich“. Die Sperrmatrix folgt den Anteilen der Mischung und ist nicht optimiert; im Saal mit Bogen (jede Reihe eine andere Länge) ist sie nicht gerechnet. Eine auf die Verteilung optimierte Vorlage (Blom, Pendavingh, Spieksma 2020, dort mit anderer Abstandsregel) ist ein anderer Vergleich und hier nicht nachgebaut.")

# ---------------------------------------------------------------------------------------------- Expander
with st.expander("🔧 Wie wir das erreichen – vollständiger Methodenvergleich"):
    tab_methods, tab_exact = st.tabs(["📊 Verfahren", "🧮 Exakt (Offline-Optimum)"])
    with tab_methods:
        st.markdown(
            """
| Vergabe | Wer wählt, nach welcher Regel |
|---|---|
| **Platzanweiser links (First-Fit)** | erste zulässige Reihe, links |
| **Platzanweiser engste Lücke (Best-Fit)** | die engste freie Lücke, in die die Gruppe passt |
| **Gäste wählen frei** | gleichverteilt unter allen zulässigen Plätzen (Random Sequential Adsorption) |
| **Gäste wählen die Mitte** | kleinster Abstand zur Mittelreihe, dann zur Reihenmitte |
| **Gäste suchen Abstand** | der Platz, dessen nächster besetzter Platz (alle Reihen, euklidisch) am weitesten entfernt ist |

Bei Gleichstand gilt die erste Reihe, links. Das **Offline-Optimum** ist ein ganzzahliges Programm (HiGHS über `scipy.optimize.milp`) mit einer 0/1-Variablen je Platzierung; es kennt die ganze Folge und wählt frei aus.
Alle Zufallsfolgen kommen aus einem eigenen SplitMix64; die Live-Rechnung nutzt """ + f"{C.LIVE_SEQS} Anfragefolgen" + """, die Messreihen 100 Folgen je Zeile (Raster: 40 oder 100).
"""
        )
    with tab_exact:
        st.markdown("Rechnet für die **erste Anfragefolge** des eingestellten Saals das Offline-Optimum neu und zeigt Status und Rechenzeit. Wird die Zeitgrenze erreicht, steht „nicht bewiesen“.")
        if st.button("Offline-Optimum rechnen", key="offline_run"):
            seq = sample_sequence(params, SplitMix64(int(seed) * C.SUBSEED_STRIDE))
            t1 = time.perf_counter()
            off = offline_optimum(params, demand_of(seq), C.OFFLINE_TLIMIT)
            st.session_state["offline_result"] = (params, int(seed), off, time.perf_counter() - t1, len(seq))
        stored = st.session_state.get("offline_result")
        if stored and stored[0] == params and stored[1] == int(seed):
            _p, _s, off, secs, nreq = stored
            st.metric("Offline-Optimum der ersten Folge", str(off.persons), delta="bewiesen" if off.status == 0 else "nicht bewiesen (Zeitgrenze)", delta_color="off")
            st.caption(f"{nreq} Anfragen, {off.variables} Variablen, {secs:.2f} s, Zeitgrenze {C.OFFLINE_TLIMIT:.0f} s.")
        elif stored:
            st.caption("Die Einstellungen haben sich geändert: erneut „Offline-Optimum rechnen“.")

with st.expander("📐 Mathematische Formulierung"):
    st.markdown(
        r"""
**Gegeben:** ein Saal mit $R$ Reihen der Längen $L_r$ (Plätze), eine Folge von Gruppen der Größen $g_1, g_2, \dots$ und eine Abstandsregel: Zellen verschiedener Gruppen dürfen nicht benachbart sein.
Jede Gruppe wird sofort gesetzt (zusammenhängend in einer Reihe) oder abgewiesen. **Gesucht** sind die gesetzten Personen je Vergabeweise im Vergleich zum Offline-Optimum.

**Offline-Optimum:** Mit einer 0/1-Variablen $x_p$ je Platzierung $p$ der Größe $g_p$ und $d_g$ Anfragen der Größe $g$:

$$\max \sum_p g_p \, x_p \quad \text{mit} \quad \sum_{p:\, g_p = g} x_p \le d_g \ \text{ und } \ \sum_{p \ni c} x_p \le 1 \ \text{ für jede Zelle } c \text{ einer virtuellen Strecke.}$$

Seitlich belegt eine Platzierung der Größe $g$ eine virtuelle Strecke von $g + 1$ Plätzen (Gruppe plus Lücke): ein Intervallgraph, die Bedingung ist exakt. Vorn/hinten und diagonal (Schachbrett, streng) kommt je Zellpaar $o_c + o_{c'} \le 1$ hinzu, wobei $o_c = \sum_{p \ni c} x_p$ die Zahl der Platzierungen ist, die die Zelle $c$ belegen. Die Strecke am Reihenende reicht gedanklich über die Wand, dort ist keine Lücke nötig.

**Reihe, gleiche Gruppen:** In einer Reihe mit $L$ Plätzen passen höchstens

$$g \left\lfloor \frac{L + 1}{g + 1} \right\rfloor$$

Personen in Gruppen der Größe $g$ (Bin-Packing mit Behältern der Länge $L + 1$ und Gegenständen der Länge $g + 1$).

**Freie Wahl, Einzelne:** Wählt jeder Gast gleichverteilt unter den zulässigen Plätzen einer Reihe mit $n$ Plätzen, ist die erwartete Besetzung $E(n)$ mit $E(n) = 0$ für $n \le 0$ und

$$E(n) = \frac{1}{n} \sum_{i=1}^{n} \bigl(1 + E(i - 2) + E(n - i - 1)\bigr).$$

| Symbol | Bedeutung |
|---|---|
| $R, L_r$ | Zahl der Reihen, Plätze der Reihe $r$ |
| $g, d_g$ | Gruppengröße, Zahl der Anfragen dieser Größe |
| $x_p, g_p$ | Platzierung $p$ gewählt (0/1), ihre Gruppengröße |
| $E(n)$ | erwartete besetzte Plätze einer Reihe mit $n$ Plätzen bei freier Wahl von Einzelnen |

**Anteil am Offline-Optimum:** gesetzte Personen durch die Personen des Optimums derselben Folge, gemittelt über die Folgen.
"""
    )

with st.expander("🚧 Wo die Annahmen enden"):
    st.markdown(
        """
- Gruppenmischungen, Gästeverhalten (frei, Mitte, Abstand suchen) und Regeln sind **gesetzte Annahmen**, nicht an echten Sälen oder Gästen gemessen. „Abstand suchen“ ist ein Modell, kein beobachtetes Verhalten; je nach Definition fällt der Verlust verschieden hoch aus.
- Das **Offline-Optimum** kennt die ganze Folge und wählt aus, welche Gruppen es setzt; es ist ein Maßstab und kein erreichbarer Wert. Bei Überangebot misst die Lücke zum Optimum auch, **wen** man bedient.
- Der Saal ist ein Raster ohne Gänge, Ränder oder Wegezeiten; Gruppen sitzen waagerecht und zusammenhängend; ein Saal mit Bogen nur bei der Regel „nur seitlich“; höchstens 14 Reihen mit 20 Plätzen.
- Die Live-Rechnung nutzt wenige Folgen; die Messreihen mehr Folgen und feste Zufalls-Seeds. Wird die Zeitgrenze des ganzzahligen Programms erreicht, steht „nicht bewiesen“.
- Die feste Sperrmatrix folgt nur den Anteilen der Mischung; optimierte Vorlagen sind nicht nachgebaut.
"""
    )
    st.markdown("**Annahmen im Überblick**")
    st.markdown(ASSUMPTIONS_MARKDOWN)

st.markdown("---")
st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). "
    "Mehr zum Thema: [Sitzplätze optimieren](https://sebastianhanisch.net/sitzplaetze-optimieren.html)."
)
