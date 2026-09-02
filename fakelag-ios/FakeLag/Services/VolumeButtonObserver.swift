import Foundation
import AVFoundation
import MediaPlayer
import Combine

public final class VolumeButtonObserver: ObservableObject {
    public static let shared = VolumeButtonObserver()

    private var initialVolume: Float = 0.5
    private var volumeView: MPVolumeView?
    private var isListening: Bool = false
    private var cancellables = Set<AnyCancellable>()

    private init() {}

    public func startListening() {
        guard !isListening else { return }
        isListening = true

        do {
            let session = AVAudioSession.sharedInstance()
            try session.setCategory(.playback, mode: .default, options: [.mixWithOthers])
            try session.setActive(true)
            initialVolume = session.outputVolume
        } catch {
            print("VolumeObserver AudioSession error: \(error)")
        }

        // Hide system volume HUD slider
        DispatchQueue.main.async {
            if self.volumeView == nil {
                let v = MPVolumeView(frame: CGRect(x: -1000, y: -1000, width: 1, height: 1))
                v.clipsToBounds = true
                if let window = UIApplication.shared.windows.first {
                    window.addSubview(v)
                }
                self.volumeView = v
            }
        }

        NotificationCenter.default.publisher(for: NSNotification.Name("AVSystemController_SystemVolumeDidChangeNotification"))
            .sink { [weak self] notification in
                guard let self = self, self.isListening else { return }
                guard let userInfo = notification.userInfo,
                      let newVol = userInfo["AVSystemController_AudioVolumeNotificationParameter"] as? Float else { return }

                if newVol > self.initialVolume {
                    // Volume UP Pressed -> Toggle TELE
                    DispatchQueue.main.async {
                        LagVpnManager.shared.toggleTele()
                    }
                } else if newVol < self.initialVolume {
                    // Volume DOWN Pressed -> Toggle LAG
                    DispatchQueue.main.async {
                        LagVpnManager.shared.toggleLag()
                    }
                }
                self.initialVolume = newVol
            }
            .store(in: &cancellables)
    }

    public func stopListening() {
        isListening = false
        cancellables.removeAll()
        volumeView?.removeFromSuperview()
        volumeView = nil
    }
}
