"""Install, uninstall, and update logic for the portable executable.

Install: copies the running .exe to ./WidgetCalculator/widget-calculator.exe
         and registers it to run on Windows startup.
Uninstall: removes the startup entry and deletes the install directory.
Update: fetches new commits from git, pulls them, rebuilds, and replaces
        the running .exe.

All operations are no-ops on non-Windows platforms (with a printed notice).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

APP_NAME = "WidgetCalculator"
INSTALL_SUBDIR = "WidgetCalculator"
STARTUP_APP_NAME = "WidgetCalculator"


def _is_windows() -> bool:
    return sys.platform == "win32"


def _install_dir() -> Path:
    """Return the install directory (./WidgetCalculator relative to CWD)."""
    return Path.cwd() / INSTALL_SUBDIR


def _exe_name() -> str:
    return f"{APP_NAME}.exe" if _is_windows() else APP_NAME


def _current_exe() -> Path:
    """Return the path of the currently running executable."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve()
    raise RuntimeError("Not running as a packaged executable (sys.frozen is False)")


def _repo_root() -> Path | None:
    """Return the git repo root if CWD is inside a git repo, else None."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
            cwd=Path.cwd(),
        )
        return Path(result.stdout.strip()).resolve()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _run_hidden(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
    """Run a command without flashing a console window on Windows."""
    creationflags = 0
    if _is_windows():
        creationflags = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        creationflags=creationflags,
        **kwargs,  # type: ignore[arg-type]
    )


def install() -> int:
    """Install the app: copy exe to ./WidgetCalculator/ and register startup."""
    if not _is_windows():
        print("Install is only supported on Windows.")
        return 1

    try:
        current = _current_exe()
    except RuntimeError as e:
        print(f"Error: {e}")
        return 1

    target_dir = _install_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    target_exe = target_dir / _exe_name()

    print(f"Copying {current} -> {target_exe}")
    shutil.copy2(current, target_exe)

    from widget_calc.infrastructure.startup_registry import WindowsStartupRegistry

    registry = WindowsStartupRegistry()
    if registry.is_enabled():
        registry.disable()
    registry.enable(str(target_exe))

    print(f"Installed to {target_exe}")
    print("Registered to run on Windows startup.")
    return 0


def uninstall() -> int:
    """Uninstall the app: remove startup entry and delete install directory."""
    if not _is_windows():
        print("Uninstall is only supported on Windows.")
        return 1

    from widget_calc.infrastructure.startup_registry import WindowsStartupRegistry

    registry = WindowsStartupRegistry()
    if registry.is_enabled():
        registry.disable()
        print("Removed from Windows startup.")
    else:
        print("Not registered in Windows startup.")

    target_dir = _install_dir()
    if target_dir.exists():
        shutil.rmtree(target_dir)
        print(f"Deleted {target_dir}")
    else:
        print(f"Install directory not found: {target_dir}")

    return 0


def _git_has_updates(repo: Path) -> bool:
    """Return True if origin has commits not in local HEAD."""
    _run_hidden(["git", "fetch"], cwd=repo)
    local = _run_hidden(["git", "rev-parse", "HEAD"], cwd=repo)
    remote = _run_hidden(["git", "rev-parse", "@{u}"], cwd=repo)
    if local.returncode != 0 or remote.returncode != 0:
        return False
    return local.stdout.strip() != remote.stdout.strip()


def _rebuild_exe(repo: Path) -> Path:
    """Run the build script and return the path to the new exe."""
    build_script = repo / "scripts" / "build.py"
    if not build_script.exists():
        raise FileNotFoundError(f"Build script not found: {build_script}")

    print("Rebuilding executable...")
    env = os.environ.copy()
    env.setdefault("PYTHONPATH", str(repo))
    result = subprocess.run(
        [sys.executable, str(build_script)],
        cwd=repo,
        env=env,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Build failed with exit code {result.returncode}")

    new_exe = repo / "dist" / _exe_name()
    if not new_exe.exists():
        raise FileNotFoundError(f"Build did not produce {new_exe}")
    return new_exe


def _schedule_replacement(new_exe: Path, target_exe: Path) -> None:
    """Replace target_exe with new_exe after the current process exits."""
    import tempfile

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".bat", delete=False, prefix="widget_calc_update_"
    ) as f:
        script_path = f.name
        f.write(
            f'@echo off\n'
            f'timeout /t 2 /nobreak >nul\n'
            f'copy /y "{new_exe}" "{target_exe}"\n'
            f'start "" "{target_exe}"\n'
            f'del "{f.name}"\n'
        )

    subprocess.Popen(
        ["cmd", "/c", script_path],
        creationflags=subprocess.CREATE_NO_WINDOW,  # type: ignore[attr-defined]
    )


def update() -> int:
    """Check for updates, pull, rebuild, and replace the running exe."""
    repo = _repo_root()
    if repo is None:
        print("Error: current directory is not inside a git repository.")
        return 1

    if not _is_windows():
        print("Update is only supported on Windows.")
        return 1

    print(f"Checking for updates in {repo}...")
    if not _git_has_updates(repo):
        print("Already up to date.")
        return 0

    print("New commits found. Pulling...")
    pull = _run_hidden(["git", "pull"], cwd=repo)
    if pull.returncode != 0:
        print(f"git pull failed:\n{pull.stderr}")
        return 1

    try:
        current = _current_exe()
        new_exe = _rebuild_exe(repo)
    except (FileNotFoundError, RuntimeError) as e:
        print(f"Update failed: {e}")
        return 1

    print(f"Replacing {current} with {new_exe.name}...")
    _schedule_replacement(new_exe, current)

    print("Update scheduled. The app will restart in a moment.")
    return 0
