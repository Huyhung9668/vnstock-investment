from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from providers.base import ProviderSchemaError, ProviderTimeoutError, TradePlanningProvider
from providers.free_provider import FreeTradePlanningProvider


DictStrAny = dict[str, Any]


class FakeFreeProvider(TradePlanningProvider):
    def provider_name(self) -> str:
        return "free"

    def health_check(self) -> dict[str, Any]:
        return {"status": "ok"}

    def get_company_profile(self, symbol: str) -> dict[str, Any]:
        return self.merge_with_metadata(
            payload={"symbol": symbol.upper(), "company_name": "FPT Corp"},
            symbol=symbol,
        )

    def get_price_summary(self, symbol: str) -> dict[str, Any]:
        return self.merge_with_metadata(
            payload={"symbol": symbol.upper(), "last_close": 123.4, "day_change_pct": 1.2},
            symbol=symbol,
        )

    def get_financial_summary(self, symbol: str) -> dict[str, Any] | None:
        return None

    def get_news_summary(self, symbol: str) -> dict[str, Any] | None:
        return self.merge_with_metadata(
            payload={"article_count": 2, "latest_title": "Positive update"},
            symbol=symbol,
        )

    def get_breadth_context(self) -> dict[str, Any] | None:
        return None


class FakePaidProvider(TradePlanningProvider):
    def provider_name(self) -> str:
        return "paid"

    def health_check(self) -> dict[str, Any]:
        return {"status": "ok"}

    def get_company_profile(self, symbol: str) -> dict[str, Any]:
        return self.merge_with_metadata(
            payload={"ticker": symbol.upper(), "name": "FPT Corporation"},
            symbol=symbol,
        )

    def get_price_summary(self, symbol: str) -> dict[str, Any]:
        return self.merge_with_metadata(
            payload={"symbol": symbol.upper(), "close": 123.4, "trend": "up"},
            symbol=symbol,
        )

    def get_financial_summary(self, symbol: str) -> dict[str, Any] | None:
        return self.merge_with_metadata(
            payload={"revenue": 1000, "profit": 200},
            symbol=symbol,
        )

    def get_news_summary(self, symbol: str) -> dict[str, Any] | None:
        return self.merge_with_metadata(
            payload={"headline_count": 3, "sentiment": "positive"},
            symbol=symbol,
        )

    def get_breadth_context(self) -> dict[str, Any] | None:
        return {"advance_decline": 1.1}


def normalize_provider_snapshot(provider: TradePlanningProvider, symbol: str) -> DictStrAny:
    normalized_symbol = symbol.strip().upper()
    warnings: list[str] = []

    company_data = provider.get_company_profile(normalized_symbol)
    price_data = provider.get_price_summary(normalized_symbol)
    financial_data = provider.get_financial_summary(normalized_symbol)
    news_data = provider.get_news_summary(normalized_symbol)

    if financial_data is None:
        warnings.append("financial_data unavailable")
    if news_data is None:
        warnings.append("news_data unavailable")

    return {
        "symbol": normalized_symbol,
        "company_data": dict(company_data),
        "price_data": dict(price_data),
        "financial_data": {
            "available": financial_data is not None,
            "payload": None if financial_data is None else dict(financial_data),
        },
        "news_data": {
            "available": news_data is not None,
            "payload": None if news_data is None else dict(news_data),
        },
        "warnings": warnings,
    }


@pytest.mark.parametrize("provider", [FakeFreeProvider(), FakePaidProvider()])
def test_provider_minimum_normalized_schema_has_required_keys(provider: TradePlanningProvider) -> None:
    snapshot = normalize_provider_snapshot(provider, "fpt")

    assert set(snapshot.keys()) >= {
        "symbol",
        "price_data",
        "financial_data",
        "news_data",
        "warnings",
    }
    assert snapshot["symbol"] == "FPT"
    assert isinstance(snapshot["company_data"], dict)
    assert isinstance(snapshot["price_data"], dict)
    assert isinstance(snapshot["financial_data"], dict)
    assert isinstance(snapshot["news_data"], dict)
    assert isinstance(snapshot["warnings"], list)
    assert snapshot["company_data"]["source"] == provider.provider_name()
    assert snapshot["price_data"]["source"] == provider.provider_name()
    assert "timestamp" in snapshot["company_data"]
    assert "timestamp" in snapshot["price_data"]


def test_free_and_paid_providers_match_same_minimum_normalized_shape() -> None:
    free_snapshot = normalize_provider_snapshot(FakeFreeProvider(), "fpt")
    paid_snapshot = normalize_provider_snapshot(FakePaidProvider(), "fpt")

    assert set(free_snapshot.keys()) == set(paid_snapshot.keys())
    assert set(free_snapshot["financial_data"].keys()) == {"available", "payload"}
    assert set(free_snapshot["news_data"].keys()) == {"available", "payload"}
    assert set(paid_snapshot["financial_data"].keys()) == {"available", "payload"}
    assert set(paid_snapshot["news_data"].keys()) == {"available", "payload"}
    assert free_snapshot["company_data"]["symbol"] == "FPT"
    assert paid_snapshot["company_data"]["symbol"] == "FPT"


def test_missing_optional_fields_are_explicit_not_silently_removed() -> None:
    snapshot = normalize_provider_snapshot(FakeFreeProvider(), "fpt")

    assert "financial_data" in snapshot
    assert snapshot["financial_data"]["available"] is False
    assert snapshot["financial_data"]["payload"] is None
    assert "financial_data unavailable" in snapshot["warnings"]


def test_present_optional_fields_are_marked_available() -> None:
    snapshot = normalize_provider_snapshot(FakePaidProvider(), "fpt")

    assert snapshot["financial_data"]["available"] is True
    assert snapshot["financial_data"]["payload"]["revenue"] == 1000
    assert snapshot["financial_data"]["payload"]["profit"] == 200
    assert snapshot["financial_data"]["payload"]["symbol"] == "FPT"
    assert snapshot["financial_data"]["payload"]["source"] == "paid"
    assert "timestamp" in snapshot["financial_data"]["payload"]
    assert snapshot["news_data"]["available"] is True
    assert snapshot["news_data"]["payload"]["headline_count"] == 3
    assert snapshot["news_data"]["payload"]["sentiment"] == "positive"
    assert snapshot["news_data"]["payload"]["symbol"] == "FPT"
    assert snapshot["news_data"]["payload"]["source"] == "paid"
    assert "timestamp" in snapshot["news_data"]["payload"]
    assert snapshot["warnings"] == []


def test_normalized_shape_does_not_depend_on_raw_field_name_differences() -> None:
    free_snapshot = normalize_provider_snapshot(FakeFreeProvider(), "fpt")
    paid_snapshot = normalize_provider_snapshot(FakePaidProvider(), "fpt")

    assert free_snapshot["symbol"] == paid_snapshot["symbol"] == "FPT"
    assert "company_data" in free_snapshot
    assert "company_data" in paid_snapshot
    assert "price_data" in free_snapshot
    assert "price_data" in paid_snapshot
    assert isinstance(free_snapshot["company_data"], dict)
    assert isinstance(paid_snapshot["company_data"], dict)
    assert isinstance(free_snapshot["price_data"], dict)
    assert isinstance(paid_snapshot["price_data"], dict)


def test_free_provider_company_profile_includes_stable_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = FreeTradePlanningProvider(source="VCI")

    monkeypatch.setattr(provider, "_get_stock_client", lambda symbol: object())
    monkeypatch.setattr(provider, "_get_company_client", lambda stock_client: object())

    def fake_required_dataframe_call(
        client: object,
        *,
        method_name: str,
        section_name: str,
        symbol: str,
        **kwargs: Any,
    ) -> Any:
        import pandas as pd

        return pd.DataFrame([{"company_name": "FPT Corporation"}])

    monkeypatch.setattr(provider, "_required_dataframe_call", fake_required_dataframe_call)

    payload = provider.get_company_profile("fpt")

    assert payload["symbol"] == "FPT"
    assert payload["source"] == "VCI"
    assert "timestamp" in payload
    assert payload["name"] == "FPT Corporation"
    assert payload["company_name"] == "FPT Corporation"


def test_free_provider_required_section_raises_explicit_schema_error(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = FreeTradePlanningProvider(source="VCI")

    class QuoteClient:
        def history(self, start: str, end: str) -> object:
            return "not-a-tabular-payload"

    with pytest.raises(ProviderSchemaError, match="price_summary returned an invalid schema"):
        provider._fetch_price_history(QuoteClient(), "FPT")


def test_free_provider_required_section_raises_explicit_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = FreeTradePlanningProvider(source="VCI")

    class QuoteClient:
        def history(self, start: str, end: str) -> object:
            raise TimeoutError("network timeout")

    with pytest.raises(ProviderTimeoutError, match="Timeout while fetching price_summary for FPT"):
        provider._fetch_price_history(QuoteClient(), "FPT")


def test_free_provider_optional_fields_remain_explicitly_unavailable() -> None:
    snapshot = normalize_provider_snapshot(FakeFreeProvider(), "fpt")

    assert snapshot["financial_data"] == {"available": False, "payload": None}
    assert snapshot["news_data"]["available"] is True


def test_free_provider_available_optional_blocks_have_stable_status_and_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = FreeTradePlanningProvider(source="VCI")

    monkeypatch.setattr(provider, "_get_stock_client", lambda symbol: object())
    monkeypatch.setattr(provider, "_get_company_client", lambda stock_client: object())
    monkeypatch.setattr(provider, "_get_finance_client", lambda stock_client: object())

    def fake_optional_dataframe_call(client: object, method_name: str, **kwargs: Any) -> Any:
        import pandas as pd

        if method_name == "news":
            return pd.DataFrame([{"title": "Catalyst"}])
        if method_name == "income_statement":
            return pd.DataFrame([{"revenue": 1000}])
        return None

    monkeypatch.setattr(provider, "_optional_dataframe_call", fake_optional_dataframe_call)

    financial_payload = provider.get_financial_summary("fpt")
    news_payload = provider.get_news_summary("fpt")

    assert financial_payload is not None
    assert financial_payload["status"] == "available"
    assert financial_payload["symbol"] == "FPT"
    assert "sections" in financial_payload

    assert news_payload is not None
    assert news_payload["status"] == "available"
    assert news_payload["symbol"] == "FPT"
    assert news_payload["article_count"] == 1
