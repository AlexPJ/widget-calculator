from __future__ import annotations

from unittest.mock import Mock

import pytest

from widget_calc.domain.calculator import CalculatorEvaluator, CurrencyConverter


@pytest.fixture
def evaluator() -> CalculatorEvaluator:
    mock_cc = Mock(spec=CurrencyConverter)
    mock_cc.convert.return_value = 42.0
    return CalculatorEvaluator(mock_cc)


@pytest.fixture
def evaluator_with_cc() -> CalculatorEvaluator:
    mock_cc = Mock(spec=CurrencyConverter)

    def convert(amount: float, from_cur: str, to_cur: str) -> float:
        rates = {"usd": 1.0, "eur": 0.92, "gbp": 0.79, "jpy": 149.0}
        if from_cur.lower() == to_cur.lower():
            return amount
        usd_amount = amount / rates[from_cur.lower()]
        return usd_amount * rates[to_cur.lower()]

    mock_cc.convert.side_effect = convert
    return CalculatorEvaluator(mock_cc)


class TestCalculatorEvaluator:
    def test_simple_addition(self, evaluator: CalculatorEvaluator) -> None:
        assert evaluator.evaluate_lines(["1 + 2"]) == ["3"]

    def test_subtraction(self, evaluator: CalculatorEvaluator) -> None:
        assert evaluator.evaluate_lines(["10 - 3"]) == ["7"]

    def test_multiplication(self, evaluator: CalculatorEvaluator) -> None:
        assert evaluator.evaluate_lines(["4 * 5"]) == ["20"]

    def test_division(self, evaluator: CalculatorEvaluator) -> None:
        assert evaluator.evaluate_lines(["20 / 4"]) == ["5"]

    def test_power(self, evaluator: CalculatorEvaluator) -> None:
        assert evaluator.evaluate_lines(["2 ** 10"]) == ["1024"]

    def test_caret_power(self, evaluator: CalculatorEvaluator) -> None:
        assert evaluator.evaluate_lines(["2 ^ 10"]) == ["1024"]

    def test_times_symbol(self, evaluator: CalculatorEvaluator) -> None:
        assert evaluator.evaluate_lines(["3 \u00d7 4"]) == ["12"]

    def test_divide_symbol(self, evaluator: CalculatorEvaluator) -> None:
        assert evaluator.evaluate_lines(["8 \u00f7 2"]) == ["4"]

    def test_pi_constant(self, evaluator: CalculatorEvaluator) -> None:
        results = evaluator.evaluate_lines(["pi"])
        assert results[0].startswith("3.14159")

    def test_e_constant(self, evaluator: CalculatorEvaluator) -> None:
        results = evaluator.evaluate_lines(["e"])
        assert results[0].startswith("2.71828")

    def test_sqrt(self, evaluator: CalculatorEvaluator) -> None:
        assert evaluator.evaluate_lines(["sqrt(9)"]) == ["3"]

    def test_sin(self, evaluator: CalculatorEvaluator) -> None:
        assert evaluator.evaluate_lines(["sin(0)"]) == ["0"]

    def test_assignment(self, evaluator: CalculatorEvaluator) -> None:
        assert evaluator.evaluate_lines(["x = 5"]) == [""]

    def test_variable_reference(self, evaluator: CalculatorEvaluator) -> None:
        assert evaluator.evaluate_lines(["x = 5", "x + 3"]) == ["", "8"]

    def test_multi_line_with_mixed(self, evaluator: CalculatorEvaluator) -> None:
        assert evaluator.evaluate_lines(["a = 10", "b = 20", "a + b"]) == ["", "", "30"]

    def test_percent_literal(self, evaluator: CalculatorEvaluator) -> None:
        assert evaluator.evaluate_lines(["10%"]) == ["0.1"]

    def test_percent_in_expression(self, evaluator: CalculatorEvaluator) -> None:
        assert evaluator.evaluate_lines(["200 * 10%"]) == ["20"]

    def test_percent_multiple(self, evaluator: CalculatorEvaluator) -> None:
        results = evaluator.evaluate_lines(["100% + 50%"])
        assert float(results[0]) == pytest.approx(1.5)

    def test_unit_conversion_time(self, evaluator: CalculatorEvaluator) -> None:
        results = evaluator.evaluate_lines(["2 h to min"])
        assert "min" in results[0]

    def test_unit_conversion_metric(self, evaluator: CalculatorEvaluator) -> None:
        results = evaluator.evaluate_lines(["10 km to m"])
        assert results[0] == "10000 m"

    def test_currency_conversion(self, evaluator: CalculatorEvaluator) -> None:
        results = evaluator.evaluate_lines(["20 usd to eur"])
        assert "EUR" in results[0] and "42" in results[0]

    def test_currency_with_expression(self, evaluator_with_cc: CalculatorEvaluator) -> None:
        results = evaluator_with_cc.evaluate_lines(["10 + 10 usd to eur"])
        assert "EUR" in results[0]
        assert "18.4" in results[0]

    def test_empty_line(self, evaluator: CalculatorEvaluator) -> None:
        assert evaluator.evaluate_lines([""]) == [""]

    def test_blank_line(self, evaluator: CalculatorEvaluator) -> None:
        assert evaluator.evaluate_lines(["   "]) == [""]

    def test_division_by_zero(self, evaluator: CalculatorEvaluator) -> None:
        results = evaluator.evaluate_lines(["1/0"])
        assert results[0].startswith("Error:")

    def test_invalid_expression(self, evaluator: CalculatorEvaluator) -> None:
        results = evaluator.evaluate_lines(["invalid syntax !!!"])
        assert results[0].startswith("Error:")

    def test_mixed_lines(self, evaluator: CalculatorEvaluator) -> None:
        lines = ["a = 5", "b = 3", "a * b", "a / b", ""]
        results = evaluator.evaluate_lines(lines)
        assert results == ["", "", "15", "1.66666666667", ""]

    def test_operator_precedence(self, evaluator: CalculatorEvaluator) -> None:
        assert evaluator.evaluate_lines(["2 + 3 * 4"]) == ["14"]

    def test_parentheses(self, evaluator: CalculatorEvaluator) -> None:
        assert evaluator.evaluate_lines(["(2 + 3) * 4"]) == ["20"]

    def test_negative_numbers(self, evaluator: CalculatorEvaluator) -> None:
        assert evaluator.evaluate_lines(["-5 + 3"]) == ["-2"]

    def test_float_result(self, evaluator: CalculatorEvaluator) -> None:
        assert evaluator.evaluate_lines(["10 / 3"]) == ["3.33333333333"]


class TestNowFunction:
    def test_now_utc_returns_iso_like_string(self, evaluator: CalculatorEvaluator) -> None:
        result = evaluator.evaluate_lines(["now('UTC')"])[0]
        assert isinstance(result, str)
        assert result.endswith("UTC")
        assert len(result) == len("2024-01-01 12:00:00 UTC")

    def test_now_known_timezone(self, evaluator: CalculatorEvaluator) -> None:
        result = evaluator.evaluate_lines(["now('Europe/Madrid')"])[0]
        assert result.endswith("CEST") or result.endswith("CET")

    def test_now_lowercase_timezone(self, evaluator: CalculatorEvaluator) -> None:
        result = evaluator.evaluate_lines(["now('utc')"])[0]
        assert result.endswith("UTC")

    def test_now_invalid_timezone(self, evaluator: CalculatorEvaluator) -> None:
        result = evaluator.evaluate_lines(["now('Not/A/Zone')"])[0]
        assert result.startswith("Error:")
        assert "Unknown timezone" in result

    def test_now_empty_timezone(self, evaluator: CalculatorEvaluator) -> None:
        result = evaluator.evaluate_lines(["now('')"])[0]
        assert result.startswith("Error:")

    def test_now_within_assignment(self, evaluator: CalculatorEvaluator) -> None:
        result = evaluator.evaluate_lines(["t = now('UTC')"])[0]
        assert result == ""


class TestSumResults:
    def test_sums_plain_numbers(self, evaluator: CalculatorEvaluator) -> None:
        assert evaluator.sum_results(["1", "2", "3"]) == 6.0

    def test_sums_floats(self, evaluator: CalculatorEvaluator) -> None:
        assert evaluator.sum_results(["1.5", "2.5"]) == 4.0

    def test_sums_negatives(self, evaluator: CalculatorEvaluator) -> None:
        assert evaluator.sum_results(["10", "-3", "1"]) == 8.0

    def test_sums_scientific_notation(self, evaluator: CalculatorEvaluator) -> None:
        assert evaluator.sum_results(["1e2", "1e1"]) == 110.0

    def test_skips_errors(self, evaluator: CalculatorEvaluator) -> None:
        assert evaluator.sum_results(["5", "Error: bad", "3"]) == 8.0

    def test_skips_quantity_strings(self, evaluator: CalculatorEvaluator) -> None:
        assert evaluator.sum_results(["5", "10 m", "3"]) == 8.0

    def test_skips_date_strings(self, evaluator: CalculatorEvaluator) -> None:
        assert evaluator.sum_results(["5", "2026-06-04 12:00:00 UTC", "3"]) == 8.0

    def test_skips_empty_lines(self, evaluator: CalculatorEvaluator) -> None:
        assert evaluator.sum_results(["", "5", "", "3", ""]) == 8.0

    def test_returns_none_when_no_numeric(self, evaluator: CalculatorEvaluator) -> None:
        assert evaluator.sum_results(["", "Error: bad", "10 m"]) is None

    def test_returns_none_for_empty(self, evaluator: CalculatorEvaluator) -> None:
        assert evaluator.sum_results([]) is None
