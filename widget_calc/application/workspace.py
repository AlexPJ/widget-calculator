from __future__ import annotations

from uuid import uuid4

from widget_calc.domain.calculator import CalculatorEvaluator
from widget_calc.domain.models import (
    MAX_HISTORY_ITEMS,
    AppState,
    WindowState,
    normalize_opacity,
    normalize_window_mode,
)
from widget_calc.domain.themes import DEFAULT_THEME_ID, get_theme

__all__ = ["WorkspaceService"]


class WorkspaceService:
    def __init__(self, evaluator: CalculatorEvaluator, initial_state: AppState | None = None) -> None:
        self._evaluator = evaluator
        self._windows: dict[str, WindowState] = {}
        self._window_order: list[str] = []
        self._focus_history: list[str] = []
        self._window_counter = 0

        state = initial_state or AppState()
        self.history: list[str] = [str(item).strip() for item in state.history if str(item).strip()][-MAX_HISTORY_ITEMS:]
        # Mark where the current session begins. Everything before this index
        # is from the previous session; everything from here on is added during
        # the current session. On next startup, the loaded history becomes the
        # new "previous session" and a fresh current session starts.
        self._session_start: int = len(self.history)
        self.theme_id = get_theme(state.theme_id).theme_id if state.theme_id else DEFAULT_THEME_ID
        self.startup_initialized = state.startup_initialized
        self.window_opacity: float = normalize_opacity(state.window_opacity)
        self.window_mode: str = normalize_window_mode(state.window_mode)
        self.last_active_window_id: str | None = state.last_active_window_id
        self.window_geometries: dict[str, tuple[int, int, int, int]] = dict(state.window_geometries)
        self.total_enabled: bool = bool(state.total_enabled)

        if state.windows:
            for window in state.windows:
                self._register_window(window)
        else:
            self.create_window()

    def _register_window(self, window: WindowState) -> None:
        normalized = WindowState(
            window_id=window.window_id,
            title=window.title or self._next_window_title(),
            editor_text=window.editor_text,
        )
        self._windows[normalized.window_id] = normalized
        if normalized.window_id not in self._window_order:
            self._window_order.append(normalized.window_id)

    def _next_window_title(self) -> str:
        self._window_counter += 1
        return f"Calculator {self._window_counter}"

    def create_window(self, editor_text: str = "") -> WindowState:
        window = WindowState(window_id=uuid4().hex[:10], title=self._next_window_title(), editor_text=editor_text)
        self._register_window(window)
        return self._windows[window.window_id]

    def window_states(self) -> list[WindowState]:
        return [self._copy_window(self._windows[window_id]) for window_id in self._window_order if window_id in self._windows]

    def evaluate_window(self, window_id: str, editor_text: str) -> list[str]:
        self._windows[window_id].editor_text = editor_text
        lines = editor_text.splitlines()
        self._record_history(lines)
        return self._evaluator.evaluate_lines(lines)

    def set_window_text(self, window_id: str, editor_text: str) -> None:
        self._windows[window_id].editor_text = editor_text

    def set_theme(self, theme_id: str) -> str:
        self.theme_id = get_theme(theme_id).theme_id
        return self.theme_id

    def set_window_opacity(self, opacity: float) -> float:
        resolved = normalize_opacity(opacity)
        self.window_opacity = resolved
        return resolved

    def set_window_mode(self, mode: str) -> str:
        resolved = normalize_window_mode(mode)
        self.window_mode = resolved
        return resolved

    def active_window_states(self, mode: str | None = None) -> list[WindowState]:
        """Return the windows that should be visible for the given mode.

        - previous: the previously active window (falls back to the most recent).
        - new: a single fresh empty window.
        - both: all saved windows.
        """
        effective = normalize_window_mode(mode) if mode is not None else self.window_mode
        if effective == "new":
            return []
        if effective == "previous":
            ordered = self.window_states()
            if not ordered:
                return []
            if self.last_active_window_id is not None:
                for state in ordered:
                    if state.window_id == self.last_active_window_id:
                        return [state]
            return ordered[-1:]
        return self.window_states()

    def set_last_active_window(self, window_id: str | None) -> None:
        if window_id is not None and window_id not in self._windows:
            return
        if window_id is not None and window_id != self.last_active_window_id:
            if window_id in self._focus_history:
                self._focus_history.remove(window_id)
            self._focus_history.insert(0, window_id)
        self.last_active_window_id = window_id

    def release_window(self, window_id: str) -> None:
        """Remove a window from the focus history. If it was active, fall back to the next."""
        if window_id in self._focus_history:
            self._focus_history.remove(window_id)
        if self.last_active_window_id == window_id:
            self.last_active_window_id = self._focus_history[0] if self._focus_history else window_id

    def get_window_geometry(self, window_id: str) -> tuple[int, int, int, int] | None:
        return self.window_geometries.get(window_id)

    def set_window_geometry(self, window_id: str, x: int, y: int, width: int, height: int) -> None:
        if window_id not in self._windows:
            return
        self.window_geometries[window_id] = (int(x), int(y), int(width), int(height))

    def set_total_enabled(self, enabled: bool) -> bool:
        resolved = bool(enabled)
        self.total_enabled = resolved
        return resolved

    def evaluate_window_text(self, window_id: str) -> list[str] | None:
        state = self._windows.get(window_id)
        if state is None:
            return None
        return self._evaluator.evaluate_lines(state.editor_text.splitlines())

    def cleanup_window_geometries(self) -> None:
        """Drop geometries for windows that no longer exist."""
        self.window_geometries = {
            wid: geom for wid, geom in self.window_geometries.items() if wid in self._windows
        }

    def replace_windows_with(self, window: WindowState) -> None:
        """Clear all saved windows and register a single replacement."""
        self._windows.clear()
        self._window_order.clear()
        self._register_window(window)
        self.last_active_window_id = window.window_id

    def _record_history(self, lines: list[str]) -> None:
        for raw_line in lines:
            command = raw_line.strip()
            if not command:
                continue
            if self.history and self.history[-1] == command:
                continue
            self.history.append(command)

        if len(self.history) > MAX_HISTORY_ITEMS:
            self.history = self.history[-MAX_HISTORY_ITEMS:]
            self._session_start = max(0, self._session_start - (len(self.history) - MAX_HISTORY_ITEMS))

    def clear_history(self) -> None:
        """Remove all commands from the history (both sessions)."""
        self.history.clear()
        self._session_start = 0

    def snapshot(self) -> AppState:
        return AppState(
            windows=self.window_states(),
            history=list(self.history),
            theme_id=self.theme_id,
            startup_initialized=self.startup_initialized,
            window_opacity=self.window_opacity,
            window_mode=self.window_mode,
            last_active_window_id=self.last_active_window_id,
            window_geometries=dict(self.window_geometries),
            total_enabled=self.total_enabled,
        )

    @staticmethod
    def _copy_window(window: WindowState) -> WindowState:
        return WindowState(window_id=window.window_id, title=window.title, editor_text=window.editor_text)
