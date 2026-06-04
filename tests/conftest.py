from __future__ import annotations

from collections.abc import Generator
from unittest.mock import Mock

import pytest

from widget_calc.domain.calculator import CurrencyConverter


@pytest.fixture
def mock_currency_converter() -> Generator[CurrencyConverter, None, None]:
    mock = Mock(spec=CurrencyConverter)
    mock.convert.return_value = 42.0
    yield mock
