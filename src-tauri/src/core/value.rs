//! The values an expression can evaluate to, and how they are rendered.

use super::units::{self, Dim, Unit, DIMENSIONLESS};

pub const MAX_DISPLAY_PRECISION: usize = 12;

/// How a quantity prefers to show itself. Carried through arithmetic so that
/// `5 km + 3 km` stays in kilometres instead of collapsing to metres.
#[derive(Debug, Clone, PartialEq)]
pub struct Display {
    pub symbol: String,
    pub factor: f64,
    pub offset: f64,
}

impl Display {
    fn from_unit(unit: &Unit) -> Self {
        Self {
            symbol: unit.symbol.to_string(),
            factor: unit.factor,
            offset: unit.offset,
        }
    }
}

/// A magnitude plus its dimension. `base` is always expressed in base units.
#[derive(Debug, Clone, PartialEq)]
pub struct Quantity {
    pub base: f64,
    pub dim: Dim,
    pub display: Option<Display>,
}

impl Quantity {
    pub fn from_unit(magnitude: f64, unit: &Unit) -> Self {
        Self {
            base: magnitude * unit.factor + unit.offset,
            dim: unit.dim,
            display: Some(Display::from_unit(unit)),
        }
    }

    pub fn is_dimensionless(&self) -> bool {
        self.dim == DIMENSIONLESS
    }

    /// The magnitude in the display unit (or in base units when there is none).
    pub fn magnitude(&self) -> f64 {
        match &self.display {
            Some(display) => (self.base - display.offset) / display.factor,
            None => self.base,
        }
    }

    /// Re-express this quantity in `unit`, failing when the dimensions differ.
    pub fn convert_to(&self, unit: &Unit) -> Result<Quantity, String> {
        if self.dim != unit.dim {
            return Err(format!(
                "Cannot convert {} to {}",
                units::dim_symbol(self.dim),
                units::dim_symbol(unit.dim)
            ));
        }
        Ok(Quantity {
            base: self.base,
            dim: self.dim,
            display: Some(Display::from_unit(unit)),
        })
    }

    /// Collapse to a plain number when the quantity has no dimension.
    /// Angles come through here, so `sin(30 deg)` sees 0.5236 radians.
    pub fn as_number(&self) -> Option<f64> {
        self.is_dimensionless().then_some(self.base)
    }
}

#[derive(Debug, Clone, PartialEq)]
pub enum Value {
    Number(f64),
    Quantity(Quantity),
    Text(String),
}

impl Value {
    /// Numeric view of a value, for functions and currency amounts.
    pub fn as_number(&self) -> Option<f64> {
        match self {
            Value::Number(number) => Some(*number),
            Value::Quantity(quantity) => quantity.as_number(),
            Value::Text(_) => None,
        }
    }

    pub fn format(&self) -> String {
        match self {
            Value::Number(number) => format_number(*number),
            Value::Text(text) => text.clone(),
            Value::Quantity(quantity) => {
                if quantity.is_dimensionless() && quantity.display.is_none() {
                    return format_number(quantity.base);
                }
                let symbol = match &quantity.display {
                    Some(display) => display.symbol.clone(),
                    None => units::dim_symbol(quantity.dim),
                };
                format!("{} {}", format_number(quantity.magnitude()), symbol)
            }
        }
    }
}

/// Equivalent of Python's `f"{value:.12g}"`.
pub fn format_number(value: f64) -> String {
    if value.is_nan() {
        return "nan".to_string();
    }
    if value.is_infinite() {
        return if value.is_sign_negative() {
            "-inf"
        } else {
            "inf"
        }
        .to_string();
    }
    if value == 0.0 {
        return "0".to_string();
    }

    // Round to the requested significant digits first, so that a value like
    // 9.9999999999999e11 lands on the exponent it will actually be printed with.
    let scientific = format!("{:.*e}", MAX_DISPLAY_PRECISION - 1, value);
    let (mantissa, exponent) = scientific
        .split_once('e')
        .expect("Rust always emits an exponent for {:e}");
    let exponent: i32 = exponent.parse().unwrap_or(0);

    if exponent < -4 || exponent >= MAX_DISPLAY_PRECISION as i32 {
        let sign = if exponent < 0 { '-' } else { '+' };
        return format!(
            "{}e{}{:02}",
            strip_trailing_zeros(mantissa),
            sign,
            exponent.abs()
        );
    }

    let decimals = (MAX_DISPLAY_PRECISION as i32 - 1 - exponent).max(0) as usize;
    strip_trailing_zeros(&format!("{value:.decimals$}"))
}

fn strip_trailing_zeros(text: &str) -> String {
    if !text.contains('.') {
        return text.to_string();
    }
    let trimmed = text.trim_end_matches('0').trim_end_matches('.');
    if trimmed.is_empty() || trimmed == "-" {
        "0".to_string()
    } else {
        trimmed.to_string()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn formats_integers_without_decimals() {
        assert_eq!(format_number(3.0), "3");
        assert_eq!(format_number(1024.0), "1024");
        assert_eq!(format_number(-2.0), "-2");
    }

    #[test]
    fn formats_repeating_decimals_to_twelve_significant_digits() {
        assert_eq!(format_number(10.0 / 3.0), "3.33333333333");
        assert_eq!(format_number(5.0 / 3.0), "1.66666666667");
    }

    #[test]
    fn formats_small_numbers_plainly() {
        assert_eq!(format_number(0.1), "0.1");
        assert_eq!(format_number(0.0001), "0.0001");
    }

    #[test]
    fn switches_to_scientific_notation_at_the_edges() {
        assert_eq!(format_number(1e20), "1e+20");
        assert_eq!(format_number(0.00001), "1e-05");
    }

    #[test]
    fn formats_non_finite_numbers() {
        assert_eq!(format_number(f64::INFINITY), "inf");
        assert_eq!(format_number(f64::NEG_INFINITY), "-inf");
        assert_eq!(format_number(f64::NAN), "nan");
        assert_eq!(format_number(0.0), "0");
    }

    #[test]
    fn quantities_render_with_their_display_unit() {
        let km = units::lookup("km").unwrap();
        let quantity = Quantity::from_unit(10.0, &km);
        assert_eq!(Value::Quantity(quantity.clone()).format(), "10 km");

        let metre = units::lookup("m").unwrap();
        let converted = quantity.convert_to(&metre).unwrap();
        assert_eq!(Value::Quantity(converted).format(), "10000 m");
    }

    #[test]
    fn quantities_without_a_display_unit_use_base_symbols() {
        let quantity = Quantity {
            base: 5.0,
            dim: units::dim_div(
                units::lookup("m").unwrap().dim,
                units::lookup("s").unwrap().dim,
            ),
            display: None,
        };
        assert_eq!(Value::Quantity(quantity).format(), "5 m/s");
    }

    #[test]
    fn mismatched_conversions_are_rejected() {
        let km = units::lookup("km").unwrap();
        let hour = units::lookup("h").unwrap();
        let error = Quantity::from_unit(1.0, &km).convert_to(&hour).unwrap_err();
        assert!(error.contains("Cannot convert"));
    }
}
