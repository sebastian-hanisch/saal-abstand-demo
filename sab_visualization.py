"""Plotly-Abbildungen. Alle Achsen sind gesperrt (fixedrange), damit Touch-Geräte beim Scrollen nicht am Diagramm hängen bleiben."""

import numpy as np
import plotly.graph_objects as go

import sab_constants as C


def lock_axes(fig):
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig


def _base(fig, height=340, legend=True):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="rgba(0,0,0,0)", showlegend=legend, legend=dict(orientation="h", y=-0.25))
    return lock_axes(fig)


def build_hall(lengths, placements):
    """Saalplan: Reihe 1 (Bühne, Leinwand) oben; belegte Plätze nach Gruppengröße gefärbt, freie Plätze hell, nicht vorhandene Plätze leer."""
    R, W = len(lengths), max(lengths)
    z = np.full((R, W), np.nan)
    for r, n in enumerate(lengths):
        z[r, :n] = 0
    text = [[""] * W for _ in range(R)]
    for gid, (r, s, g) in enumerate(placements, start=1):
        z[r, s:s + g] = g
        for x in range(s, s + g):
            text[r][x] = str(g)
    scale = [[0.0, "#e3efe9"], [1 / 7, "#e3efe9"]]
    for g in range(1, C.GMAX + 1):
        scale += [[g / 7, C.COLOR_GROUP[g]], [(g + 1) / 7, C.COLOR_GROUP[g]]]
    fig = go.Figure(go.Heatmap(z=z.tolist(), zmin=0, zmax=7, colorscale=scale, showscale=False, text=text, texttemplate="%{text}", xgap=2, ygap=2,
                               hovertemplate="Reihe %{y}, Platz %{x}<extra></extra>"))
    fig.update_yaxes(autorange="reversed", showticklabels=False)
    fig.update_xaxes(showticklabels=False)
    return _base(fig, height=60 + 32 * R, legend=False)


def build_shares(stats, current):
    """Anteil am Offline-Optimum je Vergabeweise (Mittel über die Folgen, Fehlerbalken = Standardfehler); die eingestellte Weise ist hervorgehoben."""
    labels = [C.ASSIGN_LABELS[a] for a in C.ASSIGNS]
    fig = go.Figure(go.Bar(x=labels, y=[100 * stats[a].share for a in C.ASSIGNS], error_y=dict(type="data", array=[100 * stats[a].share_se for a in C.ASSIGNS]),
                           marker_color=[C.COLOR_GOOD if a == current else C.COLOR_NEUTRAL for a in C.ASSIGNS], text=[f"{100 * stats[a].share:.1f}".replace(".", ",") + " %" for a in C.ASSIGNS],
                           textposition="outside", hovertemplate="%{x}: %{y:.1f} %<extra></extra>"))
    fig.update_yaxes(title_text="Anteil am Offline-Optimum (%)", range=[0, 110])
    fig.update_xaxes(type="category")
    return _base(fig, legend=False)


def build_free_row(rows):
    """Freie Wahl in einer Reihe: besetzte Plätze (exakt) gegen die Obergrenze je Reihenlänge."""
    xs = [str(r["n"]) for r in rows]
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Obergrenze (jeder zweite Platz)", x=xs, y=[100.0] * len(rows), marker_color=C.COLOR_GRAY))
    fig.add_trace(go.Bar(name="freie Wahl (exakt)", x=xs, y=[100 * r["exact"] / r["capacity"] for r in rows], marker_color=C.COLOR_BAD,
                         text=[f"{100 * r['exact'] / r['capacity']:.1f}".replace(".", ",") + " %" for r in rows], textposition="outside"))
    fig.update_layout(barmode="group")
    fig.update_xaxes(type="category", title_text="Plätze je Reihe")
    fig.update_yaxes(title_text="Anteil der Obergrenze (%)", range=[0, 112])
    return _base(fig)


def build_groups(rows, rule):
    """Kapazität bei gleich großen Gruppen: Personen je Gruppengröße gegen Einzelne."""
    xs = [str(r["g"]) for r in rows]
    colors = [C.COLOR_NEUTRAL] + [C.COLOR_GOOD if r["persons"] > rows[0]["persons"] else C.COLOR_BAD if r["persons"] < rows[0]["persons"] else C.COLOR_GRAY for r in rows[1:]]
    fig = go.Figure(go.Bar(x=xs, y=[100 * r["share"] for r in rows], marker_color=colors, text=[f"{100 * r['share']:.0f} %" for r in rows], textposition="outside"))
    fig.add_hline(y=100 * rows[0]["share"], line=dict(color=C.COLOR_NEUTRAL, dash="dot"))
    fig.update_xaxes(type="category", title_text="Gruppengröße (alle gleich)")
    fig.update_yaxes(title_text=f"Besetzte Plätze (%), Regel {rule}", range=[0, 105])
    return _base(fig, legend=False)
