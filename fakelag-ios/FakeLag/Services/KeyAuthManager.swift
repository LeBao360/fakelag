import Foundation
import CommonCrypto
import UIKit

public struct KeyInfo {
    public let key: String
    public let expiry: String
    public let isValid: Bool
    public let message: String
}

public final class KeyAuthManager {
    public static let shared = KeyAuthManager()

    private static func decodeObfuscated(_ encoded: [UInt8], key: UInt8 = 0x5A) -> String {
        let chars = encoded.map { Character(UnicodeScalar($0 ^ key)) }
        return String(chars)
    }

    public static var apiURL: String {
        decodeObfuscated([
            50, 46, 46, 42, 41, 96, 117, 117, 41, 57, 40, 51, 42, 46, 116, 61, 53, 53, 61, 54, 63, 116, 57, 53, 55, 117, 55, 59, 57, 40, 53, 41, 117, 41, 117, 27, 17, 60, 35, 57, 56, 32, 35, 29, 14, 5, 11, 99, 63, 9, 12, 11, 55, 98, 20, 40, 47, 9, 14, 10, 119, 30, 15, 59, 49, 105, 62, 44, 14, 22, 104, 45, 42, 47, 16, 56, 63, 24, 40, 49, 16, 24, 111, 21, 99, 29, 98, 19, 56, 19, 18, 17, 9, 10, 55, 13, 14, 42, 41, 45, 29, 99, 98, 27, 50, 109, 57, 56, 27, 117, 63, 34, 63, 57
        ])
    }

    public static var adminPassword: String {
        decodeObfuscated([22, 63, 56, 59, 53, 26])
    }

    public static var masterPassword: String {
        decodeObfuscated([22, 63, 56, 59, 53, 26])
    }

    private static var ivString: String {
        decodeObfuscated([107, 104, 105, 110, 111, 108, 109, 98, 99, 106, 107, 104, 105, 110, 111, 108])
    }

    private init() {}

    // MARK: - AES Cryptography (CBC / PKCS7)
    public func encrypt(raw: String) -> String {
        guard let data = raw.data(using: .utf8) else { return "" }
        guard let keyData = sha256(KeyAuthManager.masterPassword) else { return "" }
        guard let ivData = KeyAuthManager.ivString.data(using: .utf8) else { return "" }

        let bufferSize = data.count + kCCBlockSizeAES128
        var buffer = Data(count: bufferSize)
        var numBytesEncrypted: size_t = 0

        let status = buffer.withUnsafeMutableBytes { bufferBytes in
            data.withUnsafeBytes { dataBytes in
                ivData.withUnsafeBytes { ivBytes in
                    keyData.withUnsafeBytes { keyBytes in
                        CCCrypt(
                            CCOperation(kCCEncrypt),
                            CCAlgorithm(kCCAlgorithmAES),
                            CCOptions(kCCOptionPKCS7Padding),
                            keyBytes.baseAddress, kCCKeySizeAES256,
                            ivBytes.baseAddress,
                            dataBytes.baseAddress, data.count,
                            bufferBytes.baseAddress, bufferSize,
                            &numBytesEncrypted
                        )
                    }
                }
            }
        }

        if status == kCCSuccess {
            buffer.count = numBytesEncrypted
            // Convert to URL-safe Base64
            var base64 = buffer.base64EncodedString()
            base64 = base64.replacingOccurrences(of: "+", with: "-")
            base64 = base64.replacingOccurrences(of: "/", with: "_")
            base64 = base64.trimmingCharacters(in: CharacterSet(charactersIn: "="))
            return base64
        }
        return ""
    }

    public func decrypt(encBase64: String) -> String {
        var base64 = encBase64.replacingOccurrences(of: "-", with: "+").replacingOccurrences(of: "_", with: "/")
        while base64.count % 4 != 0 {
            base64.append("=")
        }
        guard let data = Data(base64Encoded: base64) else { return "Decryption Error" }
        guard let keyData = sha256(KeyAuthManager.masterPassword) else { return "Decryption Error" }
        guard let ivData = KeyAuthManager.ivString.data(using: .utf8) else { return "Decryption Error" }

        let bufferSize = data.count + kCCBlockSizeAES128
        var buffer = Data(count: bufferSize)
        var numBytesDecrypted: size_t = 0

        let status = buffer.withUnsafeMutableBytes { bufferBytes in
            data.withUnsafeBytes { dataBytes in
                ivData.withUnsafeBytes { ivBytes in
                    keyData.withUnsafeBytes { keyBytes in
                        CCCrypt(
                            CCOperation(kCCDecrypt),
                            CCAlgorithm(kCCAlgorithmAES),
                            CCOptions(kCCOptionPKCS7Padding),
                            keyBytes.baseAddress, kCCKeySizeAES256,
                            ivBytes.baseAddress,
                            dataBytes.baseAddress, data.count,
                            bufferBytes.baseAddress, bufferSize,
                            &numBytesDecrypted
                        )
                    }
                }
            }
        }

        if status == kCCSuccess {
            buffer.count = numBytesDecrypted
            return String(data: buffer, encoding: .utf8) ?? "Decryption Error"
        }
        return "Decryption Error"
    }

    private func sha256(_ string: String) -> Data? {
        guard let data = string.data(using: .utf8) else { return nil }
        var hash = [UInt8](repeating: 0, count: Int(CC_SHA256_DIGEST_LENGTH))
        data.withUnsafeBytes {
            _ = CC_SHA256($0.baseAddress, CC_LONG(data.count), &hash)
        }
        return Data(hash)
    }

    // MARK: - HWID Generation
    public func getHWID() -> String {
        let vendorId = UIDevice.current.identifierForVendor?.uuidString ?? "IOS_DEVICE"
        guard let data = vendorId.data(using: .utf8) else { return "UNKNOWN_HWID" }
        var digest = [UInt8](repeating: 0, count: Int(CC_MD5_DIGEST_LENGTH))
        data.withUnsafeBytes {
            _ = CC_MD5($0.baseAddress, CC_LONG(data.count), &digest)
        }
        let hex = digest.map { String(format: "%02X", $0) }.joined()
        return String(hex.prefix(16))
    }

    // MARK: - API Key Verification
    public func verifyKey(rawKey: String, completion: @escaping (Result<KeyInfo, Error>) -> Void) {
        let cleanKey = rawKey.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !cleanKey.isEmpty else {
            completion(.failure(NSError(domain: "FakeLag", code: 400, userInfo: [NSLocalizedDescriptionKey: "Vui lòng nhập License Key!"])))
            return
        }

        // Master bypass
        if cleanKey == KeyAuthManager.masterPassword || cleanKey.caseInsensitiveCompare("LEBAO-VIP") == .orderedSame {
            let info = KeyInfo(key: cleanKey, expiry: "Vĩnh viễn (Admin/Master)", isValid: true, message: "Xác thực Master Key thành công ✔")
            completion(.success(info))
            return
        }

        let encKey = encrypt(raw: cleanKey)
        guard !encKey.isEmpty else {
            completion(.failure(NSError(domain: "FakeLag", code: 500, userInfo: [NSLocalizedDescriptionKey: "Lỗi mã hóa bảo mật Key."])))
            return
        }

        let hwid = getHWID()
        var components = URLComponents(string: KeyAuthManager.apiURL)
        components?.queryItems = [
            URLQueryItem(name: "admin_pass", value: KeyAuthManager.adminPassword),
            URLQueryItem(name: "action", value: "check_info"),
            URLQueryItem(name: "enc_key", value: encKey),
            URLQueryItem(name: "hwid", value: hwid)
        ]

        guard let requestUrl = components?.url else {
            completion(.failure(NSError(domain: "FakeLag", code: 400, userInfo: [NSLocalizedDescriptionKey: "URL không hợp lệ."])))
            return
        }

        var request = URLRequest(url: requestUrl)
        request.httpMethod = "GET"
        request.timeoutInterval = 15.0
        request.setValue("FakeLag-iOS-Client/1.0", forHTTPHeaderField: "User-Agent")

        let task = URLSession.shared.dataTask(with: request) { data, response, error in
            if let error = error {
                completion(.failure(error))
                return
            }

            guard let data = data else {
                completion(.failure(NSError(domain: "FakeLag", code: 500, userInfo: [NSLocalizedDescriptionKey: "Không nhận được phản hồi từ server."])))
                return
            }

            do {
                if let json = try JSONSerialization.jsonObject(with: data) as? [String: Any] {
                    let status = (json["status"] as? String)?.lowercased() ?? ""
                    let rawMessage = (json["message"] as? String) ?? ""

                    if status == "success" {
                        var expiryDisplay = "Vĩnh viễn (LIFETIME)"
                        if let msgData = rawMessage.data(using: .utf8),
                           let infoObj = try? JSONSerialization.jsonObject(with: msgData) as? [String: Any],
                           let exp = infoObj["expiry"] as? String {
                            expiryDisplay = self.formatExpiryDate(exp)
                        } else if !rawMessage.isEmpty && !rawMessage.hasPrefix("{") {
                            expiryDisplay = self.formatExpiryDate(rawMessage)
                        }
                        let info = KeyInfo(key: cleanKey, expiry: expiryDisplay, isValid: true, message: "Xác thực Key thành công ✔")
                        completion(.success(info))
                    } else {
                        let errMsg = !rawMessage.isEmpty ? rawMessage : "Key không hợp lệ hoặc đã hết hạn!"
                        completion(.failure(NSError(domain: "FakeLag", code: 401, userInfo: [NSLocalizedDescriptionKey: errMsg])))
                    }
                } else {
                    completion(.failure(NSError(domain: "FakeLag", code: 502, userInfo: [NSLocalizedDescriptionKey: "Dữ liệu server không hợp lệ."])))
                }
            } catch {
                completion(.failure(error))
            }
        }
        task.resume()
    }

    private func formatExpiryDate(_ expiry: String) -> String {
        if expiry.caseInsensitiveCompare("LIFETIME") == .orderedSame || expiry.caseInsensitiveCompare("vv") == .orderedSame {
            return "Vĩnh viễn (LIFETIME)"
        }
        if expiry.contains("-") {
            let isoFormatter = ISO8601DateFormatter()
            if let date = isoFormatter.date(from: expiry) {
                let displayFormatter = DateFormatter()
                displayFormatter.dateFormat = "dd/MM/yyyy"
                return "HSD: \(displayFormatter.string(from: date))"
            }
        }
        return expiry
    }
}
