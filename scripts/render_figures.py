#!/usr/bin/env python3
"""Rend chaque figure en PNG — contrôle visuel rapide, hors Streamlit."""
import sys, types
from pathlib import Path

_st = types.ModuleType("streamlit")
def _cache(*a, **k):
    if a and callable(a[0]):
        return a[0]
    return lambda f: f
_st.cache_data = _cache
sys.modules["streamlit"] = _st
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import charts as C          # noqa: E402
import loaders as L         # noqa: E402

out = Path(sys.argv[1] if len(sys.argv) > 1 else "figures")
out.mkdir(parents=True, exist_ok=True)

stations, annuel, params = L.nbcn()
derniere = int(L.installations()["annee"].max()) - 1
bale = annuel[annuel["station"] == "BAS"]

figures = {
    "ges_secteurs": C.fig_ges_secteurs(),
    "ges_index": C.fig_ges_index(),
    "carburants_neuves": C.fig_parts_carburant(L.voitures_neuves(), "Voitures neuves, par motorisation"),
    "carburants_parc": C.fig_parts_carburant(L.voitures_parc(), "Parc, par motorisation"),
    "electrifiees": C.fig_electrifiees(),
    "renouvelables": C.fig_ajouts_renouvelables(derniere),
    "pv_cumule": C.fig_pv_cumule(derniere),
    "pv_cantons": C.fig_pv_cantons(derniere),
    "anomalie": C.fig_anomalie(L.serie_nationale("temp_anomalie"), "Écart annuel à la norme 1991-2020, moyenne suisse"),
    "heatmap": C.fig_heatmap("BAS"),
    "extremes": C.fig_extremes(bale, params),
    "indice_annuel": C.fig_indice_annuel(bale, "jours_chaleur", "Jours de chaleur (Tmax ≥ 30 °C)"),
    "glaciers": C.fig_glaciers(["Grosser Aletschgletscher", "Silvrettagletscher", "Griesgletscher", "Allalingletscher"]),
    "glaciers_annuel": C.fig_glaciers_annuel(),
    "pheno_serie": C.fig_pheno_serie("mprua65d", "Cerisier — pleine floraison"),
    "pheno_pentes": C.fig_pheno_pentes(),
}
for nom, fig in figures.items():
    fig.write_image(out / f"{nom}.png", width=1000, height=fig.layout.height or 400, scale=2)
    print("→", nom)
