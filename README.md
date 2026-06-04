# Widget Calculator
Modern multi-window calculator widget for Windows, built with clean architecture and PySide6.

## Features
- Resizable calculator windows with side-by-side input and evaluation panes.
- Variables and expressions (`x=1`, `y=1`, `x+y`).
- Percent support (`20%`, `50 * 10%`).
- Constants and math helpers (`pi`, `e`, `sqrt`, `sin`, `log`, etc.).
- Conversions:
  - Metric/units/time/bytes via `pint` (`10 km to m`, `2 h to min`, `1 gb to mb`).
  - Currency via live rates (`20 usd to eur`).
- Global command history.
- System tray integration, background behavior, startup toggle.
- Multiple calculator windows from tray menu.
- Theme personalization with built-in presets (Monokai, Nord, Graphite).

## Architecture
- `widget_calc/domain`: core calculator rules, state models, and theme definitions.
- `widget_calc/application`: workspace use-cases for multi-window state and history.
- `widget_calc/infrastructure`: persistence, startup registry adapter, currency API adapter.
- `widget_calc/presentation/qt`: Qt UI, theme styling, and tray/multi-window controller.

## Setup (uv)
```powershell
uv sync
```

## Run
```powershell
uv run widget-calculator
```

or

```powershell
uv run python main.py
```

## Notes
- The app auto-enables startup on first launch (can be changed from tray menu).
- Closing a window hides it to background; reopen from tray menu.
