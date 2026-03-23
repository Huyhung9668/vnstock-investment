# Agent Modes

## Agent duy nhất

Dự án này chỉ sử dụng một agent trung tâm tên **Investment Copilot**.

Agent này không tách thành nhiều agent nhỏ. Thay vào đó, agent hoạt động theo nhiều mode để giữ ngữ cảnh thống nhất, dễ debug và dễ kiểm soát đầu ra.

## Mode A - Market Scan

### Mục tiêu
Đọc bức tranh thị trường tổng quan.

### Nhiệm vụ
- Tóm tắt tình trạng thị trường chung
- Xác định nhóm ngành hoặc tín hiệu đáng chú ý
- Chỉ ra các yếu tố cần theo dõi tiếp

### Đầu ra
- báo cáo markdown ngắn
- summary thị trường
- danh sách điểm cần chú ý

## Mode B - Stock Deep Dive

### Mục tiêu
Đi sâu vào một mã cổ phiếu cụ thể.

### Nhiệm vụ
- Phân tích hồ sơ doanh nghiệp
- Phân tích dữ liệu giá
- Kết hợp dữ liệu cơ bản và dữ liệu thị trường
- Xác định điểm mạnh, điểm yếu, rủi ro và tín hiệu cần theo dõi

### Đầu ra
- báo cáo markdown theo mã
- dữ liệu giá
- chart cơ bản
- tóm tắt insight

## Mode C - Trade Planning

### Mục tiêu
Biến insight thành các kịch bản theo dõi trung tính.

### Nhiệm vụ
- Xây dựng kịch bản tích cực, trung tính, tiêu cực
- Nêu điều kiện xác nhận cho từng kịch bản
- Chỉ rõ rủi ro và tín hiệu cần quan sát
- Không đưa khuyến nghị đầu tư tuyệt đối

### Đầu ra
- kế hoạch theo dõi giao dịch
- danh sách điều kiện cần kiểm tra
- markdown summary

## Mode D - Reporting

### Mục tiêu
Đóng gói toàn bộ kết quả thành file báo cáo.

### Nhiệm vụ
- Chuẩn hóa nội dung đầu ra
- Xuất markdown là mặc định
- Có thể mở rộng sang html hoặc pdf sau
- Lưu toàn bộ kết quả vào đúng thư mục của dự án

### Đầu ra
- file markdown
- file html/pdf khi cần
- báo cáo tổng hợp hoặc báo cáo theo mã

## Quy tắc chọn mode

- Nếu yêu cầu là đọc thị trường chung, dùng Mode A
- Nếu yêu cầu là phân tích một mã cụ thể, dùng Mode B
- Nếu yêu cầu là xây dựng kịch bản theo dõi, dùng Mode C
- Nếu yêu cầu là xuất hoặc tổng hợp báo cáo, dùng Mode D

## Nguyên tắc chung

- Một agent, nhiều mode
- Không tự ý tách thành nhiều agent khi chưa cần
- Mọi mode đều phải bám `project_goal.md` và `working_rules.md`
- Mọi kết quả quan trọng đều phải lưu thành file