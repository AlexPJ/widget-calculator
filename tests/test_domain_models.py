from __future__ import annotations

import math

import pytest

from widget_calc.domain.models import (
    MAX_HISTORY_ITEMS,
    MAX_OPACITY,
    MIN_OPACITY,
    AppState,
    WindowState,
    normalize_opacity,
)


class TestWindowState:
    def test_defaults(self) -> None:
        w = WindowState(window_id="w1", title="Calc 1")
        assert w.window_id == "w1"
        assert w.title == "Calc 1"
        assert w.editor_text == ""

    def test_with_editor_text(self) -> None:
        w = WindowState(window_id="w1", title="Calc 1", editor_text="1+1")
        assert w.editor_text == "1+1"


class TestAppState:
    def test_defaults(self) -> None:
        s = AppState()
        assert s.windows == []
        assert s.history == []
        assert s.theme_id == "monokai"
        assert s.startup_initialized is False
        assert s.window_opacity == MAX_OPACITY

    def test_history_truncation(self) -> None:
        many = [str(i) for i in range(MAX_HISTORY_ITEMS + 50)]
        s = AppState(history=many)
        assert len(s.history) == MAX_HISTORY_ITEMS + 50  # no truncation in model
        assert s.history[0] == "0"
        assert s.history[-1] == str(MAX_HISTORY_ITEMS + 49)

    def test_with_windows(self) -> None:
        windows = [WindowState(window_id="w1", title="Calc 1"), WindowState(window_id="w2", title="Calc 2")]
        s = AppState(windows=windows)
        assert len(s.windows) == 2

    def test_with_window_opacity(self) -> None:
        s = AppState(window_opacity=0.5)
        assert s.window_opacity == 0.5


class TestNormalizeOpacity:
    def test_valid_value_passes_through(self) -> None:
        assert normalize_opacity(0.5) == 0.5
        assert normalize_opacity(0.25) == MIN_OPACITY
        assert normalize_opacity(1.0) == MAX_OPACITY
        assert normalize_opacity(0.75) == 0.75

    @pytest.mark.parametrize("bad", [-0.1, -1.0, 1.5, 2.0, 100.0])
    def test_out_of_range_returns_max(self, bad: float) -> None:
        assert normalize_opacity(bad) == MAX_OPACITY

    @pytest.mark.parametrize("bad", ["abc", None, [], {}])
    def test_invalid_value_returns_max(self, bad: object) -> None:
        assert normalize_opacity(bad) == MAX_OPACITY

    def test_nan_returns_max(self) -> None:
        assert normalize_opacity(float("nan")) == MAX_OPACITY

    def test_inf_returns_max(self) -> None:
        assert normalize_opacity(float("inf")) == MAX_OPACITY
        assert math.isfinite(normalize_opacity(float("inf")))

    def test_numeric_string(self) -> None:
        assert normalize_opacity("0.5") == 0.5


class TestAppStatePostInit:
    def test_appstate_normalizes_out_of_range(self) -> None:
        state = AppState(window_opacity=5.0)
        assert state.window_opacity == MAX_OPACITY

    def test_appstate_normalizes_nan(self) -> None:
        state = AppState(window_opacity=float("nan"))
        assert state.window_opacity == MAX_OPACITY

    def test_appstate_keeps_valid(self) -> None:
        state = AppState(window_opacity=0.5)
        assert state.window_opacity == 0.5

    def test_appstate_default_is_max(self) -> None:
        state = AppState()
        assert state.window_opacity == MAX_OPACITY
