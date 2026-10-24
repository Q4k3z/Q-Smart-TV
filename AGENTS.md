# Quy tắc Agent & Phong cách Phát triển — Q Smart TV

Dự án tuân thủ nguyên tắc thiết kế tối giản, hiệu quả và bền bỉ dựa trên triết lý "Lazy Senior Developer" (Ponytail) tương thích với Antigravity.

## 1. Nguyên tắc cốt lõi
- **Mã nguồn tốt nhất là mã nguồn không cần viết**: Giải quyết toàn bộ vấn đề với lượng mã nguồn mới ít nhất. Tránh over-engineering, không tạo wrapper/abstraction thừa thãi khi chưa có nhu cầu thực tế.
- **Tận dụng tối đa nền tảng**: Ưu tiên thư viện chuẩn của Python, API Windows gốc (`ctypes` cho Win32 SendInput), và các công cụ có sẵn.
- **Không cắt giảm ở ranh giới tin cậy (Trust Boundaries)**:
  - Xác thực nghiêm ngặt REST API & WebSocket qua Bearer token / auth token.
  - Không bao giờ chạy shell tùy ý hoặc `shell=True` với input từ người dùng.
  - Kiểm tra và ràng buộc đường dẫn media chặt chẽ (Path Traversal protection) chỉ trong thư mục được cấu hình.
  - IPC của mpv chỉ kết nối cục bộ qua Windows Named Pipe (`\\.\pipe\...`), không expose ra mạng.
- **Quản lý tiến trình độc lập và an toàn**:
  - Server FastAPI và Launcher là 2 thành phần độc lập.
  - Thoát TV chỉ đóng launcher, không kill server, không kill Brave cá nhân (`taskkill /IM brave.exe` bị cấm).
  - Tách profile Brave cho Launcher (`data/brave-tv-profile`) và duyệt web ngoài (`data/brave-external-profile`).

## 2. Kiểm thử và Tự kiểm tra
- Mỗi tính năng cốt lõi (xác thực, điều hướng, vòng đời tiến trình, phân tích M3U/IPTV, media) đều phải có unit test hoặc integration test với pytest.
- Không bao giờ tuyên bố kiểm thử thành công nếu chưa chạy thực tế.

## 3. Áp dụng Ponytail và Antigravity
- Nguồn đã kiểm tra: https://github.com/DietrichGebert/ponytail/blob/main/skills/ponytail/SKILL.md và docs/agent-portability.md (24/10/2026).
- Dùng một AGENTS.md ở gốc làm quy tắc chung; Antigravity IDE đọc tệp này theo hướng dẫn upstream. Không cần cài hooks hoặc chép thêm bộ quy tắc trùng lặp.
- Trước khi sửa, tìm mọi nơi gọi hàm bị ảnh hưởng; hoàn tất cả mã gọi, cấu hình và kiểm thử liên quan.
- Chỉ dùng dependency khi có nhu cầu thật; không coi việc có tên trong requirements.txt là đã tích hợp.
- Báo cáo phần đã chạy thực tế và phần chưa kiểm chứng trên TV, điện thoại, Brave hoặc mpv.
