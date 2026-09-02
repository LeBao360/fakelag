package com.fakelag.android.utils

import android.media.AudioAttributes
import android.media.AudioFormat
import android.media.AudioTrack
import android.util.Log
import kotlin.math.sin

object SoundHzHelper {

    private const val TAG = "SoundHzHelper"
    private const val SAMPLE_RATE = 44100

    fun playBeepOn(freqHz: Int = 880, durationMs: Int = 90) {
        playTone(freqHz, durationMs, volume = 0.95f)
    }

    fun playBeepOff(freqHz: Int = 440, durationMs: Int = 100) {
        playTone(freqHz, durationMs, volume = 0.95f)
    }

    fun playLagOn(freqHz: Int = 1050, durationMs: Int = 90) {
        playTone(freqHz, durationMs, volume = 0.95f)
    }

    fun playLagOff(freqHz: Int = 350, durationMs: Int = 100) {
        playTone(freqHz, durationMs, volume = 0.95f)
    }

    fun playTone(freqHz: Int, durationMs: Int = 100, volume: Float = 0.95f) {
        Thread {
            var audioTrack: AudioTrack? = null
            try {
                val numSamples = (SAMPLE_RATE * (durationMs / 1000.0)).toInt().coerceAtLeast(1)
                val buffer = ShortArray(numSamples)
                val angularFreq = 2.0 * Math.PI * freqHz / SAMPLE_RATE

                val fadeSamples = (numSamples * 0.1).toInt().coerceIn(20, 100)

                for (i in 0 until numSamples) {
                    val envelope = when {
                        i < fadeSamples -> i.toDouble() / fadeSamples
                        i > numSamples - fadeSamples -> (numSamples - i).toDouble() / fadeSamples
                        else -> 1.0
                    }
                    val sampleValue = (sin(i * angularFreq) * Short.MAX_VALUE * volume * envelope).toInt()
                    buffer[i] = sampleValue.coerceIn(Short.MIN_VALUE.toInt(), Short.MAX_VALUE.toInt()).toShort()
                }

                audioTrack = AudioTrack.Builder()
                    .setAudioAttributes(
                        AudioAttributes.Builder()
                            .setUsage(AudioAttributes.USAGE_GAME)
                            .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                            .build()
                    )
                    .setAudioFormat(
                        AudioFormat.Builder()
                            .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
                            .setSampleRate(SAMPLE_RATE)
                            .setChannelMask(AudioFormat.CHANNEL_OUT_MONO)
                            .build()
                    )
                    .setBufferSizeInBytes(buffer.size * 2)
                    .setTransferMode(AudioTrack.MODE_STATIC)
                    .build()

                audioTrack.write(buffer, 0, buffer.size)
                audioTrack.play()

                Thread.sleep(durationMs.toLong() + 30)
            } catch (e: Exception) {
                Log.e(TAG, "AudioTrack error playing $freqHz Hz: ${e.message}")
            } finally {
                try {
                    audioTrack?.stop()
                    audioTrack?.release()
                } catch (_: Exception) {
                }
            }
        }.start()
    }
}
