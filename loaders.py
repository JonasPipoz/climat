"""Chargement et préparation des jeux de données produits par scripts/build_data.py."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

DATA = Path(__file__).resolve().parent / "data"

# Secteurs de l'ordonnance sur le CO2 (identifiants de l'inventaire OFEV)
GHG_SECTEURS = {11: "Bâtiment", 12: "Transports", 13: "Industrie", 14: "Autres"}
GHG_TOTAL_ID = 1

# Objectifs inscrits dans la loi sur le CO2 et la loi sur le climat (réduction vs 1990)
OBJECTIFS = [
    (2020, 0.20, "−20 % (loi sur le CO₂ 2013-2020)"),
    (2030, 0.50, "−50 % (loi sur le CO₂ révisée)"),
    (2040, 0.75, "−75 % (loi sur le climat)"),
    (2050, 1.00, "zéro net (loi sur le climat)"),
]

CARBURANTS = {
    "Essence": "Essence",
    "Diesel": "Diesel",
    "Essence-électrique: hybride normal": "Hybride non rechargeable",
    "Diesel-électrique: hybride normal": "Hybride non rechargeable",
    "Essence-électrique: hybride rechargeable": "Hybride rechargeable",
    "Diesel-électrique: hybride rechargeable": "Hybride rechargeable",
    "Électrique": "Électrique",
}
ORDRE_CARBURANTS = [
    "Essence", "Diesel", "Hybride non rechargeable",
    "Hybride rechargeable", "Électrique", "Autre",
]

CANTONS = {
    "AG": "Aargau", "AI": "Appenzell Innerrhoden", "AR": "Appenzell Ausserrhoden",
    "BE": "Bern / Berne", "BL": "Basel-Landschaft", "BS": "Basel-Stadt",
    "FR": "Fribourg / Freiburg", "GE": "Genève", "GL": "Glarus",
    "GR": "Graubünden / Grigioni / Grischun", "JU": "Jura", "LU": "Luzern",
    "NE": "Neuchâtel", "NW": "Nidwalden", "OW": "Obwalden", "SG": "St. Gallen",
    "SH": "Schaffhausen", "SO": "Solothurn", "SZ": "Schwyz", "TG": "Thurgau",
    "TI": "Ticino", "UR": "Uri", "VD": "Vaud", "VS": "Valais / Wallis",
    "ZG": "Zug", "ZH": "Zürich",
}


@st.cache_data(show_spinner=False)
def _csv(name: str) -> pd.DataFrame:
    return pd.read_csv(DATA / name)


# --------------------------------------------------------------------- climat
@st.cache_data(show_spinner=False)
def nbcn() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    stations = _csv("nbcn_stations.csv")
    annuel = _csv("nbcn_annuel.csv").merge(stations[["station", "nom", "canton", "altitude"]], on="station")
    params = _csv("nbcn_parametres.csv")
    return stations, annuel, params


@st.cache_data(show_spinner=False)
def nbcn_mensuel() -> pd.DataFrame:
    return _csv("nbcn_mensuel.csv")


@st.cache_data(show_spinner=False)
def serie_nationale(colonne: str = "temp_anomalie") -> pd.DataFrame:
    """Moyenne suisse d'un indice, sur le socle de stations mesurant depuis 1864.

    Le socle est figé pour qu'une année ne change pas de sens quand une station
    apparaît ou disparaît ; on ne garde que les années couvertes par ≥ 80 % d'entre elles.
    """
    stations, annuel, _ = nbcn()
    socle = stations.loc[stations["depuis"] <= 1864, "station"]
    d = annuel[annuel["station"].isin(socle)].dropna(subset=[colonne])
    g = d.groupby("annee").agg(valeur=(colonne, "mean"), n=(colonne, "size")).reset_index()
    return g[g["n"] >= 0.8 * len(socle)].drop(columns="n")


@st.cache_data(show_spinner=False)
def glaciers() -> pd.DataFrame:
    return _csv("glaciers_bilan_masse.csv")


@st.cache_data(show_spinner=False)
def phenologie() -> tuple[pd.DataFrame, pd.DataFrame]:
    obs = _csv("pheno_observations.csv")
    params = _csv("pheno_parametres.csv")
    return obs, params


@st.cache_data(show_spinner=False)
def pheno_national() -> pd.DataFrame:
    """Médiane suisse du jour d'observation, par phénophase et par année."""
    obs, params = phenologie()
    g = (
        obs.groupby(["parametre", "annee"])
        .agg(jour=("jour_annee", "median"), stations=("jour_annee", "size"))
        .reset_index()
    )
    g = g[g["stations"] >= 10]  # années trop peu observées écartées
    return g.merge(params, on="parametre")


# ----------------------------------------------------------------- transition
@st.cache_data(show_spinner=False)
def ges() -> pd.DataFrame:
    d = _csv("ges_emissions.csv")
    return d[d["gaz_id"] == "test1"]  # tous les gaz, en équivalents CO₂


@st.cache_data(show_spinner=False)
def ges_par_secteur() -> pd.DataFrame:
    d = ges()
    d = d[d["secteur_id"].isin(GHG_SECTEURS)].copy()
    d["secteur"] = d["secteur_id"].map(GHG_SECTEURS)
    return d[["annee", "secteur", "valeur"]]


@st.cache_data(show_spinner=False)
def ges_total() -> pd.DataFrame:
    return ges().query("secteur_id == @GHG_TOTAL_ID")[["annee", "valeur"]].reset_index(drop=True)


@st.cache_data(show_spinner=False)
def ges_par_gaz() -> pd.DataFrame:
    d = _csv("ges_emissions.csv")
    d = d[(d["secteur_id"] == GHG_TOTAL_ID) & (d["gaz_id"] != "test1")]
    d = d[d["gaz_id"].isin(["pol9", "pol11", "pol12", "polgroup2"])]
    return d[["annee", "gaz", "valeur"]]


def _carburants(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["groupe"] = d["carburant"].map(CARBURANTS).fillna("Autre")
    d = d.groupby(["annee", "groupe"], as_index=False)["valeur"].sum()
    d["part"] = d["valeur"] / d.groupby("annee")["valeur"].transform("sum")
    d["groupe"] = pd.Categorical(d["groupe"], ORDRE_CARBURANTS, ordered=True)
    return d.sort_values(["annee", "groupe"])


@st.cache_data(show_spinner=False)
def voitures_neuves() -> pd.DataFrame:
    return _carburants(_csv("vehicules_nouvelles_immatriculations.csv"))


@st.cache_data(show_spinner=False)
def voitures_parc() -> pd.DataFrame:
    return _carburants(_csv("vehicules_parc.csv"))


@st.cache_data(show_spinner=False)
def installations() -> pd.DataFrame:
    return _csv("electricite_installations.csv")


@st.cache_data(show_spinner=False)
def population() -> pd.DataFrame:
    return _csv("population_cantons.csv")


@st.cache_data(show_spinner=False)
def capacite_cumulee(technologie: str) -> pd.DataFrame:
    """Puissance installée cumulée par canton et par année pour une technologie."""
    d = installations().query("technologie == @technologie")
    pivot = (
        d.pivot_table(index="annee", columns="canton", values="puissance_mw", aggfunc="sum")
        .reindex(range(d["annee"].min(), d["annee"].max() + 1))
        .fillna(0)
        .cumsum()
    )
    return pivot


def pente_par_decennie(x: pd.Series, y: pd.Series) -> float:
    """Tendance linéaire, exprimée par décennie (unité de y)."""
    if len(x) < 10:
        return float("nan")
    return float(np.polyfit(x.astype(float), y.astype(float), 1)[0] * 10)
