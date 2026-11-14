# Saal mit Abstand: Wer vergibt die Plätze? – Streamlit-Demo

<!-- TODO nach dem Deploy: direkt hierher den Live-Link setzen (Leerzeile davor und danach):
**[→ Demo live ausprobieren](https://sebastianhanisch-saal-abstand-demo.streamlit.app/)** -->

Fall-Demo für die Website „Sebastian Hanisch – Operations Research und Machine Learning“ (Themenseite „Sitzplätze optimieren“). Ein **Saal** (Kino, Hörsaal, Theater) hat eine **Abstandsregel**: zwischen fremden Gruppen bleibt ein Platz frei.
Gruppen von einer bis sechs Personen kommen nacheinander und werden sofort gesetzt oder abgewiesen. Die Demo vergleicht fünf **Vergabeweisen** auf denselben Anfragefolgen: ein **Platzanweiser** (links, engste Lücke), **Gäste, die frei wählen**,
die **Mitte** nehmen oder **Abstand suchen**. Als Maßstab dient das **exakte Offline-Optimum**, das die ganze Folge kennt. Dazu kommen drei **Abstandsregeln** (seitlich, Schachbrett, streng), ein **Saal mit Bogen** und eine **feste Sperrmatrix**.
Alle Annahmen (Gruppenmischungen, Gästeverhalten, Regeln) sind Regler oder gesetzt, nicht aus Daten.

## Warum dieses Problem

Wer einen Saal mit Abstandsregel betreibt, kann die Plätze **zuweisen** oder die Gäste **frei wählen** lassen. Die Obergrenze (jeder zweite Platz, Bin-Packing in der Reihe) ist bekannt. Die Demo fragt die Entscheidung dahinter:
**Wer soll die Plätze vergeben, und was kostet es, wenn die Gäste wählen?** Und: wie wählen sie, wenn sie frei wählen, die Mitte nehmen oder Abstand suchen?

## Modell

- **Saal:** Raster aus 2 bis 14 Reihen mit 6 bis 20 Plätzen. Reihe 1 liegt vorn. **Saal mit Bogen:** die Reihen werden nach hinten länger (von etwa 60 % vorn bis etwa 140 % hinten der mittleren Länge, mindestens 6 und höchstens 28 Plätze), nur bei der Regel „nur seitlich“.
- **Abstandsregel:** Zellen verschiedener Gruppen dürfen nicht benachbart sein. **ROW** („nur seitlich“): seitlich benachbart, also eine Lücke in der Reihe. **MANH** („Schachbrett“): auch vorn und hinten (vier Nachbarn). **KING** („streng“): auch diagonal (acht Nachbarn).
  Eine Gruppe sitzt waagerecht zusammenhängend in einer Reihe; keine Gänge, keine Ränder.
- **Gäste:** Gruppen mit 1 bis 6 Personen nach einer von vier Mischungen (gesetzt; im Code `einzel`, `paare`, `familie`, `gleich`): nur Einzelne (Ø 1 Person), viele Paare (Anteile 0,25 / 0,50 / 0,10 / 0,15 für 1 bis 4 Personen; Ø 2,15), Familien (0,10 / 0,25 / 0,20 / 0,30 / 0,10 / 0,05 für 1 bis 6; Ø 3,2),
  gleichmäßig 1 bis 6 (Ø 3,5). **Last** = angefragte Personen durch Plätze; die Folge endet, sobald die angefragten Personen die Last erreichen (Last 1,0 heißt: angefragt wird ein Gast je Platz; wegen der Lücken lassen sich nicht alle setzen).
- **Vergabeweisen:** **Platzanweiser links** (First-Fit: erste zulässige Reihe, links), **Platzanweiser engste Lücke** (Best-Fit: die engste freie Lücke, in die die Gruppe passt), **Gäste wählen frei** (gleichverteilt unter allen zulässigen Plätzen; Random Sequential Adsorption mit Gruppen),
  **Gäste wählen die Mitte** (kleinster Abstand zur Mittelreihe, dann zur Reihenmitte), **Gäste suchen Abstand** (der Platz, dessen nächster besetzter Platz in allen Reihen, euklidisch, am weitesten entfernt ist). Zwei weitere Definitionen von „Abstand suchen“ stehen im Experiment 1:
  nur Plätze derselben Reihe zählen, ohne und mit der Wand. Bei Gleichstand gilt die erste Reihe, links. „Gäste suchen Abstand“, „die Mitte“ und „frei“ sind **gesetzte Verhaltensmodelle**, keine Beobachtung echter Gäste.
- **Offline-Optimum:** die größte Personenzahl, wenn jemand die ganze Folge kennt und frei auswählt, welche Gruppen er setzt (ganzzahliges Programm, siehe Methodik). Es ist ein **Maßstab, kein erreichbarer Wert**; bei Überangebot misst die Lücke zum Optimum auch, **wen** man bedient.
- **Feste Sperrmatrix (Experiment 6):** der Betreiber legt vorab fest, welche Reihe in welche Gruppenplätze zerfällt (nach den Anteilen der Mischung, nicht optimiert) und weist jede Gruppe dem kleinsten freien passenden Platz zu; nur bei der Regel „nur seitlich“ und gleich langen Reihen.

## Methodik

| Verfahren | Wie es arbeitet | Grenze |
|---|---|---|
| **Vergabe-Simulation** | jede Anfragefolge wird je Vergabeweise gespielt (`sab_rules.py`, `sab_hall.py`) | Zufallsfolgen, Standardfehler wird angegeben |
| **Offline-Optimum** | ganzzahliges Programm mit einer 0/1-Variablen je waagerechter Platzierung, Bedarf je Gruppengröße, seitlich je Zelle eine virtuelle Strecke (Gruppe plus Lücke; Intervallgraph, exakt), vorn/hinten und diagonal je Zellpaar `o_c + o_c' ≤ 1` (`sab_offline.py`, HiGHS über `scipy.optimize.milp`) | Zeitgrenze: wird sie erreicht, steht „nicht bewiesen“, nie „optimal“ |
| **Freie Wahl in einer Reihe** | exakte Rekursion `E(n) = 1/n · Σ (1 + E(i − 2) + E(n − i − 1))` (`sab_exact.py`) | nur Einzelgäste, eine Reihe; die Simulation prüft sie |
| **Gleiche Gruppen in einer Reihe** | Formel `g · ⌊(n + 1) / (g + 1)⌋` | nur Regel „nur seitlich“ |

Alle Zufallsfolgen kommen aus einem eigenen SplitMix64 mit festem Zufalls-Seed; die Live-Rechnung der App nutzt 8 Anfragefolgen (Zufalls-Seeds Sitzungs-Seed · 1000 + k), die Messreihen unten 100 Folgen je Zelle (Zufalls-Seeds 100000 bis 100099 mal 1000; das Raster: 100 Folgen bei Einzelnen, 40 sonst).

## Befunde (gemessen, keine Behauptungen)

Alle Zahlen stammen aus `data/sab_results.json` (`tools/make_results.py`) und werden in `tests/test_claims.py` gezählt. Wo nichts anderes steht: Saal 8 × 16 mit gleich langen Reihen, Regel „nur seitlich“, Anteil am Offline-Optimum in Prozent der Personen, Mittel über 100 Folgen; das Offline-Optimum war in jeder Zelle der Experimente 1 bis 5 bewiesen (100 von 100 beziehungsweise 40 von 40 Folgen).
Die Mischungen heißen „viele Paare / Familien / gleichmäßig 1 bis 6“.

| Frage | Befund | Test |
|---|---|---|
| Wer soll die Plätze vergeben? | Bei Last 1,0 erreicht der **Platzanweiser links 92,4 / 93,5 / 92,9 %**; **Gäste wählen frei 81,5 / 80,1 / 78,2 %**, die **Mitte 89,0 / 88,3 / 86,3 %**, **Abstand suchen 85,9 / 88,3 / 87,4 %**. In allen 12 Zellen mit Gruppen (zwei Säle, drei Mischungen, Last 0,7 und 1,0) liegt der Platzanweiser vor jeder Gästeweise (kleinster Vorsprung 1,3 Punkte), und freie Wahl ist die schlechteste der fünf Vergabeweisen. | `test_wer_vergibt_*` |
| Braucht ein Saal mit Last 0,7 (angefragt werden 70 % der Plätze) einen Platzanweiser? | Im Modell „Gäste wählen frei“ ja: bei Last 0,7 (angefragt werden 70 % der Plätze) verliert freie Wahl **11,5 bis 15,5 %** der Personen des Optimums, bei Last 1,0 **18,5 bis 21,8 %** (sechs Zellen je Last: zwei Säle, drei Mischungen). Der Platzanweiser verliert bei Last 0,7 **höchstens 0,7 %**, bei Last 1,0 **6,5 bis 7,7 %**. | `test_last_*` |
| Was kostet freie Wahl in einer Reihe? | Einzelne Gäste besetzen bei freier Wahl (exakte Rekursion) in einer Reihe mit 10 / 20 / 50 / 100 Plätzen **4,620 / 8,944 / 21,914 / 43,530** Plätze, das sind **92,4 / 89,4 / 87,7 / 87,1 %** der Obergrenze (jeder zweite Platz); die Simulation (20 000 Läufe) liegt bei 100 Plätzen bei 43,533 ± 0,010. Grenzwert (1 − e⁻²)/2 = 0,4323 der Plätze, also **86,5 %** der Obergrenze. Der Platzanweiser erreicht 100 %. | `test_freie_wahl_reihe_*` |
| Und im Raster? | Raster 10 × 16, Einzelne, freie Wahl (200 Läufe): **ROW 72,2 von 80 (90,2 %), MANH 60,6 von 80 (75,7 %), KING 33,5 von 40 (83,7 %)**; der Platzanweiser erreicht jeweils 100 %. Bei ROW sind es zehn unabhängige Reihen: 10 · E(16) = 72,14. | `test_freie_wahl_raster_*` |
| Was bringt „Abstand suchen“, und hängt das an der Definition? | Bei Last 1,0 und Paaren: Abstand zu allen Gästen **85,9 %**, nur in der Reihe **82,9 %**, nur in der Reihe mit Wand **76,0 %**; die Reihenfolge Alle > Reihe > Reihe mit Wand gilt in allen 12 Zellen mit Gruppen. Abstand zu allen Gästen liegt **in allen 12 Zellen über freier Wahl** (mindestens 4,4 Punkte). Bei lauter Einzelnen: 82,8 % gegen 90,4 % bei freier Wahl (Saal 8 × 16), im Saal mit Bogen 92,4 % gegen 87,4 %. Im Raster liegt „Abstand suchen“ bei MANH in Familien gleichauf mit freier Wahl (Last 1,0 / 1,5: +0,2 / 0,0 Punkte) und bei Paaren darunter (Last 1,0 / 1,5: −3,0 / −2,7). | `test_abstand_suchen_*` |
| Gleichen Best-Fit und First-Fit sich? | Bei der Regel „nur seitlich“ ja: in allen 16 Zellen des Saals (gleich lange Reihen und Bogen) unterscheiden sie sich um höchstens **0,04 Punkte**, im Raster bei ROW und KING um höchstens 0,07. Beim Schachbrett (MANH) liegt Best-Fit bei Paaren **1,8 Punkte** vor First-Fit und bei Familien 0,0 bis 0,2 Punkte dahinter. | `test_best_fit_*` |
| Gilt die Rangfolge auch im Raster? | Raster 10 × 16, Paare und Familien, Last 1,0 und 1,5 (40 Folgen): Platzanweiser links **86,8 bis 93,5 %**, freie Wahl **79,6 bis 81,5 % (ROW), 76,8 bis 80,8 % (MANH), 73,2 bis 75,9 % (KING)**; der Platzanweiser liegt in allen 12 Zellen vor freier Wahl. **Beim Schachbrett (MANH) liegt die Mitte in allen vier Zellen vor dem Platzanweiser links** (bei Paaren um 3,7, bei Familien um 1,8 und 2,2 Punkte; die Familien-Unterschiede sind knapp, etwa drei Standardfehler, und beide Lasten nutzen dieselben Zufalls-Seeds), bei ROW und KING dahinter (3,1 bis 5,4 Punkte). | `test_raster_*` |
| Helfen Gruppen? | Raster 10 × 16, lauter gleich große Gruppen (exakt): ROW schafft mit Einzelnen **80**, mit Gruppen zu 2 / 3 / 4 / 5 / 6 Personen **100 / 120 / 120 / 100 / 120** Personen; MANH nie mehr als die 80 der Einzelnen (**80 / 80 / 75 / 80 / 75 / 60** für Gruppen zu 1 bis 6); KING hebt **40 auf 60** (**40 / 50 / 60 / 60 / 50 / 60**). Bei ROW stimmt das mit der Formel überein. | `test_gruppen_*` |
| Lohnt eine feste Sperrmatrix? | Nicht in der einfachen Fassung nach den Anteilen der Mischung: sie liegt in allen sechs Zellen (drei Mischungen, Last 0,7 und 1,0) **3,2 bis 5,7 Punkte** hinter dem Platzanweiser (gleich lange Reihen). Eine auf die Verteilung optimierte Vorlage ist ein anderer Vergleich und nicht nachgebaut. | `test_sperrmatrix_*` |

### Befunde und Korrekturen gegenüber der Vormessung

- **Bei der Regel „nur seitlich“ und mit Gruppen ist „Gäste suchen Abstand“ nicht schlechter als freie Wahl, sondern besser** (in allen 12 Zellen mit Gruppen im Saal 8 × 16, mindestens 4,4 Punkte); bei lauter Einzelnen im Saal mit gleich langen Reihen und im Schachbrett-Raster mit Paaren ist es schlechter. Die Vormessung (Planungsordner, nicht in diesem Repo) verglich „Abstand suchen“ mit einer Vergleichsgröße, die als „freie Wahl“ beschriftet war, in Wirklichkeit aber eine zufällige Lücke wählte
  und linksbündig setzte; echte freie Wahl (gleichverteilt unter allen zulässigen Plätzen) steht dort nur in einer Raster-Messung. Hier ist freie Wahl gleichverteilt unter allen zulässigen Plätzen, und sie ist die schlechteste Vergabe. Ausnahmen: lauter Einzelne und das Schachbrett-Raster (Tabelle oben).
- **Best-Fit und First-Fit:** die Vormessung nannte höchstens 0,3 Punkte Unterschied bei ungleich langen Reihen (Bogen von 12 bis 26 Plätzen); hier sind es bei der Regel „nur seitlich“ höchstens 0,04 Punkte (Bogen von 10 bis 22 Plätzen, andere Zufalls-Seeds). Warum das so ist, wurde nicht gemessen; eine Erklärung (nicht belegt): bei linksbündiger Vergabe hat jede Reihe nur eine offene Lücke, und frühere Reihen sind früher gefüllt.
- **Last 0,7:** die Vormessung fand dort den Platzanweiser praktisch optimal (und das gilt weiter, höchstens 0,7 % Verlust); die Demo zeigt zusätzlich, dass freie Wahl schon bei Last 0,7 11,5 bis 15,5 % verliert.
- **Sperrmatrix:** im Saal mit Bogen (jede Reihe eine andere Länge, über 2000 Muster je Programm) wurde das ganzzahlige Programm der Vorlage in dieser Umsetzung (HiGHS ohne Zeitgrenze) in mehreren Minuten nicht gelöst; das Experiment gilt nur für gleich lange Reihen.
- **Neu gemessen:** alle Zahlen der Vormessung sind Erwartungen und wurden mit mehr Folgen und eigenem Zufallsgenerator neu gemessen; sie weichen bis auf „Abstand suchen mit Wand“ nur leicht ab (dort ist die Wand anders definiert: die Vormessung zählte sie als Nachbar ohne die Pflichtlücke, hier gilt der Abstand zur Wand wie zu einem besetzten Platz; Unterschied 5,7 und 6,0 Punkte bei Paaren).

## Ehrliche Grenzen

- **Gästeverhalten ist gesetzt:** „frei“, „Mitte“ und „Abstand suchen“ sind Modelle. Wie viel „Abstand suchen“ verliert, hängt an der Definition (Experiment 1: 76,0 bis 85,9 % bei Last 1,0 und Paaren); keine Messung echter Gäste.
- **Das Offline-Optimum** kennt die ganze Folge und wählt aus, welche Gruppen es setzt; es ist ein Maßstab und kein erreichbarer Online-Wert. Bei Überangebot (Last 1,0 und darüber) misst die Lücke auch, **wen** man bedient.
- **Raster:** keine Gänge, keine Ränder, keine Wegezeiten; Gruppen sitzen waagerecht zusammenhängend; Saal mit Bogen nur bei der Regel „nur seitlich“; höchstens 14 Reihen mit 20 Plätzen (im Saal mit Bogen als mittlere Länge).
- **Rechenzeit:** die Live-Rechnung löst je Folge ein ganzzahliges Programm. Im größten Saal kann das bei der Regel Schachbrett mit Familien einige zehn Sekunden dauern; die App zeigt die Rechenzeit, und bei Erreichen der Zeitgrenze (6 Sekunden je Folge) steht das Optimum als „nicht bewiesen“. Dann ist der Bezugswert dieser Folge nur eine untere Schranke des Optimums (die beste gefundene Lösung, mindestens die beste Online-Belegung), und der Anteil fällt eher zu hoch aus (höchstens 100 %).
- **Wenige Folgen live:** die Live-Rechnung mittelt 8 Folgen; die Messreihen mehr. Kleine Unterschiede (unter etwa einem Prozentpunkt) gehen im Standardfehler unter.
- **Sperrmatrix** nur einfach (nach den Anteilen der Mischung), nur gleich lange Reihen und nur Regel „nur seitlich“.

## Verifikation

- **Kern:** Mini-Instanzen von Hand (zwei Reihen mit sechs Plätzen und Gruppen von 3 und 3 unter den drei Regeln: 6, 6 und 3 Personen), Platzanweiser, Best-Fit, Mitte, Abstand suchen, freie Wahl bei gleichem und anderem Zufalls-Seed, Anfragefolge (Last, Mischung), Saal mit Bogen, SplitMix64.
- **Orakel (`tests/test_oracle_saal_abstand.py`):** das Offline-Optimum gegen vollständige Aufzählung aller Belegungen kleiner Säle (alle drei Regeln, Saal mit Bogen), die Reihenformel `g · ⌊(n + 1) / (g + 1)⌋` gegen Aufzählung, die Rekursion der freien Wahl gegen den Mittelwert über **alle Reihenfolgen**
  (n bis 8), gegen die Simulation und gegen den Grenzwert (1 − e⁻²)/2, First-Fit gegen eine naive Schleifenversion, alle Vergaben liefern gültige Belegungen (Prüfer in reinen Schleifen), online nie besser als offline.
  Die zweite Umsetzung stammt vom selben Autor, ist aber von den Kernen unabhängig geschrieben.
- **Zahlen:** `tests/test_claims.py` zählt jede Zahl der Befund-Tabelle über die ganze Messdatei und rechnet die Rekursion, die Gruppenkapazitäten (ILP) und die freie Wahl in einer Reihe neu.
- **Verdikte:** reine Funktionen in `sab_evaluation.py`, an handgesetzten Werten und für jedes Preset geprüft (`tests/test_verdicts.py`).
- **Presets, Layout, Oberfläche:** Vollständigkeit und Werte der Presets; Schnellstart oben in der Seitenleiste, fester Kopf, aktives Preset hervorgehoben, jede Regleränderung hebt die Markierung auf; AppTest; Footer; Laufzeit-Importe.
- **Testzahl:** 235 Tests (`pytest --collect-only -q tests`).

## Dateistruktur

| Datei | Zweck |
|---|---|
| `.github/workflows/tests.yml` | CI: Push, Pull Request, wöchentlicher Canary |
| `app.py` | Streamlit-App |
| `data/sab_results.json` | vorgerechnete Messreihen |
| `requirements-dev.txt` | Laufzeit plus pytest |
| `requirements.txt` | Laufzeit-Bibliotheken (ungepinnt) |
| `tools/make_results.py` | erzeugt `data/sab_results.json` mit festen Zufalls-Seeds |
| `sab_constants.py` | Regler-Grenzen, Mischungen, Farben, Presets |
| `sab_evaluation.py` | Live-Analyse, Verdikte (reine Funktionen), Zugriff auf die Messreihen |
| `sab_exact.py` | Rekursion der freien Wahl, Reihenformel |
| `sab_hall.py` | Saal als Raster, Abstandsregeln, Prüfer für Belegungen |
| `sab_layout.py` | Fester Kopf (Stylesheet) |
| `sab_offline.py` | Offline-Optimum (ganzzahliges Programm) |
| `sab_presets.py` | Permalink, Presets (Schnellstart in der Seitenleiste, aktives Preset hervorgehoben), Zufalls-Seed-Button |
| `sab_rng.py` | eigener Zufallsgenerator (SplitMix64) |
| `sab_rules.py` | die Vergabeweisen |
| `sab_scenario.py` | Parameter des Saals (nur Schlüsselwörter), Anfragefolge |
| `sab_template.py` | feste Sperrmatrix |
| `sab_visualization.py` | Plotly-Abbildungen (Achsen gesperrt) |
| `tests/` | Kern, Randfälle, Orakel, Zahlen, Verdikte, Presets, Layout, AppTest, Footer, Laufzeit-Importe |

## Bewusst nicht umgesetzt

- **Prüfungsraum (Maximin statt Maximum) und Färbung:** kein eigener Befund über `p-center-demo` und `graph-coloring-demo` hinaus.
- **Optimierte Vorlagen für die Sperrmatrix** (Blom, Pendavingh, Spieksma 2020): ein anderer Vergleich; hier nur die einfache Vorlage.
- **Buchungszeit, Teilstrecken, Annahmeoptimierung, Haushalte, die sich trennen lassen:** andere Modelle. Verwandt: `sitzplatz-demo` (dort wählt der Fahrgast die Tür, hier der Gast den Platz im Saal).
- **Kalibrierung auf einen echten Saal:** keine Daten eingelesen.

## Lokal ausführen

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt
streamlit run app.py
```

## Tests ausführen

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

Gebaut mit Streamlit, Plotly, NumPy und SciPy.

---

Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). Mehr zum Thema: [Sitzplätze optimieren](https://sebastianhanisch.net/sitzplaetze-optimieren.html).
