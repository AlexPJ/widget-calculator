from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
import requests

from widget_calc.infrastructure.currency_api import OpenExchangeRateCurrencyConverter


@pytest.fixture
def converter() -> OpenExchangeRateCurrencyConverter:
    return OpenExchangeRateCurrencyConverter()


class TestOpenExchangeRateCurrencyConverter:
    @patch("widget_calc.infrastructure.currency_api.requests.get")
    def test_convert_usd_to_eur(self, mock_get: Mock, converter: OpenExchangeRateCurrencyConverter) -> None:
        mock_get.return_value = Mock(spec=requests.Response)
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "result": "success",
            "rates": {"EUR": 0.92, "GBP": 0.79, "JPY": 149.0},
        }
        mock_get.return_value.raise_for_status = Mock()

        result = converter.convert(100, "USD", "EUR")
        assert result == pytest.approx(92.0)
        mock_get.assert_called_once_with("https://open.er-api.com/v6/latest/USD", timeout=5)

    @patch("widget_calc.infrastructure.currency_api.requests.get")
    def test_same_currency_no_api_call(self, mock_get: Mock, converter: OpenExchangeRateCurrencyConverter) -> None:
        result = converter.convert(50, "USD", "USD")
        assert result == 50.0
        mock_get.assert_not_called()

    @patch("widget_calc.infrastructure.currency_api.requests.get")
    def test_invalid_currency_raises_error(self, mock_get: Mock, converter: OpenExchangeRateCurrencyConverter) -> None:
        mock_get.return_value = Mock(spec=requests.Response)
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "result": "success",
            "rates": {"EUR": 0.92},
        }
        mock_get.return_value.raise_for_status = Mock()

        with pytest.raises(ValueError, match="Currency code not supported"):
            converter.convert(100, "USD", "XYZ")

    @patch("widget_calc.infrastructure.currency_api.requests.get")
    def test_case_insensitivity(self, mock_get: Mock, converter: OpenExchangeRateCurrencyConverter) -> None:
        mock_get.return_value = Mock(spec=requests.Response)
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "result": "success",
            "rates": {"EUR": 0.92},
        }
        mock_get.return_value.raise_for_status = Mock()

        result = converter.convert(100, "usd", "eur")
        assert result == pytest.approx(92.0)

    @patch("widget_calc.infrastructure.currency_api.requests.get")
    def test_api_failure_raises_error(self, mock_get: Mock, converter: OpenExchangeRateCurrencyConverter) -> None:
        mock_get.return_value = Mock(spec=requests.Response)
        mock_get.return_value.raise_for_status.side_effect = requests.RequestException("API down")

        with pytest.raises(requests.RequestException):
            converter.convert(100, "USD", "EUR")

    @patch("widget_calc.infrastructure.currency_api.requests.get")
    def test_cache_reuses_rates(self, mock_get: Mock, converter: OpenExchangeRateCurrencyConverter) -> None:
        mock_get.return_value = Mock(spec=requests.Response)
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "result": "success",
            "rates": {"EUR": 0.92, "GBP": 0.79},
        }
        mock_get.return_value.raise_for_status = Mock()

        converter.convert(100, "USD", "EUR")
        converter.convert(100, "USD", "GBP")
        assert mock_get.call_count == 1  # second call should use cache

    @patch("widget_calc.infrastructure.currency_api.requests.get")
    def test_api_unsuccessful_result(self, mock_get: Mock, converter: OpenExchangeRateCurrencyConverter) -> None:
        mock_get.return_value = Mock(spec=requests.Response)
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "result": "error",
            "description": "...",
        }
        mock_get.return_value.raise_for_status = Mock()

        with pytest.raises(ValueError, match="Currency API request failed"):
            converter.convert(100, "USD", "EUR")
