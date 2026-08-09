//! Built-in colour themes. Serialised straight to the UI, which turns each
//! field into a CSS custom property.

use serde::Serialize;

pub const DEFAULT_THEME_ID: &str = "monokai";

#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct Theme {
    pub theme_id: &'static str,
    pub name: &'static str,
    pub window_bg: &'static str,
    pub surface_bg: &'static str,
    pub editor_bg: &'static str,
    pub results_bg: &'static str,
    pub border: &'static str,
    pub text: &'static str,
    pub muted_text: &'static str,
    pub accent: &'static str,
    pub accent_hover: &'static str,
    pub selection: &'static str,
    pub danger: &'static str,
    pub danger_hover: &'static str,
}

static THEMES: &[Theme] = &[
    Theme {
        theme_id: "monokai",
        name: "Monokai",
        window_bg: "#17181b",
        surface_bg: "#1f2023",
        editor_bg: "#111214",
        results_bg: "#151619",
        border: "#3d3e42",
        text: "#f8f8f2",
        muted_text: "#a8a8a2",
        accent: "#a6e22e",
        accent_hover: "#c5f467",
        selection: "#49483e",
        danger: "#e74c3c",
        danger_hover: "#ff6b5b",
    },
    Theme {
        theme_id: "nord",
        name: "Nord",
        window_bg: "#2e3440",
        surface_bg: "#3b4252",
        editor_bg: "#2b303b",
        results_bg: "#303744",
        border: "#4c566a",
        text: "#eceff4",
        muted_text: "#d8dee9",
        accent: "#88c0d0",
        accent_hover: "#9ccfdc",
        selection: "#434c5e",
        danger: "#bf616a",
        danger_hover: "#d08770",
    },
    Theme {
        theme_id: "graphite",
        name: "Graphite",
        window_bg: "#101214",
        surface_bg: "#161a1f",
        editor_bg: "#0d1014",
        results_bg: "#12161b",
        border: "#2e3640",
        text: "#ebeff5",
        muted_text: "#b9c0cc",
        accent: "#5ec2ff",
        accent_hover: "#85d1ff",
        selection: "#2a3240",
        danger: "#ff6b6b",
        danger_hover: "#ff8585",
    },
];

/// Look up a theme, falling back to the default for unknown ids.
pub fn get_theme(theme_id: &str) -> &'static Theme {
    THEMES
        .iter()
        .find(|theme| theme.theme_id == theme_id)
        .unwrap_or_else(|| {
            THEMES
                .iter()
                .find(|theme| theme.theme_id == DEFAULT_THEME_ID)
                .expect("the default theme must exist")
        })
}

pub fn all_themes() -> &'static [Theme] {
    THEMES
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn exposes_the_three_presets() {
        let ids: Vec<&str> = all_themes().iter().map(|theme| theme.theme_id).collect();
        assert_eq!(ids, vec!["monokai", "nord", "graphite"]);
    }

    #[test]
    fn looks_themes_up_by_id() {
        assert_eq!(get_theme("nord").name, "Nord");
        assert_eq!(get_theme("graphite").accent, "#5ec2ff");
    }

    #[test]
    fn falls_back_to_the_default_theme() {
        assert_eq!(get_theme("does-not-exist").theme_id, DEFAULT_THEME_ID);
        assert_eq!(get_theme("").theme_id, DEFAULT_THEME_ID);
    }

    #[test]
    fn every_theme_defines_every_colour() {
        for theme in all_themes() {
            for colour in [
                theme.window_bg,
                theme.surface_bg,
                theme.editor_bg,
                theme.results_bg,
                theme.border,
                theme.text,
                theme.muted_text,
                theme.accent,
                theme.accent_hover,
                theme.selection,
                theme.danger,
                theme.danger_hover,
            ] {
                assert!(colour.starts_with('#'), "{} has a bad colour", theme.name);
                assert_eq!(colour.len(), 7, "{} has a bad colour", theme.name);
            }
        }
    }
}
