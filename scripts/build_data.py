#!/usr/bin/env python3
"""
Construit les jeux de données compacts du tableau de bord climat-Suisse.

Toutes les sources sont des données ouvertes officielles suisses :

  nbcn      MétéoSuisse / NBCN  — séries climatiques homogènes (1864→, Bâle 1755→)
  pheno     MétéoSuisse         — observations phénologiques (1951→)
  glamos    GLAMOS              — bilan de masse des glaciers suisses (1915→)
  epp       OFEN / Pronovo      — registre des installations de production d'électricité
  vehicles  OFS / STAT-TAB      — parc et nouvelles immatriculations par carburant
  population OFS / STAT-TAB     — population résidante par canton (dénominateur)
  ghg       OFEV / LINDAS       — inventaire des gaz à effet de serre (1990→)

Usage :
    python scripts/build_data.py                 # tout reconstruire
    python scripts/build_data.py --only nbcn,ghg # sous-ensemble
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import zipfile
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "climat-dashboard/1.0 (open data, non commercial)"})
TIMEOUT = 120


def get(url: str, **kw) -> requests.Response:
    r = SESSION.get(url, timeout=TIMEOUT, **kw)
    r.raise_for_status()
    return r


def log(msg: str) -> None:
    print(f"  {msg}", flush=True)


def save(df: pd.DataFrame, name: str) -> None:
    path = DATA / name
    df.to_csv(path, index=False)
    log(f"→ {name}  ({len(df):,} lignes, {path.stat().st_size/1024:.0f} Ko)")


# --------------------------------------------------------------------------
# 1. MétéoSuisse NBCN — séries climatiques homogènes
# --------------------------------------------------------------------------
NBCN_BASE = "https://data.geo.admin.ch/ch.meteoschweiz.ogd-nbcn"

# paramètre → (colonne de sortie, libellé, unité)
NBCN_YEAR_PARAMS = {
    "ths200y0": ("temp_moy", "Température moyenne annuelle", "°C"),
    "th9120yv": ("temp_anomalie", "Écart à la norme 1991-2020", "°C"),
    "ths2dyyx": ("temp_max_moy", "Moyenne des maxima journaliers", "°C"),
    "ths2dyyn": ("temp_min_moy", "Moyenne des minima journaliers", "°C"),
    "thl200yx": ("temp_max_abs", "Maximum annuel absolu", "°C"),
    "thl200yn": ("temp_min_abs", "Minimum annuel absolu", "°C"),
    "ths25xy0": ("jours_ete", "Jours d'été (Tmax ≥ 25 °C)", "jours"),
    "ths30xy0": ("jours_chaleur", "Jours de chaleur (Tmax ≥ 30 °C)", "jours"),
    "ths35xy0": ("jours_canicule", "Jours de forte chaleur (Tmax ≥ 35 °C)", "jours"),
    "ths20ny0": ("nuits_tropicales", "Nuits tropicales (Tmin ≥ 20 °C)", "jours"),
    "ths00ny0": ("jours_gel", "Jours de gel (Tmin < 0 °C)", "jours"),
    "ths00xy0": ("jours_hiver", "Jours d'hiver (Tmax < 0 °C)", "jours"),
    "rhs150y0": ("precip", "Précipitations annuelles", "mm"),
    "rh9120yv": ("precip_pct_norme", "Précipitations, % de la norme 1991-2020", "%"),
    "shs000y0": ("ensoleillement", "Durée d'ensoleillement", "min"),
    "sh9120yv": ("ensoleillement_pct_norme", "Ensoleillement, % de la norme 1991-2020", "%"),
}
NBCN_MONTH_PARAMS = {
    "ths200m0": "temp_moy",
    "th9120mv": "temp_anomalie",
    "rhs150m0": "precip",
}


def _read_meteoswiss_csv(url: str) -> pd.DataFrame:
    raw = get(url).content
    return pd.read_csv(io.BytesIO(raw), sep=";", encoding="latin-1", low_memory=False)


def build_nbcn() -> None:
    print("MétéoSuisse NBCN — séries climatiques homogènes")
    meta = _read_meteoswiss_csv(f"{NBCN_BASE}/ogd-nbcn_meta_stations.csv")
    meta = meta.rename(
        columns={
            "station_abbr": "station",
            "station_name": "nom",
            "station_canton": "canton",
            "station_height_masl": "altitude",
            "station_coordinates_wgs84_lat": "lat",
            "station_coordinates_wgs84_lon": "lon",
        }
    )[["station", "nom", "canton", "altitude", "lat", "lon", "station_data_since"]]
    meta["depuis"] = pd.to_datetime(meta["station_data_since"], format="%d.%m.%Y").dt.year
    meta = meta.drop(columns=["station_data_since"])
    save(meta, "nbcn_stations.csv")

    annual, monthly = [], []
    for abbr in meta["station"]:
        a = abbr.lower()
        try:
            dy = _read_meteoswiss_csv(f"{NBCN_BASE}/{a}/ogd-nbcn_{a}_y.csv")
            dm = _read_meteoswiss_csv(f"{NBCN_BASE}/{a}/ogd-nbcn_{a}_m.csv")
        except requests.HTTPError as exc:
            log(f"!! {abbr} ignorée ({exc})")
            continue

        keep = {k: v[0] for k, v in NBCN_YEAR_PARAMS.items() if k in dy.columns}
        dy["annee"] = pd.to_datetime(dy["reference_timestamp"], format="%d.%m.%Y %H:%M").dt.year
        dy = dy[["station_abbr", "annee", *keep]].rename(columns={"station_abbr": "station", **keep})
        annual.append(dy)

        keepm = {k: v for k, v in NBCN_MONTH_PARAMS.items() if k in dm.columns}
        ts = pd.to_datetime(dm["reference_timestamp"], format="%d.%m.%Y %H:%M")
        dm["annee"], dm["mois"] = ts.dt.year, ts.dt.month
        dm = dm[["station_abbr", "annee", "mois", *keepm]].rename(
            columns={"station_abbr": "station", **keepm}
        )
        monthly.append(dm)
        log(f"{abbr} ok")

    ann = pd.concat(annual, ignore_index=True)
    # l'ensoleillement est publié en minutes → heures, plus parlant
    if "ensoleillement" in ann:
        ann["ensoleillement"] = ann["ensoleillement"] / 60.0
    save(ann, "nbcn_annuel.csv")
    save(pd.concat(monthly, ignore_index=True), "nbcn_mensuel.csv")

    labels = pd.DataFrame(
        [{"colonne": c, "libelle": lb, "unite": u} for _, (c, lb, u) in NBCN_YEAR_PARAMS.items()]
    )
    labels.loc[labels["colonne"] == "ensoleillement", "unite"] = "h"
    save(labels, "nbcn_parametres.csv")


# --------------------------------------------------------------------------
# 2. MétéoSuisse — phénologie
# --------------------------------------------------------------------------
PHENO_BASE = "https://data.geo.admin.ch/ch.meteoschweiz.ogd-phenology"

# sous-ensemble lisible : printemps, été, automne
PHENO_PARAMS = {
    "mtusf65d": ("Tussilage — floraison", "printemps"),
    "manen65d": ("Anémone des bois — floraison", "printemps"),
    "mtaro65d": ("Pissenlit — floraison", "printemps"),
    "mprua65d": ("Cerisier — pleine floraison", "printemps"),
    "mmald65d": ("Pommier — pleine floraison", "printemps"),
    "mfags13d": ("Hêtre — déploiement des feuilles", "printemps"),
    "maesh13d": ("Marronnier — déploiement des feuilles", "printemps"),
    "mcora60d": ("Noisetier — début de floraison", "printemps"),
    "mvitv65d": ("Vigne — floraison", "été"),
    "mhayxhsd": ("Fenaison — début", "été"),
    "mvitv89d": ("Vigne — vendanges", "automne"),
    "mfags94d": ("Hêtre — coloration des feuilles", "automne"),
    "maesh94d": ("Marronnier — coloration des feuilles", "automne"),
    "mlard94d": ("Mélèze — coloration des aiguilles", "automne"),
}


def build_pheno() -> None:
    print("MétéoSuisse — observations phénologiques")
    meta = _read_meteoswiss_csv(f"{PHENO_BASE}/ogd-phenology_meta_stations.csv")
    meta = meta.rename(
        columns={
            "station_abbr": "station",
            "station_name": "nom",
            "station_canton": "canton",
            "station_height_masl": "altitude",
            "station_coordinates_wgs84_lat": "lat",
            "station_coordinates_wgs84_lon": "lon",
        }
    )[["station", "nom", "canton", "altitude", "lat", "lon"]]

    frames = []
    for abbr in meta["station"]:
        a = abbr.lower()
        try:
            d = _read_meteoswiss_csv(f"{PHENO_BASE}/{a}/ogd-phenology_{a}_y.csv")
        except requests.HTTPError:
            continue
        cols = [c for c in PHENO_PARAMS if c in d.columns]
        if not cols:
            continue
        d["annee"] = pd.to_datetime(d["reference_timestamp"], format="%d.%m.%Y %H:%M").dt.year
        m = d.melt(
            id_vars=["station_abbr", "annee"],
            value_vars=cols,
            var_name="parametre",
            value_name="date",
        ).dropna(subset=["date"])
        if m.empty:
            continue
        dt = pd.to_datetime(m["date"].astype("Int64").astype(str), format="%Y%m%d", errors="coerce")
        m["jour_annee"] = dt.dt.dayofyear
        m = m.dropna(subset=["jour_annee"])
        frames.append(
            m[["station_abbr", "annee", "parametre", "jour_annee"]].rename(
                columns={"station_abbr": "station"}
            )
        )
    obs = pd.concat(frames, ignore_index=True)
    obs["jour_annee"] = obs["jour_annee"].astype(int)
    save(meta[meta["station"].isin(obs["station"].unique())], "pheno_stations.csv")
    save(obs, "pheno_observations.csv")
    save(
        pd.DataFrame(
            [{"parametre": k, "libelle": v[0], "saison": v[1]} for k, v in PHENO_PARAMS.items()]
        ),
        "pheno_parametres.csv",
    )


# --------------------------------------------------------------------------
# 3. GLAMOS — bilan de masse des glaciers
# --------------------------------------------------------------------------
GLAMOS_RELEASE = "https://doi.glamos.ch/data/massbalance/massbalance_{y}_r{y}.zip"
GLAMOS_PREMIERE_RELEASE = 2025  # première version publiée sous cette forme


def _glamos_derniere_release() -> int:
    """GLAMOS publie une release par an, en novembre. On prend la plus récente en ligne."""
    for annee in range(pd.Timestamp.today().year, GLAMOS_PREMIERE_RELEASE - 1, -1):
        r = SESSION.head(GLAMOS_RELEASE.format(y=annee), timeout=TIMEOUT, allow_redirects=True)
        if r.ok:
            return annee
    raise RuntimeError("aucune release GLAMOS accessible")


def build_glamos() -> None:
    print("GLAMOS — bilan de masse des glaciers")
    annee = _glamos_derniere_release()
    log(f"release {annee}")
    z = zipfile.ZipFile(io.BytesIO(get(GLAMOS_RELEASE.format(y=annee)).content))
    raw = z.read(f"massbalance_fixdate_{annee}_r{annee}.csv").decode("utf-8").splitlines()
    start = next(i for i, l in enumerate(raw) if l.startswith("glacier name"))
    # ligne d'en-tête + 2 lignes de description (noms courts, unités)
    header = raw[start].split(",")
    ncol = header.index("observer")  # la colonne « observer » contient des virgules
    rows = [l.split(",")[:ncol] for l in raw[start + 3 :] if l.strip()]
    df = pd.DataFrame(rows, columns=header[:ncol]).replace("", pd.NA)
    for c in df.columns[5:]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.rename(
        columns={
            "glacier name": "glacier",
            "glacier id": "glacier_id",
            "end date of observation": "fin",
            "winter mass balance": "bilan_hiver",
            "summer mass balance": "bilan_ete",
            "annual mass balance": "bilan_annuel",
            "equilibrium line altitude": "ligne_equilibre",
            "glacier area": "surface_km2",
        }
    )
    df["annee"] = pd.to_datetime(df["fin"]).dt.year
    df = df[
        ["glacier", "glacier_id", "annee", "bilan_hiver", "bilan_ete",
         "bilan_annuel", "ligne_equilibre", "surface_km2"]
    ].dropna(subset=["bilan_annuel"])
    df = df.sort_values(["glacier", "annee"])
    df["bilan_cumule"] = df.groupby("glacier")["bilan_annuel"].cumsum()
    save(df, "glaciers_bilan_masse.csv")


# --------------------------------------------------------------------------
# 4. OFEN / Pronovo — installations de production d'électricité
# --------------------------------------------------------------------------
EPP_URL = (
    "https://data.geo.admin.ch/ch.bfe.elektrizitaetsproduktionsanlagen/"
    "elektrizitaetsproduktionsanlagen/elektrizitaetsproduktionsanlagen_2056.csv.zip"
)
SUBCAT_FR = {
    "subcat_1": "Hydraulique",
    "subcat_2": "Photovoltaïque",
    "subcat_3": "Éolien",
    "subcat_4": "Biomasse",
    "subcat_5": "Géothermie",
    "subcat_6": "Nucléaire",
    "subcat_7": "Pétrole",
    "subcat_8": "Gaz naturel",
    "subcat_9": "Charbon",
    "subcat_10": "Déchets",
}


def build_epp() -> None:
    print("OFEN / Pronovo — installations de production d'électricité")
    z = zipfile.ZipFile(io.BytesIO(get(EPP_URL).content))
    df = pd.read_csv(
        io.BytesIO(z.read("ElectricityProductionPlant.csv")),
        usecols=["Canton", "BeginningOfOperation", "TotalPower", "SubCategory"],
        low_memory=False,
    )
    df = df.dropna(subset=["BeginningOfOperation", "TotalPower"])
    df["annee"] = pd.to_datetime(df["BeginningOfOperation"], errors="coerce").dt.year
    df = df.dropna(subset=["annee"])
    df["annee"] = df["annee"].astype(int)
    df["technologie"] = df["SubCategory"].map(SUBCAT_FR).fillna("Autre")
    df["puissance_mw"] = df["TotalPower"] / 1000.0  # kW → MW

    agg = (
        df.groupby(["annee", "Canton", "technologie"], as_index=False)
        .agg(puissance_mw=("puissance_mw", "sum"), installations=("puissance_mw", "size"))
        .rename(columns={"Canton": "canton"})
    )
    # le registre contient quelques mises en service futures → on s'arrête à l'an dernier
    agg = agg[(agg["annee"] >= 1900) & (agg["annee"] <= pd.Timestamp.today().year)]
    save(agg, "electricite_installations.csv")


# --------------------------------------------------------------------------
# 5. OFS / STAT-TAB — véhicules routiers par carburant
# --------------------------------------------------------------------------
PX = "https://www.pxweb.bfs.admin.ch/api/v1/fr/{cube}/{cube}.px"
VEHICLE_CUBES = {
    "px-x-1103020200_121": "vehicules_nouvelles_immatriculations.csv",
    "px-x-1103020100_111": "vehicules_parc.csv",
}


def _px_meta(cube: str) -> dict:
    return json.loads(get(PX.format(cube=cube)).text)


def _px_query(cube: str, query: list) -> dict:
    r = SESSION.post(
        PX.format(cube=cube),
        json={"query": query, "response": {"format": "json-stat2"}},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def _jsonstat_to_frame(js: dict) -> pd.DataFrame:
    dims = js["id"]
    idx = {}
    for d in dims:
        cat = js["dimension"][d]["category"]
        order = sorted(cat["index"], key=lambda k: cat["index"][k])
        idx[d] = [cat["label"][k] for k in order]
    mi = pd.MultiIndex.from_product([idx[d] for d in dims], names=dims)
    values = js["value"]
    if isinstance(values, dict):  # format creux
        values = [values.get(str(i)) for i in range(len(mi))]
    return pd.DataFrame({"valeur": values}, index=mi).reset_index()


def build_vehicles() -> None:
    print("OFS / STAT-TAB — véhicules routiers par carburant")
    for cube, out in VEHICLE_CUBES.items():
        meta = _px_meta(cube)
        var = {v["code"]: v for v in meta["variables"]}
        years = var["Jahr"]["values"]
        # "Voitures de tourisme" = première modalité du groupe de véhicules
        car = var["Fahrzeuggruppe"]["values"][0]
        frames = []
        for y in years:  # une requête par année : la limite de cellules est vite atteinte
            js = _px_query(
                cube,
                [
                    {"code": "Fahrzeuggruppe", "selection": {"filter": "item", "values": [car]}},
                    {"code": "Treibstoff", "selection": {"filter": "all", "values": ["*"]}},
                    {"code": "Jahr", "selection": {"filter": "item", "values": [y]}},
                ],
            )
            f = _jsonstat_to_frame(js)
            frames.append(f)
            log(f"{cube} {y} ok")
        df = pd.concat(frames, ignore_index=True)
        df = df.rename(columns={"Treibstoff": "carburant", "Jahr": "annee"})
        df = (
            df.groupby(["annee", "carburant"], as_index=False)["valeur"]
            .sum()
            .astype({"annee": int})
        )
        save(df, out)


# --------------------------------------------------------------------------
# 5b. OFS / STAT-TAB — population résidante par canton (dénominateur)
# --------------------------------------------------------------------------
POP_CUBE = "px-x-0102020000_101"


def build_population() -> None:
    print("OFS / STAT-TAB — population résidante par canton")
    meta = _px_meta(POP_CUBE)
    var = {v["code"]: v for v in meta["variables"]}

    def pick(code: str, label: str) -> str:
        v = var[code]
        return v["values"][v["valueTexts"].index(label)]

    js = _px_query(
        POP_CUBE,
        [
            {"code": "Kanton", "selection": {"filter": "all", "values": ["*"]}},
            {"code": "Jahr", "selection": {"filter": "all", "values": ["*"]}},
            {
                "code": "Staatsangehörigkeit (Kategorie)",
                "selection": {
                    "filter": "item",
                    "values": [pick("Staatsangehörigkeit (Kategorie)", "Nationalité (catégorie) - total")],
                },
            },
            {
                "code": "Geschlecht",
                "selection": {"filter": "item", "values": [pick("Geschlecht", "Sexe - total")]},
            },
            {
                "code": "Demografische Komponente",
                "selection": {
                    "filter": "item",
                    "values": [pick("Demografische Komponente", "Effectif au 31 décembre")],
                },
            },
        ],
    )
    df = _jsonstat_to_frame(js).rename(columns={"Kanton": "canton", "Jahr": "annee"})
    df = df[["canton", "annee", "valeur"]].dropna(subset=["valeur"])
    df["annee"] = df["annee"].astype(int)
    df = df[~df["canton"].isin(["Sans indication"])]
    save(df.rename(columns={"valeur": "population"}), "population_cantons.csv")


# --------------------------------------------------------------------------
# 6. OFEV / LINDAS — inventaire des gaz à effet de serre
# --------------------------------------------------------------------------
LINDAS = "https://lindas.admin.ch/query"
GHG_CUBE = "https://environment.ld.admin.ch/foen/ubd000502"


def _sparql(query: str) -> list[dict]:
    r = SESSION.post(
        LINDAS,
        data={"query": query},
        headers={"Accept": "application/sparql-results+json"},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return r.json()["results"]["bindings"]


def build_ghg() -> None:
    print("OFEV / LINDAS — inventaire des gaz à effet de serre")
    version = _sparql(
        f"""PREFIX schema: <http://schema.org/>
        SELECT (MAX(?v) AS ?ver) WHERE {{
          GRAPH <https://lindas.admin.ch/foen/cube> {{ <{GHG_CUBE}> schema:hasPart/schema:version ?v }}
        }}"""
    )[0]["ver"]["value"]
    cube = f"{GHG_CUBE}/{version}"
    log(f"cube version {version}")

    rows = _sparql(
        f"""PREFIX cube: <https://cube.link/>
        SELECT ?secteur ?gaz ?annee ?valeur WHERE {{
          <{cube}> cube:observationSet/cube:observation ?o .
          ?o <{GHG_CUBE}/sektorid> ?secteur ;
             <{GHG_CUBE}/gas> ?gaz ;
             <{GHG_CUBE}/jahr> ?annee ;
             <{GHG_CUBE}/werteNichtGerundet> ?valeur .
        }}"""
    )
    df = pd.DataFrame(
        {
            "secteur_id": [r["secteur"]["value"].rsplit("/", 1)[-1] for r in rows],
            "gaz_id": [r["gaz"]["value"].rsplit("/", 1)[-1] for r in rows],
            "annee": [int(str(r["annee"]["value"])[:4]) for r in rows],
            "valeur": [float(r["valeur"]["value"]) for r in rows],
        }
    )

    labels = _sparql(
        """PREFIX schema: <http://schema.org/>
        SELECT ?s ?name WHERE { GRAPH ?g { ?s schema:name ?name }
          FILTER(STRSTARTS(STR(?s), "https://environment.ld.admin.ch/vocabulary/ghg_emission_sectors_co2_ordinance/")
              || STRSTARTS(STR(?s), "https://ld.admin.ch/cube/dimension/pol01air/")
              || STRSTARTS(STR(?s), "https://ld.admin.ch/cube/dimension/testdimension/"))
          FILTER(lang(?name) = "fr") }"""
    )
    lut = {r["s"]["value"].rsplit("/", 1)[-1]: r["name"]["value"] for r in labels}
    df["secteur"] = df["secteur_id"].map(lut)
    df["gaz"] = df["gaz_id"].map(lut)
    # niveau hiérarchique : 1 chiffre = total, 2 = secteur CO2, 3+ = sous-secteur
    df["niveau"] = df["secteur_id"].str.len()
    save(df.sort_values(["secteur_id", "gaz_id", "annee"]), "ges_emissions.csv")


BUILDERS = {
    "nbcn": build_nbcn,
    "pheno": build_pheno,
    "glamos": build_glamos,
    "epp": build_epp,
    "vehicles": build_vehicles,
    "population": build_population,
    "ghg": build_ghg,
}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--only", help="liste séparée par des virgules : " + ", ".join(BUILDERS))
    args = p.parse_args()
    names = args.only.split(",") if args.only else list(BUILDERS)
    failed = []
    for n in names:
        n = n.strip()
        if n not in BUILDERS:
            print(f"source inconnue : {n}", file=sys.stderr)
            return 2
        try:
            BUILDERS[n]()
        except Exception as exc:  # une source indisponible ne doit pas tout bloquer
            print(f"!! échec de {n} : {exc}", file=sys.stderr)
            failed.append(n)
    if failed:
        print("\nsources en échec : " + ", ".join(failed), file=sys.stderr)
        return 1
    print("\nterminé.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
