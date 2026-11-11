# Fraud Shield v5 – Web app Streamlit (menu nhiều tầng + trợ lý nội bộ)

Team **Round Robin** · Festival Chuyển đổi số 2026 · Bảng B · case Digital Payment Fraud Shield.
Giao diện v4: menu 6 nhóm có mục con, trang dài chia thành thẻ. v5 thêm **ô trợ lý ở góc dưới phải**. Lõi mô hình giữ nguyên bản v3.2.

Bàn làm việc chống gian lận thanh toán số · Festival Chuyển đổi số 2026 · Bảng B · bản vòng Chung kết.
Mọi đặc trưng chỉ dùng thông tin có trước hoặc tại thời điểm giao dịch; Isolation Forest và bảng phân vị
tham chiếu chỉ học trên giai đoạn quá khứ (tháng 1–4).

**Mới ở v3.2 – lớp bất thường theo ngữ cảnh** (không dùng nhãn gian lận): so từng đặc trưng rủi ro của giao dịch với
giai đoạn quá khứ theo đúng chiều rủi ro, gồm 3 đặc trưng mới so với chính khách (vượt mức cao nhất từng chi, số giao
dịch trong 1 giờ, nhịp nhanh hơn thường lệ), cộng độ hiếm −log P(X ≥ x) (dạng HBOS có chiều). Giao dịch lệch mạnh mà
điểm rủi ro còn thấp được chuyển sang xác thực thêm (ngân sách ~3% giao dịch thật). Mục tiêu: bắt kiểu gian lận mô
hình có giám sát chưa từng học.

Kết quả trên Data Pack BTC (kiểm định 5-fold, ngưỡng lồng – số ngoài mẫu):

| Chỉ số | Kết quả |
|---|---|
| Recall can thiệp (chặn hoặc xác thực thêm) | 93,8% (120/128) · 3,74% khách thật phải xác thực thêm |
| Giá trị tiền gian lận bị chặn | 93,6% (98,8% nếu tính cả xác thực thêm) |
| Recall theo vụ tấn công | 85,7% (96/112 vụ) |
| Recall chặn ngay (HIGH/CRITICAL) | 82,8% (106/128) · 10 báo nhầm / 1.872 · F1 0,869 · PR-AUC 0,934 |
| Kiểm tra theo thời gian (học T1–4, thử T5–6) | F1 0,854 · can thiệp 86,4% |
| Kiểu gian lận chưa từng học (ẩn từng kiểu) | chặn 76/128 · can thiệp **117/128 (91,4%)** – v3.1: 96/128 (75%) |
| Chấm điểm thời gian thực | trùng 100% với chấm theo lô trên 8.000 giao dịch (cả lớp ngữ cảnh) · ~0,5 ms/giao dịch |

## Ứng dụng có gì – menu 6 nhóm

Bấm tên nhóm để mở/đóng danh sách mục con; bấm mục con để chỉ hiện đúng phần đó; trang dài chia thành thẻ.

| Nhóm | Mục con | Thẻ trong trang |
|---|---|---|
| **Tra cứu & phân tích** | Dashboard tổng quan · Tra cứu giao dịch | Dashboard (chỉ đếm trên 8.000 giao dịch): 1 Đã phân tích bao nhiêu → 2 Phát hiện bao nhiêu rủi ro → 3 Nguyên nhân → 4 Giao dịch có điểm Isolation Forest cao (20 giao dịch bất thường nhất ngoài nhóm tạm giữ) → 5 Hàng đợi hồ sơ. Tra cứu mặc định xếp CRITICAL → HIGH → MEDIUM → LOW |
| **Xử lý cảnh báo** | Nhật ký quyết định | – |
| **Kiểm định** (2.000 giao dịch có nhãn) | Chỉ số chính · Chấm thời gian thực | Chỉ số chính: Tổng hợp · Danh sách giao dịch có nhãn · Bắt đúng · Bỏ sót · Bắt sai · Thử đổi ngưỡng · Có hiệu chỉnh được không? |
| **Giám sát thời gian thực** | Giám sát thời gian thực | Cần xử lý ngay · Biểu đồ điểm · Giao dịch đang đến · Đối chiếu bộ mẫu |
| **Bắt gian lận mới** | Kiểu gian lận mới | Kết quả · Đánh đổi ngân sách · Cách hoạt động |
| **Dữ liệu & quản trị** | Tải & chạy dữ liệu · Tải kết quả · Học lại & quản trị | – |

Ứng dụng khách mô phỏng **FS Pay** là trang riêng: thêm `?view=khach` vào cuối link (có nút ở cuối menu và ở trang
Giám sát thời gian thực). Bộ 1.000 giao dịch mẫu (`data_demo/`, tạo bằng `tools/make_demo_set.py`) phát từ bảng điều
khiển của FS Pay lên trang giám sát.

## Trợ lý nội bộ (góc dưới phải)

Nút tròn xanh ở góc dưới phải mở ô trợ lý, có 3 chế độ:

- **Hỏi cách dùng** – trả lời từ bộ hỏi–đáp `tro_ly/hoi_dap.csv` (57 câu, mỗi câu kèm nhiều cách hỏi khác). Tìm câu gần
  nghĩa nhất bằng TF-IDF theo ký tự, gõ không dấu vẫn hiểu; câu trả lời có nút "Đi tới" trang liên quan. Không chắc
  thì gợi ý 3 câu gần nhất và nút gọi kỹ thuật.
- **Giải thích hồ sơ đang xem** – diễn giải lý do mô hình đã sinh cho hồ sơ/giao dịch vừa mở, kèm gợi ý xử lý theo loại rủi ro.
- **Gọi chuyên viên kỹ thuật** – tạo phiếu hỗ trợ (tự đính kèm trang và hồ sơ đang xem), ghi vào Nhật ký quyết định.

**Không gọi dịch vụ AI bên ngoài**: mọi thứ chạy trong app, không dữ liệu khách nào rời hệ thống. Mã khách, số tài khoản,
số điện thoại, email gõ vào ô hỏi được tự che. Sửa/thêm câu hỏi: mở `tro_ly/hoi_dap.csv` bằng Excel (giữ đúng 6 cột,
các cách hỏi khác ngăn bằng dấu `|`, cột `di_toi` là mã trang như `cases`, `live`, `ev_loto`), lưu lại dạng CSV UTF-8 –
app tự nạp lại. Bản gốc sinh bằng `python tro_ly/build_faq.py`.

## Cấu trúc

```
streamlit_app.py        giao diện (tệp chính khi deploy)
fraud_core.py           lõi mô hình: hồ sơ hành vi + Rule + Logistic Regression + Isolation Forest, 3 tầng hành động,
                        thí nghiệm ẩn từng kiểu, học lại có kiểm soát
fs_realtime.py          chấm điểm thời gian thực: bảng trạng thái trong bộ nhớ, Isolation Forest dạng mảng numpy,
                        kiểm tra trùng khớp lô – luồng
model/pretrained.json   mô hình học sẵn, dùng khi Data Pack tải lên không có nhãn
data/                   Data Pack BTC (9 tệp CSV) cho nút "Chạy với Data Pack BTC"
data_demo/              bộ 1.000 giao dịch mẫu cho app FS Pay (dữ liệu nhóm tự tạo để trình diễn)
tools/make_demo_set.py  sinh lại bộ giao dịch mẫu
.streamlit/config.toml  màu sắc, font, giới hạn tải lên 100 MB  ← BẮT BUỘC phải có trên GitHub
requirements.txt        thư viện cần cài
tests/                  unit test, scenario test, script đánh giá (python -m unittest discover -s tests -v)
```

## Đưa lên mạng (Streamlit Community Cloud, miễn phí)

**Bước 1 – Tạo repo GitHub**
Repo này: `datkhonglac/fraudshield-v5-troly` (tệp chính nằm ngay thư mục gốc).

**Bước 2 – Deploy**
1. Vào https://share.streamlit.io → **Continue with GitHub**, cho phép Streamlit truy cập repo (kể cả repo private).
2. **Create app** → **Yup, I have an app**.
3. Repository: `datkhonglac/fraudshield-v5-troly` · Branch: `main` · Main file path: `streamlit_app.py`.
4. App URL: đặt tên dễ nhớ, ví dụ `fraudshield-tendoi` → link sẽ là `https://fraudshield-tendoi.streamlit.app`.
5. **Advanced settings** → Python **3.12** → Save → **Deploy**. Lần đầu mất khoảng 2–5 phút.

**Bước 3 – Mở link cho mọi người**
Repo private thì app mặc định cũng private. Trong app bấm **Share** (góc phải trên) → **Make this app public**
(hoặc Settings → Sharing → *This app is public and searchable*). Mở link bằng tab ẩn danh để kiểm tra.

## Lưu ý

- App không có người dùng 12 giờ sẽ "ngủ"; người mở bấm **Yes, get this app back up!** và chờ khoảng 1 phút.
  Nên tự mở link trước khi gửi giáo viên / giám khảo.
- Sửa code trên GitHub → app tự cập nhật sau ít phút.
- Điền tên đội: sửa dòng `TEAM_NAME = ""` đầu tệp `streamlit_app.py`.
- Nhật ký quyết định chỉ lưu trong phiên đang mở – tải `audit_log.csv` ở tab **Tải kết quả** trước khi đóng.
- Nếu BTC không cho phép công khai Data Pack, xoá thư mục `data/`: app vẫn chạy, người dùng tự tải tệp .zip lên.

## Chạy trên máy

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Kiểm thử

```bash
python -m unittest discover -s tests -v     # 20 test, khoảng 15 giây
python tests/evaluate.py output             # ghi toàn bộ KPI, file nộp, kiểm tra luồng–lô ra thư mục output/
```
