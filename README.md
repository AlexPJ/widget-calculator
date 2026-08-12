<div align="center">

# 🧮 Widget Calculator

### A tiny, always-there calculator widget for Windows — variables, units, live currency and running totals

[![Release](https://img.shields.io/github/v/release/AlexPJ/widget-calculator?style=for-the-badge&color=a6e22e)](https://github.com/AlexPJ/widget-calculator/releases/latest)
[![Downloads](https://img.shields.io/github/downloads/AlexPJ/widget-calculator/total?style=for-the-badge&color=a6e22e)](https://github.com/AlexPJ/widget-calculator/releases)
[![License](https://img.shields.io/github/license/AlexPJ/widget-calculator?style=for-the-badge&color=a6e22e)](LICENSE)
[![Windows](https://img.shields.io/badge/Windows-10%20%7C%2011-0078D6?style=for-the-badge&logo=windows&logoColor=white)](#)
[![Rust + Tauri](https://img.shields.io/badge/Rust%20%2B%20Tauri-2-000?style=for-the-badge&logo=tauri&logoColor=white)](#)

**[⬇️ Download the latest version](https://github.com/AlexPJ/widget-calculator/releases/latest)**

</div>

---

Type a column of expressions, read the answers next to them. Every line is
evaluated as you type, variables carry from one line to the next, and the bar
at the bottom keeps a running total. It lives in the system tray, floats above
your other windows, and starts with Windows if you want it to.

## ✨ Features

- 🔢 **Line-by-line evaluation** — the left column is what you type, the right column is the answer. Nothing to press.
- 📝 **Variables** — `a = 64295.11`, then `b = a/12` on the next line. Assignments show no result, keeping the column clean.
- 📐 **Unit conversions** — `10 km to m`, `2 h to min`, `1 gb to mb`, `20 degC to degF`. Length, mass, time, data, temperature, area, volume, speed, energy, power, pressure, frequency and angles.
- 💱 **Live currency** — `20 usd to eur` uses real exchange rates, cached for 30 minutes so a whole sheet costs one request.
- ％ **Percentages** — `200 * 10%` is 20, `100% + 50%` is 1.5.
- 🧪 **Maths functions** — `sqrt`, `sin`, `cos`, `tan`, `log`, `ln`, `exp`, `round`, `min`, `max`, plus `pi`, `e` and `tau`.
- 🕐 **Clocks** — `now('Europe/Madrid')` prints the current time in any IANA time zone.
- ∑ **Running total** — sums every numeric result line, ignoring errors and quantities. Toggle it off from the bar itself.
- 🪟 **As many windows as you like** — each with its own contents, all restored where you left them.
- 🕘 **Shared command history** — the last 500 commands, across every window and session.
- 🎨 **Three themes** (Monokai, Nord, Graphite), adjustable **opacity**, and an **always on top** toggle.
- 🔔 **Lives in the system tray** — close the last window and it hides there instead of quitting.
- 🔄 **Signed automatic updates** built into the app.

## 📊 Size

No Node, no bundler, no packaged browser — the UI is plain static files
embedded in the binary, drawn by the WebView2 runtime Windows already ships.

| Artifact | Size |
| --- | --- |
| **Installer** (NSIS `-setup.exe`) | **1.94 MB** |
| Standalone executable | 6.02 MB |
| Bundled frontend (HTML/CSS/JS) | 36 KB |

## ⬇️ Download and install

1. Go to the **[releases page](https://github.com/AlexPJ/widget-calculator/releases/latest)**.
2. Download `WidgetCalculator_x.y.z_x64-setup.exe`.
3. Run it. Windows SmartScreen may warn about an unknown publisher: *More info → Run anyway*.

> Requirements: Windows 10/11 (x64). WebView2 ships with Windows 11 and with most up-to-date Windows 10 installs.

Once installed, the app updates itself: **Settings → Check for updates**.

## 🚀 Quick start

```
x = 1
y = 2
x + y            →  3
10 km to m       →  10000 m
2 h to min       →  120 min
20 usd to eur    →  18.4 EUR
200 * 10%        →  20
sqrt(9)          →  3
now('UTC')       →  2026-08-09 01:13:44 UTC
```

| Action | How |
| --- | --- |
| New window | `Ctrl+N`, or the tray menu |
| Settings | the gear at the bottom-left, or `Ctrl+,` |
| Command history | `Ctrl+H` |
| Menu bar | press `Alt` |
| Help | `F1` |
| Copy a result | click the line |
| Copy the total | click the total |
| Quit | `Ctrl+Q`, or tray → Quit |

Closing a window **discards** it and its contents — except the last one, which
**hides** to the tray so nothing is lost and the app stays one click away. To
quit for real, use the tray menu or `Ctrl+Q`.

## 🧰 How the calculator works

**Assignments** use `name = expression`. The line itself shows nothing, and
every later line in the same window can use the name.

**Conversions** use `to`. The left side must carry a unit
(`10 km to m` works, `10 to m` does not). Three-letter codes that are not
units are treated as currencies, so `20 usd to eur` hits the rate API while
`120 sec to min` stays a plain time conversion.

**Percent** is a postfix operator: `10%` is `0.1` everywhere it appears.

**Numbers** print with 12 significant digits, switching to scientific notation
outside `1e-5 … 1e12`.

**Units** combine on their own: `100 m / 10 s` gives `10 m/s`. Adding
mismatched dimensions is an error rather than a silent wrong answer.

## 🛠️ Build from source

Requirements: [Rust](https://rustup.rs) (rustup) and VS Build Tools with C++.

```powershell
git clone https://github.com/AlexPJ/widget-calculator.git
cd widget-calculator/src-tauri
cargo test                         # 88 unit tests
cargo build --release              # exe at target/release/widget-calculator.exe
```

For the installer:

```powershell
cargo install tauri-cli --locked
cargo tauri build
```

The release profile is tuned for size (`opt-level="z"`, LTO, `strip`,
`panic=abort`).

### Architecture

```
src-tauri/src/
  core/         Domain: expression parser, unit system, themes, state shapes
  application/  Workspace use cases: windows, history, preferences
  infra/        Adapters: JSON state file, currency API, legacy migration
  app/          Tauri glue: commands, tray, window management
ui/             Static frontend (no Node, no bundler): HTML/CSS/JS
```

The domain layer has no Tauri, HTTP or filesystem dependencies, which is why
almost all of the test suite runs against plain functions.

The expression engine is hand-written: a tokenizer and Pratt parser over a
value type that is either a number, a dimensioned quantity or text. Units are a
static table mapping each name onto base units, so dimensional analysis is
exponent arithmetic on a fixed-size array.

## 🔄 Publishing a new version (maintainers)

Releases are built and signed by GitHub Actions.

1. Bump the version in `src-tauri/tauri.conf.json` **and** `src-tauri/Cargo.toml`.
2. Commit, then tag and push:
   ```powershell
   git tag v0.2.0
   git push origin v0.2.0
   ```
3. The **Release** workflow builds on a Windows runner, signs the installer and
   publishes a GitHub release with the `.exe`, its `.sig` and `latest.json`.

The installed app compares its version against `latest.json` (served from
`.../releases/latest/download/latest.json`) and offers to update.

<details>
<summary>One-time setup: updater signing secrets</summary>

The signing keypair lives in `src-tauri/widgetcalc.key` (private, git-ignored)
and `src-tauri/widgetcalc.key.pub` (public, committed, and pasted into
`tauri.conf.json` as `plugins.updater.pubkey`).

Add one repository secret under **Settings → Secrets and variables → Actions**:

| Secret | Value |
| --- | --- |
| `TAURI_SIGNING_PRIVATE_KEY` | the full contents of `src-tauri/widgetcalc.key` |

The key has no password, and the workflow passes an empty one as a literal.
Do not move that into a secret: GitHub does not reliably export an empty
secret into the job, and the signer then fails with *"Wrong password for that
key"* after an otherwise successful build.

To copy the private key to the clipboard:

```powershell
Get-Content src-tauri\widgetcalc.key -Raw | Set-Clipboard
```

Keep a backup of that file somewhere safe. Lose it and existing installs can no
longer verify updates.

</details>

<details>
<summary>Building a release locally instead</summary>

```powershell
$env:TAURI_SIGNING_PRIVATE_KEY = Get-Content src-tauri\widgetcalc.key -Raw
$env:TAURI_SIGNING_PRIVATE_KEY_PASSWORD = ""
cargo tauri build
```

The installer and its signature land in
`src-tauri/target/release/bundle/nsis/`.

</details>

## 📄 License

[MIT](LICENSE) © Alejandro Padilla

<div align="center">
<sub>Built with Rust + Tauri. Small by design.</sub>
</div>
