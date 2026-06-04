from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING or sys.platform.startswith("win"):
    import winreg
else:
    winreg = None  # type: ignore[assignment]

RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"


class WindowsStartupRegistry:
    def __init__(self, value_name: str = "WidgetCalculatorWidget") -> None:
        self._value_name = value_name

    def is_enabled(self) -> bool:
        if not self._is_windows():
            return False

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_READ) as key:
                value, _ = winreg.QueryValueEx(key, self._value_name)
                return bool(str(value).strip())
        except FileNotFoundError:
            return False
        except OSError:
            return False

    def set_enabled(self, enabled: bool) -> None:
        if not self._is_windows():
            return

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                winreg.SetValueEx(key, self._value_name, 0, winreg.REG_SZ, self._build_startup_command())
                return

            try:
                winreg.DeleteValue(key, self._value_name)
            except FileNotFoundError:
                return

    @staticmethod
    def _is_windows() -> bool:
        return winreg is not None and sys.platform.startswith("win")

    @staticmethod
    def _build_startup_command() -> str:
        if getattr(sys, "frozen", False):
            executable = Path(sys.executable)
            return f'"{executable}" --background'

        root_dir = Path(__file__).resolve().parents[2]
        main_file = root_dir / "main.py"
        return f'"{sys.executable}" "{main_file}" --background'
