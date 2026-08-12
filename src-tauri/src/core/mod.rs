//! Domain layer: calculation, themes and persisted state shapes.
//! Nothing here knows about Tauri, HTTP or the filesystem.

pub mod calculator;
pub mod expr;
pub mod models;
pub mod themes;
pub mod units;
pub mod value;
