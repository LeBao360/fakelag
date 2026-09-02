package com.fakelag.android.service

import android.annotation.SuppressLint
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.graphics.PixelFormat
import android.graphics.drawable.GradientDrawable
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.util.Log
import android.util.TypedValue
import android.view.*
import android.widget.*
import androidx.appcompat.view.ContextThemeWrapper
import androidx.core.app.NotificationCompat
import com.fakelag.android.MainActivity
import com.fakelag.android.R
import com.fakelag.android.utils.SettingsManager
import kotlin.math.abs
import kotlin.math.roundToInt

class FloatingOverlayService : Service() {

    private lateinit var windowManager: WindowManager
    private lateinit var settingsManager: SettingsManager
    private lateinit var themedContext: Context

    // Luồng 1 View: TELE
    private var teleFloatingView: View? = null
    private var teleLayoutParams: WindowManager.LayoutParams? = null
    private var isTeleActiveLocal = false

    // Luồng 2 View: LAG
    private var lagFloatingView: View? = null
    private var lagLayoutParams: WindowManager.LayoutParams? = null
    private var isLagActiveLocal = false

    // Settings Panel
    private var settingsPanelView: View? = null
    private var panelLayoutParams: WindowManager.LayoutParams? = null
    private var isPanelShowing = false

    private val handler = Handler(Looper.getMainLooper())
    private var teleCountdownRunnable: Runnable? = null
    private var lagCountdownRunnable: Runnable? = null

    // Separate Receiver 1: TELE State
    private val teleStateReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            if (intent?.action == LagVpnService.BROADCAST_TELE_STATE) {
                val isActive = intent.getBooleanExtra(LagVpnService.EXTRA_IS_TELE_ACTIVE, false)
                isTeleActiveLocal = isActive
                if (!isActive) {
                    resetTeleVisual()
                }
            }
        }
    }

    // Separate Receiver 2: LAG State
    private val lagStateReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            if (intent?.action == LagVpnService.BROADCAST_LAG_STATE) {
                val isActive = intent.getBooleanExtra(LagVpnService.EXTRA_IS_LAG_ACTIVE, false)
                isLagActiveLocal = isActive
                if (!isActive) {
                    resetLagVisual()
                }
            }
        }
    }

    override fun onCreate() {
        super.onCreate()
        windowManager = getSystemService(WINDOW_SERVICE) as WindowManager
        settingsManager = SettingsManager.getInstance(this)
        themedContext = ContextThemeWrapper(this, R.style.Theme_FakeLagAndroid)

        try {
            createNotificationChannel()
            startForeground(NOTIFICATION_ID, createNotification())
        } catch (e: Exception) {
            Log.e(TAG, "Foreground service error: ${e.message}")
        }

        // Register Separate Receivers
        val filterTele = IntentFilter(LagVpnService.BROADCAST_TELE_STATE)
        val filterLag = IntentFilter(LagVpnService.BROADCAST_LAG_STATE)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            registerReceiver(teleStateReceiver, filterTele, RECEIVER_NOT_EXPORTED)
            registerReceiver(lagStateReceiver, filterLag, RECEIVER_NOT_EXPORTED)
        } else {
            registerReceiver(teleStateReceiver, filterTele)
            registerReceiver(lagStateReceiver, filterLag)
        }

        initTeleFloatingButton()
        initLagFloatingButton()
        initSettingsPanel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        try {
            createNotificationChannel()
            startForeground(NOTIFICATION_ID, createNotification())
        } catch (e: Exception) {
            Log.e(TAG, "onStartCommand foreground error: ${e.message}")
        }

        when (intent?.action) {
            ACTION_SHOW_PANEL -> showSettingsPanel()
            ACTION_STOP -> stopSelf()
            else -> {
                if (teleFloatingView == null) initTeleFloatingButton()
                if (lagFloatingView == null) initLagFloatingButton()
            }
        }
        return START_STICKY
    }

    // ==================== 1. LUỒNG TELE BUTTON ====================
    @SuppressLint("InflateParams")
    private fun initTeleFloatingButton() {
        if (teleFloatingView != null || !settingsManager.showTeleButton) return

        val layoutType = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
        } else {
            @Suppress("DEPRECATION")
            WindowManager.LayoutParams.TYPE_PHONE
        }

        val displayMetrics = resources.displayMetrics
        val defaultX = displayMetrics.widthPixels - dpToPx(80)
        val defaultY = displayMetrics.heightPixels / 4

        teleLayoutParams = WindowManager.LayoutParams(
            WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.WRAP_CONTENT,
            layoutType,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = Gravity.TOP or Gravity.START
            x = if (settingsManager.lastTeleX != -1) settingsManager.lastTeleX else defaultX
            y = if (settingsManager.lastTeleY != -1) settingsManager.lastTeleY else defaultY
        }

        val inflater = LayoutInflater.from(themedContext)
        teleFloatingView = inflater.inflate(R.layout.layout_floating_tele, null)

        setupIndependentTouch(
            view = teleFloatingView!!,
            params = teleLayoutParams!!,
            onSavePos = { x, y ->
                settingsManager.lastTeleX = x
                settingsManager.lastTeleY = y
            },
            onClick = {
                if (isTeleActiveLocal) {
                    isTeleActiveLocal = false
                    LagVpnService.stopTele(this)
                    resetTeleVisual()
                } else {
                    val duration = settingsManager.durasiTeleSeconds
                    isTeleActiveLocal = true
                    LagVpnService.triggerTele(this, duration)
                    startTeleCountdown(duration)
                }
            },
            onLongClick = {
                showSettingsPanel()
            }
        )

        try {
            if (teleFloatingView?.parent != null) {
                windowManager.removeView(teleFloatingView)
            }
            windowManager.addView(teleFloatingView, teleLayoutParams)
            applyButtonSizeAndOpacity()
        } catch (e: Exception) {
            Log.e(TAG, "Error adding teleFloatingView: ${e.message}")
        }
    }

    // ==================== 2. LUỒNG LAG DAME BUTTON ====================
    @SuppressLint("InflateParams")
    private fun initLagFloatingButton() {
        if (lagFloatingView != null || !settingsManager.showLagButton) return

        val layoutType = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
        } else {
            @Suppress("DEPRECATION")
            WindowManager.LayoutParams.TYPE_PHONE
        }

        val displayMetrics = resources.displayMetrics
        val defaultX = displayMetrics.widthPixels - dpToPx(80)
        val defaultY = displayMetrics.heightPixels / 4 + dpToPx(75)

        lagLayoutParams = WindowManager.LayoutParams(
            WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.WRAP_CONTENT,
            layoutType,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = Gravity.TOP or Gravity.START
            x = if (settingsManager.lastLagX != -1) settingsManager.lastLagX else defaultX
            y = if (settingsManager.lastLagY != -1) settingsManager.lastLagY else defaultY
        }

        val inflater = LayoutInflater.from(themedContext)
        lagFloatingView = inflater.inflate(R.layout.layout_floating_lag, null)

        setupIndependentTouch(
            view = lagFloatingView!!,
            params = lagLayoutParams!!,
            onSavePos = { x, y ->
                settingsManager.lastLagX = x
                settingsManager.lastLagY = y
            },
            onClick = {
                if (isLagActiveLocal) {
                    isLagActiveLocal = false
                    LagVpnService.stopLag(this)
                    resetLagVisual()
                } else {
                    val duration = settingsManager.durasiLagSeconds
                    isLagActiveLocal = true
                    LagVpnService.triggerLag(this, duration)
                    startLagCountdown(duration)
                }
            },
            onLongClick = {
                showSettingsPanel()
            }
        )

        try {
            if (lagFloatingView?.parent != null) {
                windowManager.removeView(lagFloatingView)
            }
            windowManager.addView(lagFloatingView, lagLayoutParams)
            applyButtonSizeAndOpacity()
        } catch (e: Exception) {
            Log.e(TAG, "Error adding lagFloatingView: ${e.message}")
        }
    }

    /**
     * Dedicated gesture detector and touch handler for each floating view
     */
    @SuppressLint("ClickableViewAccessibility")
    private fun setupIndependentTouch(
        view: View,
        params: WindowManager.LayoutParams,
        onSavePos: (Int, Int) -> Unit,
        onClick: () -> Unit,
        onLongClick: () -> Unit
    ) {
        var initialX = 0
        var initialY = 0
        var initialTouchX = 0f
        var initialTouchY = 0f
        var isMoved = false

        val gestureDetector = GestureDetector(this, object : GestureDetector.SimpleOnGestureListener() {
            override fun onDown(e: MotionEvent): Boolean = true

            override fun onSingleTapUp(e: MotionEvent): Boolean {
                onClick()
                return true
            }

            override fun onLongPress(e: MotionEvent) {
                if (!isMoved) {
                    onLongClick()
                }
            }
        })

        view.setOnTouchListener { _, event ->
            gestureDetector.onTouchEvent(event)

            when (event.action) {
                MotionEvent.ACTION_DOWN -> {
                    initialX = params.x
                    initialY = params.y
                    initialTouchX = event.rawX
                    initialTouchY = event.rawY
                    isMoved = false
                    true
                }
                MotionEvent.ACTION_MOVE -> {
                    val deltaX = (event.rawX - initialTouchX).toInt()
                    val deltaY = (event.rawY - initialTouchY).toInt()

                    if (abs(deltaX) > 12 || abs(deltaY) > 12) {
                        isMoved = true
                    }

                    if (isMoved && !settingsManager.isLockPosition) {
                        params.x = initialX + deltaX
                        params.y = initialY + deltaY
                        try {
                            windowManager.updateViewLayout(view, params)
                        } catch (ignored: Exception) {
                        }
                    }
                    true
                }
                MotionEvent.ACTION_UP -> {
                    if (isMoved) {
                        onSavePos(params.x, params.y)
                    }
                    true
                }
                else -> false
            }
        }
    }

    private fun startTeleCountdown(durationSec: Float) {
        val root = teleFloatingView ?: return
        val normal = root.findViewById<LinearLayout>(R.id.teleContentNormal) ?: return
        val tvCount = root.findViewById<TextView>(R.id.tvTeleCountdown) ?: return
        val circle = root.findViewById<FrameLayout>(R.id.circleFloatingTele) ?: return

        teleCountdownRunnable?.let { handler.removeCallbacks(it) }
        normal.visibility = View.GONE
        tvCount.visibility = View.VISIBLE

        val shape = GradientDrawable().apply {
            shape = GradientDrawable.OVAL
            colors = intArrayOf(0xFFFF2A55.toInt(), 0xFF7000FF.toInt())
            gradientType = GradientDrawable.LINEAR_GRADIENT
            setStroke(dpToPx(2), 0xFFFF2A55.toInt())
        }
        circle.background = shape

        val endTime = System.currentTimeMillis() + (durationSec * 1000).toLong()

        teleCountdownRunnable = object : Runnable {
            override fun run() {
                val remainingMs = endTime - System.currentTimeMillis()
                if (remainingMs > 0 && isTeleActiveLocal) {
                    tvCount.text = String.format("%.1fs", remainingMs / 1000.0f)
                    handler.postDelayed(this, 50)
                } else {
                    resetTeleVisual()
                }
            }
        }
        handler.post(teleCountdownRunnable!!)
    }

    private fun resetTeleVisual() {
        val root = teleFloatingView ?: return
        val normal = root.findViewById<LinearLayout>(R.id.teleContentNormal) ?: return
        val tvCount = root.findViewById<TextView>(R.id.tvTeleCountdown) ?: return
        val circle = root.findViewById<FrameLayout>(R.id.circleFloatingTele) ?: return

        teleCountdownRunnable?.let { handler.removeCallbacks(it) }
        tvCount.visibility = View.GONE
        normal.visibility = View.VISIBLE
        circle.setBackgroundResource(R.drawable.bg_circle_tele)
    }

    private fun startLagCountdown(durationSec: Float) {
        val root = lagFloatingView ?: return
        val normal = root.findViewById<LinearLayout>(R.id.lagContentNormal) ?: return
        val tvCount = root.findViewById<TextView>(R.id.tvLagCountdown) ?: return
        val circle = root.findViewById<FrameLayout>(R.id.circleFloatingLag) ?: return

        lagCountdownRunnable?.let { handler.removeCallbacks(it) }
        normal.visibility = View.GONE
        tvCount.visibility = View.VISIBLE

        val shape = GradientDrawable().apply {
            shape = GradientDrawable.OVAL
            colors = intArrayOf(0xFFFF2A55.toInt(), 0xFFC4002C.toInt())
            gradientType = GradientDrawable.LINEAR_GRADIENT
            setStroke(dpToPx(2), 0xFFFF5555.toInt())
        }
        circle.background = shape

        val endTime = System.currentTimeMillis() + (durationSec * 1000).toLong()

        lagCountdownRunnable = object : Runnable {
            override fun run() {
                val remainingMs = endTime - System.currentTimeMillis()
                if (remainingMs > 0 && isLagActiveLocal) {
                    tvCount.text = String.format("%.1fs", remainingMs / 1000.0f)
                    handler.postDelayed(this, 50)
                } else {
                    resetLagVisual()
                }
            }
        }
        handler.post(lagCountdownRunnable!!)
    }

    private fun resetLagVisual() {
        val root = lagFloatingView ?: return
        val normal = root.findViewById<LinearLayout>(R.id.lagContentNormal) ?: return
        val tvCount = root.findViewById<TextView>(R.id.tvLagCountdown) ?: return
        val circle = root.findViewById<FrameLayout>(R.id.circleFloatingLag) ?: return

        lagCountdownRunnable?.let { handler.removeCallbacks(it) }
        tvCount.visibility = View.GONE
        normal.visibility = View.VISIBLE
        circle.setBackgroundResource(R.drawable.bg_circle_lag)
    }

    private fun applyButtonSizeAndOpacity() {
        val sizePx = dpToPx(settingsManager.iconSizeDp)
        val alphaVal = (settingsManager.opacityPercent / 100f).coerceIn(0.2f, 1.0f)

        teleFloatingView?.let { root ->
            root.alpha = alphaVal
            val circle = root.findViewById<FrameLayout>(R.id.circleFloatingTele)
            circle?.layoutParams?.width = sizePx
            circle?.layoutParams?.height = sizePx
            circle?.requestLayout()
            try { windowManager.updateViewLayout(teleFloatingView, teleLayoutParams) } catch (ignored: Exception) {}
        }

        lagFloatingView?.let { root ->
            root.alpha = alphaVal
            val circle = root.findViewById<FrameLayout>(R.id.circleFloatingLag)
            circle?.layoutParams?.width = sizePx
            circle?.layoutParams?.height = sizePx
            circle?.requestLayout()
            try { windowManager.updateViewLayout(lagFloatingView, lagLayoutParams) } catch (ignored: Exception) {}
        }
    }

    // ==================== 3. SETTINGS PANEL ====================
    @SuppressLint("InflateParams")
    private fun initSettingsPanel() {
        if (settingsPanelView != null) return

        val layoutType = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
        } else {
            @Suppress("DEPRECATION")
            WindowManager.LayoutParams.TYPE_PHONE
        }

        val scale = (settingsManager.panelScalePercent / 100f).coerceIn(0.6f, 1.4f)
        val targetWidth = (320 * scale).toInt()

        val displayMetrics = resources.displayMetrics
        val savedX = settingsManager.lastPanelX
        val savedY = settingsManager.lastPanelY

        val defaultX = if (savedX >= 0) savedX else (displayMetrics.widthPixels - dpToPx(targetWidth)) / 2
        val defaultY = if (savedY >= 0) savedY else (displayMetrics.heightPixels - dpToPx(380)) / 2

        panelLayoutParams = WindowManager.LayoutParams(
            dpToPx(targetWidth),
            WindowManager.LayoutParams.WRAP_CONTENT,
            layoutType,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = Gravity.TOP or Gravity.START
            x = defaultX.coerceAtLeast(0)
            y = defaultY.coerceAtLeast(0)
        }

        val inflater = LayoutInflater.from(themedContext)
        settingsPanelView = inflater.inflate(R.layout.layout_settings_panel, null)

        setupPanelControls()
    }

    private fun applyPanelScale(scalePercent: Int) {
        val scale = (scalePercent / 100f).coerceIn(0.6f, 1.4f)
        val targetWidth = (320 * scale).toInt()

        panelLayoutParams?.width = dpToPx(targetWidth)
        if (isPanelShowing && settingsPanelView != null) {
            try {
                windowManager.updateViewLayout(settingsPanelView, panelLayoutParams)
            } catch (ignored: Exception) {
            }
        }
    }

    @SuppressLint("ClickableViewAccessibility")
    private fun setupPanelDrag(headerView: View) {
        val params = panelLayoutParams ?: return
        var initialX = 0
        var initialY = 0
        var initialTouchX = 0f
        var initialTouchY = 0f
        var isMoved = false

        headerView.setOnTouchListener { _, event ->
            when (event.action) {
                MotionEvent.ACTION_DOWN -> {
                    initialX = params.x
                    initialY = params.y
                    initialTouchX = event.rawX
                    initialTouchY = event.rawY
                    isMoved = false
                    true
                }
                MotionEvent.ACTION_MOVE -> {
                    val dx = (event.rawX - initialTouchX).toInt()
                    val dy = (event.rawY - initialTouchY).toInt()
                    if (abs(dx) > 4 || abs(dy) > 4 || isMoved) {
                        isMoved = true
                        params.x = initialX + dx
                        params.y = initialY + dy
                        try {
                            windowManager.updateViewLayout(settingsPanelView, params)
                        } catch (ignored: Exception) {}
                    }
                    true
                }
                MotionEvent.ACTION_UP -> {
                    if (isMoved) {
                        settingsManager.lastPanelX = params.x
                        settingsManager.lastPanelY = params.y
                    }
                    true
                }
                else -> false
            }
        }
    }

    @SuppressLint("ClickableViewAccessibility")
    private fun setupPanelResizeHandle(handleView: View, seekPanelScale: SeekBar, tvPanelScale: TextView) {
        var startScale = settingsManager.panelScalePercent
        var startTouchX = 0f
        var startTouchY = 0f

        handleView.setOnTouchListener { _, event ->
            when (event.action) {
                MotionEvent.ACTION_DOWN -> {
                    startScale = settingsManager.panelScalePercent
                    startTouchX = event.rawX
                    startTouchY = event.rawY
                    handleView.scaleX = 0.9f
                    handleView.scaleY = 0.9f
                    true
                }
                MotionEvent.ACTION_MOVE -> {
                    val dx = event.rawX - startTouchX
                    val dy = event.rawY - startTouchY
                    val delta = (dx + dy) / 4f
                    val newScale = (startScale + delta).toInt().coerceIn(60, 140)

                    if (newScale != settingsManager.panelScalePercent) {
                        settingsManager.panelScalePercent = newScale
                        seekPanelScale.progress = newScale
                        tvPanelScale.text = "Thu phóng menu: $newScale%"
                        applyPanelScale(newScale)
                    }
                    true
                }
                MotionEvent.ACTION_UP, MotionEvent.ACTION_CANCEL -> {
                    handleView.scaleX = 1.0f
                    handleView.scaleY = 1.0f
                    true
                }
                else -> false
            }
        }
    }

    @SuppressLint("ClickableViewAccessibility")
    private fun setupPinchToZoom(rootView: View, seekPanelScale: SeekBar, tvPanelScale: TextView) {
        val scaleDetector = ScaleGestureDetector(themedContext, object : ScaleGestureDetector.SimpleOnScaleGestureListener() {
            override fun onScale(detector: ScaleGestureDetector): Boolean {
                val factor = detector.scaleFactor
                val currentScale = settingsManager.panelScalePercent
                val targetScale = if (factor > 1.0f) {
                    currentScale + ((factor - 1.0f) * 60).toInt().coerceAtLeast(1)
                } else {
                    currentScale - ((1.0f - factor) * 60).toInt().coerceAtLeast(1)
                }
                val newScale = targetScale.coerceIn(60, 140)
                if (newScale != currentScale) {
                    settingsManager.panelScalePercent = newScale
                    seekPanelScale.progress = newScale
                    tvPanelScale.text = "Thu phóng menu: $newScale%"
                    applyPanelScale(newScale)
                }
                return true
            }
        })

        rootView.setOnTouchListener { _, event ->
            if (event.pointerCount > 1) {
                scaleDetector.onTouchEvent(event)
                true
            } else {
                false
            }
        }
    }

    private fun setupPanelControls() {
        val view = settingsPanelView ?: return

        val rootCard = view.findViewById<LinearLayout>(R.id.settingsCardRoot)
        val panelHeader = view.findViewById<LinearLayout>(R.id.panelHeader)
        val btnClose = view.findViewById<ImageView>(R.id.btnClosePanel)
        val btnMinimize = view.findViewById<ImageView>(R.id.btnMinimizePanel)
        val btnResizeHandle = view.findViewById<FrameLayout>(R.id.btnPanelResizeHandle)

        val tvPanelScale = view.findViewById<TextView>(R.id.tvPanelScale)
        val seekPanelScale = view.findViewById<SeekBar>(R.id.seekPanelScale)
        val btnScale80 = view.findViewById<TextView>(R.id.btnScale80)
        val btnScale100 = view.findViewById<TextView>(R.id.btnScale100)
        val btnScale120 = view.findViewById<TextView>(R.id.btnScale120)

        val tvDurasiTele = view.findViewById<TextView>(R.id.tvDurasiTele)
        val seekDurasiTele = view.findViewById<SeekBar>(R.id.seekDurasiTele)

        val tvDurasiLag = view.findViewById<TextView>(R.id.tvDurasiLag)
        val seekDurasiLag = view.findViewById<SeekBar>(R.id.seekDurasiLag)

        val tvUkuranIkon = view.findViewById<TextView>(R.id.tvUkuranIkon)
        val seekUkuranIkon = view.findViewById<SeekBar>(R.id.seekUkuranIkon)

        val tvOpacity = view.findViewById<TextView>(R.id.tvOpacity)
        val seekOpacity = view.findViewById<SeekBar>(R.id.seekOpacity)

        val chkShowTele = view.findViewById<CheckBox>(R.id.chkShowTele)
        val chkShowLag = view.findViewById<CheckBox>(R.id.chkShowLag)
        val chkLockPos = view.findViewById<CheckBox>(R.id.chkLockPosition)
        val chkSoundBeep = view.findViewById<CheckBox>(R.id.chkSoundBeep)
        val chkVolumeKey = view.findViewById<CheckBox>(R.id.chkVolumeKey)

        val btnMinus = view.findViewById<TextView>(R.id.btnQuickMinus)
        val btnPlus = view.findViewById<TextView>(R.id.btnQuickPlus)

        // Bind Values
        seekPanelScale.progress = settingsManager.panelScalePercent
        tvPanelScale.text = "Thu phóng menu: ${settingsManager.panelScalePercent}%"

        seekDurasiTele.progress = (settingsManager.durasiTeleSeconds * 10).roundToInt()
        tvDurasiTele.text = String.format("Thời gian TELE: %.1f giây", settingsManager.durasiTeleSeconds)

        seekDurasiLag.progress = (settingsManager.durasiLagSeconds * 10).roundToInt()
        tvDurasiLag.text = String.format("Thời gian LAG DAME: %.1f giây", settingsManager.durasiLagSeconds)

        seekUkuranIkon.progress = settingsManager.iconSizeDp
        tvUkuranIkon.text = "Kích thước nút nổi: ${settingsManager.iconSizeDp} dp"

        seekOpacity.progress = settingsManager.opacityPercent
        tvOpacity.text = "Độ mờ nút nổi: ${settingsManager.opacityPercent}%"

        chkShowTele.isChecked = settingsManager.showTeleButton
        chkShowLag.isChecked = settingsManager.showLagButton
        chkLockPos.isChecked = settingsManager.isLockPosition
        chkSoundBeep.isChecked = settingsManager.isSoundBeep
        chkVolumeKey.isChecked = settingsManager.isVolumeControl

        btnClose.setOnClickListener { hideSettingsPanel() }
        btnMinimize.setOnClickListener { hideSettingsPanel() }

        // Setup Dragging & Resize Handlers
        if (panelHeader != null) {
            setupPanelDrag(panelHeader)
        }
        if (btnResizeHandle != null) {
            setupPanelResizeHandle(btnResizeHandle, seekPanelScale, tvPanelScale)
        }
        if (rootCard != null) {
            setupPinchToZoom(rootCard, seekPanelScale, tvPanelScale)
        }

        val updateScale = { newScale: Int ->
            val safeVal = newScale.coerceIn(60, 140)
            settingsManager.panelScalePercent = safeVal
            seekPanelScale.progress = safeVal
            tvPanelScale.text = "Thu phóng menu: $safeVal%"
            applyPanelScale(safeVal)
        }

        btnScale80?.setOnClickListener { updateScale(80) }
        btnScale100?.setOnClickListener { updateScale(100) }
        btnScale120?.setOnClickListener { updateScale(120) }

        // Scale / Resize Menu Slider
        seekPanelScale.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(seekBar: SeekBar?, progress: Int, fromUser: Boolean) {
                val value = progress.coerceAtLeast(60)
                tvPanelScale.text = "Thu phóng menu: $value%"
                settingsManager.panelScalePercent = value
                applyPanelScale(value)
            }
            override fun onStartTrackingTouch(seekBar: SeekBar?) {}
            override fun onStopTrackingTouch(seekBar: SeekBar?) {}
        })

        // Tele Duration Slider
        seekDurasiTele.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(seekBar: SeekBar?, progress: Int, fromUser: Boolean) {
                val value = (progress / 10.0f).coerceAtLeast(0.2f)
                tvDurasiTele.text = String.format("Thời gian TELE: %.1f giây", value)
                settingsManager.durasiTeleSeconds = value
            }
            override fun onStartTrackingTouch(seekBar: SeekBar?) {}
            override fun onStopTrackingTouch(seekBar: SeekBar?) {}
        })

        // Lag Dame Duration Slider
        seekDurasiLag.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(seekBar: SeekBar?, progress: Int, fromUser: Boolean) {
                val value = (progress / 10.0f).coerceAtLeast(0.3f)
                tvDurasiLag.text = String.format("Thời gian LAG DAME: %.1f giây", value)
                settingsManager.durasiLagSeconds = value
            }
            override fun onStartTrackingTouch(seekBar: SeekBar?) {}
            override fun onStopTrackingTouch(seekBar: SeekBar?) {}
        })

        // Icon Size Slider
        seekUkuranIkon.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(seekBar: SeekBar?, progress: Int, fromUser: Boolean) {
                val value = progress.coerceAtLeast(40)
                tvUkuranIkon.text = "Kích thước nút nổi: $value dp"
                settingsManager.iconSizeDp = value
                applyButtonSizeAndOpacity()
            }
            override fun onStartTrackingTouch(seekBar: SeekBar?) {}
            override fun onStopTrackingTouch(seekBar: SeekBar?) {}
        })

        // Opacity Slider
        seekOpacity.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(seekBar: SeekBar?, progress: Int, fromUser: Boolean) {
                val value = progress.coerceAtLeast(20)
                tvOpacity.text = "Độ mờ nút nổi: $value%"
                settingsManager.opacityPercent = value
                applyButtonSizeAndOpacity()
            }
            override fun onStartTrackingTouch(seekBar: SeekBar?) {}
            override fun onStopTrackingTouch(seekBar: SeekBar?) {}
        })

        chkShowTele.setOnCheckedChangeListener { _, isChecked ->
            settingsManager.showTeleButton = isChecked
            if (isChecked) {
                initTeleFloatingButton()
            } else {
                teleFloatingView?.let { windowManager.removeView(it) }
                teleFloatingView = null
            }
        }

        chkShowLag.setOnCheckedChangeListener { _, isChecked ->
            settingsManager.showLagButton = isChecked
            if (isChecked) {
                initLagFloatingButton()
            } else {
                lagFloatingView?.let { windowManager.removeView(it) }
                lagFloatingView = null
            }
        }

        chkLockPos.setOnCheckedChangeListener { _, isChecked ->
            settingsManager.isLockPosition = isChecked
        }
        chkSoundBeep.setOnCheckedChangeListener { _, isChecked ->
            settingsManager.isSoundBeep = isChecked
        }
        chkVolumeKey.setOnCheckedChangeListener { _, isChecked ->
            settingsManager.isVolumeControl = isChecked
        }

        btnMinus.setOnClickListener {
            var curr = settingsManager.durasiLagSeconds - 0.2f
            if (curr < 0.2f) curr = 0.2f
            settingsManager.durasiLagSeconds = curr
            seekDurasiLag.progress = (curr * 10).roundToInt()
            tvDurasiLag.text = String.format("Thời gian LAG DAME: %.1f giây", curr)
        }

        btnPlus.setOnClickListener {
            val curr = settingsManager.durasiLagSeconds + 0.2f
            settingsManager.durasiLagSeconds = curr
            seekDurasiLag.progress = (curr * 10).roundToInt()
            tvDurasiLag.text = String.format("Thời gian LAG DAME: %.1f giây", curr)
        }
    }

    fun showSettingsPanel() {
        if (isPanelShowing) return
        if (settingsPanelView == null) {
            initSettingsPanel()
        }
        try {
            setupPanelControls()
            applyPanelScale(settingsManager.panelScalePercent)
            if (settingsPanelView?.parent != null) {
                windowManager.removeView(settingsPanelView)
            }
            windowManager.addView(settingsPanelView, panelLayoutParams)
            isPanelShowing = true
        } catch (e: Exception) {
            Log.e(TAG, "Error showing settings panel: ${e.message}")
        }
    }

    fun hideSettingsPanel() {
        if (!isPanelShowing || settingsPanelView == null) return
        try {
            windowManager.removeView(settingsPanelView)
            isPanelShowing = false
        } catch (e: Exception) {
            Log.e(TAG, "Error hiding settings panel: ${e.message}")
        }
    }

    override fun onDestroy() {
        try {
            unregisterReceiver(teleStateReceiver)
            unregisterReceiver(lagStateReceiver)
        } catch (ignored: Exception) {
        }
        teleCountdownRunnable?.let { handler.removeCallbacks(it) }
        lagCountdownRunnable?.let { handler.removeCallbacks(it) }
        hideSettingsPanel()
        if (teleFloatingView != null) {
            try { windowManager.removeView(teleFloatingView) } catch (ignored: Exception) {}
            teleFloatingView = null
        }
        if (lagFloatingView != null) {
            try { windowManager.removeView(lagFloatingView) } catch (ignored: Exception) {}
            lagFloatingView = null
        }
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun dpToPx(dp: Int): Int {
        return TypedValue.applyDimension(
            TypedValue.COMPLEX_UNIT_DIP,
            dp.toFloat(),
            resources.displayMetrics
        ).toInt()
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                NOTIFICATION_CHANNEL_ID,
                "Overlay Service",
                NotificationManager.IMPORTANCE_MIN
            ).apply {
                setShowBadge(false)
                enableLights(false)
                enableVibration(false)
                setSound(null, null)
                lockscreenVisibility = Notification.VISIBILITY_SECRET
            }
            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(channel)
        }
    }

    private fun createNotification(): Notification {
        val pendingIntent = PendingIntent.getActivity(
            this,
            0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )

        return NotificationCompat.Builder(this, NOTIFICATION_CHANNEL_ID)
            .setContentTitle("NOVA FAKE LAG")
            .setContentText("Nút nổi sẵn sàng.")
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setPriority(NotificationCompat.PRIORITY_MIN)
            .setVisibility(NotificationCompat.VISIBILITY_SECRET)
            .setCategory(NotificationCompat.CATEGORY_SERVICE)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .setSilent(true)
            .build()
    }

    companion object {
        private const val TAG = "FloatingOverlayService"
        private const val NOTIFICATION_CHANNEL_ID = "fakelag_overlay_channel"
        private const val NOTIFICATION_ID = 1002

        const val ACTION_START = "com.fakelag.android.action.START_OVERLAY"
        const val ACTION_STOP = "com.fakelag.android.action.STOP_OVERLAY"
        const val ACTION_SHOW_PANEL = "com.fakelag.android.action.SHOW_PANEL"

        fun start(context: Context, showPanelImmediately: Boolean = false) {
            val intent = Intent(context, FloatingOverlayService::class.java).apply {
                action = if (showPanelImmediately) ACTION_SHOW_PANEL else ACTION_START
            }
            try {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    context.startForegroundService(intent)
                } else {
                    context.startService(intent)
                }
            } catch (e: Exception) {
                Log.e(TAG, "Start overlay failed: ${e.message}")
                context.startService(intent)
            }
        }

        fun showPanel(context: Context) {
            val intent = Intent(context, FloatingOverlayService::class.java).apply {
                action = ACTION_SHOW_PANEL
            }
            context.startService(intent)
        }

        fun stop(context: Context) {
            val intent = Intent(context, FloatingOverlayService::class.java).apply {
                action = ACTION_STOP
            }
            context.stopService(intent)
        }
    }
}
