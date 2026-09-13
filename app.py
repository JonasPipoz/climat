"""Tableau de bord climat — Suisse.

Deux familles d'indicateurs, construites uniquement sur des données ouvertes officielles :
  • ce que nous changeons  — émissions, mobilité, production d'électricité renouvelable ;
  • ce que le climat fait  — températures, extrêmes, glaciers, saisons du vivant.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import loaders as L
from charts import (
    fig_ajouts_renouvelables, fig_anomalie, fig_electrifiees, fig_extremes, fig_ges_index,
    fig_ges_secteurs, fig_glaciers, fig_glaciers_annuel, fig_heatmap, fig_indice_annuel,
    fig_parts_carburant, fig_pheno_pentes, fig_pheno_serie, fig_pv_cantons, fig_pv_cumule,
)
from theme import SERIES, style

st.set_page_config(page_title="Climat Suisse", page_icon="🇨🇭", layout="wide")

st.markdown(
    """
    <style>
      .block-container {padding-top: 2.2rem; max-width: 1400px;}
      h1, h2, h3 {letter-spacing: -0.01em;}
      div[data-testid="stMetricValue"] {font-size: 1.9rem;}
      .note {color:#7d7c77; font-size:0.82rem; line-height:1.45; margin-top:-0.4rem;}
      .lead {color:#52514e; font-size:1.0rem; max-width:70ch;}
    </style>
    """,
    unsafe_allow_html=True,
)

def note(txt: str) -> None:
    st.markdown(f'<p class="note">{txt}</p>', unsafe_allow_html=True)


def show(fig: go.Figure) -> None:
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def tableau(df: pd.DataFrame, libelle: str = "Voir les données") -> None:
    with st.expander(libelle):
        st.dataframe(df, width="stretch", hide_index=True)


# ==========================================================================
#  Pages
# ==========================================================================
def page_apercu() -> None:
    st.title("Climat Suisse — ce qui change, et ce que ça change")
    st.markdown(
        '<p class="lead">Deux questions tiennent ce tableau de bord : la Suisse modifie-t-elle '
        "réellement ses habitudes énergétiques, et que mesure-t-on déjà du climat qui se réchauffe ? "
        "Toutes les séries proviennent de données ouvertes fédérales (OFEV, MétéoSuisse, OFEN, OFS) "
        "et de GLAMOS.</p>",
        unsafe_allow_html=True,
    )

    total = L.ges_total()
    ref90 = float(total.loc[total["annee"] == 1990, "valeur"].iloc[0])
    der = total.sort_values("annee").iloc[-1]

    anomalie = L.serie_nationale("temp_anomalie")
    a_der = anomalie.iloc[-1]
    a_ref = anomalie[anomalie["annee"].between(1864, 1900)]["valeur"].mean()

    neuves = L.voitures_neuves()
    an_v = int(neuves["annee"].max())
    part_e = neuves[(neuves["annee"] == an_v) & (neuves["groupe"] == "Électrique")]["part"].sum()
    part_e_prec = neuves[(neuves["annee"] == an_v - 1) & (neuves["groupe"] == "Électrique")]["part"].sum()

    pv = L.capacite_cumulee("Photovoltaïque").sum(axis=1)
    an_pv = int(pv.index.max()) - 1  # la dernière année du registre est incomplète
    pv_der, pv_prec = pv.loc[an_pv] / 1000, pv.loc[an_pv - 1] / 1000

    gl = L.glaciers()
    gl_an = int(gl["annee"].max())
    gl_med = gl[gl["annee"] == gl_an]["bilan_annuel"].median() / 1000

    c = st.columns(5)
    c[0].metric("Émissions de GES", f"{der['valeur']:.1f} Mt",
                f"{(der['valeur']/ref90 - 1)*100:+.0f} % vs 1990", delta_color="inverse")
    c[0].caption(f"tous gaz, {int(der['annee'])}")
    c[1].metric("Réchauffement observé", f"{a_der['valeur'] - a_ref:+.1f} °C",
                f"{a_der['valeur']:+.1f} °C vs norme 1991-2020", delta_color="off")
    c[1].caption(f"{int(a_der['annee'])} par rapport à 1864-1900")
    c[2].metric("Voitures neuves 100 % électriques", f"{part_e*100:.1f} %",
                f"{(part_e - part_e_prec)*100:+.1f} pt")
    c[2].caption(f"part de marché, {an_v}")
    c[3].metric("Parc photovoltaïque", f"{pv_der:.1f} GW", f"+{pv_der - pv_prec:.1f} GW en un an")
    c[3].caption(f"cumulé fin {an_pv}")
    c[4].metric("Bilan des glaciers", f"{gl_med:+.2f} m")
    c[4].caption(f"médiane, équivalent en eau, {gl_an}")

    st.divider()
    g1, g2 = st.columns(2)
    with g1:
        show(fig_ges_secteurs())
        note("Source : OFEV, inventaire des gaz à effet de serre (via LINDAS). Secteurs de l'ordonnance "
             "sur le CO₂. Les repères en pointillé sont les objectifs de réduction inscrits dans la loi "
             "sur le CO₂ et la loi sur le climat, rapportés au total national de 1990.")
    with g2:
        show(fig_anomalie(L.serie_nationale("temp_anomalie"),
                          "Écart de température annuel à la norme 1991-2020, moyenne suisse"))
        note("Source : MétéoSuisse, séries climatiques homogènes (NBCN). Moyenne des stations mesurant "
             "depuis 1864 au plus tard.")


def page_transition() -> None:
    st.title("Transition — ce que nous changeons")
    st.markdown(
        '<p class="lead">Des indicateurs de comportement et d\'équipement : ce qui est émis, '
        "ce qui s'achète, ce qui se construit. Ils bougent lentement, et c'est précisément l'intérêt "
        "de les suivre sur longue durée.</p>",
        unsafe_allow_html=True,
    )

    st.subheader("Émissions de gaz à effet de serre")
    show(fig_ges_secteurs())
    a, b = st.columns([3, 2])
    with a:
        show(fig_ges_index())
        note("Le bâtiment a réellement décroché — près de moitié moins qu'en 1990. Les transports, "
             "premier poste d'émissions du pays, n'ont reculé que d'un dixième en trente-cinq ans : "
             "c'est là que se joue l'écart avec la trajectoire légale.")
    with b:
        d = L.ges_par_gaz()
        fig = go.Figure()
        for i, gaz in enumerate(d.groupby("gaz")["valeur"].max().sort_values(ascending=False).index):
            s = d[d["gaz"] == gaz].sort_values("annee")
            fig.add_trace(go.Scatter(x=s["annee"], y=s["valeur"], name=gaz, mode="lines",
                                     stackgroup="g", line=dict(width=0.5, color="#fcfcfb"),
                                     fillcolor=SERIES[i], hovertemplate="%{y:.1f} Mt<extra></extra>"))
        style(fig, height=380)
        fig.update_layout(title="Composition par gaz (Mt CO₂-éq.)")
        fig.update_yaxes(rangemode="tozero", ticksuffix=" Mt")
        show(fig)
        note("Source : OFEV. Le CO₂ domine ; les gaz synthétiques, longtemps en hausse, reculent "
             "depuis le durcissement de leur réglementation.")
    tableau(L.ges_par_secteur().pivot(index="annee", columns="secteur", values="valeur").round(2).reset_index())

    st.divider()
    st.subheader("Mobilité : ce qui s'achète")
    a, b = st.columns(2)
    with a:
        show(fig_parts_carburant(L.voitures_neuves(), "Voitures de tourisme neuves, par motorisation"))
    with b:
        show(fig_parts_carburant(L.voitures_parc(), "Parc de voitures en circulation, par motorisation"))
    show(fig_electrifiees())
    note("Source : OFS, statistique des véhicules routiers (STAT-TAB). L'écart entre les deux courbes "
         "est l'inertie du parc : une voiture vendue aujourd'hui roulera encore une quinzaine d'années.")
    tableau(
        L.voitures_neuves().pivot(index="annee", columns="groupe", values="part")
        .mul(100).round(2).reset_index(), "Voir les parts de marché (%)"
    )

    st.divider()
    st.subheader("Production d'électricité renouvelable")
    derniere_complete = int(L.installations()["annee"].max()) - 1
    a, b = st.columns(2)
    with a:
        show(fig_ajouts_renouvelables(derniere_complete))
    with b:
        show(fig_pv_cumule(derniere_complete))
    note(f"Source : OFEN / Pronovo, registre des installations de production d'électricité. Les "
         f"puissances sont celles des installations encore en service ; l'année {derniere_complete + 1}, "
         "incomplète, est écartée. Le pic hydraulique de 2022 tient presque entièrement à une seule "
         "installation valaisanne de 945 MW — du pompage-turbinage, donc du stockage plutôt que de la "
         "production nouvelle. Hors cette exception, toute la croissance est photovoltaïque.")
    tableau(
        L.installations()
        .query("annee <= @derniere_complete and annee >= 2000")
        .pivot_table(index="annee", columns="technologie", values="puissance_mw", aggfunc="sum")
        .round(1).reset_index(),
        "Voir les puissances mises en service (MW)",
    )
    show(fig_pv_cantons(derniere_complete))
    note("Rapporté à la population, ce sont des cantons ruraux et peu peuplés qui mènent : le "
         "photovoltaïque suit les toitures disponibles, pas la densité.")


def page_impacts() -> None:
    st.title("Impacts — ce que le climat fait déjà")
    st.markdown(
        '<p class="lead">Des mesures, pas des projections. Températures homogénéisées depuis 1864, '
        "glaciers pesés depuis un siècle, calendrier du vivant observé depuis 1951.</p>",
        unsafe_allow_html=True,
    )

    stations, annuel, params = L.nbcn()
    noms = stations.sort_values("nom")
    options = ["Moyenne suisse"] + [f"{r.nom} ({r.canton}, {int(r.altitude)} m)" for r in noms.itertuples()]
    choix = st.selectbox("Station de mesure", options, index=0)

    if choix == "Moyenne suisse":
        serie = L.serie_nationale("temp_anomalie")
        titre = "Écart de température annuel à la norme 1991-2020, moyenne suisse"
        station_annuel = annuel.groupby("annee", as_index=False).mean(numeric_only=True)
        code = None
    else:
        code = noms.iloc[options.index(choix) - 1]["station"]
        station_annuel = annuel[annuel["station"] == code]
        serie = station_annuel[["annee", "temp_anomalie"]].dropna().rename(columns={"temp_anomalie": "valeur"})
        titre = f"Écart de température annuel à la norme 1991-2020 — {choix}"

    show(fig_anomalie(serie, titre))
    recent = serie[serie["annee"] >= serie["annee"].max() - 29]["valeur"].mean()
    ancien = serie[serie["annee"].between(1871, 1900)]["valeur"].mean()
    note(f"Les trente dernières années sont en moyenne {recent - ancien:+.1f} °C au-dessus de "
         "la période 1871-1900. Source : MétéoSuisse (NBCN), séries homogénéisées.")

    if code is not None:
        show(fig_heatmap(code))

    st.divider()
    st.subheader("Jours extrêmes")
    a, b = st.columns([2, 3])
    with a:
        lib = params.set_index("colonne")["libelle"]
        indices = ["jours_ete", "jours_chaleur", "nuits_tropicales", "jours_gel", "jours_hiver"]
        indice = st.radio("Indice", indices, format_func=lambda c: lib[c], horizontal=False)
        show(fig_indice_annuel(station_annuel, indice, lib[indice]))
    with b:
        show(fig_extremes(station_annuel, params))
        if code is None:
            note("Deux périodes de trente ans, comparées sur les mêmes stations. La moyenne suisse "
                 "mélange ici des stations de plaine et de haute altitude (jusqu'au Jungfraujoch) : "
                 "les niveaux se lisent station par station, la différence entre les deux périodes "
                 "se lit à l'échelle du réseau.")
        else:
            note("Deux périodes de trente ans, sur la même station. Les jours chauds augmentent "
                 "plus vite, en nombre de jours, que les jours de gel ne diminuent.")
    tableau(station_annuel[["annee"] + indices].dropna(how="all", subset=indices).round(1))

    st.divider()
    st.subheader("Glaciers")
    gl = L.glaciers()
    couv = gl.groupby("glacier")["annee"].agg(["min", "max", "count"])
    couv["continuite"] = couv["count"] / (couv["max"] - couv["min"] + 1)
    longs = (
        couv.query("count >= 40 and continuite >= 0.95")
        .sort_values("count", ascending=False).index.tolist()
    )
    defaut = [g for g in ["Grosser Aletschgletscher", "Silvrettagletscher", "Griesgletscher",
                          "Allalingletscher"] if g in longs][:4]
    choix_gl = st.multiselect(
        "Glaciers (8 au maximum) — seules les séries observées presque chaque année sont proposées",
        longs, default=defaut or longs[:4],
    )
    if choix_gl:
        show(fig_glaciers(choix_gl))
    show(fig_glaciers_annuel())
    note("Source : GLAMOS, Swiss Glacier Mass Balance (release 2025). Un bilan cumulé de −40 m "
         "d'équivalent en eau signifie qu'une colonne d'eau de 40 mètres a quitté le glacier, "
         "en moyenne sur toute sa surface. Aucune année positive depuis le début des années 2000.")

    st.divider()
    st.subheader("Le calendrier du vivant")
    pheno = L.pheno_national()
    libelles = pheno[["parametre", "libelle"]].drop_duplicates().sort_values("libelle")
    a, b = st.columns([3, 2])
    with a:
        sel = st.selectbox("Phénophase", libelles["libelle"].tolist(),
                           index=libelles["libelle"].tolist().index("Cerisier — pleine floraison")
                           if "Cerisier — pleine floraison" in libelles["libelle"].tolist() else 0)
        code_p = libelles.loc[libelles["libelle"] == sel, "parametre"].iloc[0]
        show(fig_pheno_serie(code_p, sel))
    with b:
        show(fig_pheno_pentes())
    note("Source : MétéoSuisse, réseau d'observation phénologique (175 stations, depuis 1951). "
         "Médiane suisse des dates observées ; seules les années comptant au moins dix observations "
         "sont retenues. Le signal du printemps est net et va toujours dans le même sens : floraisons "
         "et feuillaisons avancent de 1 à 7 jours par décennie. L'automne, lui, ne bouge presque pas, "
         "et pas dans une direction unique — la saison de végétation s'allonge surtout par son début.")


def page_sources() -> None:
    st.title("Sources et méthode")
    st.markdown(
        '<p class="lead">Chaque série de ce tableau de bord est reconstructible à partir de sa source '
        "officielle avec <code>python scripts/build_data.py</code>. Rien n'est estimé ni interpolé ici : "
        "les seuls calculs sont des sommes, des médianes, des moyennes glissantes et des régressions "
        "linéaires, tous explicités ci-dessous.</p>",
        unsafe_allow_html=True,
    )
    sources = pd.DataFrame(
        [
            ["Émissions de GES", "OFEV — inventaire national, via LINDAS (cube ubd000502)",
             "1990 →", "annuelle (avril)", "https://www.bafu.admin.ch/fr/treibhausgasinventar"],
            ["Températures et jours extrêmes", "MétéoSuisse — NBCN, séries homogénéisées",
             "1864 → (Bâle 1755)", "mensuelle", "https://opendatadocs.meteoswiss.ch"],
            ["Phénologie", "MétéoSuisse — réseau phénologique, 175 stations",
             "1951 →", "annuelle", "https://opendatadocs.meteoswiss.ch"],
            ["Glaciers", "GLAMOS — Swiss Glacier Mass Balance, release 2025",
             "1885 →", "annuelle (novembre)", "https://doi.glamos.ch"],
            ["Installations électriques", "OFEN / Pronovo — registre des installations",
             "1900 →", "mensuelle", "https://data.geo.admin.ch/ch.bfe.elektrizitaetsproduktionsanlagen"],
            ["Véhicules par carburant", "OFS — STAT-TAB, statistique des véhicules routiers",
             "2010 →", "annuelle", "https://www.pxweb.bfs.admin.ch"],
            ["Population par canton", "OFS — STAT-TAB, bilan démographique",
             "1971 →", "annuelle", "https://www.pxweb.bfs.admin.ch"],
        ],
        columns=["Indicateur", "Source", "Couverture", "Mise à jour", "Lien"],
    )
    st.dataframe(
        sources, width="stretch", hide_index=True,
        column_config={"Lien": st.column_config.LinkColumn("Lien", display_text="ouvrir")},
    )

    st.subheader("Choix de méthode")
    st.markdown(
        """
- **Moyenne suisse de température** : moyenne non pondérée des écarts à la norme 1991-2020 des
  stations NBCN mesurant depuis 1864 au plus tard. Le socle de stations est figé pour qu'une année
  ne change pas de sens quand une station apparaît ; les années couvertes par moins de 80 % du socle
  sont écartées. Ce n'est pas la moyenne spatiale officielle de MétéoSuisse, qui pondère par surface.
- **Objectifs d'émissions** : repères tirés de la loi sur le CO₂ (−20 % en 2020, −50 % en 2030) et
  de la loi sur le climat (−75 % en 2040, zéro net en 2050), rapportés au **total national** de 1990.
  Ils ne sont pas répartis par secteur sur le graphique.
- **Puissance installée** : le registre Pronovo recense les installations **en service**. Une
  installation démantelée en sort ; les cumuls sont donc un parc actuel reconstitué par date de mise
  en service, pas un historique des mises en service. La dernière année, incomplète, est écartée.
- **Phénologie** : médiane suisse des dates d'observation, années de moins de dix observations
  écartées. Les tendances sont des régressions linéaires sur 1961 → aujourd'hui, exprimées en
  jours par décennie.
- **Glaciers** : bilans de masse publiés en millimètres d'équivalent en eau (affichés ici en
  mètres), année hydrologique fixe
  (1ᵉʳ octobre → 30 septembre). Le cumul démarre à la première année observée de chaque glacier,
  qui diffère d'un glacier à l'autre : les courbes se comparent en pente, pas en niveau absolu.
        """
    )
    st.subheader("Licences")
    st.markdown(
        "Données fédérales : conditions *opendata.swiss* (utilisation libre, source à citer). "
        "GLAMOS : utilisation libre pour un usage scientifique et non commercial, avec citation "
        "(GLAMOS 2025, doi:10.18750/massbalance.2025.r2025)."
    )


PAGES = {
    "Vue d'ensemble": page_apercu,
    "Transition — ce que nous changeons": page_transition,
    "Impacts — ce que le climat fait": page_impacts,
    "Sources et méthode": page_sources,
}

with st.sidebar:
    st.markdown("### Climat Suisse")
    page = st.radio("Navigation", list(PAGES), label_visibility="collapsed")
    st.divider()
    st.caption(
        "Données ouvertes : OFEV, MétéoSuisse, OFEN/Pronovo, OFS, GLAMOS.\n\n"
        "Reconstruire les séries :\n`python scripts/build_data.py`"
    )

PAGES[page]()
