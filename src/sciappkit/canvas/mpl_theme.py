"""Light/dark theming for matplotlib figures.

A deliberately simple approach to the "dark-mode plot" problem: theme the
**chrome** (figure/axes background, spines, ticks, tick labels, axis
labels, title, grid, legend) for light or dark, and set a colorblind-safe
qualitative **color cycle** that reads on either surface. Existing traces
keep their colors by default, so series↔color correspondence is preserved
across a theme switch (recoloring live data is fraught — opt in explicitly
with ``recolor_existing=True``).

The palettes are the validated categorical + chrome colors from the
data-viz reference palette (worst adjacent CVD ΔE 24.2 light / 10.3 dark;
the dark set sits in the 8–12 floor band, which is fine here because plots
carry a legend, so identity is never color-alone).
"""

from __future__ import annotations

from dataclasses import dataclass

# Categorical cycles (fixed order — the ordering is the CVD-safety mechanism).
LIGHT_CYCLE = ["#2a78d6", "#1baf7a", "#eda100", "#008300",
               "#4a3aa7", "#e34948", "#e87ba4", "#eb6834"]
DARK_CYCLE = ["#3987e5", "#199e70", "#c98500", "#008300",
              "#9085e9", "#e66767", "#d55181", "#d95926"]


@dataclass(frozen=True)
class MplChrome:
    surface: str        # figure + axes background
    primary: str        # title
    secondary: str      # tick labels, axis labels
    muted: str          # tick marks
    grid: str           # gridlines
    baseline: str       # spines / axis
    cycle: tuple[str, ...]


LIGHT_CHROME = MplChrome(
    surface="#fcfcfb", primary="#0b0b0b", secondary="#52514e",
    muted="#898781", grid="#e1e0d9", baseline="#c3c2b7", cycle=tuple(LIGHT_CYCLE),
)
DARK_CHROME = MplChrome(
    surface="#1a1a19", primary="#ffffff", secondary="#c3c2b7",
    muted="#898781", grid="#2c2c2a", baseline="#383835", cycle=tuple(DARK_CYCLE),
)


def chrome_for(mode: str) -> MplChrome:
    """Return the :class:`MplChrome` for ``"dark"`` or ``"light"``."""
    return DARK_CHROME if mode == "dark" else LIGHT_CHROME


def apply_mpl_theme(
    figure,
    mode: str,
    *,
    set_cycle: bool = True,
    recolor_existing: bool = False,
) -> None:
    """Restyle *figure* for ``mode`` (``"light"`` / ``"dark"``).

    Themes the chrome and (by default) sets a legible color cycle for new
    artists. Set ``recolor_existing=True`` to also recolor current lines
    to the cycle — off by default so existing series keep their colors.
    """
    from cycler import cycler

    chrome = chrome_for(mode)
    figure.set_facecolor(chrome.surface)

    for ax in figure.get_axes():
        ax.set_facecolor(chrome.surface)
        for spine in ax.spines.values():
            spine.set_color(chrome.baseline)
        ax.tick_params(colors=chrome.muted, labelcolor=chrome.secondary, which="both")
        ax.xaxis.label.set_color(chrome.secondary)
        ax.yaxis.label.set_color(chrome.secondary)
        ax.title.set_color(chrome.primary)

        # Grid follows the surface (kept recessive); only affects visible grids.
        ax.grid(color=chrome.grid)

        if set_cycle:
            ax.set_prop_cycle(cycler(color=list(chrome.cycle)))
        if recolor_existing:
            for i, line in enumerate(ax.get_lines()):
                line.set_color(chrome.cycle[i % len(chrome.cycle)])

        legend = ax.get_legend()
        if legend is not None:
            frame = legend.get_frame()
            frame.set_facecolor(chrome.surface)
            frame.set_edgecolor(chrome.baseline)
            for text in legend.get_texts():
                text.set_color(chrome.secondary)
