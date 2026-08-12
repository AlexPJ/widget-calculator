//! Line-by-line evaluation: assignments, `to` conversions and running totals.

use std::sync::Arc;

use super::expr::{self, Variables};
use super::value::{format_number, Value};

/// Live exchange rates. Implemented by the infrastructure layer so the domain
/// stays free of HTTP concerns (and testable with a stub).
pub trait CurrencyConverter: Send + Sync {
    fn convert(&self, amount: f64, from_currency: &str, to_currency: &str) -> Result<f64, String>;
}

pub struct CalculatorEvaluator {
    currency: Arc<dyn CurrencyConverter>,
}

impl CalculatorEvaluator {
    pub fn new(currency: Arc<dyn CurrencyConverter>) -> Self {
        Self { currency }
    }

    /// Evaluate every line, returning one result per input line. Assignments
    /// produce an empty string and make their name available to later lines.
    pub fn evaluate_lines(&self, lines: &[String]) -> Vec<String> {
        let mut variables = Variables::new();
        let mut results = Vec::with_capacity(lines.len());

        for line in lines {
            let text = line.trim();
            if text.is_empty() {
                results.push(String::new());
                continue;
            }

            match self.evaluate_line(text, &mut variables) {
                Ok(output) => results.push(output),
                Err(error) => results.push(format!("Error: {error}")),
            }
        }

        results
    }

    fn evaluate_line(&self, text: &str, variables: &mut Variables) -> Result<String, String> {
        if let Some((name, expression)) = split_assignment(text) {
            let value = self.evaluate_statement(expression, variables)?;
            variables.insert(name.to_string(), value);
            return Ok(String::new());
        }
        Ok(self.evaluate_statement(text, variables)?.format())
    }

    /// A statement is an expression plus the two `to` conversion forms.
    fn evaluate_statement(&self, text: &str, variables: &Variables) -> Result<Value, String> {
        if let Some((amount, from_currency, to_currency)) = split_currency_conversion(text) {
            let value = expr::evaluate(amount, variables)?;
            let number = value
                .as_number()
                .ok_or_else(|| "Currency amount must resolve to a number".to_string())?;
            let converted = self.currency.convert(number, from_currency, to_currency)?;
            return Ok(Value::Text(format!(
                "{} {}",
                format_number(converted),
                to_currency.to_uppercase()
            )));
        }

        if let Some((source, target)) = split_conversion(text) {
            let value = expr::evaluate(source, variables)?;
            let Value::Quantity(quantity) = value else {
                return Err("Only quantities can use 'to' conversion".to_string());
            };
            let unit =
                expr::lookup_unit(target).ok_or_else(|| format!("Unknown unit: {target}"))?;
            return Ok(Value::Quantity(quantity.convert_to(&unit)?));
        }

        expr::evaluate(text, variables)
    }

    /// Sum every numeric result line, skipping blanks, errors and quantities.
    /// Returns `None` when nothing numeric was found.
    pub fn sum_results(&self, results: &[String]) -> Option<f64> {
        let mut total = 0.0;
        let mut counted = false;
        for raw in results {
            let text = raw.trim();
            if text.is_empty() || text.starts_with("Error:") {
                continue;
            }
            if let Ok(number) = text.parse::<f64>() {
                total += number;
                counted = true;
            }
        }
        counted.then_some(total)
    }
}

/// `name = expression`, with `name` a plain identifier. `==` is not an
/// assignment.
fn split_assignment(text: &str) -> Option<(&str, &str)> {
    let bytes = text.as_bytes();
    let mut index = 0;
    if !matches!(bytes.first(), Some(c) if c.is_ascii_alphabetic() || *c == b'_') {
        return None;
    }
    while index < bytes.len() && (bytes[index].is_ascii_alphanumeric() || bytes[index] == b'_') {
        index += 1;
    }
    let name = &text[..index];
    let rest = text[index..].trim_start();
    let expression = rest.strip_prefix('=')?;
    if expression.starts_with('=') {
        return None;
    }
    let expression = expression.trim();
    (!expression.is_empty()).then_some((name, expression))
}

/// A three-letter word that is not a unit we know about. The unit check is
/// what keeps `2 sec to min` a time conversion instead of a doomed lookup for
/// the "SEC" currency.
fn is_currency_code(token: &str) -> bool {
    token.len() == 3
        && token.chars().all(|c| c.is_ascii_alphabetic())
        && expr::lookup_unit(token).is_none()
}

/// `<expression> <XXX> to <YYY>`, e.g. `10 + 10 usd to eur`.
fn split_currency_conversion(text: &str) -> Option<(&str, &str, &str)> {
    let trimmed = text.trim_end();
    let target_start = trimmed.rfind(char::is_whitespace)? + 1;
    let target = &trimmed[target_start..];
    if !is_currency_code(target) {
        return None;
    }

    let head = trimmed[..target_start].trim_end();
    let to_start = head.rfind(char::is_whitespace)? + 1;
    if !head[to_start..].eq_ignore_ascii_case("to") {
        return None;
    }

    let head = head[..to_start].trim_end();
    let source_start = head.rfind(char::is_whitespace)? + 1;
    let source = &head[source_start..];
    if !is_currency_code(source) {
        return None;
    }

    let amount = head[..source_start].trim();
    (!amount.is_empty()).then_some((amount, source, target))
}

/// `<expression> to <unit>`, split on the first standalone `to`.
fn split_conversion(text: &str) -> Option<(&str, &str)> {
    let bytes = text.as_bytes();
    let mut search = 0;
    while let Some(offset) = text[search..].find("to") {
        let start = search + offset;
        let end = start + 2;
        let before_is_space = start > 0 && bytes[start - 1].is_ascii_whitespace();
        let after_is_space = end < bytes.len() && bytes[end].is_ascii_whitespace();
        if before_is_space && after_is_space {
            let source = text[..start].trim();
            let target = text[end..].trim();
            if !source.is_empty() && !target.is_empty() {
                return Some((source, target));
            }
        }
        search = end;
    }
    None
}

#[cfg(test)]
mod tests {
    use super::*;

    struct FixedRate(f64);

    impl CurrencyConverter for FixedRate {
        fn convert(&self, _amount: f64, _from: &str, _to: &str) -> Result<f64, String> {
            Ok(self.0)
        }
    }

    struct TableRates;

    impl CurrencyConverter for TableRates {
        fn convert(&self, amount: f64, from: &str, to: &str) -> Result<f64, String> {
            let rate = |code: &str| match code.to_ascii_lowercase().as_str() {
                "usd" => Ok(1.0),
                "eur" => Ok(0.92),
                "gbp" => Ok(0.79),
                "jpy" => Ok(149.0),
                other => Err(format!("Currency code not supported: {other}")),
            };
            if from.eq_ignore_ascii_case(to) {
                return Ok(amount);
            }
            Ok(amount / rate(from)? * rate(to)?)
        }
    }

    fn evaluator() -> CalculatorEvaluator {
        CalculatorEvaluator::new(Arc::new(FixedRate(42.0)))
    }

    fn run(lines: &[&str]) -> Vec<String> {
        let owned: Vec<String> = lines.iter().map(|line| line.to_string()).collect();
        evaluator().evaluate_lines(&owned)
    }

    #[test]
    fn evaluates_arithmetic_lines() {
        assert_eq!(run(&["1 + 2"]), vec!["3"]);
        assert_eq!(run(&["10 / 3"]), vec!["3.33333333333"]);
    }

    #[test]
    fn assignments_return_nothing_and_bind_variables() {
        assert_eq!(run(&["x = 5"]), vec![""]);
        assert_eq!(run(&["x = 5", "x + 3"]), vec!["", "8"]);
        assert_eq!(run(&["a = 10", "b = 20", "a + b"]), vec!["", "", "30"]);
    }

    #[test]
    fn mixed_lines_keep_their_positions() {
        assert_eq!(
            run(&["a = 5", "b = 3", "a * b", "a / b", ""]),
            vec!["", "", "15", "1.66666666667", ""]
        );
    }

    #[test]
    fn blank_lines_stay_blank() {
        assert_eq!(run(&[""]), vec![""]);
        assert_eq!(run(&["   "]), vec![""]);
    }

    #[test]
    fn errors_are_reported_inline() {
        assert!(run(&["1/0"])[0].starts_with("Error:"));
        assert!(run(&["invalid syntax !!!"])[0].starts_with("Error:"));
    }

    #[test]
    fn converts_units() {
        assert_eq!(run(&["10 km to m"]), vec!["10000 m"]);
        assert!(run(&["2 h to min"])[0].contains("min"));
        assert_eq!(run(&["2 h to min"]), vec!["120 min"]);
        assert_eq!(run(&["1 gb to mb"]), vec!["1000 mb"]);
    }

    #[test]
    fn rejects_conversions_of_plain_numbers() {
        assert!(run(&["2 to 3"])[0].contains("Only quantities"));
    }

    #[test]
    fn converts_currency() {
        let results = run(&["20 usd to eur"]);
        assert!(results[0].contains("EUR") && results[0].contains("42"));
    }

    #[test]
    fn currency_amount_may_be_an_expression() {
        let evaluator = CalculatorEvaluator::new(Arc::new(TableRates));
        let results = evaluator.evaluate_lines(&["10 + 10 usd to eur".to_string()]);
        assert_eq!(results, vec!["18.4 EUR"]);
    }

    #[test]
    fn percentages_behave_like_fractions() {
        assert_eq!(run(&["10%"]), vec!["0.1"]);
        assert_eq!(run(&["200 * 10%"]), vec!["20"]);
    }

    #[test]
    fn now_can_be_assigned() {
        assert_eq!(run(&["t = now('UTC')"]), vec![""]);
        assert!(run(&["t = now('UTC')", "t"])[1].ends_with("UTC"));
    }

    #[test]
    fn sums_numeric_results_only() {
        let evaluator = evaluator();
        let sum = |lines: &[&str]| {
            let owned: Vec<String> = lines.iter().map(|line| line.to_string()).collect();
            evaluator.sum_results(&owned)
        };
        assert_eq!(sum(&["1", "2", "3"]), Some(6.0));
        assert_eq!(sum(&["1.5", "2.5"]), Some(4.0));
        assert_eq!(sum(&["10", "-3", "1"]), Some(8.0));
        assert_eq!(sum(&["1e2", "1e1"]), Some(110.0));
        assert_eq!(sum(&["5", "Error: bad", "3"]), Some(8.0));
        assert_eq!(sum(&["5", "10 m", "3"]), Some(8.0));
        assert_eq!(sum(&["5", "2026-06-04 12:00:00 UTC", "3"]), Some(8.0));
        assert_eq!(sum(&["", "5", "", "3", ""]), Some(8.0));
        assert_eq!(sum(&["", "Error: bad", "10 m"]), None);
        assert_eq!(sum(&[]), None);
    }

    #[test]
    fn splits_assignments() {
        assert_eq!(split_assignment("x = 5"), Some(("x", "5")));
        assert_eq!(split_assignment("my_var=1+2"), Some(("my_var", "1+2")));
        assert_eq!(split_assignment("1 + 2"), None);
        assert_eq!(split_assignment("x == 5"), None);
        assert_eq!(split_assignment("x ="), None);
    }

    #[test]
    fn splits_currency_conversions() {
        assert_eq!(
            split_currency_conversion("10 + 10 usd to eur"),
            Some(("10 + 10", "usd", "eur"))
        );
        assert_eq!(split_currency_conversion("10 km to m"), None);
        assert_eq!(split_currency_conversion("usd to eur"), None);
        // Three-letter unit names must not be mistaken for currencies.
        assert_eq!(split_currency_conversion("2 sec to min"), None);
    }

    #[test]
    fn three_letter_units_still_convert() {
        assert_eq!(run(&["120 sec to min"]), vec!["2 min"]);
    }

    #[test]
    fn splits_unit_conversions_on_the_first_to() {
        assert_eq!(split_conversion("10 km to m"), Some(("10 km", "m")));
        assert_eq!(split_conversion("total + 1"), None);
        assert_eq!(split_conversion("2 h to min"), Some(("2 h", "min")));
    }
}
