# Problem
Build a small, resizable Windows widget-style calculator app with a dark UI, line-by-line evaluation, variables, constants (`pi`, `e`), percentages, unit conversions (metric/time/bytes), currency conversion, command history, system tray behavior, and automatic startup on boot.
## Current state
No existing project for this app exists in the current workspace, so implementation will be created in a new directory from scratch.
## Proposed changes
Restructure the app with a clean-architecture layout separating domain logic (calculator use cases), infrastructure adapters (currency API, persistence, startup registry), and presentation (Qt windows/controllers).
Implement multi-window support so the tray can create and manage multiple independent calculator widget windows, each with its own editor content and evaluated result pane.
Implement a line evaluator with assignment support (`name = expression`) where assignment lines return empty output and later lines can reference assigned variables.
Add constants (`pi`, `e`) and percentage preprocessing so inputs like `10%` evaluate as fractional values in expressions.
Support conversions with `to` syntax. Use Pint for metric/time/bytes conversions and an HTTP currency provider for currency pairs like `USD -> EUR`.
Upgrade the UI to a modern widget style and add theme personalization with built-in presets including Monokai.
Persist global history, per-window content, and selected theme to local app data so state is restored across launches.
Integrate a system tray icon with actions for creating new calculator windows, showing existing windows, theme selection, startup toggle, and quit.
Add Windows startup registration through the current-user Run registry key, enabled by default and user-controllable.
Include packaging and run instructions (`requirements.txt`, startup entrypoint) and perform a local syntax/test smoke check before handoff.