# Báo cáo kiểm chứng — 24/10/2026

## Phạm vi đợt sửa

Nền tảng FastAPI, ghép nối LAN, vòng đời launcher, một cửa sổ/trang web, Back/Home, bàn di chuột và bàn phím trực tiếp. Bổ sung tự nhận giao thức khi nhập địa chỉ trên TV/điện thoại. Không nghiệm thu media chỉ dựa trên giao diện.

## Kết quả thực chạy

| Kiểm tra | Kết quả | Giới hạn |
|---|---|---|
| `python -m pytest -q` | **78 passed**, 1 cảnh báo Starlette khuyến nghị thay httpx ở bản tương lai | Backend và service; test riêng không tác động dữ liệu cá nhân |
| `tests/controls_smoke.py` | **PASS** với Brave thật và SendInput Windows | Chuột/click/cuộn/giữ kéo, cử chỉ trên remote, IME/Unicode/sửa/xóa, focus/disconnect, điều hướng; trang mẫu bật Trusted Types |
| `tests/youtube_smoke.py` | **PASS** với YouTube thật | Thanh Back/Home, gõ/sửa/xóa tiếng Việt ở ô tìm kiếm; không gửi tìm kiếm hay phát video |
| `tests/web_smoke.py` | **PASS** với Brave đã cài | Playwright chạy giao diện bằng Brave headless, đồng thời gọi launcher Brave thật qua server |
| `tests/lifecycle_smoke.py` | **PASS** với Brave thật | Có tác động đóng/mở cửa sổ thuộc Q Smart TV; không phải test phần cứng |
| Kiểm tra cú pháp JavaScript/Python và `git diff --check` | **PASS** | Không thay cho chạy UI hoặc phần cứng |
| Xem ảnh TV 1920×1080, remote rộng 390px | Đã xem trực tiếp | Ảnh ở data/logs; kiểm tra focus thêm ở 1280px và 720px |
| Quét QR trên điện thoại thật | **Người dùng xác nhận mở trực tiếp** | PC Ethernet và điện thoại Wi-Fi cùng router, IP LAN 192.168.1.3 |
| `pip check` | **PASS** | Không có dependency bị thiếu hoặc xung đột theo metadata |
| `tests/exe_smoke.py` | **PASS** với `Q Smart TV.exe` thật | Khởi động khi server/launcher tắt, mở từ thư mục khác, mở lại và bấm đồng thời không tạo trùng; log che token; thoát TV vẫn giữ server |

Đợt kiểm thử dùng Windows, Python 3.12.14 và Brave được tìm thấy tại vị trí cài đặt tiêu chuẩn. Sandbox công cụ chặn socket loopback nội bộ của asyncio; các lần test hoàn tất chạy với quyền truy cập loopback bên ngoài sandbox, không đổi mã ứng dụng để né lỗi môi trường này.

## Những luồng đã đạt

- Server chạy nền; health trả đúng tên ứng dụng; lỗi khởi động có log riêng thay vì bị bỏ vào DEVNULL.
- Mở launcher sau khi server sẵn sàng; chỉ báo mở khi tìm được cửa sổ thật.
- Năm yêu cầu mở đồng thời vẫn chỉ có một launcher.
- Thoát TV có xác nhận. Hủy giữ launcher. Xác nhận đóng launcher; API còn online.
- Q Remote hiển thị nút mở lại; mở lại thành công sau nhiều lần đóng.
- Đóng launcher thủ công được cập nhật trạng thái sau khoảng một giây.
- Dừng server không đóng launcher; server khởi động lại nhận diện đúng profile và giữ nguyên PID launcher thay vì tạo trùng.
- Mở trình duyệt ngoài riêng; Thoát TV không đóng trình duyệt ngoài. Home đóng web TV rồi mở launcher; Brave cá nhân được giữ riêng.
- D-pad/OK từ remote tới TV qua WebSocket; Home trở về trang chính; Back đóng hộp thoại; focus theo vị trí thực của phần tử.
- Token thiếu/sai bị chặn; máy LAN không tự lấy được token qua info, QR hoặc redirect.
- Unicode dùng SendInput với cấu trúc Win32 và UTF-16. Đã gửi chữ tiếng Việt/emoji vào trang mẫu và tiếng Việt vào ô tìm kiếm YouTube trong cửa sổ riêng của Q Smart TV.
- Stop server xác minh tiến trình của bản cài, không kill bất kỳ ứng dụng nào chỉ vì đang giữ cổng 8765.
- QR bỏ qua WARP/VPN, lấy Ethernet/Wi-Fi đang hoạt động; tự cập nhật và cho chọn IP thủ công. Không thay đổi cấu hình mạng/firewall của máy.
- Mở website nhiều lần và link yêu cầu tab mới vẫn chỉ giữ một trang chính; Back đóng modal rồi theo lịch sử, hết lịch sử về launcher. Thanh Back/Home dùng DOM API để hoạt động với Trusted Types của YouTube.
- URL không có giao thức mở được từ API, form TV và form điện thoại. Tên miền mặc định HTTPS; IP nội bộ, localhost, .local dùng HTTP; giữ HTTP/HTTPS đã nhập, chặn giao thức khác và địa chỉ lỗi. Form giữ nội dung khi mở thất bại.
- Chuột Windows và pad điện thoại: di chuyển, click, hai ngón cuộn, chuột phải, giữ kéo; ngắt WebSocket tự thả chuột.
- Bàn phím: sửa giữa đoạn, xóa, dán, emoji, ghép dấu tiếng Việt, Backspace không điều hướng, Tab/Shift+Tab và chọn tất cả. Kết thúc phiên khi đổi ô/app/PID hoặc ngắt kết nối; nút bắt đầu nhập chờ WebSocket sẵn sàng.
- Bắt đầu nhập đưa trang Brave lên trước để ký tự Windows đến đúng ô, kể cả khi trước đó cửa sổ khác đang được chọn.

## Nhóm tệp thay đổi

- `config.py`, `server.py`, `core/`, `api/`: auth/ghép nối, trạng thái, điều hướng, quản lý tiến trình và cửa sổ, nhận diện lại launcher.
- `static/common.js`, `static/tv/`, `static/remote/`: request có timeout/chống trùng, báo lỗi, WebSocket TV, focus responsive, URL ghép nối không lưu trên thanh địa chỉ.
- `scripts/` và `mo_khoa_ket_noi.bat`: tìm Python, môi trường riêng, log khởi động, chống chạy trùng, dừng đúng tiến trình; firewall chỉ cấu hình thủ công Private/LocalSubnet.
- `tests/`, `requirements-dev.txt`: backend cách ly dữ liệu, kiểm thử web và vòng đời thực tế với Brave đã cài.
- `AGENTS.md`, `README.md`, `docs/repository-research.md`: quy tắc Ponytail phù hợp Antigravity, hướng dẫn chạy và phân biệt tích hợp thật với tham khảo.
- Bỏ token công khai cũ và playlist được thêm sẵn. Giữ video mẫu hiện có, chưa xác nhận phát được.

## Chưa đạt nghiệm thu / bước tiếp theo

1. Người dùng đã xác nhận QR trên điện thoại thật. Cử chỉ/bộ gõ đã kiểm thử bằng trình duyệt di động mô phỏng; còn cần trải nghiệm bàn phím Android/iOS và Wi-Fi lâu dài. Chưa thay đổi firewall máy này trong đợt sửa.
2. Chưa kiểm tra hình/âm thanh HDMI hoặc chọn đúng màn hình TV; người dùng chọn Extend/Duplicate và đầu ra HDMI trong Windows.
3. Chưa tìm thấy mpv. Tiếp theo cần cài/cấu hình mpv, sửa và kiểm tra timeout IPC, chờ playback thật, pause/seek/volume/stop, lỗi stream và tiến trình kết thúc. Adapter hiện tại còn hạn chế, không coi là hoàn tất Giai đoạn 5–6.
4. Live input hỗ trợ input/textarea có selection API; chưa hỗ trợ toàn bộ contenteditable, đọc ngược văn bản có sẵn của mọi ứng dụng Windows hoặc mọi luồng popup đăng nhập. Việc ép một trang có thể ảnh hưởng website bắt buộc popup. Chưa nghiệm thu phát video YouTube, EPG, upload playlist cục bộ và các giai đoạn khác của đặc tả.
5. Kiểm thử chạy lâu và reconnect qua Wi-Fi thực tế còn chờ. Không tự chạy cùng Windows hoặc mở dịch vụ ra Internet.

## Cách chạy lại

Nhấp đúp `Q Smart TV.exe` ngay trong thư mục dự án (hoặc dùng `start_smarttv.bat`). EXE dùng `.venv` hiện có, không hiện terminal và không cần quyền admin; có khóa khởi động riêng theo đường dẫn bản cài. Tạo lại bằng `scripts/build_exe.ps1`, mã nguồn `scripts/QuickStart.cs`. Đây là launcher cho bản cài, chưa phải bộ cài độc lập.

Trên launcher bấm **Kết nối Remote**, quét QR mới trên điện thoại cùng Wi-Fi. `stop_server.bat` là thao tác dừng server riêng. Nếu lỗi, chạy `diagnose.bat`, xem `data/logs/quickstart.log`, `startup.log` và `server.log`. Cấu hình đường dẫn/cổng/thư mục media theo `.env.example`.
