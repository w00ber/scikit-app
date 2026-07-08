"""Named syntax-highlighting color schemes for the code editor.

A :class:`HighlightTheme` bundles the editor background/foreground, the
current-line and selection tints, the gutter colors, and one color per
token kind — as a *matched set*, so contrast is guaranteed rather than
left to chance. Several well-known schemes ship built in (Dracula,
Monokai, Solarized dark/light, Zenburn, GitHub light); apps select one by
name or supply their own.

This replaces the previous ad-hoc "pick light-or-dark colors from the
widget palette" logic, which could paint dark text on a dark background
when the palette wasn't dark yet at highlighter-construction time.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HighlightTheme:
    """A complete editor + syntax color scheme."""

    name: str
    dark: bool
    background: str
    foreground: str
    current_line: str
    selection: str
    gutter_background: str
    gutter_foreground: str
    # Token colors
    keyword: str
    builtin: str
    string: str
    comment: str
    number: str
    decorator: str
    name_def: str          # def / class names


DRACULA = HighlightTheme(
    name="dracula", dark=True,
    background="#282a36", foreground="#f8f8f2",
    current_line="#44475a", selection="#44475a",
    gutter_background="#282a36", gutter_foreground="#6272a4",
    keyword="#ff79c6", builtin="#8be9fd", string="#f1fa8c",
    comment="#6272a4", number="#bd93f9", decorator="#ffb86c", name_def="#50fa7b",
)

MONOKAI = HighlightTheme(
    name="monokai", dark=True,
    background="#272822", foreground="#f8f8f2",
    current_line="#3e3d32", selection="#49483e",
    gutter_background="#272822", gutter_foreground="#90908a",
    keyword="#f92672", builtin="#66d9ef", string="#e6db74",
    comment="#75715e", number="#ae81ff", decorator="#fd971f", name_def="#a6e22e",
)

SOLARIZED_DARK = HighlightTheme(
    name="solarized-dark", dark=True,
    background="#002b36", foreground="#93a1a1",
    current_line="#073642", selection="#073642",
    gutter_background="#002b36", gutter_foreground="#586e75",
    keyword="#859900", builtin="#268bd2", string="#2aa198",
    comment="#586e75", number="#d33682", decorator="#cb4b16", name_def="#b58900",
)

SOLARIZED_LIGHT = HighlightTheme(
    name="solarized-light", dark=False,
    background="#fdf6e3", foreground="#657b83",
    current_line="#eee8d5", selection="#eee8d5",
    gutter_background="#eee8d5", gutter_foreground="#93a1a1",
    keyword="#859900", builtin="#268bd2", string="#2aa198",
    comment="#93a1a1", number="#d33682", decorator="#cb4b16", name_def="#b58900",
)

ZENBURN = HighlightTheme(
    name="zenburn", dark=True,
    background="#3f3f3f", foreground="#dcdccc",
    current_line="#4f4f4f", selection="#2b2b2b",
    gutter_background="#3f3f3f", gutter_foreground="#9f9f9f",
    keyword="#f0dfaf", builtin="#8cd0d3", string="#cc9393",
    comment="#7f9f7f", number="#8cd0d3", decorator="#dfaf8f", name_def="#efef8f",
)

GITHUB_LIGHT = HighlightTheme(
    name="github-light", dark=False,
    background="#ffffff", foreground="#24292e",
    current_line="#f6f8fa", selection="#cce5ff",
    gutter_background="#ffffff", gutter_foreground="#6a737d",
    keyword="#d73a49", builtin="#6f42c1", string="#032f62",
    comment="#6a737d", number="#005cc5", decorator="#22863a", name_def="#6f42c1",
)

#: All built-in schemes, keyed by name.
THEMES: dict[str, HighlightTheme] = {
    t.name: t for t in (
        DRACULA, MONOKAI, SOLARIZED_DARK, SOLARIZED_LIGHT, ZENBURN, GITHUB_LIGHT,
    )
}

#: Defaults used by ``theme="auto"`` (follows the app's light/dark chrome).
DEFAULT_DARK = DRACULA
DEFAULT_LIGHT = GITHUB_LIGHT


def list_themes() -> list[str]:
    """Return the built-in scheme names."""
    return list(THEMES)


def get_theme(theme: str | HighlightTheme, *, dark: bool = False) -> HighlightTheme:
    """Resolve *theme* to a :class:`HighlightTheme`.

    Accepts a :class:`HighlightTheme`, a scheme name, or ``"auto"`` (which
    picks :data:`DEFAULT_DARK` or :data:`DEFAULT_LIGHT` from *dark*).
    """
    if isinstance(theme, HighlightTheme):
        return theme
    if theme == "auto":
        return DEFAULT_DARK if dark else DEFAULT_LIGHT
    try:
        return THEMES[theme]
    except KeyError:
        raise ValueError(
            f"unknown highlight theme {theme!r}; choose from {list_themes()} or 'auto'"
        ) from None
