package com.fakelag.android.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.net.VpnService
import android.os.Build
import android.os.ParcelFileDescriptor
import android.util.Log
import androidx.core.app.NotificationCompat
import com.fakelag.android.MainActivity
import com.fakelag.android.utils.SettingsManager
import com.fakelag.android.utils.SoundHzHelper
import kotlinx.coroutines.*
import java.io.FileInputStream
import java.io.FileOutputStream
import java.util.concurrent.ConcurrentLinkedQueue
import java.util.concurrent.atomic.AtomicBoolean

class LagVpnService : VpnService() {

    private val serviceScope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private var vpnInterface: ParcelFileDescriptor? = null
    private val isRunning = AtomicBoolean(false)

    // Luồng 1: TELE Engine
    private val isTeleActive = AtomicBoolean(false)
    private var teleTimerJob: Job? = null

    // Luồng 2: LAG DAME Engine
    private val isLagActive = AtomicBoolean(false)
    private var lagTimerJob: Job? = null

    private lateinit var settingsManager: SettingsManager

    private var autoLagJob: Job? = null
    private var packetWorkerJob: Job? = null

    // Outbound bullet/hit buffer
    private val outboundHitQueue = ConcurrentLinkedQueue<ByteArray>()

    override fun onCreate() {
        super.onCreate()
        settingsManager = SettingsManager.getInstance(this)
        createSilentNotificationChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val action = intent?.action
        when (action) {
            ACTION_START -> {
                startForeground(NOTIFICATION_ID, createSilentNotification("NOVA FAKE LAG Sẵn sàng"))
                isRunning.set(true)
                stopVpnInterface()
                checkAutoLag()
                broadcastTeleState()
                broadcastLagState()
            }
            ACTION_STOP -> {
                stopTele()
                stopLag()
                isRunning.set(false)
                autoLagJob?.cancel()
                stopVpnInterface()
                stopSelf()
            }
            ACTION_TRIGGER_TELE -> {
                if (isTeleActive.get()) {
                    stopTele()
                } else {
                    val customDuration = intent.getFloatExtra(EXTRA_DURATION, -1f)
                    val duration = if (customDuration > 0) customDuration else settingsManager.durasiTeleSeconds
                    triggerTele(duration)
                }
            }
            ACTION_TRIGGER_LAG -> {
                if (isLagActive.get()) {
                    stopLag()
                } else {
                    val customDuration = intent.getFloatExtra(EXTRA_DURATION, -1f)
                    val duration = if (customDuration > 0) customDuration else settingsManager.durasiLagSeconds
                    triggerLag(duration)
                }
            }
            ACTION_TOGGLE_TELE -> {
                if (isTeleActive.get()) {
                    stopTele()
                } else {
                    triggerTele(settingsManager.durasiTeleSeconds)
                }
            }
            ACTION_TOGGLE_LAG -> {
                if (isLagActive.get()) {
                    stopLag()
                } else {
                    triggerLag(settingsManager.durasiLagSeconds)
                }
            }
            ACTION_STOP_TELE -> stopTele()
            ACTION_STOP_LAG -> stopLag()
        }
        return START_STICKY
    }

    private fun checkAutoLag() {
        autoLagJob?.cancel()
        if (settingsManager.isAutoLag && isRunning.get()) {
            autoLagJob = serviceScope.launch {
                while (isActive && isRunning.get()) {
                    val intervalMs = (settingsManager.intervalSeconds * 1000).toLong()
                    val durasiMs = (settingsManager.durasiLagSeconds * 1000).toLong()

                    delay(intervalMs.coerceAtLeast(300L))
                    if (!isActive || !isRunning.get()) break

                    triggerLag(settingsManager.durasiLagSeconds)
                    delay(durasiMs.coerceAtLeast(300L))
                }
            }
        }
    }

    // ==================== LUỒNG 1: TELE ENGINE ====================
    fun triggerTele(durationSeconds: Float) {
        isRunning.set(true)
        isTeleActive.set(true)

        if (settingsManager.isSoundBeep) {
            SoundHzHelper.playBeepOn(880, 90)
        }

        checkAndStartVpnInterface()
        broadcastTeleState()

        teleTimerJob?.cancel()
        teleTimerJob = serviceScope.launch {
            val durationMs = (durationSeconds * 1000).toLong()
            delay(durationMs)
            stopTele()
        }
    }

    fun stopTele() {
        teleTimerJob?.cancel()
        if (!isTeleActive.getAndSet(false)) return

        serviceScope.launch {
            flushOutboundHits()
            delay(30L)
            checkAndStopVpnInterface()
        }

        if (settingsManager.isSoundBeep) {
            SoundHzHelper.playBeepOff(440, 100)
        }

        broadcastTeleState()
    }

    // ==================== LUỒNG 2: LAG DAME ENGINE ====================
    fun triggerLag(durationSeconds: Float) {
        isRunning.set(true)
        isLagActive.set(true)

        if (settingsManager.isSoundBeep) {
            SoundHzHelper.playLagOn(1050, 90)
        }

        checkAndStartVpnInterface()
        broadcastLagState()

        lagTimerJob?.cancel()
        lagTimerJob = serviceScope.launch {
            val durationMs = (durationSeconds * 1000).toLong()
            delay(durationMs)
            stopLag()
        }
    }

    fun stopLag() {
        lagTimerJob?.cancel()
        if (!isLagActive.getAndSet(false)) return

        serviceScope.launch {
            flushOutboundHits()
            delay(30L)
            checkAndStopVpnInterface()
        }

        if (settingsManager.isSoundBeep) {
            SoundHzHelper.playLagOff(350, 100)
        }

        broadcastLagState()
    }

    private fun checkAndStartVpnInterface() {
        if (vpnInterface == null) {
            startVpnInterface()
        }
    }

    private fun checkAndStopVpnInterface() {
        if (!isTeleActive.get() && !isLagActive.get()) {
            stopVpnInterface()
        }
    }

    private fun startPacketWorkerLoop() {
        packetWorkerJob?.cancel()
        outboundHitQueue.clear()

        packetWorkerJob = serviceScope.launch {
            val pfd = vpnInterface ?: return@launch
            val inStream = try { FileInputStream(pfd.fileDescriptor) } catch (e: Exception) { return@launch }
            val buffer = ByteArray(32767)

            while (isActive && (isTeleActive.get() || isLagActive.get())) {
                val length = try { inStream.read(buffer) } catch (e: Exception) { -1 }
                if (length > 0) {
                    val ipVersion = (buffer[0].toInt() and 0xF0) ushr 4
                    if (ipVersion == 4 && length >= 20) {
                        val protocol = buffer[9].toInt() and 0xFF
                        if (protocol == 17) { // UDP Game Packet
                            if (outboundHitQueue.size < 500) {
                                outboundHitQueue.offer(buffer.copyOf(length))
                            }
                        }
                    }
                } else {
                    delay(3L)
                }
            }
        }
    }

    private suspend fun flushOutboundHits() = withContext(Dispatchers.IO) {
        val pfd = vpnInterface ?: return@withContext
        val outStream = try { FileOutputStream(pfd.fileDescriptor) } catch (e: Exception) { return@withContext }

        var count = 0
        while (!outboundHitQueue.isEmpty()) {
            val packet = outboundHitQueue.poll() ?: break
            try {
                outStream.write(packet)
                count++
                if (count % 3 == 0) {
                    delay(10L)
                }
            } catch (ignored: Exception) {
            }
        }
    }

    private fun startVpnInterface() {
        if (vpnInterface != null) return

        try {
            val builder = Builder()
                .setSession("NOVA FAKE LAG")
                .addAddress("10.3.30.2", 32)
                .addRoute("0.0.0.0", 0)
                .setMtu(1400)
                .setBlocking(false)

            vpnInterface = builder.establish()
            Log.d(TAG, "VPN Choke ACTIVE")

            startPacketWorkerLoop()

        } catch (e: Exception) {
            Log.e(TAG, "Error starting VPN: ${e.message}")
        }
    }

    private fun stopVpnInterface() {
        try {
            packetWorkerJob?.cancel()
            vpnInterface?.close()
            vpnInterface = null
            outboundHitQueue.clear()
            Log.d(TAG, "VPN Released (Normal Speed 100%)")
        } catch (e: Exception) {
            Log.e(TAG, "Error closing VPN: ${e.message}")
        }
    }

    private fun broadcastTeleState() {
        val intent = Intent(BROADCAST_TELE_STATE).apply {
            putExtra(EXTRA_IS_TELE_ACTIVE, isTeleActive.get())
            putExtra(EXTRA_IS_RUNNING, isRunning.get())
            setPackage(packageName)
        }
        sendBroadcast(intent)
    }

    private fun broadcastLagState() {
        val intent = Intent(BROADCAST_LAG_STATE).apply {
            putExtra(EXTRA_IS_LAG_ACTIVE, isLagActive.get())
            putExtra(EXTRA_IS_RUNNING, isRunning.get())
            setPackage(packageName)
        }
        sendBroadcast(intent)
    }

    override fun onDestroy() {
        stopTele()
        stopLag()
        stopVpnInterface()
        serviceScope.cancel()
        super.onDestroy()
    }

    private fun createSilentNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "System Service",
                NotificationManager.IMPORTANCE_MIN
            ).apply {
                description = "Background Assistant"
                setShowBadge(false)
                enableLights(false)
                enableVibration(false)
                setSound(null, null)
                lockscreenVisibility = Notification.VISIBILITY_SECRET
            }
            val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            manager.createNotificationChannel(channel)
        }
    }

    private fun createSilentNotification(content: String): Notification {
        val pendingIntent = PendingIntent.getActivity(
            this,
            0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )

        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("NOVA FAKE LAG")
            .setContentText(content)
            .setSmallIcon(android.R.drawable.ic_media_play)
            .setPriority(NotificationCompat.PRIORITY_MIN)
            .setVisibility(NotificationCompat.VISIBILITY_SECRET)
            .setCategory(NotificationCompat.CATEGORY_SERVICE)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .setSilent(true)
            .build()
    }

    companion object {
        private const val TAG = "LagVpnService"
        const val CHANNEL_ID = "fakelag_silent_channel"
        const val NOTIFICATION_ID = 1001

        const val ACTION_START = "com.fakelag.android.action.START"
        const val ACTION_STOP = "com.fakelag.android.action.STOP"

        // Luồng 1 Actions & Broadcasts
        const val ACTION_TRIGGER_TELE = "com.fakelag.android.action.TRIGGER_TELE"
        const val ACTION_TOGGLE_TELE = "com.fakelag.android.action.TOGGLE_TELE"
        const val ACTION_STOP_TELE = "com.fakelag.android.action.STOP_TELE"
        const val BROADCAST_TELE_STATE = "com.fakelag.android.broadcast.TELE_STATE"
        const val EXTRA_IS_TELE_ACTIVE = "extra_is_tele_active"

        // Luồng 2 Actions & Broadcasts
        const val ACTION_TRIGGER_LAG = "com.fakelag.android.action.TRIGGER_LAG"
        const val ACTION_TOGGLE_LAG = "com.fakelag.android.action.TOGGLE_LAG"
        const val ACTION_STOP_LAG = "com.fakelag.android.action.STOP_LAG"
        const val BROADCAST_LAG_STATE = "com.fakelag.android.broadcast.LAG_STATE"
        const val EXTRA_IS_LAG_ACTIVE = "extra_is_lag_active"

        const val EXTRA_IS_RUNNING = "extra_is_running"
        const val EXTRA_DURATION = "extra_duration"

        fun start(context: Context) {
            val intent = Intent(context, LagVpnService::class.java).apply {
                action = ACTION_START
            }
            try {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    context.startForegroundService(intent)
                } else {
                    context.startService(intent)
                }
            } catch (e: Exception) {
                context.startService(intent)
            }
        }

        fun stop(context: Context) {
            val intent = Intent(context, LagVpnService::class.java).apply {
                action = ACTION_STOP
            }
            context.stopService(intent)
        }

        fun triggerTele(context: Context, durationSec: Float) {
            val intent = Intent(context, LagVpnService::class.java).apply {
                action = ACTION_TRIGGER_TELE
                putExtra(EXTRA_DURATION, durationSec)
            }
            context.startService(intent)
        }

        fun stopTele(context: Context) {
            val intent = Intent(context, LagVpnService::class.java).apply {
                action = ACTION_STOP_TELE
            }
            context.startService(intent)
        }

        fun triggerLag(context: Context, durationSec: Float) {
            val intent = Intent(context, LagVpnService::class.java).apply {
                action = ACTION_TRIGGER_LAG
                putExtra(EXTRA_DURATION, durationSec)
            }
            context.startService(intent)
        }

        fun stopLag(context: Context) {
            val intent = Intent(context, LagVpnService::class.java).apply {
                action = ACTION_STOP_LAG
            }
            context.startService(intent)
        }

        fun toggleLag(context: Context) {
            val intent = Intent(context, LagVpnService::class.java).apply {
                action = ACTION_TOGGLE_LAG
            }
            context.startService(intent)
        }

        fun toggleTele(context: Context) {
            val intent = Intent(context, LagVpnService::class.java).apply {
                action = ACTION_TOGGLE_TELE
            }
            context.startService(intent)
        }
    }
}
