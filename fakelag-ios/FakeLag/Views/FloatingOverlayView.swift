import SwiftUI

public struct FloatingOverlayView: View {
    @ObservedObject var settings = SettingsManager.shared
    @ObservedObject var vpnManager = LagVpnManager.shared

    @State private var offset: CGSize = .zero
    @State private var lastOffset: CGSize = .zero
    @State private var scale: CGFloat = 1.0
    @State private var lastScale: CGFloat = 1.0

    public var onClose: () -> Void

    public init(onClose: @escaping () -> Void) {
        self.onClose = onClose
    }

    private var currentScaleFactor: CGFloat {
        CGFloat(settings.panelScalePercent) / 100.0
    }

    public var body: some View {
        let baseWidth: CGFloat = 320.0 * currentScaleFactor

        VStack(spacing: 8) {
            // Header Bar (Drag Handle & Title & Close)
            HStack(spacing: 8) {
                Image(systemName: "arrow.up.and.down.and.arrow.left.and.right")
                    .foregroundColor(Color(red: 0.0, green: 0.82, blue: 1.0))
                    .font(.system(size: 14, weight: .bold))

                Text("NOVA FAKE LAG PRO")
                    .font(.system(size: 13 * currentScaleFactor, weight: .bold))
                    .foregroundColor(Color(red: 0.0, green: 0.82, blue: 1.0))

                Spacer()

                Button(action: onClose) {
                    Image(systemName: "minus")
                        .font(.system(size: 12, weight: .bold))
                        .foregroundColor(.white)
                        .frame(width: 24, height: 24)
                        .background(Color(red: 0.16, green: 0.18, blue: 0.28))
                        .cornerRadius(6)
                }

                Button(action: onClose) {
                    Image(systemName: "xmark")
                        .font(.system(size: 12, weight: .bold))
                        .foregroundColor(Color(red: 1.0, green: 0.16, blue: 0.33))
                        .frame(width: 24, height: 24)
                        .background(Color(red: 0.16, green: 0.18, blue: 0.28))
                        .cornerRadius(6)
                }
            }
            .padding(.horizontal, 4)
            .padding(.top, 4)

            Divider().background(Color(red: 0.2, green: 0.23, blue: 0.35))

            // 1. Thu phóng Menu (Interactive Scale)
            VStack(alignment: .leading, spacing: 4) {
                HStack {
                    Image(systemName: "plus.magnifyingglass")
                        .foregroundColor(Color(red: 0.7, green: 0.15, blue: 1.0))
                        .font(.system(size: 13))

                    Text("Thu phóng menu: \(settings.panelScalePercent)%")
                        .font(.system(size: 11, weight: .bold))
                        .foregroundColor(.white)

                    Spacer()

                    // Quick scale buttons
                    HStack(spacing: 4) {
                        Button("80%") { setScale(80) }
                            .font(.system(size: 9, weight: .bold))
                            .foregroundColor(Color(red: 0.7, green: 0.15, blue: 1.0))
                            .padding(.horizontal, 5).padding(.vertical, 2)
                            .background(Color(red: 0.14, green: 0.15, blue: 0.24)).cornerRadius(4)

                        Button("100%") { setScale(100) }
                            .font(.system(size: 9, weight: .bold))
                            .foregroundColor(Color(red: 0.0, green: 0.82, blue: 1.0))
                            .padding(.horizontal, 5).padding(.vertical, 2)
                            .background(Color(red: 0.14, green: 0.15, blue: 0.24)).cornerRadius(4)

                        Button("120%") { setScale(120) }
                            .font(.system(size: 9, weight: .bold))
                            .foregroundColor(Color(red: 0.0, green: 1.0, blue: 0.53))
                            .padding(.horizontal, 5).padding(.vertical, 2)
                            .background(Color(red: 0.14, green: 0.15, blue: 0.24)).cornerRadius(4)
                    }
                }

                Slider(value: Binding(
                    get: { Double(settings.panelScalePercent) },
                    set: { settings.panelScalePercent = Int($0) }
                ), in: 60...140, step: 1)
                .accentColor(Color(red: 0.7, green: 0.15, blue: 1.0))
            }

            // 2. Thời gian TELE
            VStack(alignment: .leading, spacing: 4) {
                HStack {
                    Image(systemName: "bolt.fill")
                        .foregroundColor(Color(red: 0.85, green: 0.55, blue: 1.0))
                        .font(.system(size: 13))
                    Text(String(format: "Thời gian TELE: %.1fs", settings.durasiTeleSeconds))
                        .font(.system(size: 11, weight: .bold))
                        .foregroundColor(Color(red: 0.85, green: 0.55, blue: 1.0))
                }

                Slider(value: $settings.durasiTeleSeconds, in: 0.2...2.0, step: 0.1)
                    .accentColor(Color(red: 0.7, green: 0.15, blue: 1.0))
            }

            // 3. Thời gian LAG DAME
            VStack(alignment: .leading, spacing: 4) {
                HStack {
                    Image(systemName: "gamecontroller.fill")
                        .foregroundColor(Color(red: 0.0, green: 0.82, blue: 1.0))
                        .font(.system(size: 13))
                    Text(String(format: "Thời gian LAG DAME: %.1fs", settings.durasiLagSeconds))
                        .font(.system(size: 11, weight: .bold))
                        .foregroundColor(Color(red: 0.0, green: 0.82, blue: 1.0))
                }

                Slider(value: $settings.durasiLagSeconds, in: 0.3...5.0, step: 0.1)
                    .accentColor(Color(red: 0.0, green: 0.82, blue: 1.0))
            }

            // 4. Kích thước & Độ mờ
            HStack(spacing: 12) {
                VStack(alignment: .leading, spacing: 2) {
                    Text("Kích thước: \(Int(settings.iconSizeDp))dp")
                        .font(.system(size: 10, weight: .bold))
                        .foregroundColor(Color(red: 0.0, green: 1.0, blue: 0.53))
                    Slider(value: Binding(
                        get: { Double(settings.iconSizeDp) },
                        set: { settings.iconSizeDp = CGFloat($0) }
                    ), in: 40...90, step: 2)
                    .accentColor(Color(red: 0.0, green: 1.0, blue: 0.53))
                }

                VStack(alignment: .leading, spacing: 2) {
                    Text("Độ mờ: \(settings.opacityPercent)%")
                        .font(.system(size: 10, weight: .bold))
                        .foregroundColor(Color(red: 0.0, green: 0.82, blue: 1.0))
                    Slider(value: Binding(
                        get: { Double(settings.opacityPercent) },
                        set: { settings.opacityPercent = Int($0) }
                    ), in: 20...100, step: 5)
                    .accentColor(Color(red: 0.0, green: 0.82, blue: 1.0))
                }
            }

            // 5. Checkboxes
            VStack(alignment: .leading, spacing: 6) {
                Toggle(isOn: $settings.showTeleButton) {
                    HStack(spacing: 6) {
                        Image(systemName: "bolt.fill").foregroundColor(Color(red: 0.7, green: 0.15, blue: 1.0))
                        Text("Hiện nút TELE (Tím)").font(.system(size: 11, weight: .semibold)).foregroundColor(.white)
                    }
                }
                .toggleStyle(SwitchToggleStyle(tint: Color(red: 0.7, green: 0.15, blue: 1.0)))

                Toggle(isOn: $settings.showLagButton) {
                    HStack(spacing: 6) {
                        Image(systemName: "gamecontroller.fill").foregroundColor(Color(red: 0.0, green: 0.82, blue: 1.0))
                        Text("Hiện nút LAG DAME (Xanh)").font(.system(size: 11, weight: .semibold)).foregroundColor(.white)
                    }
                }
                .toggleStyle(SwitchToggleStyle(tint: Color(red: 0.0, green: 0.82, blue: 1.0)))

                Toggle(isOn: $settings.isSoundBeep) {
                    HStack(spacing: 6) {
                        Image(systemName: "speaker.wave.2.fill").foregroundColor(Color(red: 0.0, green: 0.82, blue: 1.0))
                        Text("Âm thanh Beep báo hiệu (Hz)").font(.system(size: 11, weight: .semibold)).foregroundColor(.white)
                    }
                }
                .toggleStyle(SwitchToggleStyle(tint: Color(red: 0.0, green: 0.82, blue: 1.0)))
            }

            // Bottom Quick Actions Row & Corner Resize
            HStack(spacing: 8) {
                Button(action: {
                    settings.durasiLagSeconds = max(0.2, settings.durasiLagSeconds - 0.2)
                }) {
                    Text("– 0.2s")
                        .font(.system(size: 12, weight: .bold))
                        .foregroundColor(Color(red: 0.0, green: 0.82, blue: 1.0))
                        .frame(maxWidth: .infinity)
                        .frame(height: 32)
                        .background(Color(red: 0.14, green: 0.16, blue: 0.25))
                        .cornerRadius(8)
                }

                Button(action: {
                    settings.durasiLagSeconds = min(5.0, settings.durasiLagSeconds + 0.2)
                }) {
                    Text("+ 0.2s")
                        .font(.system(size: 12, weight: .bold))
                        .foregroundColor(Color(red: 0.0, green: 0.82, blue: 1.0))
                        .frame(maxWidth: .infinity)
                        .frame(height: 32)
                        .background(Color(red: 0.14, green: 0.16, blue: 0.25))
                        .cornerRadius(8)
                }

                // Corner Resize Grip Handle
                Image(systemName: "arrow.up.left.and.down.right.and.arrow.up.right.and.down.left")
                    .font(.system(size: 12, weight: .bold))
                    .foregroundColor(Color(red: 0.0, green: 0.82, blue: 1.0))
                    .frame(width: 32, height: 32)
                    .background(Color(red: 0.16, green: 0.18, blue: 0.28))
                    .cornerRadius(8)
                    .gesture(
                        DragGesture()
                            .onChanged { val in
                                let delta = (val.translation.width + val.translation.height) / 4.0
                                let newScale = Int((CGFloat(settings.panelScalePercent) + delta).clamped(to: 60...140))
                                settings.panelScalePercent = newScale
                            }
                    )
            }

            Text("Kéo tiêu đề để di chuyển • Chụm 2 ngón để thu phóng")
                .font(.system(size: 8))
                .foregroundColor(Color(red: 0.55, green: 0.58, blue: 0.7))
        }
        .padding(12)
        .frame(width: baseWidth)
        .background(Color(red: 0.09, green: 0.1, blue: 0.16))
        .cornerRadius(18)
        .overlay(RoundedRectangle(cornerRadius: 18).stroke(Color(red: 0.2, green: 0.24, blue: 0.4), lineWidth: 1.5))
        .shadow(color: Color.black.opacity(0.6), radius: 16)
        .offset(x: offset.width + lastOffset.width, y: offset.height + lastOffset.height)
        .gesture(
            DragGesture()
                .onChanged { val in
                    offset = val.translation
                }
                .onEnded { val in
                    lastOffset.width += val.translation.width
                    lastOffset.height += val.translation.height
                    offset = .zero
                }
        )
        .gesture(
            MagnificationGesture()
                .onChanged { val in
                    let newScale = Int((CGFloat(settings.panelScalePercent) * val).clamped(to: 60...140))
                    settings.panelScalePercent = newScale
                }
        )
    }

    private func setScale(_ s: Int) {
        settings.panelScalePercent = s
    }
}

extension Comparable {
    func clamped(to limits: ClosedRange<Self>) -> Self {
        return min(max(self, limits.lowerBound), limits.upperBound)
    }
}
