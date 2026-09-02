import SwiftUI

@main
struct FakeLagApp: App {
    @StateObject private var settings = SettingsManager.shared
    @State private var isLoggedIn: Bool = false

    var body: some Scene {
        WindowGroup {
            Group {
                if isLoggedIn {
                    MainView(onLogout: {
                        isLoggedIn = false
                    })
                } else {
                    LoginView(onLoginSuccess: {
                        isLoggedIn = true
                    })
                }
            }
            .preferredColorScheme(.dark)
            .onAppear {
                checkAutoLogin()
            }
        }
    }

    private func checkAutoLogin() {
        if settings.isKeyActivated && !settings.savedLicenseKey.isEmpty {
            isLoggedIn = true
        } else {
            isLoggedIn = false
        }
    }
}
