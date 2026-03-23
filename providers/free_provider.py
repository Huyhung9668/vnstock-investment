from __future__ import annotations

import os
from datetime import date, timedelta
from typing import Any

import pandas as pd
from vnstock import Vnstock

from providers.base import ProviderSchemaError, ProviderTimeoutError, TradePlanningProvider


DictStrAny = dict[str, Any]


class FreeTradePlanningProvider(TradePlanningProvider):
    def __init__(
        self,
        *,
        source: str | None = None,
        lookback_days: int = 180,
    ) -> None:
        self.source = source or os.getenv("VNSTOCK_SOURCE", "VCI")
        self.lookback_days = lookback_days

    def provider_name(self) -> str:
        """Return the provider identifier."""
        return "free_provider"

    def health_check(self) -> dict[str, Any]:
        """Return provider health and readiness details."""
        return self.merge_with_metadata(
            payload={
            "status": "ok",
            "provider": self.provider_name(),
            "source": self.source,
            "lookback_days": self.lookback_days,
            },
            scope="provider",
        )

    def get_company_profile(self, symbol: str) -> dict[str, Any]:
        """Return normalized company profile data for a symbol."""
        stock_client = self._get_stock_client(symbol)
        company_client = self._get_company_client(stock_client)
        overview_df = self._required_dataframe_call(
            company_client,
            method_name="overview",
            section_name="company_profile",
            symbol=symbol,
        )

        row = overview_df.iloc[0].to_dict()
        profile = self._normalize_company_profile(row, symbol)
        profile["source"] = self.source
        return self.merge_with_metadata(payload=profile, symbol=symbol)

    def get_price_summary(self, symbol: str) -> dict[str, Any]:
        """Return normalized price summary data for a symbol."""
        stock_client = self._get_stock_client(symbol)
        quote_client = self._get_quote_client(stock_client)
        history_df = self._fetch_price_history(quote_client, symbol)

        if history_df is None or history_df.empty or len(history_df) < 2:
            raise ValueError(f"Insufficient price history returned for {symbol}")

        close_series = pd.to_numeric(history_df["close"], errors="coerce").dropna()
        if len(close_series) < 2:
            raise ValueError(f"Close series is not usable for {symbol}")

        first_close = float(close_series.iloc[0])
        last_close = float(close_series.iloc[-1])
        prev_close = float(close_series.iloc[-2])

        volume_series = self._numeric_series(history_df, "volume")
        high_series = self._numeric_series(history_df, "high")
        low_series = self._numeric_series(history_df, "low")

        summary: DictStrAny = {
            "symbol": symbol.upper(),
            "rows": int(len(history_df)),
            "start_date": self._extract_date(history_df, position="first"),
            "end_date": self._extract_date(history_df, position="last"),
            "first_close": round(first_close, 4),
            "last_close": round(last_close, 4),
            "prev_close": round(prev_close, 4),
            "day_change": round(last_close - prev_close, 4),
            "day_change_pct": round(self._pct_change(prev_close, last_close), 4),
            "period_change": round(last_close - first_close, 4),
            "period_change_pct": round(self._pct_change(first_close, last_close), 4),
        }

        if not volume_series.empty:
            summary["avg_volume"] = round(float(volume_series.mean()), 4)
            summary["latest_volume"] = round(float(volume_series.iloc[-1]), 4)
        if not high_series.empty:
            summary["high_max"] = round(float(high_series.max()), 4)
        if not low_series.empty:
            summary["low_min"] = round(float(low_series.min()), 4)

        summary["source"] = self.source
        return self.merge_with_metadata(payload=summary, symbol=symbol)

    def get_financial_summary(self, symbol: str) -> dict[str, Any] | None:
        """Return normalized financial summary data if available."""
        stock_client = self._get_stock_client(symbol)
        finance_client = self._get_finance_client(stock_client)
        if finance_client is None:
            return None

        candidates = [
            ("income_statement", {"period": "year"}),
            ("balance_sheet", {"period": "year"}),
            ("cash_flow", {"period": "year"}),
            ("ratios", {"period": "year"}),
        ]

        summary: DictStrAny = {}
        for method_name, kwargs in candidates:
            df = self._optional_dataframe_call(finance_client, method_name, **kwargs)
            if df is not None and not df.empty:
                summary[method_name] = self._normalize_record(df.iloc[0].to_dict())

        if not summary:
            return None

        return self.merge_with_metadata(
            payload={
                "status": "available",
                "source": self.source,
                "sections": summary,
            },
            symbol=symbol,
        )

    def get_news_summary(self, symbol: str) -> dict[str, Any] | None:
        """Return normalized news summary data if available."""
        stock_client = self._get_stock_client(symbol)
        company_client = self._get_company_client(stock_client)
        news_df = self._optional_dataframe_call(company_client, "news")

        if news_df is None or news_df.empty:
            return None

        latest_news = self._normalize_record(news_df.iloc[0].to_dict())
        return self.merge_with_metadata(
            payload={
                "status": "available",
                "source": self.source,
                "article_count": int(len(news_df)),
                "latest": latest_news,
            },
            symbol=symbol,
        )

    def get_breadth_context(self) -> dict[str, Any] | None:
        """Return normalized market breadth context if available."""
        return None

    def _get_stock_client(self, symbol: str) -> Any:
        return Vnstock().stock(symbol=symbol.upper(), source=self.source)

    def _get_company_client(self, stock_client: Any) -> Any:
        company_client = getattr(stock_client, "company", None)
        if company_client is None:
            raise AttributeError("stock.company is not available in this vnstock version")
        return company_client() if callable(company_client) else company_client

    def _get_quote_client(self, stock_client: Any) -> Any:
        quote_client = getattr(stock_client, "quote", None)
        if quote_client is None:
            raise AttributeError("stock.quote is not available in this vnstock version")
        return quote_client() if callable(quote_client) else quote_client

    def _get_finance_client(self, stock_client: Any) -> Any | None:
        finance_client = getattr(stock_client, "finance", None)
        if finance_client is None:
            return None
        return finance_client() if callable(finance_client) else finance_client

    def _fetch_price_history(self, quote_client: Any, symbol: str) -> pd.DataFrame:
        history_method = getattr(quote_client, "history", None)
        if history_method is None:
            raise AttributeError("quote.history is not available in this vnstock version")

        end_date = date.today()
        start_date = end_date - timedelta(days=self.lookback_days)
        try:
            result = history_method(start=start_date.isoformat(), end=end_date.isoformat())
        except TimeoutError as exc:
            raise ProviderTimeoutError(f"Timeout while fetching price_summary for {symbol}") from exc
        except Exception as exc:
            raise ValueError(f"Failed to fetch price_summary for {symbol}: {type(exc).__name__}: {exc}") from exc

        df = self._coerce_dataframe(result, section_name="price_summary")

        if df.empty:
            raise ValueError(f"Empty payload returned for price_summary: {symbol}")

        normalized_df = df.copy()
        if "time" in normalized_df.columns:
            normalized_df["time"] = pd.to_datetime(normalized_df["time"], errors="coerce")
            normalized_df = normalized_df.sort_values("time").reset_index(drop=True)

        return normalized_df

    def _required_dataframe_call(
        self,
        client: Any,
        *,
        method_name: str,
        section_name: str,
        symbol: str,
        **kwargs: Any,
    ) -> pd.DataFrame:
        method = getattr(client, method_name, None)
        if method is None:
            raise AttributeError(f"{section_name} method `{method_name}` is not available for {symbol}")

        try:
            result = method(**kwargs)
        except TypeError:
            try:
                result = method()
            except TimeoutError as exc:
                raise ProviderTimeoutError(f"Timeout while fetching {section_name} for {symbol}") from exc
            except Exception as exc:
                raise ValueError(f"Failed to fetch {section_name} for {symbol}: {type(exc).__name__}: {exc}") from exc
        except TimeoutError as exc:
            raise ProviderTimeoutError(f"Timeout while fetching {section_name} for {symbol}") from exc
        except Exception as exc:
            raise ValueError(f"Failed to fetch {section_name} for {symbol}: {type(exc).__name__}: {exc}") from exc

        df = self._coerce_dataframe(result, section_name=section_name)
        if df.empty:
            raise ValueError(f"Empty payload returned for {section_name}: {symbol}")
        return df

    def _optional_dataframe_call(self, client: Any, method_name: str, **kwargs: Any) -> pd.DataFrame | None:
        method = getattr(client, method_name, None)
        if method is None:
            return None

        try:
            result = method(**kwargs)
        except TypeError:
            try:
                result = method()
            except Exception:
                return None
        except Exception:
            return None

        try:
            df = self._coerce_dataframe(result, section_name=method_name)
        except ProviderSchemaError:
            return None

        if df.empty:
            return None
        return df

    def _coerce_dataframe(self, result: Any, *, section_name: str) -> pd.DataFrame:
        if result is None:
            raise ProviderSchemaError(f"{section_name} returned None")
        if isinstance(result, pd.DataFrame):
            return result
        try:
            df = pd.DataFrame(result)
        except Exception:
            raise ProviderSchemaError(f"{section_name} returned an invalid schema")
        return df

    def _normalize_record(self, payload: dict[str, Any]) -> DictStrAny:
        normalized: DictStrAny = {}
        for key, value in payload.items():
            if pd.isna(value):
                continue
            normalized[str(key)] = self._normalize_value(value)
        return normalized

    def _normalize_company_profile(self, payload: dict[str, Any], symbol: str) -> DictStrAny:
        normalized = self._normalize_record(payload)
        normalized["symbol"] = symbol.upper()

        company_name = self._first_non_empty_string(
            normalized.get("name"),
            normalized.get("company_name"),
            normalized.get("organ_name"),
            normalized.get("short_name"),
        )
        if company_name is not None:
            normalized.setdefault("name", company_name)
            normalized.setdefault("company_name", company_name)

        short_name = self._first_non_empty_string(
            normalized.get("short_name"),
            normalized.get("ticker"),
        )
        if short_name is not None:
            normalized.setdefault("short_name", short_name)

        return normalized

    def _normalize_value(self, value: Any) -> Any:
        if isinstance(value, pd.Timestamp):
            return value.isoformat()
        if hasattr(value, "item"):
            try:
                return value.item()
            except Exception:
                return value
        return value

    def _numeric_series(self, df: pd.DataFrame, column: str) -> pd.Series:
        if column not in df.columns:
            return pd.Series(dtype=float)
        return pd.to_numeric(df[column], errors="coerce").dropna()

    def _extract_date(self, df: pd.DataFrame, *, position: str) -> str:
        if "time" not in df.columns:
            return "N/A"

        series = pd.to_datetime(df["time"], errors="coerce").dropna()
        if series.empty:
            return "N/A"

        if position == "first":
            return str(series.iloc[0].date())
        return str(series.iloc[-1].date())

    def _pct_change(self, base: float, current: float) -> float:
        if base == 0:
            return 0.0
        return ((current - base) / base) * 100

    def _first_non_empty_string(self, *values: Any) -> str | None:
        for value in values:
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None
