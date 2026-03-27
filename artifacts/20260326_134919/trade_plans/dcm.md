# Trade Plan: DCM

## Thesis
- `thesis`: Xu hướng hiện tại nghiêng về xu hướng tăng. Động lượng đang ở trạng thái tích cực.

## Setup Type
- `setup_type`: pullback_buy

## Entry Zone
- `low`: 44.37
- `high`: 45.26
- `strategy`: buy_on_pullback
- `rationale`: Ưu tiên mua khi giá lùi về vùng hỗ trợ thay vì đuổi giá.

## Confirmation
- Giá phản ứng tích cực tại vùng entry và không thủng hỗ trợ trong phiên.
- Ưu tiên khi giá vượt hoặc giữ được trên vùng cản gần 51.92.
- Thanh khoản duy trì tích cực, không suy yếu rõ rệt so với các phiên gần nhất.

## Invalidation
- `invalidation`: Thesis bị vô hiệu nếu giá thủng rõ ràng vùng hỗ trợ 44.37 với áp lực bán tăng.

## Target
- `target_1`: 51.92
- `target_2`: 50.14
- `rationale`: Ưu tiên chốt một phần ở cản gần, phần còn lại theo risk-reward mở rộng.

## Stop Loss
- `stop_loss`: 42.82

## Risk Reward
- `risk_reward`: 2.73

## Position Sizing Hint
- `position_sizing_hint`: Có thể vào 2 nhịp: 50% vị thế thăm dò, 50% còn lại khi có xác nhận.

## Monitoring Checklist
- Theo dõi phản ứng giá quanh vùng entry.
- Theo dõi thanh khoản so với trung bình 20 phiên.
- Kiểm tra thị trường chung có duy trì regime thuận lợi hay không.
- Cân nhắc chốt một phần khi tiệm cận target 1 = 51.92.

## Notes
- Không có ghi chú bổ sung.
