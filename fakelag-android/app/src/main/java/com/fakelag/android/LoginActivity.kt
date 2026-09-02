package com.fakelag.android

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.fakelag.android.databinding.ActivityLoginBinding
import com.fakelag.android.utils.KeyAuthManager
import com.fakelag.android.utils.SettingsManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class LoginActivity : AppCompatActivity() {

    private lateinit var binding: ActivityLoginBinding
    private lateinit var settingsManager: SettingsManager
    private var hwid: String = ""

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityLoginBinding.inflate(layoutInflater)
        setContentView(binding.root)

        settingsManager = SettingsManager.getInstance(this)
        hwid = KeyAuthManager.getHWID(this)

        setupUI()
        checkAutoLogin()
    }

    private fun setupUI() {
        binding.tvHwidValue.text = hwid

        // Pre-fill previously saved key if available
        if (settingsManager.savedLicenseKey.isNotBlank()) {
            binding.etLicenseKey.setText(settingsManager.savedLicenseKey)
        }

        // Copy HWID
        binding.btnCopyHwid.setOnClickListener {
            val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
            val clip = ClipData.newPlainText("HWID", hwid)
            clipboard.setPrimaryClip(clip)
            Toast.makeText(this, "Đã sao chép HWID: $hwid", Toast.LENGTH_SHORT).show()
        }

        // Paste Key
        binding.btnPasteKey.setOnClickListener {
            val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
            val item = clipboard.primaryClip?.getItemAt(0)
            val pastedText = item?.text?.toString()?.trim() ?: ""
            if (pastedText.isNotBlank()) {
                binding.etLicenseKey.setText(pastedText)
                Toast.makeText(this, "Đã dán Key!", Toast.LENGTH_SHORT).show()
            } else {
                Toast.makeText(this, "Bộ nhớ tạm không có dữ liệu!", Toast.LENGTH_SHORT).show()
            }
        }

        // Verify Key Button
        binding.btnLoginVerify.setOnClickListener {
            val key = binding.etLicenseKey.text.toString().trim()
            if (key.isBlank()) {
                showStatus("Vui lòng nhập License Key!", isError = true)
                return@setOnClickListener
            }
            performKeyVerification(key)
        }

        // Contact Admin
        binding.btnContactAdmin.setOnClickListener {
            showContactDialog()
        }
    }

    private fun checkAutoLogin() {
        val savedKey = settingsManager.savedLicenseKey
        if (settingsManager.isKeyActivated && savedKey.isNotBlank()) {
            // User was previously verified, quickly re-validate in background
            performKeyVerification(savedKey, isAutoLogin = true)
        }
    }

    private fun performKeyVerification(key: String, isAutoLogin: Boolean = false) {
        setLoading(true)
        showStatus("⏳ Đang kết nối máy chủ xác thực...", isError = false, isNeutral = true)

        lifecycleScope.launch(Dispatchers.IO) {
            val result = KeyAuthManager.verifyKey(this@LoginActivity, key)

            withContext(Dispatchers.Main) {
                setLoading(false)
                result.onSuccess { info ->
                    settingsManager.savedLicenseKey = info.key
                    settingsManager.licenseExpiry = info.expiry
                    settingsManager.isKeyActivated = true

                    showStatus("✔ ${info.message}\n${info.expiry}", isError = false)
                    Toast.makeText(this@LoginActivity, "Đăng nhập thành công!", Toast.LENGTH_SHORT).show()

                    binding.root.postDelayed({
                        startMainActivity()
                    }, 600)
                }.onFailure { error ->
                    settingsManager.isKeyActivated = false
                    val errorMsg = error.message ?: "Key không hợp lệ hoặc lỗi kết nối!"
                    showStatus("✘ $errorMsg", isError = true)
                    if (!isAutoLogin) {
                        Toast.makeText(this@LoginActivity, errorMsg, Toast.LENGTH_LONG).show()
                    }
                }
            }
        }
    }

    private fun startMainActivity() {
        val intent = Intent(this, MainActivity::class.java)
        startActivity(intent)
        finish()
    }

    private fun setLoading(isLoading: Boolean) {
        binding.btnLoginVerify.isEnabled = !isLoading
        binding.pbLoginLoading.visibility = if (isLoading) View.VISIBLE else View.GONE
        binding.btnLoginVerify.text = if (isLoading) "ĐANG XÁC THỰC..." else "🚀  XÁC THỰC LICENSE KEY"
    }

    private fun showStatus(message: String, isError: Boolean = false, isNeutral: Boolean = false) {
        binding.tvLoginStatus.text = message
        val color = when {
            isNeutral -> ContextCompat.getColor(this, R.color.neon_blue)
            isError -> ContextCompat.getColor(this, R.color.neon_red)
            else -> ContextCompat.getColor(this, R.color.neon_green)
        }
        binding.tvLoginStatus.setTextColor(color)
    }

    private fun showContactDialog() {
        // Automatically copy HWID to clipboard
        val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        val clip = ClipData.newPlainText("HWID", hwid)
        clipboard.setPrimaryClip(clip)
        Toast.makeText(this, "Đã sao chép HWID: $hwid\nĐang mở Discord...", Toast.LENGTH_SHORT).show()

        try {
            val intent = Intent(Intent.ACTION_VIEW, Uri.parse("https://discord.gg/anhemnova"))
            startActivity(intent)
        } catch (e: Exception) {
            Toast.makeText(this, "Không thể mở trình duyệt: ${e.message}", Toast.LENGTH_SHORT).show()
        }
    }
}
