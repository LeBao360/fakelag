package com.fakelag.android.utils

import android.content.Context
import android.content.SharedPreferences

class SettingsManager(context: Context) {

    private val prefs: SharedPreferences =
        context.applicationContext.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)

    var iconSizeDp: Int
        get() = prefs.getInt(KEY_ICON_SIZE, 58)
        set(value) = prefs.edit().putInt(KEY_ICON_SIZE, value).apply()

    var durasiLagSeconds: Float
        get() = prefs.getFloat(KEY_DURASI_LAG, 1.5f)
        set(value) = prefs.edit().putFloat(KEY_DURASI_LAG, value).apply()

    var durasiTeleSeconds: Float
        get() = prefs.getFloat(KEY_DURASI_TELE, 0.8f)
        set(value) = prefs.edit().putFloat(KEY_DURASI_TELE, value).apply()

    var panelScalePercent: Int
        get() = prefs.getInt(KEY_PANEL_SCALE, 100)
        set(value) = prefs.edit().putInt(KEY_PANEL_SCALE, value).apply()

    var intervalSeconds: Float
        get() = prefs.getFloat(KEY_INTERVAL, 1.0f)
        set(value) = prefs.edit().putFloat(KEY_INTERVAL, value).apply()

    var opacityPercent: Int
        get() = prefs.getInt(KEY_OPACITY, 90)
        set(value) = prefs.edit().putInt(KEY_OPACITY, value).apply()

    var isLockPosition: Boolean
        get() = prefs.getBoolean(KEY_LOCK_POS, false)
        set(value) = prefs.edit().putBoolean(KEY_LOCK_POS, value).apply()

    var isSoundBeep: Boolean
        get() = prefs.getBoolean(KEY_SOUND_BEEP, true)
        set(value) = prefs.edit().putBoolean(KEY_SOUND_BEEP, value).apply()

    var isVolumeControl: Boolean
        get() = prefs.getBoolean(KEY_VOLUME_CTRL, false)
        set(value) = prefs.edit().putBoolean(KEY_VOLUME_CTRL, value).apply()

    var isAutoLag: Boolean
        get() = prefs.getBoolean(KEY_AUTO_LAG, false)
        set(value) = prefs.edit().putBoolean(KEY_AUTO_LAG, value).apply()

    var gameMode: String
        get() = prefs.getString(KEY_GAME_MODE, "FF THƯỜNG") ?: "FF THƯỜNG"
        set(value) = prefs.edit().putString(KEY_GAME_MODE, value).apply()

    var isServiceRunning: Boolean
        get() = prefs.getBoolean(KEY_SERVICE_RUNNING, false)
        set(value) = prefs.edit().putBoolean(KEY_SERVICE_RUNNING, value).apply()

    var lastTeleX: Int
        get() = prefs.getInt(KEY_TELE_X, -1)
        set(value) = prefs.edit().putInt(KEY_TELE_X, value).apply()

    var lastTeleY: Int
        get() = prefs.getInt(KEY_TELE_Y, -1)
        set(value) = prefs.edit().putInt(KEY_TELE_Y, value).apply()

    var lastLagX: Int
        get() = prefs.getInt(KEY_LAG_X, -1)
        set(value) = prefs.edit().putInt(KEY_LAG_X, value).apply()

    var lastLagY: Int
        get() = prefs.getInt(KEY_LAG_Y, -1)
        set(value) = prefs.edit().putInt(KEY_LAG_Y, value).apply()

    var lastPanelX: Int
        get() = prefs.getInt(KEY_PANEL_X, -1)
        set(value) = prefs.edit().putInt(KEY_PANEL_X, value).apply()

    var lastPanelY: Int
        get() = prefs.getInt(KEY_PANEL_Y, -1)
        set(value) = prefs.edit().putInt(KEY_PANEL_Y, value).apply()

    var showTeleButton: Boolean
        get() = prefs.getBoolean(KEY_SHOW_TELE, true)
        set(value) = prefs.edit().putBoolean(KEY_SHOW_TELE, value).apply()

    var showLagButton: Boolean
        get() = prefs.getBoolean(KEY_SHOW_LAG, true)
        set(value) = prefs.edit().putBoolean(KEY_SHOW_LAG, true).apply()

    var savedLicenseKey: String
        get() = prefs.getString(KEY_LICENSE_KEY, "") ?: ""
        set(value) = prefs.edit().putString(KEY_LICENSE_KEY, value).apply()

    var licenseExpiry: String
        get() = prefs.getString(KEY_LICENSE_EXPIRY, "") ?: ""
        set(value) = prefs.edit().putString(KEY_LICENSE_EXPIRY, value).apply()

    var isKeyActivated: Boolean
        get() = prefs.getBoolean(KEY_KEY_ACTIVATED, false)
        set(value) = prefs.edit().putBoolean(KEY_KEY_ACTIVATED, value).apply()

    fun clearLogin() {
        prefs.edit()
            .remove(KEY_LICENSE_KEY)
            .remove(KEY_LICENSE_EXPIRY)
            .putBoolean(KEY_KEY_ACTIVATED, false)
            .apply()
    }

    fun registerListener(listener: SharedPreferences.OnSharedPreferenceChangeListener) {
        prefs.registerOnSharedPreferenceChangeListener(listener)
    }

    fun unregisterListener(listener: SharedPreferences.OnSharedPreferenceChangeListener) {
        prefs.unregisterOnSharedPreferenceChangeListener(listener)
    }

    companion object {
        private const val PREF_NAME = "fakelag_prefs"
        const val KEY_ICON_SIZE = "key_icon_size"
        const val KEY_DURASI_LAG = "key_durasi_lag"
        const val KEY_DURASI_TELE = "key_durasi_tele"
        const val KEY_PANEL_SCALE = "key_panel_scale"
        const val KEY_INTERVAL = "key_interval"
        const val KEY_OPACITY = "key_opacity"
        const val KEY_LOCK_POS = "key_lock_pos"
        const val KEY_SOUND_BEEP = "key_sound_beep"
        const val KEY_VOLUME_CTRL = "key_volume_ctrl"
        const val KEY_AUTO_LAG = "key_auto_lag"
        const val KEY_GAME_MODE = "key_game_mode"
        const val KEY_SERVICE_RUNNING = "key_service_running"
        const val KEY_TELE_X = "key_tele_x"
        const val KEY_TELE_Y = "key_tele_y"
        const val KEY_LAG_X = "key_lag_x"
        const val KEY_LAG_Y = "key_lag_y"
        const val KEY_PANEL_X = "key_panel_x"
        const val KEY_PANEL_Y = "key_panel_y"
        const val KEY_SHOW_TELE = "key_show_tele"
        const val KEY_SHOW_LAG = "key_show_lag"
        const val KEY_LICENSE_KEY = "key_license_key"
        const val KEY_LICENSE_EXPIRY = "key_license_expiry"
        const val KEY_KEY_ACTIVATED = "key_key_activated"

        @Volatile
        private var instance: SettingsManager? = null

        fun getInstance(context: Context): SettingsManager {
            return instance ?: synchronized(this) {
                instance ?: SettingsManager(context).also { instance = it }
            }
        }
    }
}
