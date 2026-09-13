"""Palette et helpers de mise en forme communs aux graphiques du tableau de bord."""
from __future__ import annotations

import plotly.graph_objects as go

# Palette catégorielle validée (mode clair) — les séries prennent les emplacements
# dans l'ordre d'affichage, jamais en cycle.
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]

# Divergent : bleu ↔ rouge, gris neutre au centre
DIV_COLD = "#2a78d6"
DIV_WARM = "#d03b3b"
DIV_SCALE = [
    [0.0, "#104281"], [0.25, "#6da7ec"], [0.5, "#f0efec"],
    [0.75, "#e37e7e"], [1.0, "#8f2020"],
]
SEQ_SCALE = [
    [0.0, "#cde2fb"], [0.33, "#5598e7"], [0.66, "#256abf"], [1.0, "#0d366b"],
]

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_SOFT = "#52514e"
INK_MUTED = "#7d7c77"
GRID = "#e6e5e1"

FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"


def style(fig: go.Figure, *, height: int = 380, legend: bool = True, unified: bool = True) -> go.Figure:
    """Applique la grammaire visuelle commune : marques fines, grille discrète, encre sobre."""
    fig.update_layout(
        height=height,
        font=dict(family=FONT, size=13, color=INK_SOFT),
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        margin=dict(l=8, r=8, t=48, b=56),
        hovermode="x unified" if unified else "closest",
        hoverlabel=dict(bgcolor="#ffffff", bordercolor=GRID, font=dict(family=FONT, size=12, color=INK)),
        showlegend=legend,
        legend=dict(
            orientation="h", yanchor="top", y=-0.12, xanchor="left", x=0,
            title=None, font=dict(size=12, color=INK_SOFT), bgcolor="rgba(0,0,0,0)",
        ),
        title=dict(font=dict(size=15, color=INK), x=0, xanchor="left", y=0.97, yanchor="top"),
    )
    if not legend:
        fig.update_layout(margin=dict(l=8, r=8, t=48, b=16))
    fig.update_xaxes(showgrid=False, linecolor=GRID, ticks="outside", tickcolor=GRID,
                     tickfont=dict(size=12, color=INK_MUTED), title_font=dict(size=12, color=INK_MUTED))
    fig.update_yaxes(showgrid=True, gridcolor=GRID, gridwidth=1, zeroline=False, linecolor="rgba(0,0,0,0)",
                     tickfont=dict(size=12, color=INK_MUTED), title_font=dict(size=12, color=INK_MUTED))
    return fig


def annotate(fig: go.Figure, x, y, text: str, color: str = INK_SOFT, **kw) -> None:
    """Étiquette directe (utilisée avec parcimonie : dernier point d'une série, repère clé)."""
    fig.add_annotation(
        x=x, y=y, text=text, showarrow=False, font=dict(size=12, color=color),
        xanchor=kw.pop("xanchor", "left"), yanchor=kw.pop("yanchor", "middle"),
        xshift=kw.pop("xshift", 8), bgcolor="rgba(252,252,251,0.75)", **kw,
    )
