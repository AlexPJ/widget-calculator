from __future__ import annotations

import json
from pathlib import Path

import pytest

from widget_calc.domain.models import MAX_OPACITY, AppState, WindowState
from widget_calc.infrastructure.state_store import JsonStateStore


@pytest.fixture
def state_store(tmp_path: Path) -> JsonStateStore:
    return JsonStateStore(tmp_path)


class TestJsonStateStore:
    def test_load_returns_default_when_no_file(self, state_store: JsonStateStore) -> None:
        state = state_store.load()
        assert isinstance(state, AppState)
        assert state.windows == []
        assert state.history == []
        assert state.theme_id == "monokai"
        assert state.startup_initialized is False
        assert state.window_opacity == MAX_OPACITY

    def test_save_and_load_roundtrip(self, state_store: JsonStateStore) -> None:
        original = AppState(
            windows=[WindowState(window_id="w1", title="Calc 1", editor_text="2+2")],
            history=["1+1", "2+2"],
            theme_id="nord",
            startup_initialized=True,
            window_opacity=0.5,
        )
        state_store.save(original)

        loaded = state_store.load()
        assert len(loaded.windows) == 1
        assert loaded.windows[0].window_id == "w1"
        assert loaded.windows[0].editor_text == "2+2"
        assert loaded.history == ["1+1", "2+2"]
        assert loaded.theme_id == "nord"
        assert loaded.startup_initialized is True
        assert loaded.window_opacity == 0.5

    def test_save_and_load_multiple_windows(self, state_store: JsonStateStore) -> None:
        original = AppState(
            windows=[
                WindowState(window_id="w1", title="Calc 1", editor_text="1+1"),
                WindowState(window_id="w2", title="Calc 2", editor_text="2*3"),
            ],
            history=[],
        )
        state_store.save(original)
        loaded = state_store.load()
        assert len(loaded.windows) == 2
        assert loaded.windows[1].editor_text == "2*3"

    def test_corrupted_json_returns_default(self, state_store: JsonStateStore) -> None:
        state_store.state_path.write_text("not valid json", encoding="utf-8")
        state = state_store.load()
        assert isinstance(state, AppState)
        assert state.windows == []

    def test_empty_json_returns_default(self, state_store: JsonStateStore) -> None:
        state_store.state_path.write_text("", encoding="utf-8")
        state = state_store.load()
        assert isinstance(state, AppState)

    def test_legacy_format_with_editor_text(self, state_store: JsonStateStore) -> None:
        payload = {"editor_text": "legacy=1", "history": ["test"], "theme_id": "graphite"}
        state_store.state_path.write_text(json.dumps(payload), encoding="utf-8")
        state = state_store.load()
        assert len(state.windows) == 1
        assert state.windows[0].editor_text == "legacy=1"
        assert state.history == ["test"]
        assert state.theme_id == "graphite"

    def test_atomic_write_doesnt_corrupt(self, state_store: JsonStateStore) -> None:
        original = AppState(
            windows=[WindowState(window_id="w1", title="Calc 1", editor_text="42")],
            history=["42"],
        )
        state_store.save(original)
        content = state_store.state_path.read_text(encoding="utf-8")
        parsed = json.loads(content)
        assert parsed["windows"][0]["editor_text"] == "42"

    def test_opacity_round_trip(self, state_store: JsonStateStore) -> None:
        state_store.save(AppState(window_opacity=0.75))
        loaded = state_store.load()
        assert loaded.window_opacity == 0.75

    def test_opacity_missing_in_file_defaults_to_max(self, state_store: JsonStateStore) -> None:
        state_store.state_path.write_text(json.dumps({"theme_id": "nord"}), encoding="utf-8")
        loaded = state_store.load()
        assert loaded.window_opacity == MAX_OPACITY

    @pytest.mark.parametrize("bad", [-0.1, 1.5, "abc", None, 2.0])
    def test_opacity_invalid_value_normalized_to_max(self, state_store: JsonStateStore, bad: object) -> None:
        state_store.state_path.write_text(json.dumps({"window_opacity": bad}), encoding="utf-8")
        loaded = state_store.load()
        assert loaded.window_opacity == MAX_OPACITY

    def test_opacity_persisted_to_disk(self, state_store: JsonStateStore) -> None:
        state_store.save(AppState(window_opacity=0.6))
        parsed = json.loads(state_store.state_path.read_text(encoding="utf-8"))
        assert parsed["window_opacity"] == 0.6

    def test_opacity_invalid_in_state_normalized_on_save(self, state_store: JsonStateStore) -> None:
        state_store.save(AppState(window_opacity=5.0))
        parsed = json.loads(state_store.state_path.read_text(encoding="utf-8"))
        assert parsed["window_opacity"] == MAX_OPACITY

    def test_window_mode_round_trip(self, state_store: JsonStateStore) -> None:
        state_store.save(AppState(window_mode="previous"))
        loaded = state_store.load()
        assert loaded.window_mode == "previous"

    def test_window_mode_missing_in_file_defaults_to_both(self, state_store: JsonStateStore) -> None:
        state_store.state_path.write_text(json.dumps({"theme_id": "nord"}), encoding="utf-8")
        loaded = state_store.load()
        assert loaded.window_mode == "both"

    @pytest.mark.parametrize("bad", ["garbage", None, 42, ""])
    def test_window_mode_invalid_in_file_falls_back_to_both(
        self, state_store: JsonStateStore, bad: object
    ) -> None:
        state_store.state_path.write_text(json.dumps({"window_mode": bad}), encoding="utf-8")
        loaded = state_store.load()
        assert loaded.window_mode == "both"

    def test_window_mode_persisted_to_disk(self, state_store: JsonStateStore) -> None:
        state_store.save(AppState(window_mode="new"))
        parsed = json.loads(state_store.state_path.read_text(encoding="utf-8"))
        assert parsed["window_mode"] == "new"

    def test_last_active_window_id_round_trip(self, state_store: JsonStateStore) -> None:
        state_store.save(
            AppState(
                windows=[WindowState(window_id="abc", title="A")],
                last_active_window_id="abc",
            )
        )
        loaded = state_store.load()
        assert loaded.last_active_window_id == "abc"

    def test_last_active_window_id_missing_defaults_to_none(
        self, state_store: JsonStateStore
    ) -> None:
        state_store.state_path.write_text(json.dumps({"theme_id": "nord"}), encoding="utf-8")
        loaded = state_store.load()
        assert loaded.last_active_window_id is None

    def test_window_geometries_round_trip(self, state_store: JsonStateStore) -> None:
        state_store.save(
            AppState(
                windows=[WindowState(window_id="wid-1", title="A")],
                window_geometries={"wid-1": (10, 20, 800, 600)},
            )
        )
        loaded = state_store.load()
        assert loaded.window_geometries == {"wid-1": (10, 20, 800, 600)}

    def test_window_geometries_missing_defaults_to_empty(
        self, state_store: JsonStateStore
    ) -> None:
        state_store.state_path.write_text(json.dumps({"theme_id": "nord"}), encoding="utf-8")
        loaded = state_store.load()
        assert loaded.window_geometries == {}

    @pytest.mark.parametrize(
        "bad",
        [
            {"wid": "not-a-list"},
            {"wid": [1, 2, 3]},
            {"wid": [1, 2, 3, -10]},
            {"wid": [1, 2, 0, 100]},
        ],
    )
    def test_window_geometries_invalid_values_skipped(
        self, state_store: JsonStateStore, bad: object
    ) -> None:
        state_store.state_path.write_text(json.dumps({"window_geometries": bad}), encoding="utf-8")
        loaded = state_store.load()
        assert loaded.window_geometries == {}

    def test_total_enabled_round_trip(self, state_store: JsonStateStore) -> None:
        state_store.save(AppState(windows=[WindowState(window_id="w", title="t")], total_enabled=False))
        loaded = state_store.load()
        assert loaded.total_enabled is False

    def test_total_enabled_missing_defaults_true(
        self, state_store: JsonStateStore
    ) -> None:
        state_store.state_path.write_text(json.dumps({"theme_id": "nord"}), encoding="utf-8")
        loaded = state_store.load()
        assert loaded.total_enabled is True
