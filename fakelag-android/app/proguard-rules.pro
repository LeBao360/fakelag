# ==========================================
# NOVA FAKE LAG - ADVANCED OBFUSCATION RULES
# ==========================================

# 1. Aggressive Obfuscation & Renaming
-repackageclasses 'com.fakelag.android.core'
-allowaccessmodification
-dontusemixedcaseclassnames
-verbose

# 2. Keep Android Component Entry Points
-keep public class * extends android.app.Activity
-keep public class * extends android.app.Application
-keep public class * extends android.app.Service
-keep public class * extends android.content.BroadcastReceiver
-keep public class * extends android.content.ContentProvider
-keep public class * extends android.app.backup.BackupAgentHelper
-keep public class * extends android.preference.Preference

# 3. Keep ViewBinding Classes & Custom Views
-keepclassmembers class * implements androidx.viewbinding.ViewBinding {
    public static * inflate(...);
    public static * bind(...);
    public * getRoot();
}
-keep public class * extends android.view.View {
    public <init>(android.content.Context);
    public <init>(android.content.Context, android.util.AttributeSet);
    public <init>(android.content.Context, android.util.AttributeSet, int);
}

# 4. Keep Data classes for JSON parsing
-keepclassmembers class com.fakelag.android.utils.KeyAuthManager$KeyInfo { *; }

# 5. Keep Parcelables
-keepclassmembers class * implements android.os.Parcelable {
    public static final ** CREATOR;
}
