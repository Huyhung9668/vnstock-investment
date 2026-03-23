# providers/base.py

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo


DictStrAny = dict[str, Any]
VIETNAM_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


class ProviderError(Exception):
    """Base provider-layer error."""


class ProviderSchemaError(ProviderError):
    """Raised when provider data does not match the expected schema."""


class ProviderTimeoutError(ProviderError):
    """Raised when a provider request times out."""


class TradePlanningProvider(ABC):
    """Abstract provider contract for the trade planning pipeline."""

    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider identifier."""

    @abstractmethod
    def health_check(self) -> dict[str, Any]:
        """Return provider health and readiness details."""

    @abstractmethod
    def get_company_profile(self, symbol: str) -> dict[str, Any]:
        """Return normalized company profile data for a symbol."""

    @abstractmethod
    def get_price_summary(self, symbol: str) -> dict[str, Any]:
        """Return normalized price summary data for a symbol."""

    @abstractmethod
    def get_financial_summary(self, symbol: str) -> dict[str, Any] | None:
        """Return normalized financial summary data if available."""

    @abstractmethod
    def get_news_summary(self, symbol: str) -> dict[str, Any] | None:
        """Return normalized news summary data if available."""

    @abstractmethod
    def get_breadth_context(self) -> dict[str, Any] | None:
        """Return normalized market breadth context if available."""

    def build_metadata(self, *, symbol: str | None = None, scope: str | None = None) -> DictStrAny:
        """Build stable provider metadata for normalized payloads."""

        metadata: DictStrAny = {
            "source": self.provider_name(),
            "timestamp": datetime.now(VIETNAM_TZ).isoformat(),
        }

        if symbol is not None:
            metadata["symbol"] = symbol.strip().upper()
        if scope is not None:
            metadata["scope"] = scope

        return metadata

    def merge_with_metadata(
        self,
        *,
        payload: dict[str, Any],
        symbol: str | None = None,
        scope: str | None = None,
    ) -> DictStrAny:
        """Merge normalized data payload with stable metadata keys."""

        if not isinstance(payload, dict):
            raise ProviderSchemaError("payload must be a dictionary")

        metadata = self.build_metadata(symbol=symbol, scope=scope)
        return {
            **metadata,
            **dict(payload),
        }
