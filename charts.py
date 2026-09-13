"""Figures du tableau de bord — chaque fonction rend une seule idée.

Séparé de app.py pour rester testable et rendu hors de Streamlit
(cf. scripts/render_figures.py).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

import loaders as L
from theme import DIV_COLD, DIV_SCALE, DIV_WARM, GRID, INK_MUTED, INK_SOFT, SERIES, annotate, style

MOIS = ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin", "Juil", "Août", "Sep", "Oct", "Nov", "Déc"]


# ==========================================================================
#  Indicateurs de transition
# ==========================================================================
def fig_ges_secteurs() -> go.Figure:
    d = L.ges_par_secteur()
    total = L.ges_total()
    ref = float(total.loc[total["annee"] == 1990, "valeur"].iloc[0])

    fig = go.Figure()
    for i, secteur in enumerate(L.GHG_SECTEURS.values()):
        s = d[d["secteur"] == secteur]
        fig.add_trace(
            go.Scatter(
                x=s["annee"], y=s["valeur"], name=secteur, mode="lines",
                stackgroup="ges", line=dict(width=1.5, color="#fcfcfb"),
                fillcolor=SERIES[i], hovertemplate="%{y:.1f} Mt<extra></extra>",
            )
        )

    # trajectoire légale : repères à atteindre, reliés depuis la dernière année observée
    derniere = int(total["annee"].max())
    y_der = float(total.loc[total["annee"] == derniere, "valeur"].iloc[0])
    xs = [derniere] + [a for a, _, _ in L.OBJECTIFS if a > derniere]
    ys = [y_der] + [ref * (1 - r) for a, r, _ in L.OBJECTIFS if a > derniere]
    fig.add_trace(
        go.Scatter(
            x=xs, y=ys, name="Trajectoire légale", mode="lines+markers",
            line=dict(color=INK_MUTED, width=2, dash="dot"),
            marker=dict(size=9, color=INK_SOFT, symbol="diamond"),
            hovertemplate="objectif : %{y:.1f} Mt<extra></extra>",
        )
    )
    for annee, part, libelle in L.OBJECTIFS:
        if annee > derniere:
            annotate(fig, annee, ref * (1 - part), f"  {annee} · {libelle.split(' (')[0]}", xanchor="right", yanchor="bottom", xshift=0)

    style(fig, height=430)
    fig.update_layout(title="Émissions de gaz à effet de serre par secteur (millions de tonnes CO₂-éq.)")
    fig.update_xaxes(range=[1990, 2052])
    fig.update_yaxes(rangemode="tozero", ticksuffix=" Mt")
    return fig


def fig_ges_index() -> go.Figure:
    d = L.ges_par_secteur()
    base = d[d["annee"] == 1990].set_index("secteur")["valeur"]
    fig = go.Figure()
    for i, secteur in enumerate(L.GHG_SECTEURS.values()):
        s = d[d["secteur"] == secteur].sort_values("annee")
        y = s["valeur"] / base[secteur] * 100
        fig.add_trace(
            go.Scatter(x=s["annee"], y=y, name=secteur, mode="lines",
                       line=dict(width=2, color=SERIES[i]),
                       hovertemplate="%{y:.0f}<extra></extra>")
        )
        annotate(fig, s["annee"].iloc[-1], y.iloc[-1], f"{y.iloc[-1]:.0f}", SERIES[i])
    fig.add_hline(y=100, line=dict(color=GRID, width=1))
    style(fig, height=380)
    fig.update_layout(title="Chaque secteur rapporté à son niveau de 1990 (indice 100 = 1990)")
    fig.update_xaxes(range=[1990, int(d["annee"].max()) + 6])
    return fig


def fig_parts_carburant(d: pd.DataFrame, titre: str) -> go.Figure:
    fig = go.Figure()
    for i, groupe in enumerate(L.ORDRE_CARBURANTS):
        s = d[d["groupe"] == groupe]
        if s["valeur"].sum() == 0:
            continue
        fig.add_trace(
            go.Scatter(
                x=s["annee"], y=s["part"] * 100, name=groupe, mode="lines",
                stackgroup="p", line=dict(width=1.5, color="#fcfcfb"),
                fillcolor=SERIES[i], hovertemplate="%{y:.1f} %<extra></extra>",
            )
        )
    style(fig, height=380)
    fig.update_layout(title=titre, legend=dict(traceorder="normal"))
    fig.update_yaxes(range=[0, 100], ticksuffix=" %")
    return fig


def fig_electrifiees() -> go.Figure:
    """Part électrique + hybride rechargeable : flux (ventes) contre stock (parc)."""
    fig = go.Figure()
    for i, (d, nom) in enumerate(
        [(L.voitures_neuves(), "Voitures neuves vendues"), (L.voitures_parc(), "Parc en circulation")]
    ):
        s = (
            d[d["groupe"].isin(["Électrique", "Hybride rechargeable"])]
            .groupby("annee", as_index=False)["part"].sum()
        )
        fig.add_trace(
            go.Scatter(x=s["annee"], y=s["part"] * 100, name=nom, mode="lines+markers",
                       line=dict(width=2, color=SERIES[i]), marker=dict(size=8, color=SERIES[i]),
                       hovertemplate="%{y:.1f} %<extra></extra>")
        )
        annotate(fig, s["annee"].iloc[-1], s["part"].iloc[-1] * 100, f"{s['part'].iloc[-1]*100:.1f} %", SERIES[i])
    style(fig, height=340)
    fig.update_layout(title="Voitures rechargeables : la vente précède le parc de plusieurs années")
    fig.update_yaxes(rangemode="tozero", ticksuffix=" %")
    fig.update_xaxes(range=[2010, int(L.voitures_neuves()["annee"].max()) + 3])
    return fig


def fig_ajouts_renouvelables(derniere_complete: int) -> go.Figure:
    d = L.installations()
    technos = ["Photovoltaïque", "Éolien", "Biomasse", "Hydraulique"]
    d = d[(d["technologie"].isin(technos)) & (d["annee"] >= 1990) & (d["annee"] <= derniere_complete)]
    g = d.groupby(["annee", "technologie"], as_index=False)["puissance_mw"].sum()
    fig = go.Figure()
    for i, t in enumerate(technos):
        s = g[g["technologie"] == t]
        fig.add_trace(
            go.Bar(x=s["annee"], y=s["puissance_mw"], name=t, marker=dict(color=SERIES[i], line=dict(width=0)),
                   hovertemplate="%{y:.0f} MW<extra></extra>")
        )
    style(fig, height=380)
    fig.update_layout(barmode="stack", bargap=0.25, title="Puissance renouvelable mise en service chaque année (MW)")
    fig.update_yaxes(ticksuffix=" MW")
    return fig


def fig_pv_cumule(derniere_complete: int) -> go.Figure:
    pivot = L.capacite_cumulee("Photovoltaïque")
    s = pivot.sum(axis=1)
    s = s[(s.index >= 1990) & (s.index <= derniere_complete)] / 1000  # MW → GW
    fig = go.Figure(
        go.Scatter(x=s.index, y=s.values, mode="lines", name="Photovoltaïque",
                   line=dict(width=2, color=SERIES[0]), fill="tozeroy",
                   fillcolor="rgba(42,120,214,0.12)", hovertemplate="%{y:.2f} GW<extra></extra>")
    )
    annotate(fig, s.index[-1], s.values[-1], f"{s.values[-1]:.1f} GW", SERIES[0])
    style(fig, height=380, legend=False)
    fig.update_layout(title="Parc photovoltaïque installé, cumulé (GW)")
    fig.update_yaxes(rangemode="tozero", ticksuffix=" GW")
    fig.update_xaxes(range=[1990, derniere_complete + 4])
    return fig


def fig_pv_cantons(annee: int) -> go.Figure:
    pivot = L.capacite_cumulee("Photovoltaïque")
    an = min(annee, int(pivot.index.max()))
    cum = pivot.loc[an]
    pop = L.population()
    pop = pop[pop["annee"] == min(an, int(pop["annee"].max()))].set_index("canton")["population"]
    d = pd.DataFrame({"canton": cum.index, "mw": cum.values})
    d["habitants"] = d["canton"].map(L.CANTONS).map(pop)
    d = d.dropna(subset=["habitants"])
    d["w_par_hab"] = d["mw"] * 1e6 / d["habitants"]
    d = d.sort_values("w_par_hab")
    moyenne = d["mw"].sum() * 1e6 / d["habitants"].sum()

    fig = go.Figure(
        go.Bar(
            x=d["w_par_hab"], y=d["canton"], orientation="h",
            marker=dict(color=SERIES[0], line=dict(width=0)),
            text=[f"{v:.0f}" for v in d["w_par_hab"]], textposition="outside",
            textfont=dict(size=11, color=INK_MUTED),
            customdata=np.stack([d["mw"]], axis=-1),
            hovertemplate="%{y} · %{x:.0f} W/hab · %{customdata[0]:.0f} MW<extra></extra>",
        )
    )
    fig.add_vline(x=moyenne, line=dict(color=INK_MUTED, width=1, dash="dot"))
    fig.add_annotation(x=moyenne, y=1.02, yref="paper", text=f"Suisse {moyenne:.0f} W/hab",
                       showarrow=False, xanchor="left", font=dict(size=11, color=INK_MUTED))
    style(fig, height=620, legend=False, unified=False)
    fig.update_layout(title=f"Photovoltaïque installé par habitant, fin {an}")
    fig.update_xaxes(showgrid=True, gridcolor=GRID, ticksuffix=" W")
    fig.update_yaxes(showgrid=False)
    return fig


# ==========================================================================
#  Indicateurs d'impact
# ==========================================================================
def fig_anomalie(serie: pd.DataFrame, titre: str) -> go.Figure:
    couleurs = [DIV_WARM if v > 0 else DIV_COLD for v in serie["valeur"]]
    lissee = serie["valeur"].rolling(10, center=True, min_periods=8).mean()
    fig = go.Figure()
    fig.add_trace(
        go.Bar(x=serie["annee"], y=serie["valeur"], name="Écart annuel",
               marker=dict(color=couleurs, line=dict(width=0)),
               hovertemplate="%{y:+.2f} °C<extra></extra>")
    )
    fig.add_trace(
        go.Scatter(x=serie["annee"], y=lissee, name="Moyenne sur 10 ans", mode="lines",
                   line=dict(width=2.5, color="#0b0b0b"), hovertemplate="%{y:+.2f} °C<extra></extra>")
    )
    fig.add_hline(y=0, line=dict(color=INK_MUTED, width=1))
    style(fig, height=420)
    fig.update_layout(title=titre, bargap=0.15)
    fig.update_yaxes(ticksuffix=" °C", tickformat="+.1f")
    return fig


def fig_heatmap(station: str) -> go.Figure:
    d = L.nbcn_mensuel()
    d = d[(d["station"] == station) & (d["annee"] >= 1900)].dropna(subset=["temp_anomalie"])
    pivot = d.pivot_table(index="mois", columns="annee", values="temp_anomalie")
    lim = float(np.nanpercentile(np.abs(pivot.values), 98))
    fig = go.Figure(
        go.Heatmap(
            z=pivot.values, x=pivot.columns, y=[MOIS[m - 1] for m in pivot.index],
            colorscale=DIV_SCALE, zmid=0, zmin=-lim, zmax=lim,
            colorbar=dict(title=dict(text="°C", side="top"), thickness=10, len=0.8, outlinewidth=0,
                          tickfont=dict(size=11, color=INK_MUTED)),
            hovertemplate="%{y} %{x} · %{z:+.1f} °C<extra></extra>",
        )
    )
    style(fig, height=360, legend=False, unified=False)
    fig.update_layout(title="Écart mensuel à la norme 1991-2020")
    fig.update_yaxes(autorange="reversed", showgrid=False)
    return fig


def fig_extremes(station_annuel: pd.DataFrame, params: pd.DataFrame) -> go.Figure:
    indices = ["jours_ete", "jours_chaleur", "nuits_tropicales", "jours_gel", "jours_hiver"]
    lib = params.set_index("colonne")["libelle"]
    periodes = [(1961, 1990, "1961-1990"), (1996, 2025, "1996-2025")]
    fig = go.Figure()
    for i, (a, b, nom) in enumerate(periodes):
        sub = station_annuel[station_annuel["annee"].between(a, b)]
        vals = [sub[c].mean() for c in indices]
        fig.add_trace(
            go.Bar(x=[lib[c] for c in indices], y=vals, name=nom,
                   marker=dict(color=SERIES[i], line=dict(width=0)),
                   text=[f"{v:.0f}" for v in vals], textposition="outside",
                   textfont=dict(size=11, color=INK_MUTED),
                   hovertemplate="%{y:.1f} jours/an<extra></extra>")
        )
    style(fig, height=380, unified=False)
    fig.update_layout(barmode="group", bargap=0.3, bargroupgap=0.06,
                      title="Nombre de jours par an, moyenne sur 30 ans")
    fig.update_yaxes(ticksuffix=" j", rangemode="tozero")
    return fig


def fig_indice_annuel(station_annuel: pd.DataFrame, colonne: str, libelle: str) -> go.Figure:
    s = station_annuel.dropna(subset=[colonne]).sort_values("annee")
    lissee = s[colonne].rolling(10, center=True, min_periods=8).mean()
    fig = go.Figure()
    fig.add_trace(
        go.Bar(x=s["annee"], y=s[colonne], name=libelle,
               marker=dict(color="#9ec5f4", line=dict(width=0)),
               hovertemplate="%{y:.0f}<extra></extra>")
    )
    fig.add_trace(
        go.Scatter(x=s["annee"], y=lissee, name="Moyenne sur 10 ans", mode="lines",
                   line=dict(width=2.5, color=SERIES[0]), hovertemplate="%{y:.1f}<extra></extra>")
    )
    style(fig, height=360)
    fig.update_layout(title=libelle, bargap=0.15)
    fig.update_yaxes(rangemode="tozero")
    return fig


def fig_glaciers(choix: list[str]) -> go.Figure:
    d = L.glaciers()
    fig = go.Figure()
    for i, nom in enumerate(choix[:8]):
        s = d[d["glacier"] == nom].sort_values("annee").set_index("annee")
        # réindexation sur toutes les années : la courbe se coupe là où rien n'a été mesuré
        plein = s["bilan_cumule"].reindex(range(int(s.index.min()), int(s.index.max()) + 1)) / 1000
        fig.add_trace(
            go.Scatter(x=plein.index, y=plein.values, name=nom, mode="lines", connectgaps=False,
                       line=dict(width=2, color=SERIES[i]),
                       hovertemplate="%{y:.1f} m éq. eau<extra></extra>")
        )
        annotate(fig, plein.index[-1], plein.iloc[-1], f"{plein.iloc[-1]:.0f} m", SERIES[i])
    fig.add_hline(y=0, line=dict(color=INK_MUTED, width=1))
    style(fig, height=420)
    fig.update_layout(title="Bilan de masse cumulé (mètres d'équivalent en eau)")
    fig.update_yaxes(ticksuffix=" m")
    fig.update_xaxes(range=[1915, int(d["annee"].max()) + 10])
    return fig


def fig_glaciers_annuel() -> go.Figure:
    d = L.glaciers()
    g = d.groupby("annee").agg(median=("bilan_annuel", "median"), n=("bilan_annuel", "size")).reset_index()
    g = g[g["n"] >= 5]
    couleurs = [DIV_COLD if v > 0 else DIV_WARM for v in g["median"]]
    fig = go.Figure(
        go.Bar(x=g["annee"], y=g["median"] / 1000, marker=dict(color=couleurs, line=dict(width=0)),
               hovertemplate="%{y:+.2f} m éq. eau<extra></extra>", name="Bilan annuel médian")
    )
    fig.add_hline(y=0, line=dict(color=INK_MUTED, width=1))
    style(fig, height=340, legend=False)
    fig.update_layout(title="Bilan annuel médian des glaciers suivis (m éq. eau par an)", bargap=0.15)
    fig.update_yaxes(ticksuffix=" m", tickformat="+.1f")
    return fig


def fig_pheno_serie(parametre: str, libelle: str) -> go.Figure:
    d = L.pheno_national().query("parametre == @parametre").sort_values("annee")
    # même fenêtre que le classement des phénophases, pour que les deux chiffres concordent
    tendance = d[d["annee"] >= 1961]
    pente = L.pente_par_decennie(tendance["annee"], tendance["jour"])
    lissee = d["jour"].rolling(10, center=True, min_periods=8).mean()
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(x=d["annee"], y=d["jour"], name="Médiane suisse", mode="markers",
                   marker=dict(size=8, color="#9ec5f4", line=dict(width=1, color="#fcfcfb")),
                   hovertemplate="jour %{y:.0f}<extra></extra>")
    )
    fig.add_trace(
        go.Scatter(x=d["annee"], y=lissee, name="Moyenne sur 10 ans", mode="lines",
                   line=dict(width=2.5, color=SERIES[0]), hovertemplate="jour %{y:.0f}<extra></extra>")
    )
    style(fig, height=380)
    signe = "plus tôt" if pente < 0 else "plus tard"
    fig.update_layout(title=f"{libelle} — {abs(pente):.1f} jour(s) {signe} par décennie depuis 1961")
    fig.update_yaxes(title="jour de l'année")
    return fig


def fig_pheno_pentes() -> go.Figure:
    d = L.pheno_national()
    lignes = []
    for (p, lib, saison), s in d.groupby(["parametre", "libelle", "saison"]):
        s = s[s["annee"] >= 1961]
        lignes.append({"libelle": lib, "saison": saison, "pente": L.pente_par_decennie(s["annee"], s["jour"])})
    t = pd.DataFrame(lignes).dropna().sort_values("pente")
    couleurs = [DIV_COLD if v < 0 else DIV_WARM for v in t["pente"]]
    fig = go.Figure(
        go.Bar(x=t["pente"], y=t["libelle"], orientation="h",
               marker=dict(color=couleurs, line=dict(width=0)),
               text=[f"{v:+.1f}" for v in t["pente"]], textposition="outside",
               textfont=dict(size=11, color=INK_MUTED),
               customdata=t[["saison"]],
               hovertemplate="%{y} (%{customdata[0]}) · %{x:+.1f} j/décennie<extra></extra>")
    )
    fig.add_vline(x=0, line=dict(color=INK_MUTED, width=1))
    style(fig, height=460, legend=False, unified=False)
    fig.update_layout(title="Décalage du calendrier du vivant depuis 1961 (jours par décennie)")
    fig.update_xaxes(title="← plus tôt dans l'année · plus tard dans l'année →")
    fig.update_xaxes(showgrid=True, gridcolor=GRID, ticksuffix=" j")
    fig.update_yaxes(showgrid=False)
    return fig
