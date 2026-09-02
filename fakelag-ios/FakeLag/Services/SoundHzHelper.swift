import Foundation
import AVFoundation

public final class SoundHzHelper {
    public static let shared = SoundHzHelper()
    private let sampleRate: Double = 44100.0

    private init() {
        setupAudioSession()
    }

    private func setupAudioSession() {
        do {
            try AVAudioSession.sharedInstance().setCategory(.playback, mode: .default, options: [.mixWithOthers, .duckOthers])
            try AVAudioSession.sharedInstance().setActive(true)
        } catch {
            print("AVAudioSession init error: \(error.localizedDescription)")
        }
    }

    public func playBeepOn(freqHz: Double = 880.0, durationMs: Double = 90.0) {
        playTone(freqHz: freqHz, durationMs: durationMs, volume: 0.95)
    }

    public func playBeepOff(freqHz: Double = 440.0, durationMs: Double = 100.0) {
        playTone(freqHz: freqHz, durationMs: durationMs, volume: 0.95)
    }

    public func playLagOn(freqHz: Double = 1050.0, durationMs: Double = 90.0) {
        playTone(freqHz: freqHz, durationMs: durationMs, volume: 0.95)
    }

    public func playLagOff(freqHz: Double = 350.0, durationMs: Double = 100.0) {
        playTone(freqHz: freqHz, durationMs: durationMs, volume: 0.95)
    }

    public func playTone(freqHz: Double, durationMs: Double, volume: Float = 0.95) {
        DispatchQueue.global(qos: .userInteractive).async {
            let numSamples = Int((self.sampleRate * (durationMs / 1000.0)))
            guard numSamples > 0 else { return }

            guard let format = AVAudioFormat(standardFormatWithSampleRate: self.sampleRate, channels: 1) else { return }
            guard let buffer = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: AVAudioFrameCount(numSamples)) else { return }
            buffer.frameLength = AVAudioFrameCount(numSamples)

            let channels = buffer.floatChannelData
            guard let channelData = channels?[0] else { return }

            let angularFreq = 2.0 * Double.pi * freqHz / self.sampleRate
            let fadeCount = min(100, numSamples / 10)

            for i in 0..<numSamples {
                var envelope: Double = 1.0
                if i < fadeCount {
                    envelope = Double(i) / Double(fadeCount)
                } else if i > numSamples - fadeCount {
                    envelope = Double(numSamples - i) / Double(fadeCount)
                }
                let sample = sin(Double(i) * angularFreq) * Double(volume) * envelope
                channelData[i] = Float(sample)
            }

            let engine = AVAudioEngine()
            let player = AVAudioPlayerNode()

            engine.attach(player)
            engine.connect(player, to: engine.mainMixerNode, format: format)

            do {
                try engine.start()
                player.play()
                player.scheduleBuffer(buffer, at: nil, options: [], completionHandler: {
                    DispatchQueue.main.asyncAfter(deadline: .now() + 0.05) {
                        player.stop()
                        engine.stop()
                    }
                })
            } catch {
                print("AVAudioEngine error: \(error.localizedDescription)")
            }
        }
    }
}
