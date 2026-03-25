from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.chief_analysis_writer_service import build_chief_analysis
from services.daily_briefing_service import build_daily_briefing
from services.market_synthesis_service import build_market_synthesis
from services.report_export_service import _build_daily_briefing_content, _build_market_analysis_report_content


def test_market_synthesis_builds_focus_and_action_layers() -> None:
    ranking_df = pd.DataFrame(
        [
            {"symbol": "FPT", "score": 0.92},
            {"symbol": "VCB", "score": 0.88},
        ]
    )

    synthesis = build_market_synthesis(
        run_id="20260324_100000",
        selection_mode="top_from_universe",
        market_overview={
            "regime": {"regime": "risk_on", "explanation": "Do rong mo rong va dong tien on dinh."},
            "breadth": {"positive_ratio": 0.64, "advance_decline_ratio": 1.8},
            "index_context": {"avg_return_3m": 0.12, "proxy_index": "equal_weight_proxy"},
            "liquidity_concentration": {
                "top_n_liquidity_share": 0.48,
                "top_symbols": [{"symbol": "FPT"}, {"symbol": "VCB"}],
            },
            "sector_rotation": [{"sector": "BANKING", "rotation_label": "leading", "avg_return_3m": 0.11}],
        },
        ranking_table=ranking_df,
        top_opportunities=[
            {
                "symbol": "FPT",
                "thesis": "Dang giu nen gia va co xung luc tot.",
                "setup_type": "pullback_buy",
                "trigger": "120 - 123",
                "risk_reward": "1.8",
                "degraded_mode": False,
            }
        ],
        symbol_payloads={"FPT": {"thesis": "Thesis from analysis"}},
        trade_plan_payloads={"FPT": {"invalidation": "Mat 118 voi vol lon.", "risk_reward": 1.8}},
        execution_status={"quality": "healthy", "failed_symbols": 0},
        warnings=[],
    )

    assert synthesis["stance"] == "selective offense"
    assert synthesis["confidence"] == "medium_high"
    assert synthesis["top_stock_focus"][0]["symbol"] == "FPT"
    assert synthesis["action_plan"]
    assert synthesis["conclusion"]


def test_daily_briefing_contains_chief_analysis_and_exportable_sections() -> None:
    briefing = build_daily_briefing(
        run_id="20260324_100000",
        selection_mode="top_from_universe",
        market_overview={
            "regime": {"regime": "risk_on", "explanation": "Dong tien dang mo rong."},
            "breadth": {"market_breadth": "broad", "positive_ratio": 0.62},
            "index_context": {"volatility": "moderate"},
        },
        ranking_table=pd.DataFrame([{"symbol": "FPT", "score": 0.91}]),
        symbol_payloads={"FPT": {"thesis": "Co luc day gia ngan han."}},
        trade_plan_payloads={
            "FPT": {
                "setup_type": "pullback_buy",
                "thesis": "Co the uu tien canh mua khi test ho tro.",
                "entry_zone": {"low": 120, "high": 123, "strategy": "buy_on_pullback"},
                "invalidation": "Mat 118.",
                "risk_reward": 1.7,
            }
        },
        symbol_results=[{"symbol": "FPT", "status": "success", "degraded_mode": False, "fallback_used": False}],
        warnings=["breadth context fallback"],
    )

    assert "market_synthesis" in briefing
    assert "chief_analysis" in briefing
    assert "terminal_orchestration" in briefing
    assert "skill_pipeline" in briefing
    content = _build_daily_briefing_content(briefing)
    market_report = _build_market_analysis_report_content(briefing)

    assert content["title"]
    assert any(section.get("title") == "Tom Tat Dieu Hanh" for section in content["sections"])
    assert any(section.get("title") == "Terminal Stages" for section in market_report["sections"])
    assert any(section.get("title") == "Skill Stage Outputs" for section in market_report["sections"])
    exec_section = next(section for section in content["sections"] if section.get("title") == "Tom Tat Dieu Hanh")
    assert isinstance(exec_section.get("paragraphs"), list)
    assert len(exec_section["paragraphs"]) >= 3


def test_chief_analysis_can_merge_ai_overlay() -> None:
    chief = build_chief_analysis(
        synthesis={
            "stance": "defensive",
            "confidence": "medium",
            "conclusion": "Dung uu tien quan tri rui ro.",
            "macro_and_sentiment": ["Ap luc ngan han van con."],
            "market_state": ["Thi truong van phan hoa."],
            "flow_of_funds": ["Dong tien chua mo rong."],
            "sector_strength": ["Nganh bank dang trung tinh."],
            "top_stock_focus": [{"symbol": "FPT", "thesis": "Theo doi phan ung o ho tro.", "trigger": "120-123", "risk_reward": "1.6"}],
            "action_plan": ["Khong mua duoi gia."],
            "risk_watch": ["Neu thung ho tro thi dung mo moi."],
        },
        generated_at="20260324_100000",
        ai_analysis={
            "headline": "Thi truong can than trong ngan han",
            "market_story": "Dong tien co dau hieu chon loc.",
            "portfolio_focus": "Giu ty trong vua phai va uu tien quan tri rui ro.",
            "action_plan": ["Chi giai ngan khi co xac nhan."],
            "risk_alerts": ["Bien dong co the tang trong phien chieu."],
        },
    )

    assert chief["title"] == "Thi truong can than trong ngan han"
    assert chief["summary"] == "Dong tien co dau hieu chon loc."
    assert any(section.get("title") == "Ke Hoach Hanh Dong" for section in chief["sections"])
    market_section = next(section for section in chief["sections"] if section.get("title") == "Trang Thai Thi Truong")
    assert isinstance(market_section.get("paragraphs"), list)
    assert market_section["paragraphs"]
