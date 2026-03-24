from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from models.analysis_package import AnalysisPackage
from providers.base import TradePlanningProvider


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.analysis_service import build_analysis_result


VIETNAM_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


class FakeProvider(TradePlanningProvider):
    def provider_name(self) -> str:
        return "fake"

    def health_check(self) -> dict[str, object]:
        return {"status": "ok"}

    def get_company_profile(self, symbol: str) -> dict[str, object]:
        return {"symbol": symbol, "name": "Demo Corp"}

    def get_price_summary(self, symbol: str) -> dict[str, object]:
        return {"symbol": symbol, "close": 100.0}

    def get_financial_summary(self, symbol: str) -> dict[str, object] | None:
        return None

    def get_news_summary(self, symbol: str) -> dict[str, object] | None:
        return None

    def get_breadth_context(self) -> dict[str, object] | None:
        return None


def test_build_analysis_result_marks_degraded_and_warns_on_missing_optional_sections() -> None:
    result = build_analysis_result(
        provider=FakeProvider(),
        symbol="FPT",
        runtime_config={"mode": "free"},
    )

    assert isinstance(result.analysis_package, AnalysisPackage)
    assert result.degraded is True
    assert result.errors == []
    assert result.warnings == [
        "Missing optional sections: `financial_summary`, `news_summary`, `breadth_context`"
    ]
    assert result.runtime_context == {"mode": "free"}


def test_build_analysis_result_preserves_timezone_safe_generated_at() -> None:
    result = build_analysis_result(
        provider=FakeProvider(),
        symbol="FPT",
        runtime_config=None,
    )

    assert isinstance(result.analysis_package.generated_at, datetime)
    assert result.analysis_package.generated_at.tzinfo == VIETNAM_TZ
