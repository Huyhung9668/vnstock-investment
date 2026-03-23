# providers/base.py

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


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