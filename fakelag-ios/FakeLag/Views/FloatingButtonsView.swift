import SwiftUI

public struct FloatingButtonsView: View {
    @ObservedObject var settings = SettingsManager.shared
    @ObservedObject var vpnManager = LagVpnManager.shared

    @State private var telePosition: CGPoint = CGPoint(
        x: UIScreen.main.bounds.width - 45,
        y: UIScreen.main.bounds.height * 0.35
    )
    @State private var lagPosition: CGPoint = CGPoint(
        x: UIScreen.main.bounds.width - 45,
        y: UIScreen.main.bounds.height * 0.35 + 75
    )

    @State private var tempTeleDrag: CGSize = .zero
    @State private var tempLagDrag: CGSize = .zero

    public init() {}

    private var buttonOpacity: Double {
        Double(settings.opacityPercent) / 100.0
    }

    public var body: some View {
        ZStack {
            // TELE Floating Button
            if settings.showTeleButton {
                Button(action: {
                    vpnManager.toggleTele()
                }) {
                    ZStack {
                        Circle()
                            .fill(vpnManager.isTeleActive ?
                                LinearGradient(colors: [Color(red: 1.0, green: 0.16, blue: 0.33), Color(red: 0.7, green: 0.15, blue: 1.0)], startPoint: .top, endPoint: .bottom) :
                                LinearGradient(colors: [Color(red: 0.7, green: 0.15, blue: 1.0), Color(red: 0.44, green: 0.0, blue: 1.0)], startPoint: .top, endPoint: .bottom)
                            )
                            .overlay(Circle().stroke(vpnManager.isTeleActive ? Color(red: 1.0, green: 0.16, blue: 0.33) : Color(red: 0.7, green: 0.15, blue: 1.0), lineWidth: 2))
                            .shadow(color: Color.purple.opacity(0.8), radius: 10)

                        if vpnManager.isTeleActive {
                            Text(String(format: "%.1fs", vpnManager.teleRemainingSeconds))
                                .font(.system(size: settings.iconSizeDp * 0.28, weight: .bold))
                                .foregroundColor(.white)
                        } else {
                            VStack(spacing: 2) {
                                Image(systemName: "bolt.fill")
                                    .font(.system(size: settings.iconSizeDp * 0.38, weight: .bold))
                                    .foregroundColor(.white)
                                Text("TELE")
                                    .font(.system(size: settings.iconSizeDp * 0.18, weight: .bold))
                                    .foregroundColor(.white)
                            }
                        }
                    }
                    .frame(width: settings.iconSizeDp, height: settings.iconSizeDp)
                    .opacity(buttonOpacity)
                }
                .position(
                    x: telePosition.x + tempTeleDrag.width,
                    y: telePosition.y + tempTeleDrag.height
                )
                .gesture(
                    DragGesture()
                        .onChanged { val in
                            if !settings.isLockPosition {
                                tempTeleDrag = val.translation
                            }
                        }
                        .onEnded { val in
                            if !settings.isLockPosition {
                                telePosition.x += val.translation.width
                                telePosition.y += val.translation.height
                                tempTeleDrag = .zero
                            }
                        }
                )
                .simultaneousGesture(
                    LongPressGesture(minimumDuration: 0.6).onEnded { _ in
                        settings.isPanelShowing.toggle()
                    }
                )
            }

            // LAG DAME Floating Button
            if settings.showLagButton {
                Button(action: {
                    vpnManager.toggleLag()
                }) {
                    ZStack {
                        Circle()
                            .fill(vpnManager.isLagActive ?
                                LinearGradient(colors: [Color(red: 1.0, green: 0.16, blue: 0.33), Color(red: 0.77, green: 0.0, blue: 0.17)], startPoint: .top, endPoint: .bottom) :
                                LinearGradient(colors: [Color(red: 0.0, green: 0.82, blue: 1.0), Color(red: 0.0, green: 0.4, blue: 1.0)], startPoint: .top, endPoint: .bottom)
                            )
                            .overlay(Circle().stroke(vpnManager.isLagActive ? Color(red: 1.0, green: 0.3, blue: 0.3) : Color(red: 0.0, green: 0.82, blue: 1.0), lineWidth: 2))
                            .shadow(color: Color.blue.opacity(0.8), radius: 10)

                        if vpnManager.isLagActive {
                            Text(String(format: "%.1fs", vpnManager.lagRemainingSeconds))
                                .font(.system(size: settings.iconSizeDp * 0.28, weight: .bold))
                                .foregroundColor(.white)
                        } else {
                            VStack(spacing: 2) {
                                Image(systemName: "gamecontroller.fill")
                                    .font(.system(size: settings.iconSizeDp * 0.38, weight: .bold))
                                    .foregroundColor(.white)
                                Text("LAG")
                                    .font(.system(size: settings.iconSizeDp * 0.18, weight: .bold))
                                    .foregroundColor(.white)
                            }
                        }
                    }
                    .frame(width: settings.iconSizeDp, height: settings.iconSizeDp)
                    .opacity(buttonOpacity)
                }
                .position(
                    x: lagPosition.x + tempLagDrag.width,
                    y: lagPosition.y + tempLagDrag.height
                )
                .gesture(
                    DragGesture()
                        .onChanged { val in
                            if !settings.isLockPosition {
                                tempLagDrag = val.translation
                            }
                        }
                        .onEnded { val in
                            if !settings.isLockPosition {
                                lagPosition.x += val.translation.width
                                lagPosition.y += val.translation.height
                                tempLagDrag = .zero
                            }
                        }
                )
                .simultaneousGesture(
                    LongPressGesture(minimumDuration: 0.6).onEnded { _ in
                        settings.isPanelShowing.toggle()
                    }
                )
            }
        }
        .zIndex(999)
    }
}
