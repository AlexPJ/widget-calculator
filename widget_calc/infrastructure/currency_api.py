from __future__ import annotations

import time
from dataclasses import dataclass

import requests


@dataclass(slots=True)
class _CacheItem:
    loaded_at: float
    rates: dict[str, float]


class OpenExchangeRateCurrencyConverter:
    API_TEMPLATE = "https://open.er-api.com/v6/latest/{base}"
    CACHE_SECONDS = 1800

    def __init__(self) -> None:
        self._cache: dict[str, _CacheItem] = {}

    def convert(self, amount: float, from_currency: str, to_currency: str) -> float:
        source = from_currency.upper()
        target = to_currency.upper()
        if source == target:
            return amount

        rates = self._get_rates(source)
        if target not in rates:
            raise ValueError(f"Currency code not supported: {target}")
        return amount * rates[target]

    def _get_rates(self, base_currency: str) -> dict[str, float]:
        now = time.time()
        cached = self._cache.get(base_currency)
        if cached and now - cached.loaded_at < self.CACHE_SECONDS:
            return cached.rates

        response = requests.get(self.API_TEMPLATE.format(base=base_currency), timeout=5)
        response.raise_for_status()
        payload = response.json()

        if payload.get("result") != "success":
            raise ValueError("Currency API request failed")

        raw_rates = payload.get("rates")
        if not isinstance(raw_rates, dict):
            raise ValueError("Currency API returned invalid data")

        rates = {str(code).upper(): float(rate) for code, rate in raw_rates.items()}
        self._cache[base_currency] = _CacheItem(loaded_at=now, rates=rates)
        return rates
