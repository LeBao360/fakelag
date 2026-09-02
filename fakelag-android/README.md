# FakeLag Android

Ứng dụng FakeLag cho điện thoại Android với giao diện nút nổi (Floating Overlay), tùy chỉnh menu cài đặt (Settings Panel) và cơ chế làm lag độ trễ mạng UDP thực tế qua Android `VpnService` không cần Root.

---

## 📱 Các tính năng chính

1. **Floating Icon (Icon nổi trên màn hình):**
   - Di chuyển kéo thả (drag & drop) bất kỳ vị trí nào trên màn hình.
   - **Chạm 1 lần (Tap):** Bật/Tắt Lag tức thì (Icon chuyển sang màu đỏ khi lag, có âm thanh beep thông báo).
   - **Giữ lâu (Hold/Long Press):** Hiển thị bảng cài đặt (Settings Panel).
   
2. **Floating Settings Panel (Bảng cài đặt):**
   - **Ukuran ikon (Kích thước icon):** Điều chỉnh kích thước icon nổi (dp).
   - **Durasi lag (Thời gian lag):** Thời lượng trễ mỗi lần kích hoạt (từ 0.5s đến 30.0s).
   - **Interval (Chu kỳ):** Khoảng thời gian nghỉ giữa các lần lag.
   - **Opacity (Độ mờ):** Độ trong suốt của icon nổi (10% - 100%).
   - **Lock position icon:** Khóa cố định vị trí icon nổi không bị trôi khi chạm.
   - **Sound beep:** Bật/tắt âm thanh bip khi bắt đầu/kết thúc lag.
   - **Volume up and down:** Kích hoạt lag nhanh bằng nút âm lượng.
   - **Auto Lag:** Tự động lặp lại chu kỳ lag theo interval.
   - **Nút `-` và `+`:** Tăng/giảm nhanh thời gian lag.

3. **Cơ chế Lag mạng qua VpnService:**
   - Hoạt động trên Android 5.0 trở lên, **không cần root**.
   - Can thiệp và tạo độ trễ/drop các gói tin UDP (giao thức mạng thời gian thực của game như Free Fire, PUBG Mobile, MLBB,...).
   - Duy trì các kết nối TCP/ICMP bình thường.

---

## 🛠️ Hướng dẫn cài đặt & Build APK

### Cách 1: Mở bằng Android Studio (Khuyên dùng)
1. Mở **Android Studio**.
2. Chọn **Open** -> Chọn thư mục `fakelag-android`.
3. Chờ Gradle sync xong.
4. Kết nối điện thoại Android (bật USB Debugging) hoặc chạy máy ảo Emulator.
5. Bấm nút **Run** (icon tam giác màu xanh) hoặc vào menu **Build > Build Bundle(s) / APK(s) > Build APK(s)** để xuất file APK.

### Cách 2: Build bằng dòng lệnh (Command Line)
Nếu máy bạn đã cài JDK 17+:
```bash
cd fakelag-android
gradle assembleDebug
```
File APK xuất ra tại: `app/build/outputs/apk/debug/app-debug.apk`

---

## ⚠️ Lưu ý khi sử dụng trên Android
- Khi mở app lần đầu, cần cấp **Quyền hiển thị trên các ứng dụng khác** (Display over other apps).
- Khi nhấn **START**, hệ thống sẽ yêu cầu xác nhận kết nối **VPN**, hãy chọn **OK / Đồng ý**.
