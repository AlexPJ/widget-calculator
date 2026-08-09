// Widget Calculator — one instance of this script runs per calculator window.
// The window label carries the workspace id, so the Rust side always knows
// which window is talking to it.

const { invoke } = window.__TAURI__.core;
const { listen } = window.__TAURI__.event;
const appWindow = window.__TAURI__.window.getCurrentWindow();
const clipboard = window.__TAURI__.clipboardManager;

const $ = (id) => document.getElementById(id);

const EVALUATE_DEBOUNCE_MS = 120;

const ABOUT_TEXT =
  "Widget Calculator\n\n" +
  "A resizable calculator widget for Windows with variables, unit " +
  "conversions, live currency rates, running totals and themes.\n\n" +
  "Built with Rust and Tauri.";

const HELP_TEXT =
  "Examples:\n" +
  "  x = 1\n" +
  "  y = 2\n" +
  "  x + y\n" +
  "  10 km to m\n" +
  "  20 usd to eur\n" +
  "  200 * 10%\n" +
  "  sqrt(9)\n" +
  "  now('Europe/Madrid')\n\n" +
  "Press Alt to show the menu bar. Click a result line to copy it.\n" +
  "Use the gear icon (bottom-left) for settings.\n" +
  "Closing a window discards it; the last one hides to the tray instead.";

let boot = null;
let evaluateTimer = null;
let evaluateSequence = 0;
let syncingScroll = false;

// --------------------------------------------------------------- utilities

let toastTimer = null;
function toast(message) {
  const element = $("toast");
  element.textContent = message;
  element.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    element.hidden = true;
  }, 1600);
}

async function copy(text) {
  if (!text) return;
  try {
    await clipboard.writeText(text);
    toast("Copied");
  } catch (error) {
    toast(String(error));
  }
}

// ------------------------------------------------------------------ themes

function applyTheme(theme) {
  const root = document.documentElement;
  for (const [key, value] of Object.entries(theme)) {
    if (key === "theme_id" || key === "name") continue;
    root.style.setProperty(`--${key.replace(/_/g, "-")}`, value);
  }
  for (const input of document.querySelectorAll('input[name="theme"]')) {
    input.checked = input.value === theme.theme_id;
  }
}

function applyOpacity(opacity) {
  document.documentElement.style.setProperty("--app-opacity", String(opacity));
  $("opacity").value = String(Math.round(opacity * 100));
  $("opacity-value").textContent = `${Math.round(opacity * 100)}%`;
}

// -------------------------------------------------------------- evaluation

function renderResults(lines) {
  const container = $("results");
  container.replaceChildren(
    ...lines.map((line) => {
      const element = document.createElement("div");
      element.className = line.startsWith("Error:") ? "rline error" : "rline";
      element.textContent = line;
      return element;
    })
  );
}

function renderTotal(total) {
  $("total-value").textContent = total ?? "";
}

async function evaluateNow() {
  const sequence = ++evaluateSequence;
  const text = $("editor").value;
  try {
    const outcome = await invoke("evaluate", { text });
    // A slow currency lookup must not overwrite newer results.
    if (sequence !== evaluateSequence) return;
    renderResults(outcome.results);
    renderTotal(outcome.total);
  } catch (error) {
    if (sequence !== evaluateSequence) return;
    toast(String(error));
  }
}

function scheduleEvaluate() {
  clearTimeout(evaluateTimer);
  evaluateTimer = setTimeout(evaluateNow, EVALUATE_DEBOUNCE_MS);
}

// ------------------------------------------------------------- title bar

$("tb-min").onclick = () => appWindow.minimize();
$("tb-max").onclick = () => appWindow.toggleMaximize();
$("tb-close").onclick = () => appWindow.close();

$("titlebar").addEventListener("mousedown", (event) => {
  if (event.button !== 0 || event.target.closest(".tb-button")) return;
  if (event.detail === 2) appWindow.toggleMaximize();
  else appWindow.startDragging();
});

async function syncMaximized() {
  const maximized = await appWindow.isMaximized();
  document.body.classList.toggle("maximized", maximized);
  $("tb-max").textContent = maximized ? "❐" : "□";
  $("tb-max").title = maximized ? "Restore" : "Maximize";
}
window.addEventListener("resize", syncMaximized);

// ----------------------------------------------------------- resize grips

for (const grip of document.querySelectorAll(".grip")) {
  grip.addEventListener("mousedown", (event) => {
    if (event.button !== 0) return;
    event.preventDefault();
    appWindow.startResizeDragging(grip.dataset.direction);
  });
}

// -------------------------------------------------------------- splitter

(() => {
  const splitter = $("splitter");
  const panes = $("panes");
  let dragging = false;

  splitter.addEventListener("mousedown", (event) => {
    if (event.button !== 0) return;
    dragging = true;
    splitter.classList.add("dragging");
    event.preventDefault();
  });

  document.addEventListener("mousemove", (event) => {
    if (!dragging) return;
    const bounds = panes.getBoundingClientRect();
    const fraction = (event.clientX - bounds.left) / bounds.width;
    const clamped = Math.min(0.85, Math.max(0.15, fraction));
    document.documentElement.style.setProperty("--split", `${clamped * 100}%`);
  });

  document.addEventListener("mouseup", () => {
    if (!dragging) return;
    dragging = false;
    splitter.classList.remove("dragging");
    localStorage.setItem(
      "split",
      getComputedStyle(document.documentElement).getPropertyValue("--split").trim()
    );
  });

  const savedSplit = localStorage.getItem("split");
  if (savedSplit) document.documentElement.style.setProperty("--split", savedSplit);
})();

// ---------------------------------------------------------------- editor

const editor = $("editor");
const results = $("results");

editor.addEventListener("input", scheduleEvaluate);
editor.addEventListener("blur", () => {
  invoke("store_text", { text: editor.value }).catch(() => {});
});

// Keep both columns showing the same lines.
function linkScroll(source, target) {
  source.addEventListener("scroll", () => {
    if (syncingScroll) return;
    syncingScroll = true;
    target.scrollTop = source.scrollTop;
    syncingScroll = false;
  });
}
linkScroll(editor, results);
linkScroll(results, editor);

results.addEventListener("click", (event) => {
  const line = event.target.closest(".rline");
  if (line && line.textContent) copy(line.textContent);
});

// Tab indents instead of moving focus out of the editor.
editor.addEventListener("keydown", (event) => {
  if (event.key !== "Tab") return;
  event.preventDefault();
  const { selectionStart, selectionEnd, value } = editor;
  editor.value = `${value.slice(0, selectionStart)}  ${value.slice(selectionEnd)}`;
  editor.selectionStart = editor.selectionEnd = selectionStart + 2;
  scheduleEvaluate();
});

// -------------------------------------------------------------- total bar

$("total-switch").addEventListener("click", async () => {
  const enabled = $("total-switch").getAttribute("aria-checked") !== "true";
  await invoke("set_total_enabled", { enabled });
});

$("total-value").addEventListener("click", () => {
  if ($("totalbar").classList.contains("off")) return;
  copy($("total-value").textContent);
});

function applyTotalEnabled(enabled) {
  $("total-switch").setAttribute("aria-checked", String(enabled));
  $("totalbar").classList.toggle("off", !enabled);
  if (!enabled) renderTotal(null);
}

// --------------------------------------------------------------- menu bar

const menubar = $("menubar");

function showMenuBar() {
  menubar.hidden = false;
  document.body.classList.add("menu-open");
}

function hideMenuBar() {
  menubar.hidden = true;
  document.body.classList.remove("menu-open");
  for (const menu of menubar.querySelectorAll(".menu")) menu.classList.remove("open");
}

for (const menu of menubar.querySelectorAll(".menu")) {
  menu.querySelector(".menu-label").addEventListener("click", () => {
    const wasOpen = menu.classList.contains("open");
    for (const other of menubar.querySelectorAll(".menu")) other.classList.remove("open");
    menu.classList.toggle("open", !wasOpen);
  });
}

document.addEventListener("mousedown", (event) => {
  if (!menubar.hidden && !event.target.closest(".menubar")) hideMenuBar();
});

// ---------------------------------------------------------------- dialogs

function openDialog(id) {
  $("overlay").hidden = false;
  for (const dialog of document.querySelectorAll(".dialog")) {
    dialog.hidden = dialog.id !== id;
  }
}

function closeDialogs() {
  $("overlay").hidden = true;
  for (const dialog of document.querySelectorAll(".dialog")) dialog.hidden = true;
}

$("overlay").addEventListener("mousedown", (event) => {
  if (event.target === $("overlay")) closeDialogs();
});

for (const button of document.querySelectorAll("[data-close]")) {
  button.addEventListener("click", closeDialogs);
}

function showMessage(title, body) {
  $("message-title").textContent = title;
  $("message-body").textContent = body;
  openDialog("dialog-message");
}

async function showHistory() {
  const history = await invoke("get_history");
  renderHistory(history);
  openDialog("dialog-history");
}

function renderHistory(history) {
  const list = $("history-list");
  if (!history.length) {
    list.innerHTML = '<span class="empty">No commands yet.</span>';
    return;
  }
  list.textContent = history.join("\n");
  list.scrollTop = list.scrollHeight;
}

$("history-clear").addEventListener("click", async () => {
  await invoke("clear_history");
  renderHistory([]);
});

// ---------------------------------------------------------------- updates

let pendingUpdateButton = null;

async function checkForUpdates() {
  const status = $("update-status");
  openDialog("dialog-settings");
  status.textContent = "Checking for updates...";
  pendingUpdateButton?.remove();
  pendingUpdateButton = null;

  try {
    const update = await invoke("check_for_updates");
    if (!update) {
      status.textContent = `You are up to date (v${boot.version}).`;
      return;
    }
    status.textContent = `Version ${update.version} is available (you have ${update.current_version}).`;
    pendingUpdateButton = document.createElement("button");
    pendingUpdateButton.className = "btn";
    pendingUpdateButton.textContent = "Install and restart";
    pendingUpdateButton.addEventListener("click", async () => {
      pendingUpdateButton.disabled = true;
      status.textContent = "Downloading update...";
      try {
        await invoke("install_update");
      } catch (error) {
        status.textContent = `Update failed: ${error}`;
        pendingUpdateButton.disabled = false;
      }
    });
    status.after(pendingUpdateButton);
  } catch (error) {
    status.textContent = `Could not check for updates: ${error}`;
  }
}

// ---------------------------------------------------------------- actions

const actions = {
  "new-window": () => invoke("new_window"),
  settings: () => openDialog("dialog-settings"),
  quit: () => invoke("quit"),
  history: showHistory,
  "show-all": () => invoke("show_all_windows"),
  about: () => showMessage("About Widget Calculator", ABOUT_TEXT),
  help: () => showMessage("Help", HELP_TEXT),
  "check-updates": checkForUpdates,
  undo: () => document.execCommand("undo"),
  redo: () => document.execCommand("redo"),
  cut: () => document.execCommand("cut"),
  copy: () => document.execCommand("copy"),
  paste: () => document.execCommand("paste"),
};

document.addEventListener("click", (event) => {
  const trigger = event.target.closest("[data-action]");
  if (!trigger) return;
  hideMenuBar();
  const action = actions[trigger.dataset.action];
  if (action) Promise.resolve(action()).catch((error) => toast(String(error)));
});

$("gear").addEventListener("click", () => openDialog("dialog-settings"));

// ------------------------------------------------------------- shortcuts

document.addEventListener("keydown", (event) => {
  if (event.key === "Alt" && !event.repeat) {
    event.preventDefault();
    if (menubar.hidden) showMenuBar();
    else hideMenuBar();
    return;
  }

  if (event.key === "Escape") {
    if (!$("overlay").hidden) closeDialogs();
    else hideMenuBar();
    return;
  }

  if (event.key === "F1") {
    event.preventDefault();
    actions.help();
    return;
  }

  if (!event.ctrlKey || event.altKey) return;
  const key = event.key.toLowerCase();
  const shortcuts = {
    n: "new-window",
    q: "quit",
    h: "history",
    ",": "settings",
  };
  const action = shortcuts[key];
  if (!action) return;
  event.preventDefault();
  Promise.resolve(actions[action]()).catch((error) => toast(String(error)));
});

// ------------------------------------------------------------- settings

$("opacity").addEventListener("input", (event) => {
  const percent = Number(event.target.value);
  $("opacity-value").textContent = `${percent}%`;
  document.documentElement.style.setProperty("--app-opacity", String(percent / 100));
});

$("opacity").addEventListener("change", (event) => {
  invoke("set_opacity", { opacity: Number(event.target.value) / 100 });
});

$("always-on-top").addEventListener("change", (event) => {
  invoke("set_always_on_top", { enabled: event.target.checked });
});

$("startup").addEventListener("change", (event) => {
  invoke("set_startup", { enabled: event.target.checked });
});

for (const radio of document.querySelectorAll('input[name="window-mode"]')) {
  radio.addEventListener("change", (event) => {
    if (event.target.checked) invoke("set_window_mode", { mode: event.target.value });
  });
}

function buildThemeOptions(themes, activeId) {
  const container = $("theme-options");
  container.replaceChildren(
    ...themes.map((theme) => {
      const label = document.createElement("label");
      label.className = "check";
      const input = document.createElement("input");
      input.type = "radio";
      input.name = "theme";
      input.value = theme.theme_id;
      input.checked = theme.theme_id === activeId;
      input.addEventListener("change", () => {
        if (input.checked) invoke("set_theme", { themeId: theme.theme_id });
      });
      const text = document.createElement("span");
      text.textContent = theme.name;
      label.append(input, text);
      return label;
    })
  );
}

// ------------------------------------------------------- events from Rust

listen("theme-changed", (event) => applyTheme(event.payload));
listen("opacity-changed", (event) => applyOpacity(event.payload));
listen("total-changed", async (event) => {
  applyTotalEnabled(event.payload);
  if (!event.payload) return;
  // `recompute` instead of `evaluate`: refreshing must not re-record history.
  const outcome = await invoke("recompute");
  renderTotal(outcome.total);
});
listen("history-changed", (event) => renderHistory(event.payload));
listen("always-on-top-changed", (event) => {
  $("always-on-top").checked = event.payload;
});
listen("startup-changed", (event) => {
  $("startup").checked = event.payload;
});
listen("window-mode-changed", (event) => {
  for (const radio of document.querySelectorAll('input[name="window-mode"]')) {
    radio.checked = radio.value === event.payload;
  }
});
listen("menu:settings", () => openDialog("dialog-settings"));
listen("menu:history", showHistory);
listen("menu:check-updates", checkForUpdates);

// ----------------------------------------------------------------- start

async function start() {
  boot = await invoke("bootstrap");

  $("tb-title").textContent = boot.title;
  editor.value = boot.editor_text;

  applyTheme(boot.theme);
  buildThemeOptions(boot.themes, boot.theme.theme_id);
  applyOpacity(boot.opacity);
  applyTotalEnabled(boot.total_enabled);
  $("always-on-top").checked = boot.always_on_top;
  $("startup").checked = boot.startup_enabled;
  for (const radio of document.querySelectorAll('input[name="window-mode"]')) {
    radio.checked = radio.value === boot.window_mode;
  }

  await syncMaximized();
  await evaluateNow();
  editor.focus();
}

start().catch((error) => {
  document.body.textContent = `Could not start: ${error}`;
});
