from __future__ import annotations

from notifiers.telegram import build_daily_summary_message


def test_build_daily_summary_message_prefers_chief_analysis_narrative() -> None:
    message = build_daily_summary_message(
        {
            "run_id": "20260325_154918",
            "headline": "Headline cu",
            "warnings": ["warning 1"],
            "manifest_path": "artifacts/20260325154918/manifest.json",
            "chief_analysis": {
                "title": "Nhan Dinh Thi Truong & Ke Hoach Hanh Dong",
                "update_line": "Cap nhat: phien 25/03/2026",
                "summary": "Thi truong dang trong giai doan chon loc co phieu va can uu tien ky luat quan tri rui ro.",
                "sections": [
                    {
                        "title": "Trang Thai Thi Truong",
                        "paragraphs": [
                            "Do rong thi truong chua that su dong thuan, nhung mot so co phieu dau nganh van giu duoc nen gia.",
                        ],
                    },
                    {
                        "title": "Ke Hoach Hanh Dong",
                        "paragraphs": [
                            "Uu tien theo doi cac ma co xac nhan dong tien va chi giai ngan tung phan khi diem vao ro rang.",
                        ],
                    },
                ],
            },
        }
    )

    assert "Daily Run Report" not in message
    assert "*Stats*" not in message
    assert "*Warnings*" not in message
    assert "*Artifacts*" not in message
    assert "Nhan Dinh Thi Truong & Ke Hoach Hanh Dong" in message
    assert "1. Trang Thai Thi Truong" in message
    assert "2. Ke Hoach Hanh Dong" in message
