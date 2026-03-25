# Nhan Dinh Thi Truong & Ke Hoach Hanh Dong

## Headline
- `run_id`: 20260325_151746
- `headline`: Pipeline o che do degraded; dung ACB nhu mot y tuong can review, khong nen auto-trade.
- `selection_mode`: top_from_universe
- `update_line`: Cap nhat: 20260325_151746
- `stance`: defensive
- `confidence`: medium

## Executive Summary
Thi truong dang o che do risk_off, nhung pipeline con degraded; dung ACB nhu y tuong can review thay vi auto-trade.

## Tom Tat Dieu Hanh
Thi truong dang o che do risk_off, nhung pipeline con degraded; dung ACB nhu y tuong can review thay vi auto-trade.
Neu nhin tong the, bo canh thi truong dang phan anh trang thai risk_off, va dieu nay ung ho cach tiep can defensive hon la theo duoi cac nhip tang ngan han.
Muc do tin cay cua bo tong hop dang o muc medium; vi vay bao cao nay nen duoc dung nhu khung dinh huong de uu tien watchlist, diem vao va kich ban quan tri rui ro.
Portfolio focus hien tai nghieng ve defensive, voi muc do tin cay du lieu o muc medium.
Du lieu co the dung de dinh huong, nhung can tach ro phan chac chan va phan can xac minh them.

## Tin Hieu Vi Mo Va Sentiment
Lop vi mo va tam ly hien dang nghieng ve risk_off; vi the, dieu quan trong la doc su dong pha giua sentiment, do rong va hanh vi gia thay vi tach rieng tung manh thong tin.
Tong hop nhanh cho thay Trang thai vi mo va sentiment hien tai nghieng ve che do risk_off: Độ rộng thị trường yếu, bên giảm giá chiếm ưu thế và dòng tiền phòng thủ hơn; Do manh trung han cua universe dang phan anh qua avg_return_3m = -0.1191; dong thoi co dau hieu degraded trong pipeline, can tach ro phan du lieu chac chan va phan can review them. Nhung diem nay nen duoc xem la bo canh xac nhan cho cac quyet dinh ngan han.
- Trang thai vi mo va sentiment hien tai nghieng ve che do risk_off: Độ rộng thị trường yếu, bên giảm giá chiếm ưu thế và dòng tiền phòng thủ hơn.
- Do manh trung han cua universe dang phan anh qua avg_return_3m = -0.1191.
- Co dau hieu degraded trong pipeline, can tach ro phan du lieu chac chan va phan can review them.

## Trang Thai Thi Truong
Tu goc do van dong noi tai, thi truong dang cho thay Thi truong dang van dong trong che do risk_off; chat luong pipeline hien tai = degraded; Do rong tang gia uoc tinh positive_ratio = 0.1; dong thoi ty le advance/decline hien tai = 0.1111, bo canh chi so dang duoc noi suy tu universe_equal_weight_proxy. Do do, cach tiep can nen uu tien van la defensive, tranh mo rong danh muc chi vi hieu ung ngan han.
- Thi truong dang van dong trong che do risk_off; chat luong pipeline hien tai = degraded.
- Do rong tang gia uoc tinh positive_ratio = 0.1.
- Ty le advance/decline hien tai = 0.1111.
- Bo canh chi so dang duoc noi suy tu universe_equal_weight_proxy.

## Dong Tien Va Luan Chuyen Nganh
Xet theo dau vet dong tien Dong tien tap trung vao nhom dan dat voi top_n_liquidity_share = 1; Cac ma hut thanh khoan noi bat: ACB, AAA, ANV; dong thoi dong tien dang uu tien nhom co xung luc gia, ma noi bat la ads. Canh bao lon nhat o day la kha nang dong tien chi tap trung vao nhom hep, khien do ben xu huong khong thuc su ben vung.
O cap do nganh Nhom UNKNOWN dang o trang thai lagging voi avg_return_3m = -0.1191. Suc manh cua cac nhom dan dat se quyet dinh liẹu nhịp hưng phấn có lan tỏa hay chi dung lai o mot cum co phieu.
- Dong tien tap trung vao nhom dan dat voi top_n_liquidity_share = 1.
- Cac ma hut thanh khoan noi bat: ACB, AAA, ANV.
- Dong tien dang uu tien nhom co xung luc gia, ma noi bat la ADS.
- Nhom UNKNOWN dang o trang thai lagging voi avg_return_3m = -0.1191.

## Co Hoi Dang Chu Y
Trong nhom co phieu duoc uu tien, ACB dang noi len nhu diem nhan chinh do Xu hướng hiện tại chưa thật sự rõ ràng. Va vung kich hoat uu tien hien tai la wait.
Tuy nhien, van can tach rieng cac ma dang o che do degraded nhu ACB, ACC, ABS de tranh dien giai qua muc.
- ACB: Xu hướng hiện tại chưa thật sự rõ ràng. Trigger = wait. Risk/reward = n/a.
- ACC: Xu hướng hiện tại chưa thật sự rõ ràng. Trigger = wait. Risk/reward = n/a.
- ABS: Xu hướng hiện tại chưa thật sự rõ ràng. Trigger = wait. Risk/reward = n/a.
- AAA: Xu hướng hiện tại chưa thật sự rõ ràng. Trigger = wait. Risk/reward = n/a.
- ANV: Xu hướng hiện tại chưa thật sự rõ ràng. Trigger = wait. Risk/reward = n/a.

## Ke Hoach Hanh Dong
Portfolio focus hien tai nghieng ve defensive, voi muc do tin cay du lieu o muc medium.
Ke hoach hanh dong uu tien Can review ky cac phan degraded/fallback truoc khi bien bao cao thanh hanh dong giao dich; Lap watchlist hanh dong ngan han cho: ACB, ACC, ABS; dong thoi review thu cong luan diem va muc gia cho: acb, acc, abs, neu can do phu cao hon, can tang tier api hoac tach batch de tranh rate limit. Trong boi canh confidence = medium, ky luat vao lenh quan trong hon viec co mat trong moi nhip tang ngan han.
- Can review ky cac phan degraded/fallback truoc khi bien bao cao thanh hanh dong giao dich.
- Lap watchlist hanh dong ngan han cho: ACB, ACC, ABS.
- Review thu cong luan diem va muc gia cho: ACB, ACC, ABS.
- Neu can do phu cao hon, can tang tier API hoac tach batch de tranh rate limit.

## Rui Ro Va Dieu Kien Vo Hieu
Dieu can than trong nhat luc nay la Mot phan top ideas dang o che do degraded, can tranh overconfidence khi dien giai; Dieu kien vo hieu can theo doi sat: Thesis bị vô hiệu nếu cấu trúc giá xấu đi và động lượng chuyển sang tiêu cực; dong thoi symbol=acb warning: trade_plan degraded_mode enabled, symbol=acc warning: trade_plan degraded_mode enabled, symbol=abs warning: trade_plan degraded_mode enabled. Noi cach khac, can vao lenh voi kich ban vo hieu ro rang ngay tu dau thay vi sua sai sau.
Du lieu co the dung de dinh huong, nhung can tach ro phan chac chan va phan can xac minh them.
- Mot phan top ideas dang o che do degraded, can tranh overconfidence khi dien giai.
- Dieu kien vo hieu can theo doi sat: Thesis bị vô hiệu nếu cấu trúc giá xấu đi và động lượng chuyển sang tiêu cực.
- symbol=ACB warning: trade_plan degraded_mode enabled
- symbol=ACC warning: trade_plan degraded_mode enabled
- symbol=ABS warning: trade_plan degraded_mode enabled

## Ket Luan
Thi truong dang o che do risk_off, nhung pipeline con degraded; dung ACB nhu y tuong can review thay vi auto-trade. Chot lai, chien luoc nen nghieng ve defensive, trong boi canh confidence = medium; dieu can giu la ky luat, khong phai su hung phan voi nhung nhan dinh som.

## Market Context
- `summary`: Độ rộng thị trường yếu, bên giảm giá chiếm ưu thế và dòng tiền phòng thủ hơn.
- `regime`: risk_off
- `breadth`: unknown
- `volatility`: unknown

## Execution Status
- `quality`: degraded
- `total_symbols`: 6
- `success_symbols`: 6
- `failed_symbols`: 0
- `degraded_symbols`: 6
- `fallback_used`: False
- `summary`: Pipeline degraded: 6/6 symbol co ket qua, 6 symbol dang o che do fallback.

## AI Interpretation
- `ai_headline`: Chưa có dữ liệu
- `market_story`: Chưa có dữ liệu
- `portfolio_focus`: Chưa có dữ liệu
- `model`: Chưa có dữ liệu

## Top Opportunities
| symbol | setup_type | trigger | risk_reward | degraded_mode |
| --- | --- | --- | --- | --- |
| ACB | breakout_or_wait | wait | n/a | True |
| ACC | breakout_or_wait | wait | n/a | True |
| ABS | breakout_or_wait | wait | n/a | True |
| AAA | breakout_or_wait | wait | n/a | True |
| ANV | breakout_or_wait | wait | n/a | True |

## AI Notes By Symbol
- Chưa có dữ liệu bảng.

## Synthesis Focus Table
| symbol | setup_type | trigger | risk_reward | degraded_mode |
| --- | --- | --- | --- | --- |
| ACB | breakout_or_wait | wait | n/a | True |
| ACC | breakout_or_wait | wait | n/a | True |
| ABS | breakout_or_wait | wait | n/a | True |
| AAA | breakout_or_wait | wait | n/a | True |
| ANV | breakout_or_wait | wait | n/a | True |

## Skill Pipeline Stages
| skill_stage | status | summary |
| --- | --- | --- |
| macro_context | ready | Độ rộng thị trường yếu, bên giảm giá chiếm ưu thế và dòng tiền phòng thủ hơn. Do rong thi truong positive_ratio = 0.1. |
| futures_radar | proxy |  |
| flow_of_funds | ready | Dong tien hien dang tap trung vao nhom dan dat: ACB, AAA, ANV. Muc tap trung thanh khoan = 1. |
| stock_scanner | ready | Scanner chon ra nhom uu tien: ACB, ACC, ABS, AAA, ANV. |
| technical_profiler | ready | Technical profiler da lap ho so cho 6 symbol. |
| fundamental_profiler | ready | Fundamental profiler co du lieu tai chinh cho 6/6 symbol. |
| risk_engine | ready | Risk engine danh gia portfolio risk = elevated. |
| portfolio_auditor | ready | Portfolio auditor de xuat posture = defensive. Co 6 setup can giam size hoac quan sat them. |

## Runtime Normalization

## News Context
- `status`: Chưa có dữ liệu
- `selected_symbol_count`: Chưa có dữ liệu
- `symbols_with_news_context`: Chưa có dữ liệu
- `news_items_total`: Chưa có dữ liệu
- `market_sentiment_summary`: Chưa có dữ liệu

## News By Symbol
- Chưa có dữ liệu bảng.

## Next Actions
- Can xem lai cac canh bao degraded/fallback truoc khi dung bao cao de vao lenh that.
- Review thu cong du lieu cho: ACB, ACC, ABS.
- Tao watchlist hanh dong cho: ACB, ACC, ABS.
- Neu can full scan tren cloud, can API tier cao hon hoac self-hosted runner de tranh rate limit.

## Synthesis Action Plan
- Can review ky cac phan degraded/fallback truoc khi bien bao cao thanh hanh dong giao dich.
- Lap watchlist hanh dong ngan han cho: ACB, ACC, ABS.
- Review thu cong luan diem va muc gia cho: ACB, ACC, ABS.
- Neu can do phu cao hon, can tang tier API hoac tach batch de tranh rate limit.

## Synthesis Risk Watch
- Mot phan top ideas dang o che do degraded, can tranh overconfidence khi dien giai.
- Dieu kien vo hieu can theo doi sat: Thesis bị vô hiệu nếu cấu trúc giá xấu đi và động lượng chuyển sang tiêu cực.
- symbol=ACB warning: trade_plan degraded_mode enabled
- symbol=ACC warning: trade_plan degraded_mode enabled
- symbol=ABS warning: trade_plan degraded_mode enabled

## AI Action Plan
- AI chua de xuat hanh dong them.

## AI Risk Alerts
- AI chua co canh bao bo sung.

## Warnings
- symbol=ACB warning: trade_plan degraded_mode enabled
- symbol=ACC warning: trade_plan degraded_mode enabled
- symbol=ABS warning: trade_plan degraded_mode enabled
- symbol=AAA warning: trade_plan degraded_mode enabled
- symbol=ANV warning: trade_plan degraded_mode enabled
- symbol=AGG warning: trade_plan degraded_mode enabled
- unexpected build_deep_dive_for_symbols error: SystemExit: Rate limit exceeded. 
============================================================
⚠️  GIỚI HẠN API ĐÃ ĐẠT TỐI ĐA (Rate Limit Exceeded)
============================================================

📌 Bạn đã đạt giới hạn tối đa số lượt yêu cầu API trong 1 phút (minute).
   (You have reached the maximum API request limit for this period)

📊 Chi tiết (Details):
   • Gói hiện tại: Phiên bản cộng đồng (Community)
   • Giới hạn: 60 requests/phút
   • Đã sử dụng: 60/60
   • Chờ 3 giây để tiếp tục (Wait to retry)

💡 Giải pháp (Solutions):
   1️⃣ Chờ 3 giây rồi thử lại
      (Wait and retry)
   2️⃣ Tham gia gói thành viên tài trợ để sử dụng không bị gián đoạn
      (Join sponsor membership for uninterrupted access)

🚀 Nâng cấp (Upgrade):
   • Gói thành viên tài trợ (180-600 request/phút - Sponsor):
     Tham gia: https://vnstocks.com/insiders-program

============================================================

╔═════════════════════════════════════════════════════════════════╗
║                                                                 ║
║   🚫 ĐANG BỊ CHẶN BỞI GIỚI HẠN API? GIẢI PHÁP Ở ĐÂY!            ║
║                                                                 ║
║   ✓ Tăng ngay 10X tốc độ gọi API - Không còn lỗi RateLimit      ║
║   ✓ Tiết kiệm 85% thời gian chờ đợi giữa các request            ║
║                                                                 ║
║   ➤ NÂNG CẤP NGAY VỚI GÓI TÀI TRỢ VNSTOCK:                      ║
║     https://vnstocks.com/insiders-program                       ║
║                                                                 ║
╚═════════════════════════════════════════════════════════════════╝

 Process terminated.
