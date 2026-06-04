from __future__ import annotations

from unittest.mock import Mock

import pytest

from widget_calc.application.workspace import WorkspaceService
from widget_calc.domain.calculator import CalculatorEvaluator, CurrencyConverter
from widget_calc.domain.models import AppState, WindowState


@pytest.fixture
def workspace() -> WorkspaceService:
    cc = Mock(spec=CurrencyConverter)
    cc.convert.return_value = 42.0
    evaluator = CalculatorEvaluator(cc)
    return WorkspaceService(evaluator)


@pytest.fixture
def preloaded_workspace() -> WorkspaceService:
    cc = Mock(spec=CurrencyConverter)
    cc.convert.return_value = 42.0
    evaluator = CalculatorEvaluator(cc)
    initial = AppState(
        windows=[WindowState(window_id="existing-1", title="Saved Calc", editor_text="2+2")],
        history=["1+1", "2+2"],
        theme_id="nord",
        startup_initialized=True,
    )
    return WorkspaceService(evaluator, initial)


class TestWorkspaceService:
    def test_creates_default_window(self, workspace: WorkspaceService) -> None:
        states = workspace.window_states()
        assert len(states) == 1
        assert states[0].title == "Calculator 1"

    def test_create_additional_window(self, workspace: WorkspaceService) -> None:
        w2 = workspace.create_window()
        assert w2.title == "Calculator 2"
        assert w2.window_id != workspace.window_states()[0].window_id

    def test_window_states_in_order(self, workspace: WorkspaceService) -> None:
        workspace.create_window()
        workspace.create_window()
        states = workspace.window_states()
        assert len(states) == 3
        assert states[0].title == "Calculator 1"
        assert states[1].title == "Calculator 2"
        assert states[2].title == "Calculator 3"

    def test_evaluate_window(self, workspace: WorkspaceService) -> None:
        wid = workspace.window_states()[0].window_id
        results = workspace.evaluate_window(wid, "1 + 1")
        assert results == ["2"]

    def test_evaluate_stores_editor_text(self, workspace: WorkspaceService) -> None:
        wid = workspace.window_states()[0].window_id
        workspace.evaluate_window(wid, "42")
        assert workspace.window_states()[0].editor_text == "42"

    def test_set_window_text(self, workspace: WorkspaceService) -> None:
        wid = workspace.window_states()[0].window_id
        workspace.set_window_text(wid, "hello")
        assert workspace.window_states()[0].editor_text == "hello"

    def test_set_theme(self, workspace: WorkspaceService) -> None:
        result = workspace.set_theme("nord")
        assert result == "nord"
        assert workspace.theme_id == "nord"

    def test_set_theme_invalid_returns_default(self, workspace: WorkspaceService) -> None:
        result = workspace.set_theme("bogus")
        assert result == "monokai"

    def test_history_recording(self, workspace: WorkspaceService) -> None:
        wid = workspace.window_states()[0].window_id
        workspace.evaluate_window(wid, "a = 1\nb = 2\na + b")
        assert "a = 1" in workspace.history
        assert "b = 2" in workspace.history
        assert "a + b" in workspace.history

    def test_history_dedup(self, workspace: WorkspaceService) -> None:
        wid = workspace.window_states()[0].window_id
        workspace.evaluate_window(wid, "1+1")
        workspace.evaluate_window(wid, "1+1")
        assert workspace.history.count("1+1") == 1

    def test_snapshot_contains_all_data(self, workspace: WorkspaceService) -> None:
        workspace.create_window()
        workspace.set_theme("graphite")
        workspace.startup_initialized = True
        snap = workspace.snapshot()
        assert len(snap.windows) == 2
        assert snap.theme_id == "graphite"
        assert snap.startup_initialized is True

    def test_loads_pre_existing_windows(self, preloaded_workspace: WorkspaceService) -> None:
        states = preloaded_workspace.window_states()
        assert len(states) == 1
        assert states[0].window_id == "existing-1"
        assert states[0].editor_text == "2+2"

    def test_loads_history(self, preloaded_workspace: WorkspaceService) -> None:
        assert "1+1" in preloaded_workspace.history
        assert "2+2" in preloaded_workspace.history

    def test_loads_theme(self, preloaded_workspace: WorkspaceService) -> None:
        assert preloaded_workspace.theme_id == "nord"

    def test_loads_startup_flag(self, preloaded_workspace: WorkspaceService) -> None:
        assert preloaded_workspace.startup_initialized is True

    def test_default_opacity(self, workspace: WorkspaceService) -> None:
        assert workspace.window_opacity == 1.0

    def test_set_window_opacity_clamps_above(self, workspace: WorkspaceService) -> None:
        result = workspace.set_window_opacity(2.0)
        assert result == 1.0
        assert workspace.window_opacity == 1.0

    def test_set_window_opacity_clamps_below(self, workspace: WorkspaceService) -> None:
        result = workspace.set_window_opacity(0.1)
        assert result == 1.0
        assert workspace.window_opacity == 1.0

    def test_set_window_opacity_accepts_valid(self, workspace: WorkspaceService) -> None:
        result = workspace.set_window_opacity(0.5)
        assert result == 0.5
        assert workspace.window_opacity == 0.5

    def test_set_window_opacity_at_min(self, workspace: WorkspaceService) -> None:
        result = workspace.set_window_opacity(0.25)
        assert result == 0.25

    def test_snapshot_includes_opacity(self, workspace: WorkspaceService) -> None:
        workspace.set_window_opacity(0.6)
        snap = workspace.snapshot()
        assert snap.window_opacity == 0.6

    def test_loads_opacity_from_initial_state(self) -> None:
        cc = Mock(spec=CurrencyConverter)
        cc.convert.return_value = 42.0
        evaluator = CalculatorEvaluator(cc)
        initial = AppState(window_opacity=0.4)
        ws = WorkspaceService(evaluator, initial)
        assert ws.window_opacity == 0.4

    def test_loads_opacity_normalized(self) -> None:
        cc = Mock(spec=CurrencyConverter)
        cc.convert.return_value = 42.0
        evaluator = CalculatorEvaluator(cc)
        initial = AppState(window_opacity=5.0)
        ws = WorkspaceService(evaluator, initial)
        assert ws.window_opacity == 1.0

    def test_default_window_mode(self, workspace: WorkspaceService) -> None:
        assert workspace.window_mode == "both"

    def test_set_window_mode(self, workspace: WorkspaceService) -> None:
        result = workspace.set_window_mode("previous")
        assert result == "previous"
        assert workspace.window_mode == "previous"

    def test_set_window_mode_invalid_returns_default(self, workspace: WorkspaceService) -> None:
        result = workspace.set_window_mode("nonsense")
        assert result == "both"
        assert workspace.window_mode == "both"

    def test_snapshot_includes_window_mode(self, workspace: WorkspaceService) -> None:
        workspace.set_window_mode("new")
        snap = workspace.snapshot()
        assert snap.window_mode == "new"

    def test_active_window_states_previous_returns_last(self) -> None:
        cc = Mock(spec=CurrencyConverter)
        cc.convert.return_value = 42.0
        evaluator = CalculatorEvaluator(cc)
        initial = AppState(
            windows=[
                WindowState(window_id="a", title="A"),
                WindowState(window_id="b", title="B"),
                WindowState(window_id="c", title="C"),
            ],
        )
        ws = WorkspaceService(evaluator, initial)
        active = ws.active_window_states("previous")
        assert [s.window_id for s in active] == ["c"]

    def test_active_window_states_new_returns_empty(self) -> None:
        cc = Mock(spec=CurrencyConverter)
        cc.convert.return_value = 42.0
        evaluator = CalculatorEvaluator(cc)
        initial = AppState(
            windows=[
                WindowState(window_id="a", title="A"),
                WindowState(window_id="b", title="B"),
            ],
        )
        ws = WorkspaceService(evaluator, initial)
        assert ws.active_window_states("new") == []

    def test_active_window_states_both_returns_all(self) -> None:
        cc = Mock(spec=CurrencyConverter)
        cc.convert.return_value = 42.0
        evaluator = CalculatorEvaluator(cc)
        initial = AppState(
            windows=[
                WindowState(window_id="a", title="A"),
                WindowState(window_id="b", title="B"),
            ],
        )
        ws = WorkspaceService(evaluator, initial)
        active = ws.active_window_states("both")
        assert [s.window_id for s in active] == ["a", "b"]

    def test_replace_windows_with_keeps_only_one(self) -> None:
        cc = Mock(spec=CurrencyConverter)
        cc.convert.return_value = 42.0
        evaluator = CalculatorEvaluator(cc)
        initial = AppState(
            windows=[
                WindowState(window_id="a", title="A"),
                WindowState(window_id="b", title="B"),
            ],
        )
        ws = WorkspaceService(evaluator, initial)
        ws.replace_windows_with(WindowState(window_id="z", title="Z"))
        ids = [s.window_id for s in ws.window_states()]
        assert ids == ["z"]

    def test_active_window_states_previous_uses_last_active(self) -> None:
        cc = Mock(spec=CurrencyConverter)
        cc.convert.return_value = 42.0
        evaluator = CalculatorEvaluator(cc)
        initial = AppState(
            windows=[
                WindowState(window_id="first", title="First"),
                WindowState(window_id="second", title="Second"),
                WindowState(window_id="third", title="Third"),
            ],
            last_active_window_id="second",
        )
        ws = WorkspaceService(evaluator, initial)
        active = ws.active_window_states("previous")
        assert [s.window_id for s in active] == ["second"]

    def test_active_window_states_previous_falls_back_to_last(self) -> None:
        cc = Mock(spec=CurrencyConverter)
        cc.convert.return_value = 42.0
        evaluator = CalculatorEvaluator(cc)
        initial = AppState(
            windows=[
                WindowState(window_id="first", title="First"),
                WindowState(window_id="second", title="Second"),
            ],
            last_active_window_id="deleted-window",
        )
        ws = WorkspaceService(evaluator, initial)
        active = ws.active_window_states("previous")
        assert [s.window_id for s in active] == ["second"]

    def test_set_last_active_window_updates_state(self) -> None:
        cc = Mock(spec=CurrencyConverter)
        cc.convert.return_value = 42.0
        evaluator = CalculatorEvaluator(cc)
        ws = WorkspaceService(evaluator)
        first_id = ws.window_states()[0].window_id
        ws.set_last_active_window(first_id)
        assert ws.last_active_window_id == first_id
        assert ws.snapshot().last_active_window_id == first_id

    def test_set_last_active_window_ignores_unknown_id(self) -> None:
        cc = Mock(spec=CurrencyConverter)
        cc.convert.return_value = 42.0
        evaluator = CalculatorEvaluator(cc)
        ws = WorkspaceService(evaluator)
        ws.set_last_active_window("nonexistent-window")
        assert ws.last_active_window_id is None

    def test_replace_windows_updates_last_active(self) -> None:
        cc = Mock(spec=CurrencyConverter)
        cc.convert.return_value = 42.0
        evaluator = CalculatorEvaluator(cc)
        initial = AppState(
            windows=[WindowState(window_id="old", title="Old")],
            last_active_window_id="old",
        )
        ws = WorkspaceService(evaluator, initial)
        ws.replace_windows_with(WindowState(window_id="fresh", title="Fresh"))
        assert ws.last_active_window_id == "fresh"

    def test_release_window_falls_back_to_previous(self) -> None:
        cc = Mock(spec=CurrencyConverter)
        cc.convert.return_value = 42.0
        evaluator = CalculatorEvaluator(cc)
        initial = AppState(
            windows=[
                WindowState(window_id="a", title="A"),
                WindowState(window_id="b", title="B"),
                WindowState(window_id="c", title="C"),
            ],
        )
        ws = WorkspaceService(evaluator, initial)
        ws.set_last_active_window("a")
        ws.set_last_active_window("b")
        ws.set_last_active_window("c")
        assert ws.last_active_window_id == "c"
        ws.release_window("c")
        assert ws.last_active_window_id == "b"
        ws.release_window("b")
        assert ws.last_active_window_id == "a"
        ws.release_window("a")
        assert ws.last_active_window_id == "a"  # last one to be closed

    def test_release_unknown_window_is_noop(self) -> None:
        cc = Mock(spec=CurrencyConverter)
        cc.convert.return_value = 42.0
        evaluator = CalculatorEvaluator(cc)
        ws = WorkspaceService(evaluator)
        ws.set_last_active_window(ws.window_states()[0].window_id)
        active_before = ws.last_active_window_id
        ws.release_window("nonexistent")
        assert ws.last_active_window_id == active_before

    def test_set_window_geometry_stores_value(self) -> None:
        cc = Mock(spec=CurrencyConverter)
        cc.convert.return_value = 42.0
        evaluator = CalculatorEvaluator(cc)
        ws = WorkspaceService(evaluator)
        wid = ws.window_states()[0].window_id
        ws.set_window_geometry(wid, 100, 200, 800, 500)
        assert ws.get_window_geometry(wid) == (100, 200, 800, 500)

    def test_set_window_geometry_ignores_unknown_window(self) -> None:
        cc = Mock(spec=CurrencyConverter)
        cc.convert.return_value = 42.0
        evaluator = CalculatorEvaluator(cc)
        ws = WorkspaceService(evaluator)
        ws.set_window_geometry("ghost", 0, 0, 100, 100)
        assert ws.get_window_geometry("ghost") is None

    def test_total_enabled_defaults_true(self) -> None:
        cc = Mock(spec=CurrencyConverter)
        cc.convert.return_value = 1.0
        evaluator = CalculatorEvaluator(cc)
        ws = WorkspaceService(evaluator)
        assert ws.total_enabled is True

    def test_set_total_enabled_toggles(self) -> None:
        cc = Mock(spec=CurrencyConverter)
        cc.convert.return_value = 1.0
        evaluator = CalculatorEvaluator(cc)
        ws = WorkspaceService(evaluator)
        ws.set_total_enabled(False)
        assert ws.total_enabled is False
        ws.set_total_enabled(True)
        assert ws.total_enabled is True

    def test_evaluate_window_text_returns_results(self) -> None:
        cc = Mock(spec=CurrencyConverter)
        cc.convert.return_value = 1.0
        evaluator = CalculatorEvaluator(cc)
        ws = WorkspaceService(evaluator)
        wid = ws.window_states()[0].window_id
        ws.set_window_text(wid, "1 + 2\n3 * 4")
        results = ws.evaluate_window_text(wid)
        assert results == ["3", "12"]

    def test_evaluate_window_text_unknown_window(self) -> None:
        cc = Mock(spec=CurrencyConverter)
        cc.convert.return_value = 1.0
        evaluator = CalculatorEvaluator(cc)
        ws = WorkspaceService(evaluator)
        assert ws.evaluate_window_text("ghost") is None

    def test_geometry_round_trips_through_snapshot(self) -> None:
        cc = Mock(spec=CurrencyConverter)
        cc.convert.return_value = 42.0
        evaluator = CalculatorEvaluator(cc)
        ws = WorkspaceService(evaluator)
        wid = ws.window_states()[0].window_id
        ws.set_window_geometry(wid, 50, 60, 700, 400)
        snap = ws.snapshot()
        assert snap.window_geometries[wid] == (50, 60, 700, 400)

    def test_cleanup_drops_geometries_for_missing_windows(self) -> None:
        cc = Mock(spec=CurrencyConverter)
        cc.convert.return_value = 42.0
        evaluator = CalculatorEvaluator(cc)
        ws = WorkspaceService(evaluator)
        wid = ws.window_states()[0].window_id
        ws.set_window_geometry(wid, 50, 60, 700, 400)
        ws.set_window_geometry("ghost", 0, 0, 100, 100)
        ws.cleanup_window_geometries()
        assert wid in ws.window_geometries
        assert "ghost" not in ws.window_geometries
