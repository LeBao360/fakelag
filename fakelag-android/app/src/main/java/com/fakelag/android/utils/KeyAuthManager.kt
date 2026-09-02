package com.fakelag.android.utils

import android.annotation.SuppressLint
import android.content.Context
import android.os.Build
import android.provider.Settings
import android.util.Base64
import android.util.Log
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder
import java.security.MessageDigest
import java.text.SimpleDateFormat
import java.util.*
import javax.crypto.Cipher
import javax.crypto.spec.IvParameterSpec
import javax.crypto.spec.SecretKeySpec

object KeyAuthManager {

    private const val TAG = "KeyAuthManager"

    private fun decodeObfuscated(encoded: IntArray, key: Int = 0x5A): String {
        val chars = CharArray(encoded.size)
        for (i in encoded.indices) {
            chars[i] = (encoded[i] xor key).toChar()
        }
        return String(chars)
    }

    // Obfuscated constants to protect from strings extraction & decompilation
    val API_URL: String by lazy {
        decodeObfuscated(intArrayOf(
            50, 46, 46, 42, 41, 96, 117, 117, 41, 57, 40, 51, 42, 46, 116, 61, 53, 53, 61, 54, 63, 116, 57, 53, 55, 117, 55, 59, 57, 40, 53, 41, 117, 41, 117, 27, 17, 60, 35, 57, 56, 32, 35, 29, 14, 5, 11, 99, 63, 9, 12, 11, 55, 98, 20, 40, 47, 9, 14, 10, 119, 30, 15, 59, 49, 105, 62, 44, 14, 22, 104, 45, 42, 47, 16, 56, 63, 24, 40, 49, 16, 24, 111, 21, 99, 29, 98, 19, 56, 19, 18, 17, 9, 10, 55, 13, 14, 42, 41, 45, 29, 99, 98, 27, 50, 109, 57, 56, 27, 117, 63, 34, 63, 57
        ))
    }

    val ADMIN_PASSWORD: String by lazy {
        decodeObfuscated(intArrayOf(22, 63, 56, 59, 53, 26))
    }

    val MASTER_PASSWORD: String by lazy {
        decodeObfuscated(intArrayOf(22, 63, 56, 59, 53, 26))
    }

    private val IV_STRING: String by lazy {
        decodeObfuscated(intArrayOf(107, 104, 105, 110, 111, 108, 109, 98, 99, 106, 107, 104, 105, 110, 111, 108))
    }

    data class KeyInfo(
        val key: String,
        val expiry: String,
        val isValid: Boolean,
        val message: String
    )

    // ==================== 1. AES CRYPTOGRAPHY ====================
    private val aesKeySpec: SecretKeySpec by lazy {
        val sha256 = MessageDigest.getInstance("SHA-256")
        val keyBytes = sha256.digest(MASTER_PASSWORD.toByteArray(Charsets.UTF_8))
        SecretKeySpec(keyBytes, "AES")
    }

    private val ivSpec: IvParameterSpec by lazy {
        val ivBytes = IV_STRING.toByteArray(Charsets.UTF_8)
        IvParameterSpec(ivBytes)
    }

    fun encrypt(raw: String): String {
        return try {
            val cipher = Cipher.getInstance("AES/CBC/PKCS5Padding")
            cipher.init(Cipher.ENCRYPT_MODE, aesKeySpec, ivSpec)
            val encryptedBytes = cipher.doFinal(raw.toByteArray(Charsets.UTF_8))
            Base64.encodeToString(encryptedBytes, Base64.URL_SAFE or Base64.NO_WRAP)
        } catch (e: Exception) {
            Log.e(TAG, "Encryption error: ${e.message}")
            ""
        }
    }

    fun decrypt(encBase64: String): String {
        return try {
            val cipher = Cipher.getInstance("AES/CBC/PKCS5Padding")
            cipher.init(Cipher.DECRYPT_MODE, aesKeySpec, ivSpec)
            val decodedBytes = Base64.decode(encBase64, Base64.URL_SAFE or Base64.NO_WRAP)
            val decryptedBytes = cipher.doFinal(decodedBytes)
            String(decryptedBytes, Charsets.UTF_8)
        } catch (e: Exception) {
            Log.e(TAG, "Decryption error: ${e.message}")
            "Decryption Error"
        }
    }

    // ==================== 2. HWID GENERATION ====================
    @SuppressLint("HardwareIds")
    fun getHWID(context: Context): String {
        return try {
            val androidId = Settings.Secure.getString(context.contentResolver, Settings.Secure.ANDROID_ID) ?: ""
            val raw = if (androidId.isNotBlank()) {
                androidId
            } else {
                "${Build.BOARD}_${Build.BRAND}_${Build.DEVICE}_${Build.MODEL}"
            }
            val md5 = MessageDigest.getInstance("MD5").digest(raw.toByteArray(Charsets.UTF_8))
            md5.joinToString("") { "%02X".format(it) }.take(16)
        } catch (e: Exception) {
            "UNKNOWN_HWID"
        }
    }

    // ==================== 3. VERIFY KEY API ====================
    fun verifyKey(context: Context, rawKey: String): Result<KeyInfo> {
        val cleanKey = rawKey.trim()
        if (cleanKey.isEmpty()) {
            return Result.failure(Exception("Vui lòng nhập License Key!"))
        }

        // Master admin password bypass
        if (cleanKey == MASTER_PASSWORD || cleanKey.equals("LEBAO-VIP", ignoreCase = true) || cleanKey.equals("ADMIN-KEY", ignoreCase = true)) {
            val keyInfo = KeyInfo(cleanKey, "Vĩnh viễn (Admin/Master)", true, "Xác thực Master Key thành công ✔")
            return Result.success(keyInfo)
        }

        val encKey = encrypt(cleanKey)
        if (encKey.isEmpty()) {
            return Result.failure(Exception("Lỗi mã hóa bảo mật Key."))
        }

        val hwid = getHWID(context)

        return try {
            val queryParams = "admin_pass=${URLEncoder.encode(ADMIN_PASSWORD, "UTF-8")}" +
                    "&action=check_info" +
                    "&enc_key=${URLEncoder.encode(encKey, "UTF-8")}" +
                    "&hwid=${URLEncoder.encode(hwid, "UTF-8")}"

            val responseBody = executeHttpRequestWithRedirects("$API_URL?$queryParams")
            val json = JSONObject(responseBody)

            val status = json.optString("status")
            val rawMessage = json.optString("message", "")

            if (status.equals("success", ignoreCase = true)) {
                var expiryDisplay = "Vĩnh viễn (LIFETIME)"
                try {
                    val infoObj = JSONObject(rawMessage)
                    val expiry = infoObj.optString("expiry", "LIFETIME")
                    expiryDisplay = formatExpiryDate(expiry)
                } catch (_: Exception) {
                    if (rawMessage.isNotBlank() && !rawMessage.startsWith("{")) {
                        expiryDisplay = formatExpiryDate(rawMessage)
                    }
                }

                val keyInfo = KeyInfo(cleanKey, expiryDisplay, true, "Xác thực Key thành công ✔")
                Result.success(keyInfo)
            } else {
                val errorMsg = if (rawMessage.isNotBlank()) rawMessage else "Key không hợp lệ hoặc đã hết hạn!"
                Result.failure(Exception(errorMsg))
            }
        } catch (e: Exception) {
            Log.e(TAG, "Verify request error: ${e.message}")
            Result.failure(Exception("Lỗi kết nối máy chủ: ${e.localizedMessage ?: "Vui lòng thử lại sau"}"))
        }
    }

    private fun formatExpiryDate(expiry: String): String {
        return when {
            expiry.equals("LIFETIME", ignoreCase = true) || expiry.equals("vv", ignoreCase = true) -> {
                "Vĩnh viễn (LIFETIME)"
            }
            expiry.contains("-") -> {
                try {
                    val cleanStr = expiry.replace("Z", "+00:00")
                    val isoFormat = SimpleDateFormat("yyyy-MM-dd", Locale.getDefault())
                    val parsed = isoFormat.parse(cleanStr.substring(0, 10))
                    val displayFormat = SimpleDateFormat("dd/MM/yyyy", Locale.getDefault())
                    if (parsed != null) "HSD: ${displayFormat.format(parsed)}" else expiry
                } catch (_: Exception) {
                    expiry
                }
            }
            else -> expiry
        }
    }

    private fun executeHttpRequestWithRedirects(initialUrl: String, maxRedirects: Int = 6): String {
        var currentUrl = initialUrl
        var redirectsCount = 0

        while (redirectsCount < maxRedirects) {
            val url = URL(currentUrl)
            val conn = (url.openConnection() as HttpURLConnection).apply {
                requestMethod = "GET"
                connectTimeout = 15000
                readTimeout = 15000
                instanceFollowRedirects = false
                setRequestProperty("User-Agent", "FakeLag-Android-Client/1.0")
            }

            val status = conn.responseCode
            if (status == HttpURLConnection.HTTP_MOVED_TEMP ||
                status == HttpURLConnection.HTTP_MOVED_PERM ||
                status == HttpURLConnection.HTTP_SEE_OTHER ||
                status == 307 || status == 308
            ) {
                val newUrl = conn.getHeaderField("Location")
                conn.disconnect()
                if (newUrl == null) throw Exception("Chuyển hướng thất bại (Location rỗng)")
                currentUrl = newUrl
                redirectsCount++
            } else if (status in 200..299) {
                val reader = BufferedReader(InputStreamReader(conn.inputStream))
                val sb = StringBuilder()
                var line: String?
                while (reader.readLine().also { line = it } != null) {
                    sb.append(line)
                }
                reader.close()
                conn.disconnect()
                return sb.toString()
            } else {
                val errorStream = conn.errorStream
                val errMsg = if (errorStream != null) {
                    BufferedReader(InputStreamReader(errorStream)).use { it.readText() }
                } else {
                    "HTTP Status: $status"
                }
                conn.disconnect()
                throw Exception(errMsg)
            }
        }
        throw Exception("Quá số lần chuyển hướng tối đa")
    }
}
