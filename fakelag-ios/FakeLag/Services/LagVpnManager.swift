import Foundation
import NetworkExtension
import Combine

public final class LagVpnManager: ObservableObject {
    public static let shared = LagVpnManager()

    @Published public var isTeleActive: Bool = false
    @Published public var isLagActive: Bool = false
    @Published public var teleRemainingSeconds: Double = 0.0
    @Published public var lagRemainingSeconds: Double = 0.0

    private var teleTimer: Timer?
    private var lagTimer: Timer?
    private let settings = SettingsManager.shared
    private let sound = SoundHzHelper.shared

    private init() {}

    // MARK: - TELEPORT (Flash Lag)
    public func toggleTele() {
        if isTeleActive {
            stopTele()
        } else {
            triggerTele(duration: settings.durasiTeleSeconds)
        }
    }

    public func triggerTele(duration: Double) {
        teleTimer?.invalidate()
        isTeleActive = true
        teleRemainingSeconds = duration

        if settings.isSoundBeep {
            sound.playBeepOn(freqHz: 880, durationMs: 90)
        }

        let step = 0.05
        teleTimer = Timer.scheduledTimer(withTimeInterval: step, repeats: true) { [weak self] timer in
            guard let self = self else { return }
            self.teleRemainingSeconds -= step
            if self.teleRemainingSeconds <= 0 {
                timer.invalidate()
                self.stopTele()
            }
        }
    }

    public func stopTele() {
        teleTimer?.invalidate()
        teleTimer = nil
        guard isTeleActive else { return }
        isTeleActive = false
        teleRemainingSeconds = 0.0

        if settings.isSoundBeep {
            sound.playBeepOff(freqHz: 440, durationMs: 100)
        }
    }

    // MARK: - LAG DAME (UDP Delay)
    public func toggleLag() {
        if isLagActive {
            stopLag()
        } else {
            triggerLag(duration: settings.durasiLagSeconds)
        }
    }

    public func triggerLag(duration: Double) {
        lagTimer?.invalidate()
        isLagActive = true
        lagRemainingSeconds = duration

        if settings.isSoundBeep {
            sound.playLagOn(freqHz: 1050, durationMs: 90)
        }

        let step = 0.05
        lagTimer = Timer.scheduledTimer(withTimeInterval: step, repeats: true) { [weak self] timer in
            guard let self = self else { return }
            self.lagRemainingSeconds -= step
            if self.lagRemainingSeconds <= 0 {
                timer.invalidate()
                self.stopLag()
            }
        }
    }

    public func stopLag() {
        lagTimer?.invalidate()
        lagTimer = nil
        guard isLagActive else { return }
        isLagActive = false
        lagRemainingSeconds = 0.0

        if settings.isSoundBeep {
            sound.playLagOff(freqHz: 350, durationMs: 100)
        }
    }
}
