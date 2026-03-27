from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.deep_technical_lab_service import build_deep_technical_lab
from services.foreign_flow_decoder_service import build_foreign_flow_decoder
from services.global_domestic_macro_lens_service import build_global_domestic_macro_lens
from services.market_internals_liquidity_service import build_market_internals_liquidity
from services.news_pressure_gauge_service import build_news_pressure_gauge
from services.scenario_engine_service import build_scenario_engine
from services.sector_strength_map_service import build_sector_strength_map
from services.vnindex_vn30_derivatives_state_service import build_vnindex_vn30_derivatives_state


def _sample_market_overview() -> dict[str, object]:
    return {
        "generated_at": "2026-03-26T12:00:00",
        "regime": {"regime": "risk_off", "explanation": "Độ rộng yếu và dòng tiền tập trung hẹp."},
        "breadth": {"positive_ratio": 0.28, "advance_decline_ratio": 0.39, "advancers": 14, "decliners": 36},
        "index_context": {"avg_return_3m": -0.0582},
        "liquidity_concentration": {"top_n_liquidity_share": 0.6048, "top_symbols": [{"symbol": "SSI"}, {"symbol": "HPG"}, {"symbol": "VIX"}]},
    }


def test_new_market_layers_build_expected_payloads() -> None:
    market = _sample_market_overview()
    ranking = pd.DataFrame(
        [
            {"symbol": "SSI", "sector": "Chứng khoán", "return_3m": 0.12, "day_change_pct": 1.2, "volume_ratio_20d": 1.4, "score": 0.8, "news_signal": 0.1},
            {"symbol": "VCB", "sector": "Ngân hàng", "return_3m": 0.08, "day_change_pct": 0.6, "volume_ratio_20d": 1.1, "score": 0.7, "news_signal": 0.0},
            {"symbol": "NVL", "sector": "Bất động sản", "return_3m": -0.15, "day_change_pct": -0.8, "volume_ratio_20d": 0.9, "score": 0.3, "news_signal": 0.0},
        ]
    )
    news = {"headline_digest": ["DXY tăng gây áp lực tỷ giá", "Bad Gateway 502 ở một feed dữ liệu"]}
    plans = {
        "SSI": {"trend": "uptrend", "momentum": "strong", "setup_type": "pullback_buy", "risk_reward": 2.8, "entry_zone": {"low": 30, "high": 31, "strategy": "buy_on_pullback"}},
    }

    assert build_global_domestic_macro_lens(market_overview=market, market_news_summary=news, warnings=[])["status"] in {"ready", "degraded"}
    assert "basis_proxy" in build_vnindex_vn30_derivatives_state(market_overview=market, warnings=[])
    assert build_foreign_flow_decoder(market_overview=market, ranking_rows=ranking.to_dict(orient="records"), warnings=[])["structural_vs_tactical_flow"] in {"structural", "tactical"}
    assert build_sector_strength_map(ranking_table=ranking)["status"] == "ready"
    assert build_news_pressure_gauge(market_news_summary=news, warnings=[])["severity"] in {"low", "medium", "high"}
    assert build_deep_technical_lab(symbol_payloads={}, trade_plan_payloads=plans)["status"] == "ready"
    assert build_market_internals_liquidity(market_overview=market, ranking_rows=ranking.to_dict(orient="records"))["health"] in {"healthy", "narrow"}
    assert build_scenario_engine(market_overview=market, long_candidates={"selected": [{"symbol": "SSI"}]}, sector_strength={"leading": [{"sector": "Chứng khoán"}]})["base_case"] in {"positive", "base", "negative"}
