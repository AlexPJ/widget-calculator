from __future__ import annotations

from dataclasses import dataclass

DEFAULT_THEME_ID = "monokai"


@dataclass(frozen=True, slots=True)
class Theme:
    theme_id: str
    name: str
    window_bg: str
    surface_bg: str
    editor_bg: str
    results_bg: str
    border: str
    text: str
    muted_text: str
    accent: str
    accent_hover: str
    selection: str
    danger: str = "#e74c3c"
    danger_hover: str = "#ff6b5b"


THEMES: dict[str, Theme] = {
    "monokai": Theme(
        theme_id="monokai",
        name="Monokai",
        window_bg="#17181b",
        surface_bg="#1f2023",
        editor_bg="#111214",
        results_bg="#151619",
        border="#3d3e42",
        text="#f8f8f2",
        muted_text="#a8a8a2",
        accent="#a6e22e",
        accent_hover="#c5f467",
        selection="#49483e",
        danger="#e74c3c",
        danger_hover="#ff6b5b",
    ),
    "nord": Theme(
        theme_id="nord",
        name="Nord",
        window_bg="#2e3440",
        surface_bg="#3b4252",
        editor_bg="#2b303b",
        results_bg="#303744",
        border="#4c566a",
        text="#eceff4",
        muted_text="#d8dee9",
        accent="#88c0d0",
        accent_hover="#9ccfdc",
        selection="#434c5e",
        danger="#bf616a",
        danger_hover="#d08770",
    ),
    "graphite": Theme(
        theme_id="graphite",
        name="Graphite",
        window_bg="#101214",
        surface_bg="#161a1f",
        editor_bg="#0d1014",
        results_bg="#12161b",
        border="#2e3640",
        text="#ebeff5",
        muted_text="#b9c0cc",
        accent="#5ec2ff",
        accent_hover="#85d1ff",
        selection="#2a3240",
        danger="#ff6b6b",
        danger_hover="#ff8585",
    ),
}


def get_theme(theme_id: str) -> Theme:
    return THEMES.get(theme_id, THEMES[DEFAULT_THEME_ID])


def all_themes() -> list[Theme]:
    return list(THEMES.values())
