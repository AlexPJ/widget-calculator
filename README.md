<div align="center">

# 🧮 Widget Calculator

### A tiny, always-there calculator widget — variables, units, live currency and running totals

[![Release](https://img.shields.io/github/v/release/AlexPJ/widget-calculator?style=for-the-badge&color=a6e22e)](https://github.com/AlexPJ/widget-calculator/releases/latest)
[![Downloads](https://img.shields.io/github/downloads/AlexPJ/widget-calculator/total?style=for-the-badge&color=a6e22e)](https://github.com/AlexPJ/widget-calculator/releases)
[![License](https://img.shields.io/github/license/AlexPJ/widget-calculator?style=for-the-badge&color=a6e22e)](LICENSE)
[![Windows](https://img.shields.io/badge/Windows-10%20%7C%2011-0078D6?style=for-the-badge&logo=windows&logoColor=white)](#)
[![macOS](https://img.shields.io/badge/macOS-10.15%2B-000000?style=for-the-badge&logo=apple&logoColor=white)](#)
[![Linux](https://img.shields.io/badge/Linux-deb%20%7C%20rpm%20%7C%20AppImage-FCC624?style=for-the-badge&logo=linux&logoColor=black)](#)
[![Rust + Tauri](https://img.shields.io/badge/Rust%20%2B%20Tauri-2-000?style=for-the-badge&logo=tauri&logoColor=white)](#)

**[⬇️ Download the latest version](https://github.com/AlexPJ/widget-calculator/releases/latest)**

</div>

---

Type a column of expressions, read the answers next to them. Every line is
evaluated as you type, variables carry from one line to the next, and the bar
at the bottom keeps a running total. It lives in the system tray, floats above
your other windows, and starts with your desktop session if you want it to.

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

No Node, no bundler, no packaged browser — the UI is 37 KB of plain static
files embedded in the binary, drawn by the webview each OS already ships:
WebView2 on Windows, WKWebView on macOS, WebKitGTK on Linux.

| Platform | Installer | Installed application |
| --- | --- | --- |
| Windows | **1.94 MB** (NSIS `-setup.exe`) | 6.02 MB |
| macOS | **4.78 MB** (universal `.dmg`) | 10.98 MB |

The published macOS build is universal, so it carries both an Intel and an
Apple Silicon copy of the binary. Building for one architecture alone roughly
halves it: 2.37 MB and 5.00 MB on Apple Silicon.

Linux sizes are not listed yet — the `.deb`, `.rpm` and `.AppImage` land with
the first release built after Linux was added.

## ⬇️ Download and install

Everything is on the **[releases page](https://github.com/AlexPJ/widget-calculator/releases/latest)**.

**Windows** — download `WidgetCalculator_x.y.z_x64-setup.exe` and run it.
SmartScreen may warn about an unknown publisher: *More info → Run anyway*.
Needs Windows 10/11 (x64); WebView2 ships with Windows 11 and with most
up-to-date Windows 10 installs.

**macOS** — download `WidgetCalculator_x.y.z_universal.dmg`, open it and drag
the app to Applications. Needs macOS 10.15 or newer; runs natively on both
Apple Silicon and Intel. The app is signed ad-hoc rather than notarized, so
macOS blocks the first launch — open **System Settings → Privacy & Security**
and press **Open Anyway**.

**Linux** — download the `.AppImage`, make it executable and run it, or install
the `.deb` / `.rpm` with your package manager. Needs WebKitGTK 4.1 and, for the
tray icon, an AppIndicator-compatible desktop. The AppImage is the only Linux
format the in-app updater can replace in place; `.deb` and `.rpm` installs
update through your package manager instead.

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

| Action | Windows & Linux | macOS |
| --- | --- | --- |
| New window | `Ctrl+N`, or the tray menu | `⌘N`, or the tray menu |
| Settings | the gear at the bottom-left, or `Ctrl+,` | the gear, or `⌘,` |
| Command history | `Ctrl+H` | `⌘Y` |
| Menu bar | press `Alt` | press `⌥` |
| Help | `F1` | `F1` or `⌘?` |
| Quit | `Ctrl+Q`, or tray → Quit | `⌘Q`, or tray → Quit |

Click a result line to copy it, and click the total to copy the total.

Two macOS shortcuts are not just Ctrl swapped for Command. `⌘H` is the
system-wide *hide application* and never reaches the app, so history follows
Safari onto `⌘Y`. And `F1` is a brightness key on a Mac keyboard unless you
have turned that off, so help also answers to `⌘?`.

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

[Rust](https://rustup.rs) via rustup, plus your platform's toolchain:

| Platform | Also needs |
| --- | --- |
| Windows | VS Build Tools with C++ |
| macOS | Xcode Command Line Tools — `xcode-select --install` |
| Linux | `libwebkit2gtk-4.1-dev libayatana-appindicator3-dev librsvg2-dev libxdo-dev libssl-dev patchelf build-essential` |

```bash
git clone https://github.com/AlexPJ/widget-calculator.git
cd widget-calculator/src-tauri
cargo test                         # 90 unit tests
cargo build --release              # binary at target/release/widget-calculator
```

For the installer:

```bash
cargo install tauri-cli --locked
cargo tauri build --config '{"bundle":{"createUpdaterArtifacts":false}}'
```

`cargo tauri build` packages whatever the host can produce and ignores the
rest, so the same command yields the NSIS installer on Windows, a `.dmg` on
macOS, and `.deb` / `.rpm` / `.AppImage` on Linux. On macOS, add
`--target universal-apple-darwin` to cover Intel Macs too (install the extra
architecture first with `rustup target add x86_64-apple-darwin`).

The `--config` override is what keeps a plain local build working:
`createUpdaterArtifacts` is on, and signing those artifacts needs the private
key, which only CI has. Drop the override when you do have the key — see
*Building a release locally* below.

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
   ```bash
   git tag v0.2.0
   git push origin v0.2.0
   ```
3. The **Release** workflow builds on Windows, macOS and Linux runners, signs
   every artifact and publishes a GitHub release with the installers, their
   `.sig` files and `latest.json`.

The three jobs run one at a time rather than in parallel. Each of them merges
its own platform into the same `latest.json` already attached to the release,
and that read-modify-write would otherwise race: the loser would publish an
updater manifest listing only its own platform.

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
Get-Content src-tauri\widgetcalc.key -Raw | Set-Clipboard   # Windows
```

```bash
pbcopy < src-tauri/widgetcalc.key                           # macOS
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

```bash
export TAURI_SIGNING_PRIVATE_KEY="$(cat src-tauri/widgetcalc.key)"
export TAURI_SIGNING_PRIVATE_KEY_PASSWORD=""
cargo tauri build
```

Each bundle and its signature land under `src-tauri/target/release/bundle/`, in
a directory named after the format — `nsis/`, `dmg/`, `deb/`, `rpm/`,
`appimage/`.

</details>

## 📄 License

[MIT](LICENSE) © Alejandro Padilla

<div align="center">
<sub>Built with Rust + Tauri. Small by design.</sub>
</div>
