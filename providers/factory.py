from __future__ import annotations

from typing import Any

from providers.base import TradePlanningProvider


DictStrAny = dict[str, Any]


def create_provider(
    *,
    name: str,
    mode: str | None = None,
    config: DictStrAny | None = None,
) -> TradePlanningProvider:
    normalized_name = name.strip().lower()
    _ = mode
    _ = config

    if normalized_name == "free":
        from providers.free_provider import FreeTradePlanningProvider

        return FreeTradePlanningProvider()

    if normalized_name == "paid":
        from providers.paid_provider import PaidTradePlanningProvider

        return PaidTradePlanningProvider()

    raise ValueError(f"Unsupported provider name: {normalized_name}")


def build_provider(
    *,
    name: str,
    mode: str | None = None,
    config: DictStrAny | None = None,
) -> TradePlanningProvider:
    return create_provider(name=name, mode=mode, config=config)


def get_provider(
    *,
    name: str,
    mode: str | None = None,
    config: DictStrAny | None = None,
) -> TradePlanningProvider:
    return create_provider(name=name, mode=mode, config=config)
