import SwiftUI

public struct LoginView: View {
    @ObservedObject var settings = SettingsManager.shared
    @State private var licenseKey: String = ""
    @State private var hwid: String = ""
    @State private var statusMessage: String = ""
    @State private var isError: Bool = false
    @State private var isLoading: Bool = false
    @State private var showCopiedAlert: Bool = false

    public var onLoginSuccess: () -> Void

    public init(onLoginSuccess: @escaping () -> Void) {
        self.onLoginSuccess = onLoginSuccess
    }

    public var body: some View {
        ZStack {
            Color(red: 0.05, green: 0.06, blue: 0.09).ignoresSafeArea()

            ScrollView {
                VStack(spacing: 20) {
                    // Top Logo Header
                    VStack(spacing: 10) {
                        ZStack {
                            Circle()
                                .fill(LinearGradient(
                                    colors: [Color(red: 0.7, green: 0.15, blue: 1.0), Color(red: 0.0, green: 0.8, blue: 1.0)],
                                    startPoint: .topLeading, endPoint: .bottomTrailing
                                ))
                                .frame(width: 80, height: 80)
                                .shadow(color: Color(red: 0.7, green: 0.15, blue: 1.0).opacity(0.6), radius: 12)

                            Image(systemName: "bolt.shield.fill")
                                .resizable()
                                .scaledToFit()
                                .frame(width: 42, height: 42)
                                .foregroundColor(.white)
                        }

                        Text("NOVA FAKE LAG PRO")
                            .font(.system(size: 22, weight: .bold, design: .rounded))
                            .foregroundColor(Color(red: 0.0, green: 0.82, blue: 1.0))
                            .tracking(2)

                        Text("HỆ THỐNG XÁC THỰC BẢN QUYỀN (IOS)")
                            .font(.system(size: 11, weight: .semibold))
                            .foregroundColor(Color(red: 0.55, green: 0.58, blue: 0.7))
                            .tracking(1)
                    }
                    .padding(.top, 20)

                    // HWID Card
                    HStack(spacing: 12) {
                        Image(systemName: "lock.shield.fill")
                            .foregroundColor(Color(red: 0.0, green: 0.82, blue: 1.0))
                            .font(.system(size: 20))

                        VStack(alignment: .leading, spacing: 3) {
                            Text("MÃ MÁY (HWID)")
                                .font(.system(size: 10, weight: .bold))
                                .foregroundColor(Color(red: 0.55, green: 0.58, blue: 0.7))

                            Text(hwid)
                                .font(.system(size: 13, weight: .bold, design: .monospaced))
                                .foregroundColor(Color(red: 0.7, green: 0.15, blue: 1.0))
                        }

                        Spacer()

                        Button(action: copyHwid) {
                            Image(systemName: "doc.on.doc.fill")
                                .font(.system(size: 14, weight: .bold))
                                .foregroundColor(Color(red: 0.0, green: 1.0, blue: 0.53))
                                .frame(width: 34, height: 34)
                                .background(Color(red: 0.14, green: 0.16, blue: 0.25))
                                .cornerRadius(8)
                        }
                    }
                    .padding(14)
                    .background(Color(red: 0.09, green: 0.1, blue: 0.16))
                    .cornerRadius(14)
                    .overlay(RoundedRectangle(cornerRadius: 14).stroke(Color(red: 0.18, green: 0.2, blue: 0.33), lineWidth: 1.5))

                    // Key Input Card
                    VStack(alignment: .leading, spacing: 12) {
                        HStack {
                            Image(systemName: "key.fill")
                                .foregroundColor(Color(red: 1.0, green: 0.84, blue: 0.0))
                                .font(.system(size: 16))

                            Text("NHẬP LICENSE KEY")
                                .font(.system(size: 12, weight: .bold))
                                .foregroundColor(.white)

                            Spacer()

                            Button(action: pasteKey) {
                                Text("Dán Key")
                                    .font(.system(size: 11, weight: .bold))
                                    .foregroundColor(Color(red: 0.0, green: 1.0, blue: 0.53))
                                    .padding(.horizontal, 8)
                                    .padding(.vertical, 4)
                                    .background(Color(red: 0.12, green: 0.14, blue: 0.22))
                                    .cornerRadius(6)
                            }
                        }

                        TextField("Nhập hoặc dán key vào đây...", text: $licenseKey)
                            .padding(12)
                            .background(Color(red: 0.07, green: 0.08, blue: 0.12))
                            .foregroundColor(.white)
                            .font(.system(size: 14, weight: .semibold))
                            .cornerRadius(10)
                            .overlay(RoundedRectangle(cornerRadius: 10).stroke(Color(red: 0.2, green: 0.23, blue: 0.35), lineWidth: 1))
                            .autocapitalization(.none)
                            .disableAutocorrection(true)

                        if !statusMessage.isEmpty {
                            Text(statusMessage)
                                .font(.system(size: 12, weight: .bold))
                                .foregroundColor(isError ? Color(red: 1.0, green: 0.16, blue: 0.33) : Color(red: 0.0, green: 1.0, blue: 0.53))
                                .frame(maxWidth: .infinity, alignment: .center)
                                .multilineTextAlignment(.center)
                        }

                        if isLoading {
                            ProgressView()
                                .progressViewStyle(CircularProgressViewStyle(tint: Color(red: 0.0, green: 0.82, blue: 1.0)))
                                .frame(maxWidth: .infinity)
                        }

                        Button(action: verifyKeyAction) {
                            HStack {
                                Image(systemName: "paperplane.fill")
                                Text("XÁC THỰC LICENSE KEY")
                                    .font(.system(size: 15, weight: .bold))
                            }
                            .foregroundColor(.white)
                            .frame(maxWidth: .infinity)
                            .frame(height: 50)
                            .background(LinearGradient(
                                colors: [Color(red: 0.0, green: 0.8, blue: 0.4), Color(red: 0.0, green: 0.6, blue: 0.3)],
                                startPoint: .top, endPoint: .bottom
                            ))
                            .cornerRadius(12)
                            .shadow(color: Color.green.opacity(0.3), radius: 8)
                        }
                        .disabled(isLoading)
                    }
                    .padding(16)
                    .background(Color(red: 0.09, green: 0.1, blue: 0.16))
                    .cornerRadius(16)
                    .overlay(RoundedRectangle(cornerRadius: 16).stroke(Color(red: 0.18, green: 0.2, blue: 0.33), lineWidth: 1.5))

                    // Discord Link Button
                    VStack(spacing: 8) {
                        Button(action: openDiscord) {
                            HStack(spacing: 10) {
                                Image(systemName: "bubble.left.and.bubble.right.fill")
                                    .font(.system(size: 16, weight: .bold))
                                    .foregroundColor(Color(red: 0.35, green: 0.4, blue: 0.95))

                                Text("DISCORD: discord.gg/anhemnova")
                                    .font(.system(size: 13, weight: .bold))
                                    .foregroundColor(.white)
                            }
                            .frame(maxWidth: .infinity)
                            .frame(height: 48)
                            .background(Color(red: 0.14, green: 0.15, blue: 0.24))
                            .cornerRadius(12)
                            .overlay(RoundedRectangle(cornerRadius: 12).stroke(Color(red: 0.35, green: 0.4, blue: 0.95), lineWidth: 1.5))
                        }

                        Text("Tham gia Discord để lấy key, mua key VIP & hỗ trợ 24/7")
                            .font(.system(size: 10, weight: .medium))
                            .foregroundColor(Color(red: 0.55, green: 0.58, blue: 0.7))

                        Text("Nova Fake Lag iOS • Phiên bản 1.6 • 2026")
                            .font(.system(size: 9))
                            .foregroundColor(Color(red: 0.4, green: 0.42, blue: 0.55))
                            .padding(.top, 10)
                    }
                }
                .padding(20)
            }
        }
        .onAppear {
            hwid = KeyAuthManager.shared.getHWID()
            if !settings.savedLicenseKey.isEmpty {
                licenseKey = settings.savedLicenseKey
            }
        }
        .alert(isPresented: $showCopiedAlert) {
            Alert(title: Text("Đã sao chép"), message: Text("Đã sao chép HWID: \(hwid)"), dismissButton: .default(Text("OK")))
        }
    }

    private func copyHwid() {
        UIPasteboard.general.string = hwid
        showCopiedAlert = true
    }

    private func pasteKey() {
        if let pasteString = UIPasteboard.general.string?.trimmingCharacters(in: .whitespacesAndNewlines), !pasteString.isEmpty {
            licenseKey = pasteString
        }
    }

    private func openDiscord() {
        UIPasteboard.general.string = hwid
        if let url = URL(string: "https://discord.gg/anhemnova") {
            UIApplication.shared.open(url)
        }
    }

    private func verifyKeyAction() {
        let key = licenseKey.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !key.isEmpty else {
            statusMessage = "Vui lòng nhập License Key!"
            isError = true
            return
        }

        isLoading = true
        statusMessage = "Đang kết nối máy chủ xác thực..."
        isError = false

        KeyAuthManager.shared.verifyKey(rawKey: key) { result in
            DispatchQueue.main.async {
                self.isLoading = false
                switch result {
                case .success(let info):
                    self.settings.savedLicenseKey = info.key
                    self.settings.licenseExpiry = info.expiry
                    self.settings.isKeyActivated = true
                    self.statusMessage = "✔ \(info.message)\n\(info.expiry)"
                    self.isError = false
                    DispatchQueue.main.asyncAfter(deadline: .now() + 0.6) {
                        self.onLoginSuccess()
                    }
                case .failure(let error):
                    self.settings.isKeyActivated = false
                    self.statusMessage = "✘ \(error.localizedDescription)"
                    self.isError = true
                }
            }
        }
    }
}
