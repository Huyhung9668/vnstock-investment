# Working Rules

## Mục đích

File này định nghĩa cách Codex làm việc trong dự án Investment Copilot để mọi thay đổi nhất quán, dễ kiểm tra và dễ mở rộng.

## Quy tắc chung

- Mỗi lần chỉ xử lý một mục tiêu rõ ràng.
- Mỗi script chỉ nên làm một nhiệm vụ chính.
- Không sửa nhiều file không liên quan trong một lần.
- Khi tạo file mới, phải nêu ngắn gọn lý do tạo file đó.
- Ưu tiên thay đổi nhỏ, dễ kiểm tra, dễ quay lui.

## Quy tắc cấu trúc thư mục

- Dữ liệu thô lưu trong `data/raw/`
- Dữ liệu đã xử lý lưu trong `data/processed/`
- Script lưu trong `scripts/`
- Báo cáo lưu trong `reports/`
- Tài liệu hướng dẫn và đặc tả lưu trong `docs/`

## Quy tắc làm việc với dữ liệu

- Kiểm tra dữ liệu sẵn có trước khi tải mới.
- Không bịa dữ liệu khi thiếu nguồn.
- Nếu thiếu dữ liệu, phải nói rõ dữ liệu nào đang thiếu.
- Ưu tiên dữ liệu có thể tái sử dụng cho các bước sau.
- Đầu ra dữ liệu phải có tên file rõ nghĩa.

## Quy tắc làm việc với code

- Ưu tiên Python cho xử lý dữ liệu và sinh báo cáo.
- Viết code rõ ràng, chia nhỏ chức năng theo file hợp lý.
- Không thêm phụ thuộc mới nếu chưa cần thiết.
- Khi sửa code, ưu tiên giữ tương thích với cấu trúc hiện tại.
- Mọi bước quan trọng nên có cách kiểm tra đầu ra.

## Quy tắc làm việc với báo cáo

- Báo cáo mặc định dùng Markdown.
- Có thể mở rộng sang HTML hoặc PDF sau.
- Báo cáo phải phân biệt rõ dữ liệu, suy luận và kịch bản theo dõi.
- Không viết như một khuyến nghị đầu tư chắc chắn.
- Mọi báo cáo phải lưu thành file, không chỉ trả lời trong chat.

## Quy tắc thực thi từng bước

1. Đọc yêu cầu hiện tại
2. Đối chiếu với `project_goal.md`
3. Xác định file cần tạo hoặc cần sửa
4. Thực hiện thay đổi nhỏ nhất có ích
5. Tự kiểm tra đầu ra
6. Tóm tắt ngắn gọn những gì đã làm

## Điều cần tránh

- Không tự ý đổi hướng dự án
- Không tạo nhiều file dư thừa
- Không sửa hàng loạt khi chưa được yêu cầu
- Không kết luận khi chưa có dữ liệu đủ tốt
- Không biến phân tích thành khuyến nghị mua bán tuyệt đối