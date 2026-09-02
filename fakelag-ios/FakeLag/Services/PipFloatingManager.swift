import Foundation
import UIKit
import AVKit
import Combine

public final class PipFloatingManager: NSObject, ObservableObject {
    public static let shared = PipFloatingManager()

    private var pipController: AVPictureInPictureController?
    private var sampleBufferLayer: AVSampleBufferDisplayLayer?
    private var displayLink: CADisplayLink?
    private var overlayWindow: UIWindow?

    @Published public var isPipActive: Bool = false

    private override init() {
        super.init()
    }

    public func setupPip(in view: UIView) {
        guard AVPictureInPictureController.isPictureInPictureSupported() else {
            print("PiP is not supported on this device.")
            return
        }

        let layer = AVSampleBufferDisplayLayer()
        layer.frame = CGRect(x: 0, y: 0, width: 280, height: 160)
        layer.videoGravity = .resizeAspectFill
        view.layer.addSublayer(layer)
        self.sampleBufferLayer = layer

        let contentSource = AVPictureInPictureController.ContentSource(sampleBufferDisplayLayer: layer, playbackDelegate: self)
        let controller = AVPictureInPictureController(contentSource: contentSource)
        controller.delegate = self
        controller.canStartPictureInPictureAutomaticallyFromInline = true
        self.pipController = controller
    }

    public func startPip() {
        if pipController?.isPictureInPictureActive == false {
            pipController?.startPictureInPicture()
        }
    }

    public func stopPip() {
        if pipController?.isPictureInPictureActive == true {
            pipController?.stopPictureInPicture()
        }
    }
}

extension PipFloatingManager: AVPictureInPictureSampleBufferPlaybackDelegate, AVPictureInPictureControllerDelegate {
    public func pictureInPictureController(_ pictureInPictureController: AVPictureInPictureController, setPlaying playing: Bool) {
        // Handle play/pause
    }

    public func pictureInPictureControllerTimeRangeForPlayback(_ pictureInPictureController: AVPictureInPictureController) -> CMTimeRange {
        return CMTimeRange(start: .zero, duration: CMTime(seconds: 3600, preferredTimescale: 1))
    }

    public func pictureInPictureControllerIsPlaybackLikelyToKeepUp(_ pictureInPictureController: AVPictureInPictureController) -> Bool {
        return true
    }

    public func pictureInPictureController(_ pictureInPictureController: AVPictureInPictureController, didTransitionToRenderSize newRenderSize: CMVideoDimensions) {
    }

    public func pictureInPictureController(_ pictureInPictureController: AVPictureInPictureController, skipByInterval skipInterval: CMTime, completion completionHandler: @escaping () -> Void) {
        // Forward / backward button in PiP can toggle Tele / Lag!
        LagVpnManager.shared.toggleTele()
        completionHandler()
    }

    public func pictureInPictureControllerWillStartPictureInPicture(_ pictureInPictureController: AVPictureInPictureController) {
        isPipActive = true
    }

    public func pictureInPictureControllerDidStopPictureInPicture(_ pictureInPictureController: AVPictureInPictureController) {
        isPipActive = false
    }
}
