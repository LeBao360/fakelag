import Foundation
import SwiftUI
import Combine

public final class SettingsManager: ObservableObject {
    public static let shared = SettingsManager()

    private let defaults = UserDefaults.standard

    @Published public var iconSizeDp: CGFloat {
        didSet { defaults.set(Double(iconSizeDp), forKey: "key_icon_size") }
    }

    @Published public var durasiLagSeconds: Double {
        didSet { defaults.set(durasiLagSeconds, forKey: "key_durasi_lag") }
    }

    @Published public var durasiTeleSeconds: Double {
        didSet { defaults.set(durasiTeleSeconds, forKey: "key_durasi_tele") }
    }

    @Published public var panelScalePercent: Int {
        didSet { defaults.set(panelScalePercent, forKey: "key_panel_scale") }
    }

    @Published public var opacityPercent: Int {
        didSet { defaults.set(opacityPercent, forKey: "key_opacity") }
    }

    @Published public var isLockPosition: Bool {
        didSet { defaults.set(isLockPosition, forKey: "key_lock_pos") }
    }

    @Published public var isSoundBeep: Bool {
        didSet { defaults.set(isSoundBeep, forKey: "key_sound_beep") }
    }

    @Published public var gameMode: String {
        didSet { defaults.set(gameMode, forKey: "key_game_mode") }
    }

    @Published public var isServiceRunning: Bool {
        didSet { defaults.set(isServiceRunning, forKey: "key_service_running") }
    }

    @Published public var savedLicenseKey: String {
        didSet { defaults.set(savedLicenseKey, forKey: "key_license_key") }
    }

    @Published public var licenseExpiry: String {
        didSet { defaults.set(licenseExpiry, forKey: "key_license_expiry") }
    }

    @Published public var isKeyActivated: Bool {
        didSet { defaults.set(isKeyActivated, forKey: "key_key_activated") }
    }

    @Published public var showTeleButton: Bool {
        didSet { defaults.set(showTeleButton, forKey: "key_show_tele") }
    }

    @Published public var showLagButton: Bool {
        didSet { defaults.set(showLagButton, forKey: "key_show_lag") }
    }

    @Published public var isPanelShowing: Bool = false

    private init() {
        self.iconSizeDp = CGFloat(defaults.double(forKey: "key_icon_size") != 0 ? defaults.double(forKey: "key_icon_size") : 58.0)
        self.durasiLagSeconds = defaults.double(forKey: "key_durasi_lag") != 0 ? defaults.double(forKey: "key_durasi_lag") : 1.5
        self.durasiTeleSeconds = defaults.double(forKey: "key_durasi_tele") != 0 ? defaults.double(forKey: "key_durasi_tele") : 0.8
        self.panelScalePercent = defaults.integer(forKey: "key_panel_scale") != 0 ? defaults.integer(forKey: "key_panel_scale") : 100
        self.opacityPercent = defaults.integer(forKey: "key_opacity") != 0 ? defaults.integer(forKey: "key_opacity") : 90
        self.isLockPosition = defaults.bool(forKey: "key_lock_pos")
        self.isSoundBeep = defaults.object(forKey: "key_sound_beep") != nil ? defaults.bool(forKey: "key_sound_beep") : true
        self.gameMode = defaults.string(forKey: "key_game_mode") ?? "FF THƯỜNG"
        self.isServiceRunning = defaults.bool(forKey: "key_service_running")
        self.savedLicenseKey = defaults.string(forKey: "key_license_key") ?? ""
        self.licenseExpiry = defaults.string(forKey: "key_license_expiry") ?? ""
        self.isKeyActivated = defaults.bool(forKey: "key_key_activated")
        self.showTeleButton = defaults.object(forKey: "key_show_tele") != nil ? defaults.bool(forKey: "key_show_tele") : true
        self.showLagButton = defaults.object(forKey: "key_show_lag") != nil ? defaults.bool(forKey: "key_show_lag") : true
    }

    public func clearLogin() {
        savedLicenseKey = ""
        licenseExpiry = ""
        isKeyActivated = false
        defaults.removeObject(forKey: "key_license_key")
        defaults.removeObject(forKey: "key_license_expiry")
        defaults.set(false, forKey: "key_key_activated")
    }
}
