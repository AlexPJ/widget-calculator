//! Dimensional analysis and the unit table.
//!
//! Replaces the `pint` registry the Python version used. Every unit is stored
//! as a linear map onto a fixed set of base units:
//!
//! ```text
//! base_value = magnitude * factor + offset
//! ```
//!
//! `offset` is only non-zero for the temperature scales, which is exactly the
//! `autoconvert_offset_to_baseunit=True` behaviour the Python registry had.

use std::f64::consts::PI;

/// Exponents of the base units, in this order:
/// length, mass, time, current, temperature, information, substance, luminous.
pub const DIM_COUNT: usize = 8;
pub type Dim = [i8; DIM_COUNT];

pub const DIMENSIONLESS: Dim = [0; DIM_COUNT];

const BASE_SYMBOLS: [&str; DIM_COUNT] = ["m", "kg", "s", "A", "K", "B", "mol", "cd"];

/// One argument per base dimension; the arity is the point.
#[allow(clippy::too_many_arguments)]
const fn d(l: i8, m: i8, t: i8, i: i8, k: i8, b: i8, n: i8, j: i8) -> Dim {
    [l, m, t, i, k, b, n, j]
}

const NONE: Dim = d(0, 0, 0, 0, 0, 0, 0, 0);
const LEN: Dim = d(1, 0, 0, 0, 0, 0, 0, 0);
const AREA: Dim = d(2, 0, 0, 0, 0, 0, 0, 0);
const VOL: Dim = d(3, 0, 0, 0, 0, 0, 0, 0);
const MASS: Dim = d(0, 1, 0, 0, 0, 0, 0, 0);
const TIME: Dim = d(0, 0, 1, 0, 0, 0, 0, 0);
const CURRENT: Dim = d(0, 0, 0, 1, 0, 0, 0, 0);
const TEMP: Dim = d(0, 0, 0, 0, 1, 0, 0, 0);
const INFO: Dim = d(0, 0, 0, 0, 0, 1, 0, 0);
const SUBSTANCE: Dim = d(0, 0, 0, 0, 0, 0, 1, 0);
const LUMINOUS: Dim = d(0, 0, 0, 0, 0, 0, 0, 1);
const SPEED: Dim = d(1, 0, -1, 0, 0, 0, 0, 0);
const ACCEL: Dim = d(1, 0, -2, 0, 0, 0, 0, 0);
const FORCE: Dim = d(1, 1, -2, 0, 0, 0, 0, 0);
const ENERGY: Dim = d(2, 1, -2, 0, 0, 0, 0, 0);
const POWER: Dim = d(2, 1, -3, 0, 0, 0, 0, 0);
const PRESSURE: Dim = d(-1, 1, -2, 0, 0, 0, 0, 0);
const FREQ: Dim = d(0, 0, -1, 0, 0, 0, 0, 0);
const CHARGE: Dim = d(0, 0, 1, 1, 0, 0, 0, 0);
const VOLTAGE: Dim = d(2, 1, -3, -1, 0, 0, 0, 0);

/// A unit definition: how to map a magnitude onto the base units.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Unit {
    pub symbol: &'static str,
    pub factor: f64,
    pub offset: f64,
    pub dim: Dim,
}

const DAY: f64 = 86_400.0;
const KIB: f64 = 1024.0;

/// `(alias, canonical symbol, factor, offset, dimension)`.
///
/// Aliases are matched exactly first, then case-insensitively, so `B` is a byte
/// while `b` is a bit, but `KM` still resolves to `km`.
#[rustfmt::skip]
static UNITS: &[(&str, &str, f64, f64, Dim)] = &[
    // ----- length (base: metre) -----
    ("m", "m", 1.0, 0.0, LEN), ("metre", "m", 1.0, 0.0, LEN), ("metres", "m", 1.0, 0.0, LEN),
    ("meter", "m", 1.0, 0.0, LEN), ("meters", "m", 1.0, 0.0, LEN),
    ("km", "km", 1e3, 0.0, LEN), ("kilometre", "km", 1e3, 0.0, LEN), ("kilometres", "km", 1e3, 0.0, LEN),
    ("kilometer", "km", 1e3, 0.0, LEN), ("kilometers", "km", 1e3, 0.0, LEN),
    ("dm", "dm", 1e-1, 0.0, LEN),
    ("cm", "cm", 1e-2, 0.0, LEN), ("centimetre", "cm", 1e-2, 0.0, LEN), ("centimetres", "cm", 1e-2, 0.0, LEN),
    ("centimeter", "cm", 1e-2, 0.0, LEN), ("centimeters", "cm", 1e-2, 0.0, LEN),
    ("mm", "mm", 1e-3, 0.0, LEN), ("millimetre", "mm", 1e-3, 0.0, LEN), ("millimetres", "mm", 1e-3, 0.0, LEN),
    ("millimeter", "mm", 1e-3, 0.0, LEN), ("millimeters", "mm", 1e-3, 0.0, LEN),
    ("um", "um", 1e-6, 0.0, LEN), ("\u{b5}m", "\u{b5}m", 1e-6, 0.0, LEN), ("micrometre", "um", 1e-6, 0.0, LEN),
    ("nm", "nm", 1e-9, 0.0, LEN),
    ("mi", "mi", 1609.344, 0.0, LEN), ("mile", "mi", 1609.344, 0.0, LEN), ("miles", "mi", 1609.344, 0.0, LEN),
    ("yd", "yd", 0.9144, 0.0, LEN), ("yard", "yd", 0.9144, 0.0, LEN), ("yards", "yd", 0.9144, 0.0, LEN),
    ("ft", "ft", 0.3048, 0.0, LEN), ("foot", "ft", 0.3048, 0.0, LEN), ("feet", "ft", 0.3048, 0.0, LEN),
    ("in", "in", 0.0254, 0.0, LEN), ("inch", "in", 0.0254, 0.0, LEN), ("inches", "in", 0.0254, 0.0, LEN),
    ("nmi", "nmi", 1852.0, 0.0, LEN),
    ("ly", "ly", 9.4607304725808e15, 0.0, LEN),
    ("au", "au", 1.495978707e11, 0.0, LEN),

    // ----- area -----
    ("ha", "ha", 1e4, 0.0, AREA), ("hectare", "ha", 1e4, 0.0, AREA), ("hectares", "ha", 1e4, 0.0, AREA),
    ("acre", "acre", 4046.8564224, 0.0, AREA), ("acres", "acre", 4046.8564224, 0.0, AREA),

    // ----- volume -----
    ("l", "l", 1e-3, 0.0, VOL), ("liter", "l", 1e-3, 0.0, VOL), ("liters", "l", 1e-3, 0.0, VOL),
    ("litre", "l", 1e-3, 0.0, VOL), ("litres", "l", 1e-3, 0.0, VOL),
    ("ml", "ml", 1e-6, 0.0, VOL), ("cl", "cl", 1e-5, 0.0, VOL), ("dl", "dl", 1e-4, 0.0, VOL),
    ("gal", "gal", 3.785411784e-3, 0.0, VOL), ("gallon", "gal", 3.785411784e-3, 0.0, VOL),
    ("gallons", "gal", 3.785411784e-3, 0.0, VOL),

    // ----- mass (base: kilogram) -----
    ("kg", "kg", 1.0, 0.0, MASS), ("kilogram", "kg", 1.0, 0.0, MASS), ("kilograms", "kg", 1.0, 0.0, MASS),
    ("g", "g", 1e-3, 0.0, MASS), ("gram", "g", 1e-3, 0.0, MASS), ("grams", "g", 1e-3, 0.0, MASS),
    ("mg", "mg", 1e-6, 0.0, MASS), ("ug", "ug", 1e-9, 0.0, MASS),
    ("t", "t", 1e3, 0.0, MASS), ("tonne", "t", 1e3, 0.0, MASS), ("tonnes", "t", 1e3, 0.0, MASS),
    ("lb", "lb", 0.45359237, 0.0, MASS), ("lbs", "lb", 0.45359237, 0.0, MASS),
    ("pound", "lb", 0.45359237, 0.0, MASS), ("pounds", "lb", 0.45359237, 0.0, MASS),
    ("oz", "oz", 0.028349523125, 0.0, MASS), ("ounce", "oz", 0.028349523125, 0.0, MASS),
    ("ounces", "oz", 0.028349523125, 0.0, MASS),
    ("st", "st", 6.35029318, 0.0, MASS), ("stone", "st", 6.35029318, 0.0, MASS),

    // ----- time (base: second) -----
    ("s", "s", 1.0, 0.0, TIME), ("sec", "s", 1.0, 0.0, TIME), ("secs", "s", 1.0, 0.0, TIME),
    ("second", "s", 1.0, 0.0, TIME), ("seconds", "s", 1.0, 0.0, TIME),
    ("ms", "ms", 1e-3, 0.0, TIME), ("us", "us", 1e-6, 0.0, TIME), ("ns", "ns", 1e-9, 0.0, TIME),
    ("min", "min", 60.0, 0.0, TIME), ("mins", "min", 60.0, 0.0, TIME),
    ("minute", "min", 60.0, 0.0, TIME), ("minutes", "min", 60.0, 0.0, TIME),
    ("h", "h", 3600.0, 0.0, TIME), ("hr", "h", 3600.0, 0.0, TIME), ("hrs", "h", 3600.0, 0.0, TIME),
    ("hour", "h", 3600.0, 0.0, TIME), ("hours", "h", 3600.0, 0.0, TIME),
    ("d", "d", DAY, 0.0, TIME), ("day", "d", DAY, 0.0, TIME), ("days", "d", DAY, 0.0, TIME),
    ("week", "week", 7.0 * DAY, 0.0, TIME), ("weeks", "week", 7.0 * DAY, 0.0, TIME),
    ("month", "month", 30.436875 * DAY, 0.0, TIME), ("months", "month", 30.436875 * DAY, 0.0, TIME),
    ("year", "year", 365.25 * DAY, 0.0, TIME), ("years", "year", 365.25 * DAY, 0.0, TIME),
    ("yr", "year", 365.25 * DAY, 0.0, TIME),

    // ----- temperature -----
    ("K", "K", 1.0, 0.0, TEMP), ("kelvin", "K", 1.0, 0.0, TEMP),
    ("degC", "\u{b0}C", 1.0, 273.15, TEMP), ("celsius", "\u{b0}C", 1.0, 273.15, TEMP),
    ("\u{b0}C", "\u{b0}C", 1.0, 273.15, TEMP),
    ("degF", "\u{b0}F", 5.0 / 9.0, 255.3722222222222, TEMP),
    ("fahrenheit", "\u{b0}F", 5.0 / 9.0, 255.3722222222222, TEMP),
    ("\u{b0}F", "\u{b0}F", 5.0 / 9.0, 255.3722222222222, TEMP),

    // ----- information (base: byte, decimal prefixes; *ib are binary) -----
    ("B", "B", 1.0, 0.0, INFO), ("byte", "B", 1.0, 0.0, INFO), ("bytes", "B", 1.0, 0.0, INFO),
    ("b", "bit", 0.125, 0.0, INFO), ("bit", "bit", 0.125, 0.0, INFO), ("bits", "bit", 0.125, 0.0, INFO),
    ("kb", "kb", 1e3, 0.0, INFO), ("kilobyte", "kb", 1e3, 0.0, INFO), ("kilobytes", "kb", 1e3, 0.0, INFO),
    ("mb", "mb", 1e6, 0.0, INFO), ("megabyte", "mb", 1e6, 0.0, INFO), ("megabytes", "mb", 1e6, 0.0, INFO),
    ("gb", "gb", 1e9, 0.0, INFO), ("gigabyte", "gb", 1e9, 0.0, INFO), ("gigabytes", "gb", 1e9, 0.0, INFO),
    ("tb", "tb", 1e12, 0.0, INFO), ("terabyte", "tb", 1e12, 0.0, INFO), ("terabytes", "tb", 1e12, 0.0, INFO),
    ("pb", "pb", 1e15, 0.0, INFO),
    ("kib", "kib", KIB, 0.0, INFO), ("mib", "mib", KIB * KIB, 0.0, INFO),
    ("gib", "gib", KIB * KIB * KIB, 0.0, INFO), ("tib", "tib", KIB * KIB * KIB * KIB, 0.0, INFO),
    ("kbit", "kbit", 125.0, 0.0, INFO), ("mbit", "mbit", 125e3, 0.0, INFO),
    ("gbit", "gbit", 125e6, 0.0, INFO),

    // ----- angle (dimensionless, like pint) -----
    ("rad", "rad", 1.0, 0.0, NONE), ("radian", "rad", 1.0, 0.0, NONE), ("radians", "rad", 1.0, 0.0, NONE),
    ("deg", "deg", PI / 180.0, 0.0, NONE), ("degree", "deg", PI / 180.0, 0.0, NONE),
    ("degrees", "deg", PI / 180.0, 0.0, NONE),
    ("grad", "grad", PI / 200.0, 0.0, NONE),
    ("turn", "turn", 2.0 * PI, 0.0, NONE), ("turns", "turn", 2.0 * PI, 0.0, NONE),

    // ----- speed / acceleration -----
    ("kph", "kph", 1000.0 / 3600.0, 0.0, SPEED), ("kmh", "kph", 1000.0 / 3600.0, 0.0, SPEED),
    ("mph", "mph", 1609.344 / 3600.0, 0.0, SPEED),
    ("knot", "knot", 1852.0 / 3600.0, 0.0, SPEED), ("knots", "knot", 1852.0 / 3600.0, 0.0, SPEED),
    ("gravity", "g0", 9.80665, 0.0, ACCEL),

    // ----- force / energy / power / pressure -----
    ("N", "N", 1.0, 0.0, FORCE), ("newton", "N", 1.0, 0.0, FORCE), ("kN", "kN", 1e3, 0.0, FORCE),
    ("J", "J", 1.0, 0.0, ENERGY), ("joule", "J", 1.0, 0.0, ENERGY), ("joules", "J", 1.0, 0.0, ENERGY),
    ("kJ", "kJ", 1e3, 0.0, ENERGY), ("MJ", "MJ", 1e6, 0.0, ENERGY),
    ("cal", "cal", 4.184, 0.0, ENERGY), ("kcal", "kcal", 4184.0, 0.0, ENERGY),
    ("Wh", "Wh", 3600.0, 0.0, ENERGY), ("kWh", "kWh", 3.6e6, 0.0, ENERGY),
    ("W", "W", 1.0, 0.0, POWER), ("watt", "W", 1.0, 0.0, POWER), ("watts", "W", 1.0, 0.0, POWER),
    ("kW", "kW", 1e3, 0.0, POWER), ("MW", "MW", 1e6, 0.0, POWER),
    ("hp", "hp", 745.6998715822702, 0.0, POWER),
    ("Pa", "Pa", 1.0, 0.0, PRESSURE), ("pascal", "Pa", 1.0, 0.0, PRESSURE),
    ("kPa", "kPa", 1e3, 0.0, PRESSURE), ("hPa", "hPa", 1e2, 0.0, PRESSURE),
    ("bar", "bar", 1e5, 0.0, PRESSURE), ("mbar", "mbar", 1e2, 0.0, PRESSURE),
    ("psi", "psi", 6894.757293168361, 0.0, PRESSURE), ("atm", "atm", 101325.0, 0.0, PRESSURE),

    // ----- frequency / electrical -----
    ("Hz", "Hz", 1.0, 0.0, FREQ), ("kHz", "kHz", 1e3, 0.0, FREQ), ("MHz", "MHz", 1e6, 0.0, FREQ),
    ("GHz", "GHz", 1e9, 0.0, FREQ),
    ("A", "A", 1.0, 0.0, CURRENT), ("ampere", "A", 1.0, 0.0, CURRENT), ("mA", "mA", 1e-3, 0.0, CURRENT),
    ("C", "C", 1.0, 0.0, CHARGE), ("coulomb", "C", 1.0, 0.0, CHARGE),
    ("V", "V", 1.0, 0.0, VOLTAGE), ("volt", "V", 1.0, 0.0, VOLTAGE), ("volts", "V", 1.0, 0.0, VOLTAGE),
    ("mV", "mV", 1e-3, 0.0, VOLTAGE), ("kV", "kV", 1e3, 0.0, VOLTAGE),

    // ----- remaining base units -----
    ("mol", "mol", 1.0, 0.0, SUBSTANCE), ("mole", "mol", 1.0, 0.0, SUBSTANCE),
    ("cd", "cd", 1.0, 0.0, LUMINOUS), ("candela", "cd", 1.0, 0.0, LUMINOUS),
];

/// Resolve a unit name. Exact match wins, then a case-insensitive match.
pub fn lookup(name: &str) -> Option<Unit> {
    let build = |entry: &(&str, &'static str, f64, f64, Dim)| Unit {
        symbol: entry.1,
        factor: entry.2,
        offset: entry.3,
        dim: entry.4,
    };
    if let Some(entry) = UNITS.iter().find(|entry| entry.0 == name) {
        return Some(build(entry));
    }
    let lowered = name.to_ascii_lowercase();
    UNITS
        .iter()
        .find(|entry| entry.0.to_ascii_lowercase() == lowered)
        .map(build)
}

pub fn dim_mul(a: Dim, b: Dim) -> Dim {
    let mut out = DIMENSIONLESS;
    for index in 0..DIM_COUNT {
        out[index] = a[index] + b[index];
    }
    out
}

pub fn dim_div(a: Dim, b: Dim) -> Dim {
    let mut out = DIMENSIONLESS;
    for index in 0..DIM_COUNT {
        out[index] = a[index] - b[index];
    }
    out
}

pub fn dim_pow(a: Dim, exponent: i8) -> Dim {
    let mut out = DIMENSIONLESS;
    for index in 0..DIM_COUNT {
        out[index] = a[index] * exponent;
    }
    out
}

/// Render a dimension as a symbol, e.g. `m/s` or `kg·m/s^2`.
pub fn dim_symbol(dim: Dim) -> String {
    let mut numerator: Vec<String> = Vec::new();
    let mut denominator: Vec<String> = Vec::new();
    for (index, &exponent) in dim.iter().enumerate() {
        let symbol = BASE_SYMBOLS[index];
        match exponent {
            0 => {}
            1 => numerator.push(symbol.to_string()),
            -1 => denominator.push(symbol.to_string()),
            n if n > 1 => numerator.push(format!("{symbol}^{n}")),
            n => denominator.push(format!("{symbol}^{}", -n)),
        }
    }
    let head = if numerator.is_empty() {
        "1".to_string()
    } else {
        numerator.join("\u{b7}")
    };
    if denominator.is_empty() {
        head
    } else {
        format!("{head}/{}", denominator.join("\u{b7}"))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn resolves_exact_aliases() {
        assert_eq!(lookup("km").unwrap().factor, 1e3);
        assert_eq!(lookup("kilometers").unwrap().symbol, "km");
    }

    #[test]
    fn byte_and_bit_keep_their_case() {
        assert_eq!(lookup("B").unwrap().symbol, "B");
        assert_eq!(lookup("b").unwrap().symbol, "bit");
    }

    #[test]
    fn falls_back_to_case_insensitive() {
        assert_eq!(lookup("KM").unwrap().symbol, "km");
        assert_eq!(lookup("Miles").unwrap().symbol, "mi");
    }

    #[test]
    fn rejects_unknown_units() {
        assert!(lookup("banana").is_none());
    }

    #[test]
    fn temperature_scales_carry_offsets() {
        let celsius = lookup("degC").unwrap();
        assert_eq!(celsius.offset, 273.15);
        let fahrenheit = lookup("degF").unwrap();
        // 20 °C is 68 °F.
        let base = 20.0 * celsius.factor + celsius.offset;
        let converted = (base - fahrenheit.offset) / fahrenheit.factor;
        assert!((converted - 68.0).abs() < 1e-9);
    }

    #[test]
    fn renders_derived_symbols() {
        assert_eq!(dim_symbol(SPEED), "m/s");
        // Base symbols are emitted in dimension order (length before mass).
        assert_eq!(dim_symbol(FORCE), "m\u{b7}kg/s^2");
        assert_eq!(dim_symbol(DIMENSIONLESS), "1");
    }

    #[test]
    fn dimension_arithmetic() {
        assert_eq!(dim_div(LEN, TIME), SPEED);
        assert_eq!(dim_mul(SPEED, TIME), LEN);
        assert_eq!(dim_pow(LEN, 2), AREA);
    }
}
