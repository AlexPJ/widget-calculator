//! Tokenizer, Pratt parser and evaluator for a single expression.
//!
//! Replaces the Python version's `eval()` + `pint.parse_expression()` pair with
//! one grammar that understands units natively, so `10 km / 2 h` and `sqrt(9)`
//! go through the same path.

use std::collections::HashMap;
use std::f64::consts::{E, PI, TAU};

use chrono::Utc;
use chrono_tz::{Tz, TZ_VARIANTS};

use super::units::{self, Unit};
use super::value::{Quantity, Value};

#[derive(Debug, Clone, PartialEq)]
enum Token {
    Number(f64),
    Ident(String),
    Text(String),
    Plus,
    Minus,
    Star,
    Slash,
    Caret,
    Percent,
    LParen,
    RParen,
    Comma,
}

fn is_ident_start(c: char) -> bool {
    c.is_alphabetic() || c == '_' || c == '\u{b0}' || c == '\u{b5}'
}

fn is_ident_continue(c: char) -> bool {
    is_ident_start(c) || c.is_ascii_digit()
}

fn tokenize(input: &str) -> Result<Vec<Token>, String> {
    let chars: Vec<char> = input.chars().collect();
    let mut tokens = Vec::new();
    let mut index = 0;

    while index < chars.len() {
        let current = chars[index];

        if current.is_whitespace() {
            index += 1;
            continue;
        }

        if current.is_ascii_digit()
            || (current == '.' && matches!(chars.get(index + 1), Some(c) if c.is_ascii_digit()))
        {
            let start = index;
            while index < chars.len() && (chars[index].is_ascii_digit() || chars[index] == '.') {
                index += 1;
            }
            // Exponent form: 1e5, 2.5e-3
            if index < chars.len() && (chars[index] == 'e' || chars[index] == 'E') {
                let mut lookahead = index + 1;
                if matches!(chars.get(lookahead), Some('+') | Some('-')) {
                    lookahead += 1;
                }
                if matches!(chars.get(lookahead), Some(c) if c.is_ascii_digit()) {
                    index = lookahead;
                    while index < chars.len() && chars[index].is_ascii_digit() {
                        index += 1;
                    }
                }
            }
            let literal: String = chars[start..index].iter().collect();
            let number = literal
                .parse::<f64>()
                .map_err(|_| format!("Invalid number: {literal}"))?;
            tokens.push(Token::Number(number));
            continue;
        }

        if is_ident_start(current) {
            let start = index;
            while index < chars.len() && is_ident_continue(chars[index]) {
                index += 1;
            }
            tokens.push(Token::Ident(chars[start..index].iter().collect()));
            continue;
        }

        if current == '"' || current == '\'' {
            let quote = current;
            index += 1;
            let start = index;
            while index < chars.len() && chars[index] != quote {
                index += 1;
            }
            if index >= chars.len() {
                return Err("Unterminated string".to_string());
            }
            tokens.push(Token::Text(chars[start..index].iter().collect()));
            index += 1;
            continue;
        }

        index += 1;
        match current {
            '+' => tokens.push(Token::Plus),
            '-' => tokens.push(Token::Minus),
            '*' => {
                if chars.get(index) == Some(&'*') {
                    index += 1;
                    tokens.push(Token::Caret);
                } else {
                    tokens.push(Token::Star);
                }
            }
            '\u{d7}' => tokens.push(Token::Star),
            '/' | '\u{f7}' => tokens.push(Token::Slash),
            '^' => tokens.push(Token::Caret),
            '%' => tokens.push(Token::Percent),
            '(' => tokens.push(Token::LParen),
            ')' => tokens.push(Token::RParen),
            ',' => tokens.push(Token::Comma),
            other => return Err(format!("Unexpected character: {other}")),
        }
    }

    Ok(tokens)
}

/// Variables assigned by earlier lines in the same evaluation.
pub type Variables = HashMap<String, Value>;

struct Parser<'a> {
    tokens: Vec<Token>,
    position: usize,
    variables: &'a Variables,
}

pub fn evaluate(expression: &str, variables: &Variables) -> Result<Value, String> {
    let tokens = tokenize(expression)?;
    if tokens.is_empty() {
        return Err("Empty expression".to_string());
    }
    let mut parser = Parser {
        tokens,
        position: 0,
        variables,
    };
    let value = parser.parse_expression()?;
    if parser.position < parser.tokens.len() {
        return Err(format!("Unexpected input near {}", parser.describe_rest()));
    }
    Ok(value)
}

impl<'a> Parser<'a> {
    fn peek(&self) -> Option<&Token> {
        self.tokens.get(self.position)
    }

    fn advance(&mut self) -> Option<Token> {
        let token = self.tokens.get(self.position).cloned();
        if token.is_some() {
            self.position += 1;
        }
        token
    }

    fn describe_rest(&self) -> String {
        match self.tokens.get(self.position) {
            Some(Token::Ident(name)) => name.clone(),
            Some(Token::Number(number)) => number.to_string(),
            Some(token) => format!("{token:?}"),
            None => "end of line".to_string(),
        }
    }

    fn parse_expression(&mut self) -> Result<Value, String> {
        let mut left = self.parse_term()?;
        loop {
            match self.peek() {
                Some(Token::Plus) => {
                    self.advance();
                    let right = self.parse_term()?;
                    left = add(&left, &right)?;
                }
                Some(Token::Minus) => {
                    self.advance();
                    let right = self.parse_term()?;
                    left = subtract(&left, &right)?;
                }
                _ => return Ok(left),
            }
        }
    }

    fn parse_term(&mut self) -> Result<Value, String> {
        let mut left = self.parse_unary()?;
        loop {
            match self.peek() {
                Some(Token::Star) => {
                    self.advance();
                    let right = self.parse_unary()?;
                    left = multiply(&left, &right)?;
                }
                Some(Token::Slash) => {
                    self.advance();
                    let right = self.parse_unary()?;
                    left = divide(&left, &right)?;
                }
                _ => return Ok(left),
            }
        }
    }

    fn parse_unary(&mut self) -> Result<Value, String> {
        match self.peek() {
            Some(Token::Minus) => {
                self.advance();
                let value = self.parse_unary()?;
                negate(&value)
            }
            Some(Token::Plus) => {
                self.advance();
                self.parse_unary()
            }
            _ => self.parse_power(),
        }
    }

    fn parse_power(&mut self) -> Result<Value, String> {
        let base = self.parse_postfix()?;
        if matches!(self.peek(), Some(Token::Caret)) {
            self.advance();
            // Right associative, and the exponent may itself be signed.
            let exponent = self.parse_unary()?;
            return power(&base, &exponent);
        }
        Ok(base)
    }

    fn parse_postfix(&mut self) -> Result<Value, String> {
        let mut value = self.parse_juxtaposition()?;
        while matches!(self.peek(), Some(Token::Percent)) {
            self.advance();
            value = divide(&value, &Value::Number(100.0))?;
        }
        Ok(value)
    }

    /// `10 km` and `9.8 m/s` — a primary followed by unit names multiplies.
    /// Only unit names take part, so `2 x` stays an error just like it was
    /// under `pint.parse_expression`.
    fn parse_juxtaposition(&mut self) -> Result<Value, String> {
        let mut value = self.parse_primary()?;
        loop {
            let name = match self.peek() {
                Some(Token::Ident(name)) => name.clone(),
                _ => return Ok(value),
            };
            if self.variables.contains_key(&name) || is_reserved(&name) {
                return Ok(value);
            }
            let Some(unit) = units::lookup(&name) else {
                return Ok(value);
            };
            self.advance();
            value = multiply(&value, &Value::Quantity(Quantity::from_unit(1.0, &unit)))?;
        }
    }

    fn parse_primary(&mut self) -> Result<Value, String> {
        match self.advance() {
            Some(Token::Number(number)) => Ok(Value::Number(number)),
            Some(Token::Text(text)) => Ok(Value::Text(text)),
            Some(Token::LParen) => {
                let value = self.parse_expression()?;
                match self.advance() {
                    Some(Token::RParen) => Ok(value),
                    _ => Err("Missing closing parenthesis".to_string()),
                }
            }
            Some(Token::Ident(name)) => self.parse_identifier(name),
            Some(token) => Err(format!("Unexpected token: {token:?}")),
            None => Err("Unexpected end of expression".to_string()),
        }
    }

    fn parse_identifier(&mut self, name: String) -> Result<Value, String> {
        if matches!(self.peek(), Some(Token::LParen)) {
            self.advance();
            let mut arguments = Vec::new();
            if !matches!(self.peek(), Some(Token::RParen)) {
                loop {
                    arguments.push(self.parse_expression()?);
                    match self.peek() {
                        Some(Token::Comma) => {
                            self.advance();
                        }
                        _ => break,
                    }
                }
            }
            match self.advance() {
                Some(Token::RParen) => {}
                _ => return Err("Missing closing parenthesis".to_string()),
            }
            return call_function(&name, &arguments);
        }

        if let Some(value) = self.variables.get(&name) {
            return Ok(value.clone());
        }
        match name.as_str() {
            "pi" => return Ok(Value::Number(PI)),
            "e" => return Ok(Value::Number(E)),
            "tau" => return Ok(Value::Number(TAU)),
            _ => {}
        }
        if let Some(unit) = units::lookup(&name) {
            return Ok(Value::Quantity(Quantity::from_unit(1.0, &unit)));
        }
        Err(format!("Unknown identifier: {name}"))
    }
}

fn is_reserved(name: &str) -> bool {
    matches!(name, "pi" | "e" | "tau") || FUNCTIONS.contains(&name)
}

const FUNCTIONS: &[&str] = &[
    "abs", "round", "floor", "ceil", "min", "max", "pow", "sqrt", "sin", "cos", "tan", "asin",
    "acos", "atan", "log", "log10", "ln", "exp", "now",
];

// ---------------------------------------------------------------- arithmetic

fn as_quantity(value: &Value) -> Result<Quantity, String> {
    match value {
        Value::Number(number) => Ok(Quantity {
            base: *number,
            dim: units::DIMENSIONLESS,
            display: None,
        }),
        Value::Quantity(quantity) => Ok(quantity.clone()),
        Value::Text(_) => Err("Cannot use text in arithmetic".to_string()),
    }
}

/// Collapse a plain dimensionless result back to a bare number.
fn simplify(quantity: Quantity) -> Value {
    if quantity.is_dimensionless() && quantity.display.is_none() {
        Value::Number(quantity.base)
    } else {
        Value::Quantity(quantity)
    }
}

/// Keep a display unit only when it is a pure scale factor; carrying an
/// offset scale (°C, °F) through arithmetic would misrepresent the result.
fn carry_display(quantity: &Quantity) -> Option<super::value::Display> {
    match &quantity.display {
        Some(display) if display.offset == 0.0 => Some(display.clone()),
        _ => None,
    }
}

fn add(left: &Value, right: &Value) -> Result<Value, String> {
    let (a, b) = (as_quantity(left)?, as_quantity(right)?);
    if a.dim != b.dim {
        return Err(format!(
            "Cannot add {} and {}",
            units::dim_symbol(a.dim),
            units::dim_symbol(b.dim)
        ));
    }
    Ok(simplify(Quantity {
        base: a.base + b.base,
        dim: a.dim,
        display: carry_display(&a).or_else(|| carry_display(&b)),
    }))
}

fn subtract(left: &Value, right: &Value) -> Result<Value, String> {
    let (a, b) = (as_quantity(left)?, as_quantity(right)?);
    if a.dim != b.dim {
        return Err(format!(
            "Cannot subtract {} from {}",
            units::dim_symbol(b.dim),
            units::dim_symbol(a.dim)
        ));
    }
    Ok(simplify(Quantity {
        base: a.base - b.base,
        dim: a.dim,
        display: carry_display(&a).or_else(|| carry_display(&b)),
    }))
}

fn multiply(left: &Value, right: &Value) -> Result<Value, String> {
    let (a, b) = (as_quantity(left)?, as_quantity(right)?);
    let display = if is_plain_scalar(&a) {
        carry_display(&b)
    } else if is_plain_scalar(&b) {
        carry_display(&a)
    } else {
        None
    };
    Ok(simplify(Quantity {
        base: a.base * b.base,
        dim: units::dim_mul(a.dim, b.dim),
        display,
    }))
}

fn divide(left: &Value, right: &Value) -> Result<Value, String> {
    let (a, b) = (as_quantity(left)?, as_quantity(right)?);
    if b.base == 0.0 {
        return Err("Division by zero".to_string());
    }
    let display = if is_plain_scalar(&b) {
        carry_display(&a)
    } else {
        None
    };
    Ok(simplify(Quantity {
        base: a.base / b.base,
        dim: units::dim_div(a.dim, b.dim),
        display,
    }))
}

fn negate(value: &Value) -> Result<Value, String> {
    let quantity = as_quantity(value)?;
    Ok(simplify(Quantity {
        base: -quantity.base,
        dim: quantity.dim,
        display: carry_display(&quantity),
    }))
}

fn power(base: &Value, exponent: &Value) -> Result<Value, String> {
    let exponent = exponent
        .as_number()
        .ok_or_else(|| "Exponent must be a number".to_string())?;
    let quantity = as_quantity(base)?;

    if quantity.is_dimensionless() && quantity.display.is_none() {
        return Ok(Value::Number(quantity.base.powf(exponent)));
    }
    if exponent.fract() != 0.0 || exponent.abs() > 127.0 {
        return Err("Units can only be raised to an integer power".to_string());
    }
    Ok(simplify(Quantity {
        base: quantity.base.powf(exponent),
        dim: units::dim_pow(quantity.dim, exponent as i8),
        display: None,
    }))
}

fn is_plain_scalar(quantity: &Quantity) -> bool {
    quantity.is_dimensionless() && quantity.display.is_none()
}

// ----------------------------------------------------------------- functions

fn number_argument(name: &str, arguments: &[Value], index: usize) -> Result<f64, String> {
    arguments
        .get(index)
        .and_then(Value::as_number)
        .ok_or_else(|| format!("{name}() expects a number"))
}

fn call_function(name: &str, arguments: &[Value]) -> Result<Value, String> {
    if name == "now" {
        let timezone = match arguments.first() {
            Some(Value::Text(text)) => text.clone(),
            _ => return Err("now() requires a timezone name, e.g. now('UTC')".to_string()),
        };
        return now(&timezone).map(Value::Text);
    }

    match name {
        "min" | "max" => {
            if arguments.is_empty() {
                return Err(format!("{name}() expects at least one number"));
            }
            let mut best = number_argument(name, arguments, 0)?;
            for index in 1..arguments.len() {
                let candidate = number_argument(name, arguments, index)?;
                best = if name == "min" {
                    best.min(candidate)
                } else {
                    best.max(candidate)
                };
            }
            Ok(Value::Number(best))
        }
        "round" => {
            let value = number_argument(name, arguments, 0)?;
            let digits = match arguments.len() {
                0 | 1 => 0,
                _ => number_argument(name, arguments, 1)? as i32,
            };
            Ok(Value::Number(round_half_even(value, digits)))
        }
        "log" => {
            let value = number_argument(name, arguments, 0)?;
            if arguments.len() > 1 {
                let base = number_argument(name, arguments, 1)?;
                Ok(Value::Number(value.log(base)))
            } else {
                Ok(Value::Number(value.ln()))
            }
        }
        "pow" => {
            let value = number_argument(name, arguments, 0)?;
            let exponent = number_argument(name, arguments, 1)?;
            Ok(Value::Number(value.powf(exponent)))
        }
        _ => {
            if !FUNCTIONS.contains(&name) {
                return Err(format!("Unknown function: {name}"));
            }
            let value = number_argument(name, arguments, 0)?;
            let result = match name {
                "abs" => value.abs(),
                "floor" => value.floor(),
                "ceil" => value.ceil(),
                "sqrt" => value.sqrt(),
                "sin" => value.sin(),
                "cos" => value.cos(),
                "tan" => value.tan(),
                "asin" => value.asin(),
                "acos" => value.acos(),
                "atan" => value.atan(),
                "log10" => value.log10(),
                "ln" => value.ln(),
                "exp" => value.exp(),
                _ => return Err(format!("Unknown function: {name}")),
            };
            Ok(Value::Number(result))
        }
    }
}

/// Python's `round()` rounds halves to even; mirror that so ported sheets
/// keep giving the same answers.
fn round_half_even(value: f64, digits: i32) -> f64 {
    let scale = 10f64.powi(digits);
    let scaled = value * scale;
    if !scaled.is_finite() {
        return value;
    }
    let floor = scaled.floor();
    let rounded = if scaled - floor == 0.5 {
        if (floor as i64) % 2 == 0 {
            floor
        } else {
            floor + 1.0
        }
    } else {
        scaled.round()
    };
    rounded / scale
}

fn now(timezone_name: &str) -> Result<String, String> {
    let trimmed = timezone_name.trim();
    if trimmed.is_empty() {
        return Err("now() requires a timezone name, e.g. now('UTC')".to_string());
    }
    let zone = resolve_timezone(trimmed).ok_or_else(|| format!("Unknown timezone: '{trimmed}'"))?;
    Ok(Utc::now()
        .with_timezone(&zone)
        .format("%Y-%m-%d %H:%M:%S %Z")
        .to_string())
}

fn resolve_timezone(name: &str) -> Option<Tz> {
    if let Ok(zone) = name.parse::<Tz>() {
        return Some(zone);
    }
    let lowered = name.to_ascii_lowercase();
    TZ_VARIANTS
        .iter()
        .find(|zone| zone.name().to_ascii_lowercase() == lowered)
        .copied()
}

/// Resolve a bare unit name, used by the `to` conversion syntax.
pub fn lookup_unit(name: &str) -> Option<Unit> {
    units::lookup(name.trim())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn eval(expression: &str) -> Result<Value, String> {
        evaluate(expression, &Variables::new())
    }

    fn rendered(expression: &str) -> String {
        eval(expression).unwrap().format()
    }

    #[test]
    fn evaluates_basic_arithmetic() {
        assert_eq!(rendered("1 + 2"), "3");
        assert_eq!(rendered("10 - 3"), "7");
        assert_eq!(rendered("4 * 5"), "20");
        assert_eq!(rendered("20 / 4"), "5");
    }

    #[test]
    fn honours_precedence_and_parentheses() {
        assert_eq!(rendered("2 + 3 * 4"), "14");
        assert_eq!(rendered("(2 + 3) * 4"), "20");
        assert_eq!(rendered("-5 + 3"), "-2");
    }

    #[test]
    fn supports_both_power_operators() {
        assert_eq!(rendered("2 ** 10"), "1024");
        assert_eq!(rendered("2 ^ 10"), "1024");
        // Unary minus binds looser than exponentiation, as in Python.
        assert_eq!(rendered("-5 ** 2"), "-25");
    }

    #[test]
    fn accepts_typographic_operators() {
        assert_eq!(rendered("3 \u{d7} 4"), "12");
        assert_eq!(rendered("8 \u{f7} 2"), "4");
    }

    #[test]
    fn exposes_constants_and_functions() {
        assert!(rendered("pi").starts_with("3.14159"));
        assert!(rendered("e").starts_with("2.71828"));
        assert_eq!(rendered("sqrt(9)"), "3");
        assert_eq!(rendered("sin(0)"), "0");
        assert_eq!(rendered("max(1, 7, 3)"), "7");
        assert_eq!(rendered("round(2.5)"), "2");
        assert_eq!(rendered("round(3.5)"), "4");
        assert_eq!(rendered("round(2.34567, 2)"), "2.35");
    }

    #[test]
    fn treats_percent_as_a_postfix_operator() {
        assert_eq!(rendered("10%"), "0.1");
        assert_eq!(rendered("200 * 10%"), "20");
        assert_eq!(rendered("100% + 50%"), "1.5");
        assert_eq!(rendered("(10 + 10)%"), "0.2");
    }

    #[test]
    fn attaches_units_by_juxtaposition() {
        assert_eq!(rendered("10 km"), "10 km");
        assert_eq!(rendered("5 km + 3 km"), "8 km");
        assert_eq!(rendered("10 km / 2"), "5 km");
    }

    #[test]
    fn derives_compound_units() {
        assert_eq!(rendered("100 m / 10 s"), "10 m/s");
    }

    #[test]
    fn angles_are_dimensionless() {
        let value = eval("180 deg").unwrap().as_number().unwrap();
        assert!((value - PI).abs() < 1e-12);
        assert!((eval("sin(90 deg)").unwrap().as_number().unwrap() - 1.0).abs() < 1e-12);
    }

    #[test]
    fn resolves_variables() {
        let mut variables = Variables::new();
        variables.insert("x".to_string(), Value::Number(5.0));
        assert_eq!(evaluate("x + 3", &variables).unwrap().format(), "8");
    }

    #[test]
    fn variables_shadow_units() {
        let mut variables = Variables::new();
        variables.insert("m".to_string(), Value::Number(4.0));
        assert_eq!(evaluate("m * 2", &variables).unwrap().format(), "8");
    }

    #[test]
    fn rejects_division_by_zero() {
        assert!(eval("1/0").is_err());
    }

    #[test]
    fn rejects_unknown_identifiers() {
        assert!(eval("invalid syntax !!!").is_err());
        assert!(eval("banana + 1").is_err());
    }

    #[test]
    fn rejects_mismatched_dimensions() {
        assert!(eval("1 km + 1 h").is_err());
    }

    #[test]
    fn now_formats_a_timestamp() {
        let Value::Text(stamp) = eval("now('UTC')").unwrap() else {
            panic!("now() must return text");
        };
        assert!(stamp.ends_with("UTC"));
        assert_eq!(stamp.len(), "2024-01-01 12:00:00 UTC".len());
    }

    #[test]
    fn now_accepts_lowercase_zones() {
        let Value::Text(stamp) = eval("now('utc')").unwrap() else {
            panic!("now() must return text");
        };
        assert!(stamp.ends_with("UTC"));
    }

    #[test]
    fn now_reports_unknown_zones() {
        let error = eval("now('Not/A/Zone')").unwrap_err();
        assert!(error.contains("Unknown timezone"));
        assert!(eval("now('')").is_err());
    }

    #[test]
    fn now_resolves_named_regions() {
        let Value::Text(stamp) = eval("now('Europe/Madrid')").unwrap() else {
            panic!("now() must return text");
        };
        assert!(stamp.ends_with("CET") || stamp.ends_with("CEST"));
    }
}
