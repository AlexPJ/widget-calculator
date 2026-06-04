from __future__ import annotations

import math
import re
from datetime import datetime
from typing import Any, Protocol
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pint

ASSIGNMENT_RE = re.compile(r"^\s*([A-Za-z_]\w*)\s*=\s*(.+)$")
CURRENCY_CONVERSION_RE = re.compile(r"^\s*(.+?)\s+([A-Za-z]{3})\s+to\s+([A-Za-z]{3})\s*$", re.IGNORECASE)
GENERIC_CONVERSION_RE = re.compile(r"^\s*(.+?)\s+to\s+(.+?)\s*$", re.IGNORECASE)
PERCENT_RE = re.compile(r"(\b[A-Za-z_]\w*|\d+(?:\.\d+)?|\([^()]+\))\s*%")
FUNCTION_CALL_RE = re.compile(r"^\s*([A-Za-z_]\w*)\s*\((.*)\)\s*$")
MAX_DISPLAY_PRECISION = 12


class CurrencyConverter(Protocol):
    def convert(self, amount: float, from_currency: str, to_currency: str) -> float: ...


class CalculatorEvaluator:
    def __init__(self, currency_converter: CurrencyConverter) -> None:
        self._currency_converter = currency_converter
        self._unit_registry: pint.UnitRegistry[Any] = pint.UnitRegistry(autoconvert_offset_to_baseunit=True)
        self._quantity_type = self._unit_registry.Quantity
        self._symbols = {
            "pi": math.pi,
            "e": math.e,
            "tau": math.tau,
            "abs": abs,
            "round": round,
            "min": min,
            "max": max,
            "pow": pow,
            "sqrt": math.sqrt,
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
            "asin": math.asin,
            "acos": math.acos,
            "atan": math.atan,
            "log": math.log,
            "log10": math.log10,
            "ln": math.log,
            "exp": math.exp,
            "now": self._now,
        }

    def _now(self, timezone_name: str) -> str:
        if not isinstance(timezone_name, str) or not timezone_name.strip():
            raise ValueError("now() requires a timezone name, e.g. now('UTC')")
        try:
            zone = ZoneInfo(timezone_name.strip())
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"Unknown timezone: {timezone_name!r}") from exc
        return datetime.now(zone).strftime("%Y-%m-%d %H:%M:%S %Z")

    def evaluate_lines(self, lines: list[str]) -> list[str]:
        variables: dict[str, Any] = {}
        results: list[str] = []

        for line in lines:
            text = line.strip()
            if not text:
                results.append("")
                continue

            try:
                assignment_match = ASSIGNMENT_RE.match(text)
                if assignment_match:
                    name, expression = assignment_match.groups()
                    variables[name] = self._evaluate_value(expression, variables)
                    results.append("")
                    continue

                value = self._evaluate_statement(text, variables)
                if isinstance(value, str):
                    results.append(value)
                else:
                    results.append(self._format_value(value))
            except Exception as exc:
                results.append(f"Error: {exc}")

        return results

    def sum_results(self, results: list[str]) -> float | None:
        """Sum every numeric result line, skipping strings, errors, and quantities.

        Returns the running total as a float, or None when nothing numeric was found.
        """
        total = 0.0
        counted = False
        for raw in results:
            text = raw.strip()
            if not text:
                continue
            if text.startswith("Error:"):
                continue
            try:
                total += float(text)
            except ValueError:
                continue
            counted = True
        return total if counted else None

    def _evaluate_statement(self, text: str, variables: dict[str, Any]) -> Any:
        currency_match = CURRENCY_CONVERSION_RE.match(text)
        if currency_match:
            amount_expr, source_currency, target_currency = currency_match.groups()
            amount = self._as_dimensionless_number(self._evaluate_value(amount_expr, variables))
            converted = self._currency_converter.convert(amount, source_currency, target_currency)
            return f"{self._format_number(converted)} {target_currency.upper()}"

        conversion_match = GENERIC_CONVERSION_RE.match(text)
        if conversion_match:
            source_expr, target_unit = conversion_match.groups()
            value = self._evaluate_value(source_expr, variables)
            if not isinstance(value, self._quantity_type):
                raise ValueError("Only quantities can use 'to' conversion")
            converted_qty = value.to(target_unit.strip())
            magnitude = self._format_number(float(converted_qty.magnitude))
            return f"{magnitude} {converted_qty.units:~P}"

        return self._evaluate_value(text, variables)

    def _evaluate_value(self, expression: str, variables: dict[str, Any]) -> Any:
        prepared = self._prepare_expression(expression)
        symbols = {**self._symbols, **variables}

        function_match = FUNCTION_CALL_RE.match(prepared)
        if function_match:
            name, raw_args = function_match.groups()
            if name in self._symbols and callable(self._symbols[name]):
                args = self._parse_function_args(raw_args, variables)
                fn = self._symbols[name]
                assert callable(fn)
                return fn(*args)

        try:
            return eval(prepared, {"__builtins__": {}}, symbols)
        except Exception:
            return self._unit_registry.parse_expression(prepared, **symbols)

    def _parse_function_args(
        self, raw_args: str, variables: dict[str, Any]
    ) -> list[Any]:
        raw_args = raw_args.strip()
        if not raw_args:
            return []
        args: list[str] = []
        depth = 0
        current: list[str] = []
        in_string: str | None = None
        for char in raw_args:
            if in_string is not None:
                current.append(char)
                if char == in_string:
                    in_string = None
                continue
            if char in {'"', "'"}:
                in_string = char
                current.append(char)
                continue
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            if char == "," and depth == 0:
                args.append("".join(current).strip())
                current = []
            else:
                current.append(char)
        if current:
            args.append("".join(current).strip())

        parsed: list[Any] = []
        for arg in args:
            if not arg:
                continue
            if (arg.startswith('"') and arg.endswith('"')) or (
                arg.startswith("'") and arg.endswith("'")
            ):
                parsed.append(arg[1:-1])
            else:
                parsed.append(self._evaluate_value(arg, variables))
        return parsed

    def _prepare_expression(self, expression: str) -> str:
        prepared = expression.replace("×", "*").replace("÷", "/").replace("^", "**")
        previous = None
        while prepared != previous:
            previous = prepared
            prepared = PERCENT_RE.sub(r"(\1/100)", prepared)
        return prepared

    def _as_dimensionless_number(self, value: Any) -> float:
        if isinstance(value, self._quantity_type):
            if not value.dimensionless:
                raise ValueError("Currency amount must be dimensionless")
            return float(value.magnitude)

        if isinstance(value, (int, float)):
            return float(value)

        raise ValueError("Currency amount must resolve to a number")

    def _format_value(self, value: Any) -> str:
        if isinstance(value, self._quantity_type):
            if value.dimensionless:
                return self._format_number(float(value.magnitude))
            compact = value.to_compact()
            return f"{self._format_number(float(compact.magnitude))} {compact.units:~P}"

        if isinstance(value, (int, float)):
            return self._format_number(float(value))

        return str(value)

    def _format_number(self, number: float) -> str:
        if not math.isfinite(number):
            return str(number)
        return f"{number:.{MAX_DISPLAY_PRECISION}g}"
