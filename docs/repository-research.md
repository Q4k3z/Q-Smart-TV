# Nghiên cứu repository và phạm vi tích hợp

Đối chiếu tài liệu upstream ngày 24/10/2026. Không clone hay nhúng mã nguồn của các dự án bên dưới vào ứng dụng. Giấy phép nêu theo upstream, cần giữ thông báo tương ứng nếu sau này phân phối lại mã hoặc binary.

| Repository | Sử dụng thực tế trong Q Smart TV | Giấy phép và Windows/dependency |
|---|---|---|
| [Ponytail](https://github.com/DietrichGebert/ponytail) | Tham khảo quy tắc và diễn giải trong `AGENTS.md`: sửa nhỏ nhưng đầy đủ, kiểm tra nơi gọi, không bỏ xác thực và lỗi. Không cài plugin/hooks. | MIT. Là hướng dẫn cho agent, không phải thư viện runtime. [Tài liệu portability](https://github.com/DietrichGebert/ponytail/blob/main/docs/agent-portability.md) nêu Antigravity IDE dùng `AGENTS.md` gốc. Chưa chạy Antigravity trên máy này. |
| [FastAPI](https://github.com/fastapi/fastapi) | Tích hợp thật: REST, xác thực, WebSocket, phục vụ TV và Q Remote. Đã chạy trên Windows với Python 3.12. | MIT; dependency Python gồm Starlette, Pydantic; Uvicorn chạy ASGI. |
| [mpv](https://github.com/mpv-player/mpv) | Có adapter phát tiến trình và JSON IPC trong `core/mpv_service.py`. Chưa xác nhận phát thật vì máy chưa có mpv. Không gọi đây là tính năng đã nghiệm thu. | GPLv2+ mặc định, có cấu hình LGPLv2.1+ tùy build; xem [Copyright](https://github.com/mpv-player/mpv/blob/master/Copyright). Windows dùng binary riêng, không cần nhúng libmpv. Cần xem giấy phép của binary và dependency nếu đóng gói lại. |
| [iptv-org/iptv](https://github.com/iptv-org/iptv) | Tham khảo cấu trúc playlist mở rộng M3U và metadata kênh. Không coi đây là thư viện đã tích hợp. Bỏ playlist quốc gia được tự thêm sẵn, người dùng tự cung cấp nguồn. | Unlicense cho repository; không bảo đảm quyền sử dụng mọi stream. Không cần Node.js của repo để đọc M3U trong Q Smart TV. |
| [iptv-org/epg](https://github.com/iptv-org/epg) | Chỉ tham khảo. Chưa cần triển khai EPG trong giai đoạn nền tảng. | Unlicense; công cụ lấy lịch có môi trường Node.js và các nguồn dữ liệu riêng. Không thêm dependency này. |
| [globocom/m3u8](https://github.com/globocom/m3u8) | Đã nghiên cứu: thư viện phân tích HLS. Mã hiện tại dùng parser Extended M3U riêng cho danh mục kênh, không import m3u8. Đã bỏ dependency không dùng và sửa mô tả “đã tích hợp”. | MIT, thư viện Python dùng được trên Windows. Khi cần phân tích master/media HLS sẽ thêm có kiểm thử; không diễn giải các segment HLS thành kênh IPTV. |
| [playwright-python](https://github.com/microsoft/playwright-python) | Tích hợp thật cho kiểm thử web tùy chọn: giao diện, vòng đời, pad/bàn phím, URL và ô tìm kiếm YouTube thật. Dùng Brave đã cài, không tải browser binary. | Apache-2.0; hỗ trợ Windows; chỉ thuộc `requirements-dev.txt`, không phải dependency chạy server. |
| [pytest](https://github.com/pytest-dev/pytest) | Tích hợp thật: kiểm thử API, token, WebSocket, vòng đời và các service. Dữ liệu test cách ly khỏi cấu hình thật. | MIT; Python trên Windows, pytest-asyncio cho các hàm async. |
| [uv](https://github.com/astral-sh/uv) | Tùy chọn, chưa dùng. Giữ venv và pip để tránh chuyển công cụ không cần thiết. | MIT hoặc Apache-2.0; có Windows build; không bắt buộc cài. |

## Các kết luận kỹ thuật

- Ponytail không phải framework hay dependency của ứng dụng. Dùng một tệp hướng dẫn chung là đủ; không chép nguyên upstream để tạo luật trùng lặp.
- [Tài liệu mpv JSON IPC](https://mpv.io/manual/stable/#json-ipc) và [input-ipc-server](https://mpv.io/manual/stable/#options-input-ipc-server) quy định named pipe trên Windows. Adapter chỉ dùng pipe cục bộ; không biến giao thức này thành dịch vụ LAN.
- Extended M3U danh sách kênh và playlist HLS phục vụ các mục đích khác nhau. `m3u8` là parser HLS, không tự cung cấp thư viện kênh hoặc quyền xem.
- Không cần clone chín repository để làm ứng dụng. Cài dependency Python thật sự dùng; gọi mpv ngoài tiến trình; dẫn nguồn các tài liệu tham khảo.
- Hoàn thành nền tảng và vòng đời trước. Kiểm thử mpv, timeout IPC, stream lỗi và phát thật là công việc tiếp theo, không được đánh dấu đạt nhờ chỉ tạo được tiến trình.
