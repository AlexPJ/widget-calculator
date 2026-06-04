from __future__ import annotations

import json
import os
from pathlib import Path

from widget_calc.domain.models import (
    DEFAULT_WINDOW_MODE,
    MAX_HISTORY_ITEMS,
    MAX_OPACITY,
    AppState,
    WindowState,
    normalize_opacity,
    normalize_window_mode,
)
from widget_calc.domain.themes import DEFAULT_THEME_ID, get_theme

APP_DIR_NAME = "WidgetCalculatorWidget"
STATE_FILE_NAME = "state.json"


class JsonStateStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or self._default_dir()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.base_dir / STATE_FILE_NAME

    @staticmethod
    def _default_dir() -> Path:
        app_data = os.getenv("APPDATA")
        if app_data:
            return Path(app_data) / APP_DIR_NAME
        return Path.home() / f".{APP_DIR_NAME.lower()}"

    def load(self) -> AppState:
        if not self.state_path.exists():
            return AppState()

        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        except Exception:
            return AppState()

        windows = self._parse_windows(payload)
        history = [str(item).strip() for item in payload.get("history", []) if str(item).strip()][-MAX_HISTORY_ITEMS:]
        startup_initialized = bool(payload.get("startup_initialized", False))
        theme_id = get_theme(str(payload.get("theme_id", DEFAULT_THEME_ID))).theme_id
        window_opacity = normalize_opacity(payload.get("window_opacity", MAX_OPACITY))
        window_mode = normalize_window_mode(payload.get("window_mode", DEFAULT_WINDOW_MODE))
        raw_active = payload.get("last_active_window_id")
        last_active_window_id = str(raw_active) if raw_active else None
        window_geometries = self._parse_geometries(payload.get("window_geometries", {}))
        total_enabled = bool(payload.get("total_enabled", True))

        return AppState(
            windows=windows,
            history=history,
            theme_id=theme_id,
            startup_initialized=startup_initialized,
            window_opacity=window_opacity,
            window_mode=window_mode,
            last_active_window_id=last_active_window_id,
            window_geometries=window_geometries,
            total_enabled=total_enabled,
        )

    def save(self, state: AppState) -> None:
        payload = {
            "windows": [
                {
                    "window_id": window.window_id,
                    "title": window.title,
                    "editor_text": window.editor_text,
                }
                for window in state.windows
            ],
            "history": list(state.history)[-MAX_HISTORY_ITEMS:],
            "theme_id": state.theme_id,
            "startup_initialized": bool(state.startup_initialized),
            "window_opacity": normalize_opacity(state.window_opacity),
            "window_mode": normalize_window_mode(state.window_mode),
            "last_active_window_id": state.last_active_window_id,
            "window_geometries": {
                wid: [geom[0], geom[1], geom[2], geom[3]]
                for wid, geom in state.window_geometries.items()
            },
            "total_enabled": bool(state.total_enabled),
        }

        temp_path = self.state_path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temp_path.replace(self.state_path)

    @staticmethod
    def _parse_geometries(raw: object) -> dict[str, tuple[int, int, int, int]]:
        parsed: dict[str, tuple[int, int, int, int]] = {}
        if not isinstance(raw, dict):
            return parsed
        for window_id, geom in raw.items():
            if not isinstance(geom, (list, tuple)) or len(geom) != 4:
                continue
            try:
                x, y, w, h = (int(geom[0]), int(geom[1]), int(geom[2]), int(geom[3]))
            except (TypeError, ValueError):
                continue
            if w <= 0 or h <= 0:
                continue
            parsed[str(window_id)] = (x, y, w, h)
        return parsed

    @staticmethod
    def _parse_windows(payload: dict[str, object]) -> list[WindowState]:
        parsed_windows: list[WindowState] = []
        raw_windows = payload.get("windows")

        if isinstance(raw_windows, list):
            for index, item in enumerate(raw_windows, start=1):
                if not isinstance(item, dict):
                    continue
                window_id = str(item.get("window_id") or f"window-{index}")
                title = str(item.get("title") or f"Calculator {index}")
                editor_text = str(item.get("editor_text", ""))
                parsed_windows.append(WindowState(window_id=window_id, title=title, editor_text=editor_text))

        if parsed_windows:
            return parsed_windows

        legacy_text = str(payload.get("editor_text", ""))
        return [WindowState(window_id="window-1", title="Calculator 1", editor_text=legacy_text)]
