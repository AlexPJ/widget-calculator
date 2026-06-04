from __future__ import annotations

from dataclasses import dataclass, field

MAX_HISTORY_ITEMS = 500
MIN_OPACITY = 0.25
MAX_OPACITY = 1.0

WINDOW_MODE_PREVIOUS = "previous"
WINDOW_MODE_NEW = "new"
WINDOW_MODE_BOTH = "both"
VALID_WINDOW_MODES = (WINDOW_MODE_PREVIOUS, WINDOW_MODE_NEW, WINDOW_MODE_BOTH)
DEFAULT_WINDOW_MODE = WINDOW_MODE_BOTH


def normalize_opacity(value: object) -> float:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return MAX_OPACITY
    if number != number:  # NaN check
        return MAX_OPACITY
    if number < MIN_OPACITY or number > MAX_OPACITY:
        return MAX_OPACITY
    return number


def normalize_window_mode(value: object) -> str:
    if isinstance(value, str) and value in VALID_WINDOW_MODES:
        return value
    return DEFAULT_WINDOW_MODE


@dataclass(slots=True)
class WindowState:
    window_id: str
    title: str
    editor_text: str = ""


@dataclass(slots=True)
class AppState:
    windows: list[WindowState] = field(default_factory=list)
    history: list[str] = field(default_factory=list)
    theme_id: str = "monokai"
    startup_initialized: bool = False
    window_opacity: float = MAX_OPACITY
    window_mode: str = DEFAULT_WINDOW_MODE
    last_active_window_id: str | None = None
    window_geometries: dict[str, tuple[int, int, int, int]] = field(default_factory=dict)
    total_enabled: bool = True

    def __post_init__(self) -> None:
        self.window_opacity = normalize_opacity(self.window_opacity)
        self.window_mode = normalize_window_mode(self.window_mode)
