from __future__ import annotations

import pytest

from widget_calc.domain.themes import DEFAULT_THEME_ID, Theme, all_themes, get_theme


class TestTheme:
    def test_all_themes_contains_presets(self) -> None:
        themes = all_themes()
        ids = [t.theme_id for t in themes]
        assert "monokai" in ids
        assert "nord" in ids
        assert "graphite" in ids

    def test_get_theme_valid(self) -> None:
        theme = get_theme("nord")
        assert isinstance(theme, Theme)
        assert theme.theme_id == "nord"
        assert theme.name == "Nord"

    def test_get_theme_invalid_falls_back_to_default(self) -> None:
        theme = get_theme("nonexistent")
        assert theme.theme_id == DEFAULT_THEME_ID

    def test_theme_is_frozen(self) -> None:
        theme = get_theme("monokai")
        with pytest.raises(AttributeError):  # noqa: PT012
            theme.name = "Changed"  # type: ignore[misc]

    def test_all_themes_returns_distinct_copies(self) -> None:
        themes = all_themes()
        ids = [t.theme_id for t in themes]
        assert len(ids) == len(set(ids))
