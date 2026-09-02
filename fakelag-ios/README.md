# NOVA FAKE LAG PRO - iOS Version ⚡

Dự án **FakeLag & DelayDame Pro** tối ưu hóa dành riêng cho hệ điều hành **iOS** (iPhone / iPad), phát triển bằng **Swift / SwiftUI**.

---

## 🌟 Tính năng nổi bật

1. **🔐 Hệ thống Key & Bảo mật đồng bộ (AES-CBC 256-bit)**:
   - Sử dụng chung cơ sở dữ liệu và hệ thống API Google Apps Script của `fakelag.py` và bản Android.
   - Thuật toán mã hóa AES-CBC 256-bit chuẩn `CommonCrypto`.
   - Trích xuất mã máy **HWID iOS** tự động, có nút sao chép và dán key nhanh.
   - Nút liên kết trực tiếp cộng đồng **Discord**: `https://discord.gg/anhemnova`.

2. **🖐️ Menu nổi Kéo thả & Thu phóng thông minh (`Drag & Drop + Pinch-to-Zoom`)**:
   - **Kéo thả di chuyển**: Chạm và giữ thanh tiêu đề để kéo menu đến bất kỳ vị trí nào trên màn hình.
   - **Thu phóng 2 ngón tay (Pinch-to-Zoom)**: Chụm/mở 2 ngón tay trực tiếp trên menu để phóng to / thu nhỏ tỉ lệ từ 60% đến 140%.
   - **Kéo góc thu phóng (Corner Drag Handle)**: Chạm icon góc `⤢` kéo theo đường chéo để đổi kích thước mượt mà theo thời gian thực.
   - **Phím tắt tỉ lệ nhanh**: `[80%]`, `[100%]`, `[120%]`.

3. **🎮 Nút nổi Gaming TELE & LAG DAME**:
   - Nút tròn nổi độc lập, di chuyển tự do khắp màn hình.
   - **Cơ chế Bật / Tắt 1 chạm (Toggle)**: Nhấn 1 lần để BẬT, nhấn lần nữa khi đang chạy sẽ TẮT NGAY LẬP TỨC.
   - Hiển thị thời gian đếm lùi trực quan trên nút.
   - Tùy chỉnh kích thước (`40dp - 90dp`) và độ mờ (`20% - 100%`).

4. **🔊 Âm thanh tần số Beep Hz (AVAudioEngine / CoreAudio)**:
   - Chạy trên luồng âm thanh game (`mixWithOthers`), không làm dừng nhạc hay âm thanh trong game.
   - ⚡ **Bật TELE**: Phát tiếng tần số cao `880 Hz`.
   - 🛑 **Tắt TELE**: Phát tiếng hạ âm `440 Hz`.
   - 🎮 **Bật LAG DAME**: Phát tiếng tần số cao `1050 Hz`.
   - 🛑 **Tắt LAG DAME**: Phát tiếng hạ âm `350 Hz`.

---

## 📁 Cấu trúc thư mục mã nguồn

```
fakelag-ios/
├── FakeLag/
│   ├── App/
│   │   └── FakeLagApp.swift             # Điểm khởi chạy ứng dụng & điều hướng Login/Main
│   ├── Services/
│   │   ├── KeyAuthManager.swift         # Mã hóa AES-256, HWID iOS, Client API
│   │   ├── SettingsManager.swift        # Lưu trữ cấu hình, tọa độ, scale, key
│   │   ├── SoundHzHelper.swift          # Phát âm thanh tần số Hz sóng sin
│   │   └── LagVpnManager.swift          # Bộ đếm thời gian, quản lý trạng thái Tele & Lag
│   ├── Views/
│   │   ├── LoginView.swift              # Giao diện Đăng nhập, HWID, Dán Key, Discord
│   │   ├── MainView.swift               # Màn hình chính Dashboard, Game Modes, VIP badge
│   │   ├── FloatingOverlayView.swift    # Bảng Menu nổi kéo thả & thu phóng
│   │   └── FloatingButtonsView.swift    # Các nút tròn nổi TELE / LAG DAME
│   ├── Assets.xcassets/                 # Bộ icon AppIcon trích xuất từ icon.ico
│   └── Info.plist                       # Cấu hình quyền và background modes
└── README.md
```

---

## 🚀 Hướng dẫn Cài đặt & Sử dụng trên iOS

### Cách 1: Mở và Build bằng Xcode (Dành cho máy Mac)
1. Mở thư mục `fakelag-ios` trong **Xcode**.
2. Chọn thiết bị iPhone của bạn hoặc Simulator.
3. Nhấn **Run (Cmd + R)** để cài đặt trực tiếp lên máy.

### Cách 2: Ký IPA & Cài đặt không cần Jailbreak (Sideloading)
1. Đóng gói thư mục thành file `FakeLag.ipa`.
2. Sử dụng các công cụ cài đặt file IPA phổ biến trên iOS:
   - **TrollStore** (iOS 14.0 - 16.6.1 / 17.0 - Khuyên dùng vì không bao giờ bị thu hồi chứng chỉ).
   - **Sideloadly** / **AltStore** (Cài đặt qua máy tính Windows / Mac).
   - **Scarlet** / **Esign** / **Gbox** (Ký chứng chỉ doanh nghiệp trực tiếp trên iPhone).
