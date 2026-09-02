import SwiftUI

public struct MainView: View {
    @ObservedObject var settings = SettingsManager.shared
    @ObservedObject var vpnManager = LagVpnManager.shared

    @State private var showLogoutAlert: Bool = false
    public var onLogout: () -> Void

    private let gameModes = ["FF THƯỜNG", "FF TỐC ĐỘ", "MLBB ULTRA", "PUBGM TICK", "TẤT CẢ UDP"]

    public init(onLogout: @escaping () -> Void) {
        self.onLogout = onLogout
    }

    public var body: some View {
        ZStack {
            Color(red: 0.05, green: 0.06, blue: 0.09).ignoresSafeArea()

            VStack(spacing: 16) {
                // Top Header
                VStack(spacing: 6) {
                    Text("⚡ NOVA FAKE LAG PRO")
                        .font(.system(size: 22, weight: .bold, design: .rounded))
                        .foregroundColor(Color(red: 0.0, green: 0.82, blue: 1.0))
                        .tracking(2)

                    Text("ASSISTANT FOR FREE FIRE & GAMING (IOS)")
                        .font(.system(size: 10, weight: .semibold))
                        .foregroundColor(Color(red: 0.55, green: 0.58, blue: 0.7))

                    // License Badge Row
                    HStack(spacing: 6) {
                        Image(systemName: "key.fill")
                            .foregroundColor(Color(red: 1.0, green: 0.84, blue: 0.0))
                            .font(.system(size: 11))

                        Text(settings.licenseExpiry.isEmpty ? "VIP: Vĩnh viễn (LIFETIME)" : settings.licenseExpiry)
                            .font(.system(size: 11, weight: .bold))
                            .foregroundColor(Color(red: 1.0, green: 0.84, blue: 0.0))

                        Button(action: { showLogoutAlert = true }) {
                            Image(systemName: "rectangle.portrait.and.arrow.right")
                                .font(.system(size: 11, weight: .bold))
                                .foregroundColor(Color(red: 1.0, green: 0.16, blue: 0.33))
                                .padding(4)
                                .background(Color(red: 0.14, green: 0.16, blue: 0.25))
                                .cornerRadius(4)
                        }
                    }
                    .padding(.horizontal, 10)
                    .padding(.vertical, 4)
                    .background(Color(red: 0.12, green: 0.14, blue: 0.22))
                    .cornerRadius(8)
                }
                .padding(.top, 10)

                // Preview Card
                VStack(spacing: 12) {
                    Text("BẢNG ĐIỀU KHIỂN NỔI GAMING")
                        .font(.system(size: 11, weight: .bold))
                        .foregroundColor(Color(red: 0.55, green: 0.58, blue: 0.7))

                    // Floating preview buttons
                    HStack(spacing: 12) {
                        // Tele preview
                        Button(action: { vpnManager.toggleTele() }) {
                            ZStack {
                                Circle().fill(LinearGradient(colors: [Color(red: 0.7, green: 0.15, blue: 1.0), Color(red: 0.44, green: 0.0, blue: 1.0)], startPoint: .top, endPoint: .bottom))
                                    .frame(width: 54, height: 54)
                                VStack(spacing: 1) {
                                    Image(systemName: "bolt.fill").foregroundColor(.white).font(.system(size: 18))
                                    Text("TELE").font(.system(size: 9, weight: .bold)).foregroundColor(.white)
                                }
                            }
                        }

                        // Lag preview
                        Button(action: { vpnManager.toggleLag() }) {
                            ZStack {
                                Circle().fill(LinearGradient(colors: [Color(red: 0.0, green: 0.82, blue: 1.0), Color(red: 0.0, green: 0.4, blue: 1.0)], startPoint: .top, endPoint: .bottom))
                                    .frame(width: 54, height: 54)
                                VStack(spacing: 1) {
                                    Image(systemName: "gamecontroller.fill").foregroundColor(.white).font(.system(size: 18))
                                    Text("LAG").font(.system(size: 9, weight: .bold)).foregroundColor(.white)
                                }
                            }
                        }

                        // Menu button
                        Button(action: { settings.isPanelShowing.toggle() }) {
                            Image(systemName: "gearshape.fill")
                                .font(.system(size: 20))
                                .foregroundColor(.white)
                                .frame(width: 38, height: 54)
                        }
                    }
                    .padding(8)
                    .background(Color(red: 0.07, green: 0.08, blue: 0.13))
                    .cornerRadius(16)
                    .overlay(RoundedRectangle(cornerRadius: 16).stroke(Color(red: 0.2, green: 0.23, blue: 0.35), lineWidth: 1))

                    Text(String(format: "⚡ TELE: %.1fs  |  🎮 LAG DAME: %.1fs", settings.durasiTeleSeconds, settings.durasiLagSeconds))
                        .font(.system(size: 13, weight: .bold))
                        .foregroundColor(Color(red: 0.0, green: 1.0, blue: 0.53))
                }
                .padding(16)
                .frame(maxWidth: .infinity)
                .background(Color(red: 0.09, green: 0.1, blue: 0.16))
                .cornerRadius(18)
                .overlay(RoundedRectangle(cornerRadius: 18).stroke(Color(red: 0.18, green: 0.2, blue: 0.33), lineWidth: 1.5))
                .padding(.horizontal, 16)

                // Action Buttons
                VStack(spacing: 12) {
                    // START
                    Button(action: {
                        settings.isServiceRunning = true
                        settings.isPanelShowing = true
                    }) {
                        Text("BẮT ĐẦU NÚT NỔI")
                            .font(.system(size: 16, weight: .bold))
                            .foregroundColor(.white)
                            .frame(maxWidth: .infinity)
                            .frame(height: 52)
                            .background(LinearGradient(colors: [Color(red: 0.0, green: 0.8, blue: 0.4), Color(red: 0.0, green: 0.6, blue: 0.3)], startPoint: .top, endPoint: .bottom))
                            .cornerRadius(12)
                            .shadow(color: Color.green.opacity(0.3), radius: 6)
                    }

                    // STOP
                    Button(action: {
                        settings.isServiceRunning = false
                        settings.isPanelShowing = false
                        vpnManager.stopTele()
                        vpnManager.stopLag()
                    }) {
                        Text("DỪNG LẠI")
                            .font(.system(size: 16, weight: .bold))
                            .foregroundColor(.white)
                            .frame(maxWidth: .infinity)
                            .frame(height: 52)
                            .background(LinearGradient(colors: [Color(red: 1.0, green: 0.16, blue: 0.33), Color(red: 0.8, green: 0.0, blue: 0.2)], startPoint: .top, endPoint: .bottom))
                            .cornerRadius(12)
                            .shadow(color: Color.red.opacity(0.3), radius: 6)
                    }

                    // Game Mode Picker Button
                    Button(action: cycleGameMode) {
                        Text("CHẾ ĐỘ: \(settings.gameMode)")
                            .font(.system(size: 14, weight: .bold))
                            .foregroundColor(Color(red: 0.7, green: 0.15, blue: 1.0))
                            .frame(maxWidth: .infinity)
                            .frame(height: 50)
                            .background(Color(red: 0.09, green: 0.1, blue: 0.16))
                            .cornerRadius(12)
                            .overlay(RoundedRectangle(cornerRadius: 12).stroke(Color(red: 0.7, green: 0.15, blue: 1.0), lineWidth: 1.5))
                    }
                }
                .padding(.horizontal, 16)

                Spacer()

                Text("Bấm icon Bánh răng ⚙️ để mở bảng Menu thu phóng")
                    .font(.system(size: 11, weight: .bold))
                    .foregroundColor(Color(red: 1.0, green: 0.55, blue: 0.0))
                    .padding(.bottom, 16)
            }

            // Floating Buttons Overlay Layer
            if settings.isServiceRunning {
                FloatingButtonsView()
            }

            // Floating Settings Menu Overlay Layer
            if settings.isPanelShowing {
                FloatingOverlayView(onClose: {
                    settings.isPanelShowing = false
                })
            }
        }
        .alert(isPresented: $showLogoutAlert) {
            Alert(
                title: Text("ĐỔI LICENSE KEY"),
                message: Text("Bạn có muốn đăng xuất Key hiện tại và nhập Key mới không?"),
                primaryButton: .destructive(Text("Đăng xuất")) {
                    settings.clearLogin()
                    onLogout()
                },
                secondaryButton: .cancel(Text("Hủy"))
            )
        }
    }

    private func cycleGameMode() {
        if let idx = gameModes.firstIndex(of: settings.gameMode) {
            let nextIdx = (idx + 1) % gameModes.count
            settings.gameMode = gameModes[nextIdx]
        } else {
            settings.gameMode = gameModes[0]
        }
    }
}
