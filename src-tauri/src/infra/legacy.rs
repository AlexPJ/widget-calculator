//! One-off migration from the PySide6 version.
//!
//! That version registered its own `Run` entry pointing at `python.exe main.py`.
//! Once this build replaces it, that entry would launch a script that is no
//! longer there, so the first run hands the job over to the Tauri autostart
//! plugin and removes the stale value.

/// The value name the Python version used under
/// `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`.
#[cfg(windows)]
const LEGACY_VALUE_NAME: &str = "WidgetCalculatorWidget";

#[cfg(windows)]
const RUN_KEY_PATH: &str = r"Software\Microsoft\Windows\CurrentVersion\Run";

/// Remove the old entry. Returns `true` when one was actually there, which
/// tells the caller the user had start-up enabled and it should be preserved.
#[cfg(windows)]
pub fn remove_legacy_startup_entry() -> bool {
    use winreg::enums::{HKEY_CURRENT_USER, KEY_READ, KEY_SET_VALUE};
    use winreg::RegKey;

    let Ok(run_key) = RegKey::predef(HKEY_CURRENT_USER)
        .open_subkey_with_flags(RUN_KEY_PATH, KEY_READ | KEY_SET_VALUE)
    else {
        return false;
    };
    if run_key.get_value::<String, _>(LEGACY_VALUE_NAME).is_err() {
        return false;
    }
    run_key.delete_value(LEGACY_VALUE_NAME).is_ok()
}

#[cfg(not(windows))]
pub fn remove_legacy_startup_entry() -> bool {
    false
}
