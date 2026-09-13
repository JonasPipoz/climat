# Tableau de bord climat — Suisse

**→ [climat-switzerland.streamlit.app](https://climat-switzerland.streamlit.app/)**

Un tableau de bord Streamlit qui suit deux familles d'indicateurs, côte à côte :

- **la transition** — ce que la Suisse change : émissions de gaz à effet de serre par secteur,
  motorisation des voitures neuves et du parc, puissance renouvelable mise en service ;
- **les impacts** — ce que le climat fait déjà : températures homogénéisées depuis 1864, jours
  de chaleur et nuits tropicales, bilan de masse des glaciers, calendrier phénologique du vivant.

Toutes les séries proviennent de données ouvertes officielles suisses, téléchargées à la source.
Aucune donnée n'est saisie à la main.

## Sources

| Indicateur | Source | Couverture |
|---|---|---|
| Émissions de GES par secteur et par gaz | OFEV, inventaire national (LINDAS, cube `ubd000502`) | 1990 → |
| Températures, jours extrêmes, précipitations | MétéoSuisse, réseau NBCN (séries homogénéisées) | 1864 → (Bâle 1755) |
| Phénologie (floraisons, feuillaisons, vendanges) | MétéoSuisse, réseau phénologique, 175 stations | 1951 → |
| Bilan de masse des glaciers | GLAMOS, *Swiss Glacier Mass Balance*, dernière release en ligne | 1885 → |
| Installations de production d'électricité | OFEN / Pronovo, registre fédéral | 1900 → |
| Véhicules routiers par carburant | OFS, STAT-TAB (`px-x-1103020100_111`, `px-x-1103020200_121`) | 2010 → |
| Population résidante par canton | OFS, STAT-TAB (`px-x-0102020000_101`) | 1971 → |

## Installation

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Construire les données

Les CSV du dossier `data/` sont produits par un seul script, qui va chercher chaque source
à l'endroit officiel :

```bash
.venv/bin/python scripts/build_data.py
```

Pour ne reconstruire qu'une partie :

```bash
.venv/bin/python scripts/build_data.py --only nbcn,ghg
```

Sources disponibles : `nbcn`, `pheno`, `glamos`, `epp`, `vehicles`, `population`, `ghg`.
Une source indisponible n'interrompt pas les autres ; le script sort en code 1 et liste les échecs.

Rythme de mise à jour utile : l'inventaire des GES paraît en avril, les glaciers en novembre,
MétéoSuisse en continu, le registre Pronovo chaque mois.

## Lancer le tableau de bord

En ligne : **[climat-switzerland.streamlit.app](https://climat-switzerland.streamlit.app/)**.

En local :

```bash
.venv/bin/streamlit run app.py
```

## Contrôle visuel des figures

Chaque figure peut être rendue en PNG hors de Streamlit, ce qui permet de les relire d'un coup
après une modification :

```bash
.venv/bin/pip install kaleido
.venv/bin/python scripts/render_figures.py figures/
```

## Déploiement

L'application est déployée sur Streamlit Community Cloud :
**[climat-switzerland.streamlit.app](https://climat-switzerland.streamlit.app/)**, servie depuis
la branche `main` de ce dépôt, fichier principal `app.py`. Aucun secret ni variable
d'environnement n'est nécessaire.

Elle ne fait **aucun appel réseau à l'exécution** : elle lit uniquement les CSV de `data/`,
versionnés ici (3,8 Mo au total). Une indisponibilité des serveurs fédéraux ne peut donc pas
casser la page en ligne — elle ne fait que retarder la prochaine mise à jour des données.

Cloud redéploie à chaque `push` sur `main`. Pour publier un changement, il suffit donc de
pousser.

Points de vigilance si le déploiement est refait ailleurs :

- `requirements.txt` doit rester à la racine — c'est ce que Cloud installe. `kaleido`
  (rendu PNG) est volontairement dans `requirements-dev.txt` : inutile en ligne, et lourd.
- `data/` **doit** être versionné : Cloud ne lance pas `scripts/build_data.py`.
- Une application gratuite se met en veille après une période sans visite et redémarre à la
  première consultation suivante.

### Mise à jour automatique des données

Le workflow [`.github/workflows/maj-donnees.yml`](.github/workflows/maj-donnees.yml) reconstruit
les jeux de données le 3 de chaque mois (et à la demande, depuis l'onglet Actions). Il ne committe
que si une source a effectivement publié de nouvelles valeurs, et le `push` qui en résulte
déclenche le redéploiement de l'application.

Une source indisponible n'empêche pas de committer les autres : l'échec est signalé en fin de job.
Le workflow a besoin de *Settings → Actions → General → Workflow permissions* réglé sur
**Read and write permissions**.

À la main, si besoin :

```bash
.venv/bin/python scripts/build_data.py
git add data && git commit -m "Mise à jour des données" && git push
```

## Organisation

```
app.py                  pages et mise en page Streamlit
charts.py               une fonction par figure, sans dépendance à Streamlit
loaders.py              lecture des CSV, agrégats et séries dérivées (avec cache)
theme.py                palette validée et grammaire visuelle commune
scripts/build_data.py   téléchargement et mise en forme des sources officielles
scripts/render_figures.py  rendu PNG de toutes les figures
data/                   CSV compacts, reconstructibles
```

## Méthode

Les partis pris de calcul (socle de stations pour la moyenne suisse, traitement des années
incomplètes, tendances phénologiques, cumuls de bilan glaciaire) sont détaillés dans la page
« Sources et méthode » du tableau de bord.

## Licences des données

Données fédérales : conditions *opendata.swiss* — utilisation libre, source à citer.
GLAMOS : utilisation libre pour un usage scientifique et non commercial, avec citation
(GLAMOS 2025, doi:10.18750/massbalance.2025.r2025).
