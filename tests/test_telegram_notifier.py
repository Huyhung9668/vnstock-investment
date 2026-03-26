from __future__ import annotations

from notifiers.telegram import build_daily_summary_message, build_daily_summary_messages


def test_build_daily_summary_messages_splits_into_four_sections() -> None:
    messages = build_daily_summary_messages(
        {
            "run_id": "20260326_073300",
            "execution_quality": "healthy",
            "vnindex_context": {
                "headline": "VNINDEX đang ở nhịp phòng thủ; bên bán vẫn chiếm ưu thế và dòng tiền chưa mở rộng đủ mạnh.",
                "metrics": {
                    "advancers": 3,
                    "decliners": 17,
                    "total_symbols": 20,
                    "positive_ratio": 0.15,
                    "advance_decline_ratio": 0.1765,
                    "avg_return_3m": -0.0902,
                    "top_n_liquidity_share": 0.9892,
                },
                "bullets": [
                    "Độ rộng hiện tại: 3 mã tăng / 17 mã giảm / 0 mã đi ngang trên tổng 20 mã theo dõi.",
                    "Tỷ lệ mã tăng chỉ đạt 15.00%; tỷ lệ tăng/giảm ở mức 0.18.",
                ],
                "sector_bullets": ["Nhóm yếu hơn mặt bằng: Chưa phân loại (-9.02%)."],
                "action_bias": "Ưu tiên LONG có chọn lọc, giải ngân chậm và chỉ tập trung vào vài mã khỏe nhất.",
                "risk_note": "Độ rộng quá hẹp là rủi ro lớn nhất.",
            },
            "news_impact": {
                "headline": "Hiện chưa có cụm tin tức đủ mạnh để đảo chiều tâm lý toàn thị trường.",
                "positive_items": ["ACB: duy trì trạng thái tích cực ở nhóm ngân hàng."],
                "negative_items": ["Áp lực bán vẫn chiếm ưu thế ở phần lớn mã midcap."],
                "shock_items": ["primary provider error: 502 - Bad Gateway"],
                "conclusion": "Chỉ ưu tiên LONG khi giá không gãy cấu trúc và dòng tiền còn bám ở nhóm khỏe.",
            },
            "long_candidates": {
                "headline": "Top LONG hiện tại tập trung vào ACB, ADG.",
                "selection_rule": "Ưu tiên mã tăng trong phiên, tăng trên chu kỳ theo dõi, có setup LONG rõ và RR đủ hấp dẫn.",
                "selected": [
                    {
                        "symbol": "ACB",
                        "day_change_pct": 3.03,
                        "period_change_pct": 2.5,
                        "volume_ratio": 1.24,
                        "risk_reward": 4.0,
                        "trigger": "22.37 - 22.82 (mua khi điều chỉnh)",
                        "selection_reasons": [
                            "phiên gần nhất tăng +3.03%",
                            "xung lực 3 tháng đạt +2.50%",
                            "khối lượng gần nhất tương đương 1.24 lần trung bình",
                        ],
                        "selection_note": "ACB được giữ trong danh sách LONG vì phiên gần nhất tăng tốt và vẫn duy trì xung lực dương.",
                    }
                ],
            },
            "entry_execution": {
                "portfolio_posture": "Giải ngân chậm, ưu tiên xác nhận rồi mới gia tăng.",
                "global_rules": [
                    "Không mua đuổi khi cổ phiếu đã tăng nóng rời xa vùng nền.",
                    "Mỗi lệnh đều phải có điểm vô hiệu rõ ràng trước khi vào vị thế.",
                ],
                "entries": [
                    {
                        "symbol": "ACB",
                        "entry_zone": "22.37 - 22.82 (mua khi điều chỉnh)",
                        "allocation_plan": [
                            "30% vị thế thăm dò khi giá về đúng vùng mua hoặc giữ được nền hỗ trợ.",
                            "30% tiếp theo khi giá xác nhận hồi phục hoặc bật lên với thanh khoản ổn định.",
                        ],
                        "stop_note": "Dừng lại nếu thủng 22.37 với áp lực bán tăng.",
                        "take_profit_note": "Chốt lời từng phần khi tỷ lệ lợi nhuận/rủi ro tiến gần mức 4.0.",
                    }
                ],
            },
        }
    )

    assert len(messages) == 4
    assert "[1/4]" in messages[0]
    assert "VNINDEX" in messages[0]
    assert "3/20 mã tăng" in messages[0] or "3 mã tăng / 17 mã giảm" in messages[0]
    assert "[2/4]" in messages[1]
    assert "Tin tức" in messages[1]
    assert "502" in messages[1]
    assert "[3/4]" in messages[2]
    assert "ACB" in messages[2]
    assert "RR tham chiếu" in messages[2]
    assert "[4/4]" in messages[3]
    assert "vùng mua" in messages[3]


def test_build_daily_summary_message_keeps_compatibility() -> None:
    message = build_daily_summary_message({"run_id": "20260326_073300"})
    assert "[1/4]" in message
    assert "[4/4]" in message
