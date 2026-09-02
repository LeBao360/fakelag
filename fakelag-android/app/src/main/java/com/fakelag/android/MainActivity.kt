package com.fakelag.android

import android.app.Activity
import android.content.Intent
import android.content.SharedPreferences
import android.net.Uri
import android.net.VpnService
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.view.KeyEvent
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import com.fakelag.android.databinding.ActivityMainBinding
import com.fakelag.android.service.FloatingOverlayService
import com.fakelag.android.service.LagVpnService
import com.fakelag.android.utils.SettingsManager

class MainActivity : AppCompatActivity(), SharedPreferences.OnSharedPreferenceChangeListener {

    private lateinit var binding: ActivityMainBinding
    private lateinit var settingsManager: SettingsManager

    private val gameModes = arrayOf("FF THƯỜNG", "FF TỐC ĐỘ", "MLBB ULTRA", "PUBGM TICK", "TẤT CẢ UDP")
    private var currentGameModeIndex = 0

    private val vpnPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode == Activity.RESULT_OK) {
            startServices()
        } else {
            Toast.makeText(this, "Cần cấp quyền VPN để FakeLag can thiệp độ trễ mạng!", Toast.LENGTH_LONG).show()
        }
    }

    private val overlayPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) {
        if (checkOverlayPermission()) {
            checkAndStartVpn()
        } else {
            Toast.makeText(this, "Vui lòng gạt bật 'Hiển thị trên ứng dụng khác' cho FakeLag!", Toast.LENGTH_LONG).show()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        settingsManager = SettingsManager.getInstance(this)

        // Check if user is authenticated with a valid key
        if (!settingsManager.isKeyActivated || settingsManager.savedLicenseKey.isBlank()) {
            val intent = Intent(this, LoginActivity::class.java)
            startActivity(intent)
            finish()
            return
        }

        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        settingsManager.registerListener(this)

        setupUI()
    }

    private fun setupUI() {
        updateDurasiText()
        updateLicenseText()

        binding.btnLogoutKey.setOnClickListener {
            showLogoutConfirmDialog()
        }

        val savedMode = settingsManager.gameMode
        val idx = gameModes.indexOf(savedMode)
        if (idx != -1) currentGameModeIndex = idx
        binding.btnFfNormal.text = gameModes[currentGameModeIndex]

        binding.btnStart.setOnClickListener {
            handleStartClicked()
        }

        binding.btnStop.setOnClickListener {
            handleStopClicked()
        }

        binding.btnFfNormal.setOnClickListener {
            currentGameModeIndex = (currentGameModeIndex + 1) % gameModes.size
            val selected = gameModes[currentGameModeIndex]
            settingsManager.gameMode = selected
            binding.btnFfNormal.text = selected
            Toast.makeText(this, "Chế độ: $selected", Toast.LENGTH_SHORT).show()
        }

        binding.cardPreview.setOnClickListener {
            if (!checkOverlayPermission()) {
                requestOverlayPermission()
            } else {
                FloatingOverlayService.start(this, showPanelImmediately = true)
                Toast.makeText(this, "Đã mở thanh phím nổi!", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun updateDurasiText() {
        binding.tvDurasiLagMain.text = String.format(
            "⚡ TELE: %.1fs  |  🎮 LAG DAME: %.1fs",
            settingsManager.durasiTeleSeconds,
            settingsManager.durasiLagSeconds
        )
    }

    private fun updateLicenseText() {
        val expiry = settingsManager.licenseExpiry
        val text = if (expiry.isNotBlank()) {
            "VIP: $expiry"
        } else {
            "License: Đã kích hoạt ✔"
        }
        binding.tvLicenseStatusMain.text = text
    }

    private fun showLogoutConfirmDialog() {
        AlertDialog.Builder(this)
            .setTitle("ĐỔI LICENSE KEY")
            .setMessage("Bạn có muốn đăng xuất Key hiện tại và nhập Key mới không?")
            .setPositiveButton("Đổi Key") { _, _ ->
                FloatingOverlayService.stop(this)
                LagVpnService.stop(this)
                settingsManager.isServiceRunning = false
                settingsManager.clearLogin()
                Toast.makeText(this, "Đã đăng xuất Key!", Toast.LENGTH_SHORT).show()
                val intent = Intent(this, LoginActivity::class.java)
                startActivity(intent)
                finish()
            }
            .setNegativeButton("Hủy", null)
            .show()
    }

    private fun handleStartClicked() {
        if (!checkOverlayPermission()) {
            requestOverlayPermission()
            return
        }
        checkAndStartVpn()
    }

    private fun checkOverlayPermission(): Boolean {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            Settings.canDrawOverlays(this)
        } else {
            true
        }
    }

    private fun requestOverlayPermission() {
        AlertDialog.Builder(this)
            .setTitle(R.string.permission_overlay_title)
            .setMessage(R.string.permission_overlay_desc)
            .setPositiveButton("Đi đến Cài đặt") { _, _ ->
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                    val intent = Intent(
                        Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                        Uri.parse("package:$packageName")
                    )
                    overlayPermissionLauncher.launch(intent)
                }
            }
            .setNegativeButton("Hủy", null)
            .show()
    }

    private fun checkAndStartVpn() {
        val vpnIntent = VpnService.prepare(this)
        if (vpnIntent != null) {
            vpnPermissionLauncher.launch(vpnIntent)
        } else {
            startServices()
        }
    }

    private fun startServices() {
        FloatingOverlayService.start(this, showPanelImmediately = true)
        LagVpnService.start(this)
        settingsManager.isServiceRunning = true
        Toast.makeText(this, "FakeLag đã bật!", Toast.LENGTH_SHORT).show()
    }

    private fun handleStopClicked() {
        FloatingOverlayService.stop(this)
        LagVpnService.stop(this)
        settingsManager.isServiceRunning = false
        Toast.makeText(this, "FakeLag đã dừng", Toast.LENGTH_SHORT).show()
    }

    override fun onKeyDown(keyCode: Int, event: KeyEvent?): Boolean {
        if (settingsManager.isVolumeControl) {
            if (keyCode == KeyEvent.KEYCODE_VOLUME_UP || keyCode == KeyEvent.KEYCODE_VOLUME_DOWN) {
                LagVpnService.toggleLag(this)
                return true
            }
        }
        return super.onKeyDown(keyCode, event)
    }

    override fun onSharedPreferenceChanged(sharedPreferences: SharedPreferences?, key: String?) {
        if (key == SettingsManager.KEY_DURASI_LAG || key == SettingsManager.KEY_DURASI_TELE) {
            runOnUiThread { updateDurasiText() }
        }
    }

    override fun onDestroy() {
        settingsManager.unregisterListener(this)
        super.onDestroy()
    }
}
