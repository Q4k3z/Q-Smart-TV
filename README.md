# Q SMART TV

> **Hệ thống biến máy tính Windows 11 kết nối TV cũ qua HDMI thành Smart TV hoàn chỉnh, điều khiển bằng điện thoại thông qua Wi-Fi mạng LAN.**

---

## 1. Giới thiệu tổng quan

**Q Smart TV** biến máy tính Windows 11 kết nối với TV qua cổng HDMI thành một chiếc Smart TV cao cấp:
- **Màn hình TV (HDMI):** Giao diện Launcher toàn màn hình hiện đại, tối giản, chữ to, sắc nét, tương phản cao, điều hướng mượt mà bằng bàn phím hoặc remote. Hỗ trợ hiển thị mã QR trực tiếp trên màn hình để kết nối điện thoại chỉ trong 1 giây.
- **Q Remote (Điện thoại):** Giao diện web responsive siêu nhẹ, không cần cài app từ Store. Tích hợp sẵn:
  - Bàn phím điều hướng D-pad & phím media.
  - Danh mục **Phim của tôi** duyệt trực tiếp trên điện thoại, bấm để phát ngay lên TV.
  - Danh mục **Truyền hình IPTV** duyệt và tìm kiếm kênh trực tiếp trên điện thoại, bấm để chuyển kênh trên TV.
  - Thanh trạng thái media hiển thị nội dung đang phát và nút dừng nhanh.
- **Backend:** FastAPI Server chạy ngầm, quản lý tiến trình độc lập giữa Server, Launcher, Trình duyệt Brave và Trình phát media mpv.

---

## 2. Báo cáo nghiên cứu & tích hợp các Repository mã nguồn mở

Theo yêu cầu đặc tả sản phẩm, dưới đây là bảng đánh giá và phân loại việc sử dụng 9 kho lưu trữ mã nguồn mở:

| STT | Repository | Trạng thái | Chi tiết áp dụng |
|---|---|---|---|
| 1 | [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail) | **Đã tích hợp** | Áp dụng triết lý "Lazy Senior Developer" vào [`AGENTS.md`](file:///d:/Non-Smart%20tv/AGENTS.md): tối giản mã nguồn, không over-engineering, bảo vệ nghiêm ngặt ranh giới bảo mật (trust boundaries). |
| 2 | [fastapi/fastapi](https://github.com/fastapi/fastapi) | **Đã tích hợp** | Framework backend chính: cung cấp REST API, WebSocket truyền trạng thái thời gian thực và StaticFiles. |
| 3 | [mpv-player/mpv](https://github.com/mpv-player/mpv) | **Đã tích hợp** | Trình phát video offline và IPTV thông qua Windows Named Pipe JSON IPC (`\\.\pipe\qsmarttv_mpv`), quản lý tiến trình độc lập. |
| 4 | [iptv-org/iptv](https://github.com/iptv-org/iptv) | **Đã tích hợp** | Chuẩn cấu trúc playlist M3U/M3U8 và nguồn kênh mẫu kiểm thử hợp lệ. |
| 5 | [iptv-org/epg](https://github.com/iptv-org/epg) | **Tham khảo** | Tham khảo cấu trúc lịch phát sóng điện tử (EPG). Không đưa vào bản MVP để tránh làm phình to mã nguồn ngoài phạm vi cốt lõi. |
| 6 | [globocom/m3u8](https://github.com/globocom/m3u8) | **Đã tích hợp** | Thư viện và giải thuật phân tích playlist HLS/M3U8, trích xuất thuộc tính kênh, logo và nhóm kênh. |
| 7 | [microsoft/playwright-python](https://github.com/microsoft/playwright-python) | **Tham khảo** | Tham khảo cho kịch bản kiểm thử trình duyệt diện rộng. Bộ test cốt lõi dùng FastAPI TestClient + Pytest để chạy nhanh và nhẹ. |
| 8 | [pytest-dev/pytest](https://github.com/pytest-dev/pytest) | **Đã tích hợp** | Khung kiểm thử tự động toàn diện: kiểm tra bảo mật, phân tích IPTV, API endpoints, vòng đời tiến trình. |
| 9 | [astral-sh/uv](https://github.com/astral-sh/uv) | **Tham khảo** | Tùy chọn tăng tốc tải gói. Hệ thống mặc định dùng `venv` + `pip` chuẩn của Python để đảm bảo tương thích mọi máy Windows 11 mà không cần cài thêm công cụ ngoài. |

---

## 3. Kiến trúc phân lớp & Quy tắc vòng đời

```
Q Remote trên điện thoại (HTTP LAN / WebSocket)
        |
FastAPI Server (Cổng 8765)
        +-- Authentication & Security (Bearer Token, Whitelist, Path validation)
        +-- AppController & ProcessManager (Quản lý tiến trình độc lập)
        +-- LauncherService (Brave TV Profile: data/brave-tv-profile)
        +-- BraveService (Brave External Profile: data/brave-external-profile)
        +-- MPVService (JSON IPC qua Windows Named Pipe)
        +-- IPTVService (Phân tích & lưu trữ playlist M3U)
        +-- InputService (Gửi phím Win32 mô phỏng D-pad, text)
        +-- SystemService (Quét phim offline an toàn)
```

### Quy tắc vòng đời quan trọng:
1. **Server và Launcher độc lập:** Khi người dùng chọn "Thoát TV", hệ thống chỉ đóng cửa sổ Launcher trên màn hình TV, **Server vẫn tiếp tục chạy ngầm**.
2. **Mở lại TV:** Trên màn hình điện thoại sẽ hiện thẻ **"Mở lại TV"**, chỉ cần bấm 1 chạm là giao diện TV mở lại ngay lập tức mà không cần khởi động lại máy tính.
3. **Bảo vệ Brave cá nhân:** Tuyệt đối không dùng `taskkill /IM brave.exe`. Quản lý tiến trình dựa trên PID riêng biệt và phân tách hoàn toàn 2 profile dữ liệu:
   - `data/brave-tv-profile`: Dành riêng cho giao diện Q Smart TV Launcher.
   - `data/brave-external-profile`: Dành riêng cho YouTube và các trang web bên ngoài.

---

## 4. Hướng dẫn cài đặt & Khởi chạy

### Bước 1: Chuẩn bị máy tính Windows 11
Cắm dây HDMI từ máy tính vào TV. Nhấn tổ hợp phím `Windows + P`, chọn **Duplicate** (nhân bản màn hình) hoặc **Extend** (mở rộng màn hình sang TV). Chọn đầu ra âm thanh là TV HDMI.

### Bước 2: Cài đặt tự động
Chạy tệp sau bằng cách nhấp đúp:
```cmd
scripts\setup.bat
```
Script sẽ tự động:
- Kiểm tra Python.
- Tạo virtual environment `.venv`.
- Cài đặt toàn bộ thư viện từ `requirements.txt`.
- Tự động phát hiện Brave Browser và mpv.

### Bước 3: Khởi động Q Smart TV
Nhấp đúp vào:
```cmd
scripts\start_smarttv.bat
```
- Server sẽ khởi động ngầm.
- Cửa sổ Q Smart TV Launcher sẽ mở toàn màn hình trên Brave Browser.
- Màn hình console và giao diện TV sẽ hiển thị mã QR cùng địa chỉ truy cập Q Remote trên điện thoại, ví dụ:
  `http://192.168.1.7:8765/remote?token=...`

### Bước 4: Điều khiển bằng điện thoại
Mở máy ảnh điện thoại (iPhone hoặc Android), quét mã QR trên màn hình TV hoặc truy cập vào địa chỉ trên. Điện thoại và máy tính cần kết nối chung mạng Wi-Fi gia đình.

### Các script tiện ích khác:
- `scripts\diagnose.bat`: Chẩn đoán trạng thái môi trường, IP LAN, cổng 8765, đường dẫn Brave và mpv mà không làm lộ token bảo mật.
- `scripts\stop_server.bat`: Dừng hoàn toàn server Q Smart TV khi không còn sử dụng.

---

## 5. Cấu hình Media & IPTV

### Phim offline:
- Mặc định hệ thống quét thư mục `data/media` và thư mục `Videos` của người dùng.
- Tệp mẫu `data/media/Mau_Phim_Thu_Nghiem.mp4` đã được tích hợp sẵn để thử nghiệm ngay.
- Bạn có thể chép thêm các tệp phim `.mp4`, `.mkv`, `.avi` vào thư mục `data/media`.

### Truyền hình IPTV:
- Vào mục **IPTV** trên màn hình TV hoặc chọn tab **📺 Truyền hình** trên Q Remote điện thoại.
- Kênh mẫu kiểm thử đã được cấu hình sẵn từ cộng đồng mã nguồn mở hợp pháp.

---

## 6. Kết quả kiểm thử tự động

Tất cả các bài kiểm tra được viết bằng `pytest` và chạy tự động với kết quả 18/18 bài kiểm thử đạt 100%:
```cmd
.\.venv\Scripts\pytest.exe -v
```
- `test_security.py`: Kiểm tra xác thực Bearer token, chống Path Traversal, chặn URL giao thức nguy hiểm (`file:`, `javascript:`, `data:`), danh sách trắng phím điều khiển.
- `test_api.py`: Kiểm tra Health check, xác thực trạng thái hệ thống, tạo mã QR SVG, lệnh điều hướng D-pad.
- `test_iptv.py`: Kiểm tra bộ phân tích M3U IPTV, quản lý danh sách kênh và kênh yêu thích.
- `test_launcher.py`: Kiểm tra tính toàn vẹn khi đóng/mở vòng đời Launcher.
- `test_process_manager.py`: Kiểm tra quản lý tiến trình độc lập và dừng tiến trình an toàn.
