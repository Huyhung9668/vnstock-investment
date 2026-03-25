# Trade Plan: ADG

## Thesis
- `thesis`: Xu hướng hiện tại chưa thật sự rõ ràng.

## Setup Type
- `setup_type`: breakout_or_wait

## Entry Zone
- `low`: Chưa có dữ liệu
- `high`: Chưa có dữ liệu
- `strategy`: wait
- `rationale`: Thiếu current_price nên chưa thể xác định entry zone đáng tin cậy.

## Confirmation
- Giá đóng cửa giữ trên vùng entry sau khi giải ngân thăm dò.

## Invalidation
- `invalidation`: Thesis bị vô hiệu nếu cấu trúc giá xấu đi và động lượng chuyển sang tiêu cực.

## Target
- `target_1`: Chưa có dữ liệu
- `target_2`: Chưa có dữ liệu
- `rationale`: Thiếu dữ liệu để xác định target.

## Stop Loss
- `stop_loss`: Chưa có dữ liệu

## Risk Reward
- `risk_reward`: Chưa có dữ liệu

## Position Sizing Hint
- `position_sizing_hint`: Ưu tiên vị thế nhỏ đến trung bình, giải ngân từng phần thay vì vào đủ ngay.

## Monitoring Checklist
- Theo dõi phản ứng giá quanh vùng entry.
- Theo dõi thanh khoản so với trung bình 20 phiên.
- Kiểm tra thị trường chung có duy trì regime thuận lợi hay không.

## Notes
- Thiếu current_price đáng tin cậy.
- Thiếu support rõ ràng, entry/stop dùng fallback.
- Thiếu resistance rõ ràng, target dùng heuristic.
- Thiếu ATR, stop loss dùng rule theo %.
