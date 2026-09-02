# -*- coding: utf-8 -*-
import sys
import os
import ctypes
import ctypes.wintypes
import threading
import winsound
import queue as _Q
import time as _time
import hashlib
import base64
import json
import uuid
import subprocess

try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad, unpad
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QSlider, QLineEdit,
    QStackedWidget, QSystemTrayIcon, QMenu,
    QComboBox, QMessageBox, QDialog
)
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QTimer,
    QPropertyAnimation, QEasingCurve, QParallelAnimationGroup,
    QPoint
)
from PyQt6.QtGui import (
    QColor, QPalette, QIcon, QPixmap, QPainter, QKeySequence
)
import webbrowser


# ─────────────────────────────────────────────────────────────────────────────
# Admin elevation
# ─────────────────────────────────────────────────────────────────────────────

def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def request_elevation():
    exe    = sys.executable
    script = os.path.abspath(sys.argv[0])
    if getattr(sys, 'frozen', False) or exe.lower() == script.lower():
        params = " ".join(f'"{a}"' for a in sys.argv[1:])
        ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params or None, None, 1)
    else:
        params = " ".join(f'"{a}"' for a in sys.argv[1:])
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", exe, f'"{script}" {params}', None, 1
        )
    sys.exit(0)


# ─────────────────────────────────────────────────────────────────────────────
# .NET Runtime Check
# ─────────────────────────────────────────────────────────────────────────────

DOTNET_REQUIRED_MAJOR = 8
DOTNET_DOWNLOAD_URL   = "https://dotnet.microsoft.com/en-us/download/dotnet/8.0"


def _check_dotnet_registry() -> tuple[bool, str]:
    try:
        import winreg
        paths = [
            (winreg.HKEY_LOCAL_MACHINE,
             r"SOFTWARE\dotnet\Setup\InstalledVersions\x64\sharedhost", "Version"),
            (winreg.HKEY_LOCAL_MACHINE,
             r"SOFTWARE\WOW6432Node\dotnet\Setup\InstalledVersions\x64\sharedhost", "Version"),
        ]
        for hive, path, key in paths:
            try:
                with winreg.OpenKey(hive, path) as k:
                    val, _ = winreg.QueryValueEx(k, key)
                    if int(str(val).split('.')[0]) >= DOTNET_REQUIRED_MAJOR:
                        return True, str(val)
            except Exception:
                continue
    except Exception:
        pass
    return False, ""


def _check_dotnet_cli() -> tuple[bool, str]:
    try:
        flag = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        r = subprocess.run(["dotnet", "--list-runtimes"],
                           capture_output=True, text=True, timeout=5, creationflags=flag)
        if r.returncode == 0:
            for line in r.stdout.splitlines():
                if "Microsoft.NETCore.App" in line:
                    parts = line.split()
                    if len(parts) >= 2 and int(parts[1].split('.')[0]) >= DOTNET_REQUIRED_MAJOR:
                        return True, parts[1]
            return False, f"Có .NET nhưng < {DOTNET_REQUIRED_MAJOR}.0"
    except Exception:
        pass
    return False, ""


def check_dotnet() -> tuple[bool, str]:
    ok, ver = _check_dotnet_registry()
    if ok:
        return True, ver
    ok, ver = _check_dotnet_cli()
    if ok:
        return True, ver
    return False, ver or f".NET {DOTNET_REQUIRED_MAJOR}.0 chưa cài đặt"


class DotNetCheckWorker(QThread):
    result_signal = pyqtSignal(bool, str)
    def run(self):
        ok, msg = check_dotnet()
        self.result_signal.emit(ok, msg)


# Direct download link — Microsoft aka.ms redirects to latest .NET 8.x Runtime
DOTNET_INSTALLER_URL = "https://aka.ms/dotnet/8.0/dotnet-runtime-win-x64.exe"


class DotNetInstallWorker(QThread):
    """
    Downloads the .NET 8.0 Runtime installer in the background,
    then launches it and waits for completion (tool already runs as admin).
    """
    progress  = pyqtSignal(str)   # progress message
    finished2 = pyqtSignal(bool, str)  # (success, message)

    def run(self):
        import urllib.request
        import tempfile
        try:
            self.progress.emit("⬇  Đang tải .NET 8.0 Runtime (~50 MB)…")
            tmp = os.path.join(tempfile.gettempdir(), "dotnet8_runtime_installer.exe")
            # Download with progress callback
            def _reporthook(count, block_size, total_size):
                if total_size > 0:
                    pct = min(100, int(count * block_size * 100 / total_size))
                    self.progress.emit(f"⬇  Đang tải .NET 8.0… {pct}%")
            urllib.request.urlretrieve(DOTNET_INSTALLER_URL, tmp, _reporthook)

            self.progress.emit("🔧  Đang cài đặt .NET 8.0 (vui lòng chờ)…")
            # Tool already runs as admin — run installer directly and wait
            flag = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            process = subprocess.Popen(
                [tmp, "/install", "/quiet", "/norestart"],
                creationflags=flag
            )
            process.wait()  # Wait for installer to finish!

            # Check if it was successfully installed
            ok, msg = check_dotnet()
            if ok:
                self.finished2.emit(True, f"✔  Cài đặt .NET 8.0 thành công!\nPhiên bản hiện tại: {msg}")
            else:
                self.finished2.emit(False, "❌  Cài đặt hoàn tất nhưng không tìm thấy .NET 8.0.\nVui lòng thử cài đặt thủ công.")
        except Exception as exc:
            self.finished2.emit(False, f"Lỗi: {exc}\n\nHãy tải thủ công tại: {DOTNET_DOWNLOAD_URL}")


class DotNetInstallDialog(QDialog):
    """
    Shows a .NET missing warning and automatically installs it.
    The tool already has admin rights so no extra elevation needed.
    """
    def __init__(self, error_msg: str, parent=None):
        super().__init__(parent)
        self._worker: DotNetInstallWorker | None = None
        self._error  = error_msg
        self._build()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Dialog
        )
        self.setFixedSize(400, 220)
        if parent:
            pg = parent.window().geometry()
            self.move(
                pg.x() + (pg.width()  - self.width())  // 2,
                pg.y() + (pg.height() - self.height()) // 2,
            )

    def _build(self):
        self.setStyleSheet(f"""
            QDialog   {{ background: #1a0a10; border: 2px solid {RED}; border-radius: 12px; }}
            QLabel    {{ background: transparent; color: {TXT}; }}
            QPushButton {{
                border-radius: 7px; font-size: 11px; font-weight: 700;
                padding: 8px 16px; letter-spacing: 1px;
            }}
            QPushButton#installBtn {{
                background: #6a0020; color: #ff8899;
                border: 1px solid {RED};
            }}
            QPushButton#installBtn:hover {{ background: {RED}; color: white; }}
            QPushButton#installBtn:disabled {{ background: #2a1018; color: #555; border-color: #3a1020; }}
            QPushButton#skipBtn {{
                background: #1e1e2a; color: {TXT_DIM};
                border: 1px solid {BORDER};
            }}
            QPushButton#skipBtn:hover {{ background: {BTN_HVR}; color: {TXT}; }}
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(12)

        title = QLabel("⚠️   .NET 8.0 RUNTIME CHƯA CÀI ĐẶT")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"color: {RED}; font-size: 13px; font-weight: 700; letter-spacing: 2px; background: transparent;")
        lay.addWidget(title)

        sub = QLabel(f"Tool cần <b>.NET Runtime 8.0</b> trở lên để hoạt động đầy đủ.<br><small>{self._error}</small>")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet(f"color: {TXT_DIM}; font-size: 10px; background: transparent;")
        sub.setTextFormat(Qt.TextFormat.RichText)
        lay.addWidget(sub)

        self.progress_lbl = QLabel("Đang tự động tải và cài đặt .NET 8.0...")
        self.progress_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_lbl.setStyleSheet(f"color: {TXT_MUTED}; font-size: 10px; background: transparent;")
        lay.addWidget(self.progress_lbl)

        btn_row = QHBoxLayout(); btn_row.setSpacing(10)
        self.install_btn = QPushButton("⬇  CÀI ĐẶT .NET 8.0 NGAY")
        self.install_btn.setObjectName("installBtn")
        self.install_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.install_btn.clicked.connect(self._start_install)
        btn_row.addWidget(self.install_btn)

        skip_btn = QPushButton("Bỏ qua")
        skip_btn.setObjectName("skipBtn")
        skip_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        skip_btn.clicked.connect(self.accept)
        btn_row.addWidget(skip_btn)
        lay.addLayout(btn_row)

    def showEvent(self, event):
        super().showEvent(event)
        # Start download automatically 100ms after showing the dialog
        QTimer.singleShot(100, self._start_install)

    def _start_install(self):
        if self._worker is not None:
            return
        self.install_btn.setEnabled(False)
        self.install_btn.setText("⏳  Đang xử lý…")
        self._worker = DotNetInstallWorker()
        self._worker.progress.connect(self._on_progress)
        self._worker.finished2.connect(self._on_done)
        self._worker.start()

    def _on_progress(self, msg: str):
        self.progress_lbl.setText(msg)

    def _on_done(self, ok: bool, msg: str):
        self.progress_lbl.setText(msg)
        if ok:
            self.install_btn.setText("✔  Thành công")
        else:
            self.install_btn.setEnabled(True)
            self.install_btn.setText("🔄  Thử lại")
            # Fallback: open browser
            webbrowser.open(DOTNET_DOWNLOAD_URL)


def show_dotnet_prompt(parent=None, error_msg: str = ""):
    """Show the .NET install dialog (auto-download + run)."""
    dlg = DotNetInstallDialog(error_msg, parent)
    dlg.exec()


# ─────────────────────────────────────────────────────────────────────────────
# Key System & Environment Secrets
# ─────────────────────────────────────────────────────────────────────────────

def _load_env():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    if os.path.exists(env_path):
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k, v = line.split('=', 1)
                        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
        except Exception:
            pass

_load_env()

API_URL    = os.getenv("FAKELAG_API_URL", "https://script.google.com/macros/s/AKfycbzyGT_Q9eSVQm8NruSTP-DUak3dvTL2wpuJbeBrkJB5O9G8IbIHKSPmWTpswG98Ah7cbA/exec")
ADMIN_PASS = os.getenv("FAKELAG_ADMIN_PASSWORD", "Lebao@")
MASTER_PW  = os.getenv("FAKELAG_MASTER_PASSWORD", "Lebao@")


def _get_hwid() -> str:
    try:
        return hashlib.md5(str(uuid.getnode()).encode()).hexdigest()[:16].upper()
    except Exception:
        return "UNKNOWN"


class _Security:
    def __init__(self):
        self.key = hashlib.sha256(MASTER_PW.encode()).digest()
        self.iv  = b'1234567890123456'

    def encrypt(self, raw: str) -> str:
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        return base64.urlsafe_b64encode(
            cipher.encrypt(pad(raw.encode(), AES.block_size))
        ).decode()


_sec = _Security() if CRYPTO_AVAILABLE else None


def _post(params: dict) -> dict:
    if not REQUESTS_AVAILABLE:
        return {"status": "error", "message": "Thiếu thư viện: requests"}
    try:
        params["admin_pass"] = ADMIN_PASS
        r = requests.post(API_URL, params=params, timeout=15)
        return r.json()
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


def verify_key(raw_key: str) -> tuple[bool, str]:
    if not CRYPTO_AVAILABLE:
        return False, "Thiếu thư viện: pycryptodome"
    enc  = _sec.encrypt(raw_key)
    hwid = _get_hwid()
    res  = _post({"action": "check_info", "enc_key": enc, "hwid": hwid})
    if res.get("status") == "success":
        try:
            info   = json.loads(res.get("message", "{}"))
            expiry = info.get("expiry", "?")
            if expiry in ("LIFETIME", "vv"):
                return True, "Key vĩnh viễn ✔"
            elif expiry and expiry not in ("null", "?"):
                from datetime import datetime
                dt = datetime.fromisoformat(expiry.replace("Z", "+00:00"))
                return True, f"HH: {dt.strftime('%d/%m/%Y')} ✔"
            return True, "Key hợp lệ ✔"
        except Exception:
            return True, "Key hợp lệ ✔"
    return False, res.get("message", "Lỗi không xác định")


# ─────────────────────────────────────────────────────────────────────────────
# Beep
# ─────────────────────────────────────────────────────────────────────────────

def beep_async(freq: int, duration_ms: int = 150):
    threading.Thread(target=winsound.Beep, args=(freq, duration_ms), daemon=True).start()


# ─────────────────────────────────────────────────────────────────────────────
# pydivert ctypes patch
# ─────────────────────────────────────────────────────────────────────────────

def _patch_pydivert():
    try:
        import pydivert
        _orig = pydivert.WinDivert.open
        def _patched(self):
            _l, _f = self._layer, self._flags
            self._layer, self._flags = int(_l), int(_f)
            try: _orig(self)
            finally: self._layer, self._flags = _l, _f
        pydivert.WinDivert.open = _patched
    except Exception:
        pass

_patch_pydivert()


# ─────────────────────────────────────────────────────────────────────────────
# Global Hotkey  (Win32 RegisterHotKey — no external library needed)
# ─────────────────────────────────────────────────────────────────────────────

# F-key VK codes
_F_VK = {f"F{i}": 0x6F + i for i in range(1, 13)}   # F1=0x70 … F12=0x7B

# Map Qt.Key → readable display name (for common keys)
_QT_KEY_NAME: dict[int, str] = {
    int(Qt.Key.Key_Insert):   "INS",
    int(Qt.Key.Key_Delete):   "DEL",
    int(Qt.Key.Key_Home):     "HOME",
    int(Qt.Key.Key_End):      "END",
    int(Qt.Key.Key_PageUp):   "PGUP",
    int(Qt.Key.Key_PageDown): "PGDN",
    int(Qt.Key.Key_NumLock):  "NUMLK",
    int(Qt.Key.Key_Pause):    "PAUSE",
    int(Qt.Key.Key_Print):    "PRTSC",
    int(Qt.Key.Key_ScrollLock): "SCRLK",
    int(Qt.Key.Key_Tab):      "TAB",
    int(Qt.Key.Key_CapsLock): "CAPS",
}


class WinHotkeyManager:
    """
    Registers a global hotkey via Windows RegisterHotKey API.
    Works without the 'keyboard' library — pure ctypes.
    """
    WM_HOTKEY = 0x0312
    _HK_ID    = 9001
    _user32   = ctypes.windll.user32

    def __init__(self, callback):
        self._cb     = callback
        self._vk     = 0
        self._stop   = threading.Event()
        self._thread: threading.Thread | None = None

    def register(self, vk: int) -> bool:
        """Register `vk` (Windows Virtual Key code) as global hotkey."""
        if vk == 0:
            return False
        self.unregister()
        self._vk  = vk
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="WinHotkeyLoop"
        )
        self._thread.start()
        return True

    def unregister(self):
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.6)
        self._thread = None

    def _loop(self):
        ok = self._user32.RegisterHotKey(None, self._HK_ID, 0, self._vk)
        if not ok:
            return
        msg = ctypes.wintypes.MSG()
        while not self._stop.is_set():
            if self._user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):
                if msg.message == self.WM_HOTKEY and msg.wParam == self._HK_ID:
                    try:
                        self._cb()
                    except Exception:
                        pass
            _time.sleep(0.012)
        self._user32.UnregisterHotKey(None, self._HK_ID)


def _default_hk() -> tuple[str, int]:
    """Return (display_name, vk_code) for the default hotkey F8."""
    return "F8", 0x77


# ─────────────────────────────────────────────────────────────────────────────
# Key-Capture Dialog
# ─────────────────────────────────────────────────────────────────────────────

class KeyCaptureDialog(QDialog):
    """
    Frameless dialog that grabs keyboard and waits for a single keypress.
    Works entirely via PyQt6 — no external library needed.
    """

    def __init__(self, current_key: str, parent=None):
        super().__init__(parent)
        self.key_name: str = ""
        self.key_vk:   int = 0
        self._current  = current_key
        self._build()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Dialog
        )
        self.setFixedSize(320, 140)
        if parent:
            pg = parent.window().geometry()
            cx = pg.x() + (pg.width()  - self.width())  // 2
            cy = pg.y() + (pg.height() - self.height()) // 2
            self.move(cx, cy)

    def _build(self):
        self.setStyleSheet(f"""
            QDialog {{
                background: #1a0a36;
                border: 2px solid {PURPLE_ACC};
                border-radius: 12px;
            }}
            QLabel {{
                background: transparent;
                color: {TXT};
            }}
            QPushButton {{
                background: #252530;
                color: {TXT_DIM};
                border: 1px solid {BORDER};
                border-radius: 6px;
                font-size: 11px;
                font-weight: 700;
                padding: 7px 24px;
            }}
            QPushButton:hover {{
                background: {BTN_HVR};
                color: {TXT};
                border-color: #555565;
            }}
        """)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(12)

        title = QLabel("⌨   NHẤN PHÍM BẤT KỲ")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            f"color: {PURPLE}; font-size: 15px; font-weight: 700; letter-spacing: 3px;"
        )
        lay.addWidget(title)

        cur = QLabel(f"Phím hiện tại:  {self._current}")
        cur.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cur.setStyleSheet(f"color: {TXT_MUTED}; font-size: 10px;")
        lay.addWidget(cur)

        self.hint = QLabel("Đang chờ nhấn phím…")
        self.hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hint.setStyleSheet(f"color: {TXT_DIM}; font-size: 11px;")
        lay.addWidget(self.hint)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel = QPushButton("✕   HỦY  (ESC)")
        cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel.clicked.connect(self.reject)
        btn_row.addWidget(cancel)
        btn_row.addStretch()
        lay.addLayout(btn_row)

    def showEvent(self, e):
        super().showEvent(e)
        self.setFocus()
        self.grabKeyboard()

    def hideEvent(self, e):
        super().hideEvent(e)
        try:
            self.releaseKeyboard()
        except Exception:
            pass

    def keyPressEvent(self, e):
        qt_key = e.key()

        # ESC = cancel
        if qt_key == Qt.Key.Key_Escape:
            self.reject()
            return

        # Windows VK code
        vk = e.nativeVirtualKey()

        # Build display name
        name = ""
        # Check Qt's built-in sequence string first
        qs = QKeySequence(qt_key).toString().strip()
        if qs and len(qs) <= 6:
            name = qs
        # Override with our readable map
        name = _QT_KEY_NAME.get(qt_key, name)
        # Fallback
        if not name:
            name = f"KEY{vk:02X}" if vk else "???"

        if vk == 0:
            self.hint.setText(f"❌ Phím này không hỗ trợ, thử phím khác")
            return

        self.key_name = name.upper()
        self.key_vk   = vk
        self.accept()


# ─────────────────────────────────────────────────────────────────────────────
# Game Database
# ─────────────────────────────────────────────────────────────────────────────

KNOWN_GAMES = {
    "PUBG": {
        "exe": ["tslgame-win64-shipping.exe", "tslgame.exe", "pubg.exe"],
        "filter": "udp and (udp.DstPort == 10012 or udp.SrcPort == 10012)",
        "icon": "🟠",
    },
    "Free Fire": {
        "exe": ["freefirepc.exe", "ffgame-android.exe", "garena.exe", "freefire.exe"],
        "filter": "udp and udp.PayloadLength >= 10 and udp.PayloadLength <= 200",
        "icon": "🔴",
    },
    "Valorant": {
        "exe": ["valorant-win64-shipping.exe", "valorant.exe"],
        "filter": "udp and udp.DstPort >= 7000 and udp.DstPort <= 8000",
        "icon": "🔴",
    },
    "CS2 / CS:GO": {
        "exe": ["cs2.exe", "csgo.exe"],
        "filter": "udp and (udp.DstPort == 27015 or udp.SrcPort == 27015)",
        "icon": "🟡",
    },
    "Mobile Legends": {
        "exe": ["mlbb.exe", "mobilelegendspc.exe", "mlegends.exe"],
        "filter": "udp and udp.PayloadLength >= 10 and udp.PayloadLength <= 150",
        "icon": "🔵",
    },
    "Fortnite": {
        "exe": ["fortniteclient-win64-shipping.exe", "fortnite.exe"],
        "filter": "udp and udp.DstPort >= 9000 and udp.DstPort <= 9100",
        "icon": "💜",
    },
    "Rainbow Six Siege": {
        "exe": ["rainbowsix.exe", "rainbowsix_be.exe", "r6.exe"],
        "filter": "udp and udp.DstPort >= 10000 and udp.DstPort <= 10100",
        "icon": "🟤",
    },
    "Call of Duty": {
        "exe": ["cod.exe", "modernwarfare.exe", "warzone.exe", "codmw.exe"],
        "filter": "udp and (udp.DstPort == 3074 or udp.SrcPort == 3074)",
        "icon": "⚫",
    },
    "Apex Legends": {
        "exe": ["r5apex.exe", "apex.exe"],
        "filter": "udp and (udp.DstPort == 37015 or udp.SrcPort == 37015)",
        "icon": "🟣",
    },
    "GTA Online": {
        "exe": ["gta5.exe", "gtavlauncher.exe"],
        "filter": "udp and (udp.DstPort == 6672 or udp.SrcPort == 6672)",
        "icon": "🟢",
    },
}

KNOWN_VPNS = {
    "ExitLag": {"exe": ["exitlag.exe", "exitlag3.exe"], "icon": "⚡"},
    "GearUP Booster": {"exe": ["gearup.exe", "gearupbooster.exe"], "icon": "⚡"},
    "WTFast": {"exe": ["wtfast.exe"], "icon": "⚡"},
    "Mudfish": {"exe": ["mudfish.exe", "mudflow.exe"], "icon": "⚡"},
    "PingBooster": {"exe": ["pingbooster.exe"], "icon": "⚡"},
    "OpenVPN": {"exe": ["openvpn.exe"], "icon": "🔒"},
    "WireGuard": {"exe": ["wireguard.exe"], "icon": "🔒"},
}

GENERIC_FILTER = "udp and udp.PayloadLength >= 20 and udp.PayloadLength <= 512"


_wnd_enum_proc_cache = None

def get_processes_with_windows() -> dict:
    """Enumerates PIDs of processes that have at least one visible, titled window."""
    global _wnd_enum_proc_cache
    pids = {}
    user32 = ctypes.windll.user32
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.wintypes.BOOL, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)

    def enum_windows_callback(hwnd, lParam):
        try:
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buf = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buf, length + 1)
                    title = buf.value.strip()
                    if title:
                        pid = ctypes.wintypes.DWORD()
                        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                        if pid.value:
                            if pid.value not in pids or len(title) > len(pids[pid.value]):
                                pids[pid.value] = title
        except Exception:
            pass
        return True

    _wnd_enum_proc_cache = WNDENUMPROC(enum_windows_callback)
    user32.EnumWindows(_wnd_enum_proc_cache, 0)
    return pids


def clean_title(title: str) -> str:
    cleaned = title.replace('\ufffd', '').replace('\uFFFD', '').strip()
    return cleaned


def get_process_name_by_pid(pid: int) -> str:
    try:
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        kernel32 = ctypes.windll.kernel32
        h_process = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not h_process:
            h_process = kernel32.OpenProcess(0x0400, False, pid)
            
        if h_process:
            buf = ctypes.create_unicode_buffer(260)
            size = ctypes.wintypes.DWORD(260)
            if kernel32.QueryFullProcessImageNameW(h_process, 0, buf, ctypes.byref(size)):
                kernel32.CloseHandle(h_process)
                return os.path.basename(buf.value)
            kernel32.CloseHandle(h_process)
    except Exception:
        pass
    return ""


_PROCESS_BLACKLIST = {
    # System core
    "system", "system idle process", "registry", "memory compression",
    "smss.exe", "csrss.exe", "wininit.exe", "winlogon.exe",
    "services.exe", "lsass.exe", "svchost.exe", "lsm.exe",
    "spoolsv.exe", "sppsvc.exe", "searchindexer.exe",
    "searchhost.exe", "searchapp.exe",
    "taskhostw.exe", "taskeng.exe",
    "runtimebroker.exe", "shellexperiencehost.exe",
    "startmenuexperiencehost.exe", "fontdrvhost.exe",
    "dwm.exe", "audiodg.exe", "ctfmon.exe",
    "conhost.exe", "condrv.exe", "dllhost.exe",
    "sihost.exe", "securityhealthservice.exe",
    "securityhealthsystray.exe", "securityhealthhost.exe",
    "wmiprvse.exe", "wmiapsrv.exe", "wlanext.exe",
    "msdtc.exe", "vssvc.exe", "msiexec.exe",
    # Windows components
    "explorer.exe",
    "cmd.exe", "powershell.exe", "powershell_ise.exe", "pwsh.exe",
    "mmc.exe", "taskmgr.exe", "regedit.exe",
    "msconfig.exe", "control.exe",
    "werfault.exe", "werfaultsecure.exe",
    "wuauclt.exe", "wudfhost.exe",
    # Dev / tools noise
    "git-credential-manager.exe", "git.exe",
    "python.exe", "python3.exe", "pythonw.exe",
    "node.exe", "npm.cmd",
    "vctip.exe", "vcpkgsrv.exe",
    "mbam.exe",
    # Nvidia / AMD GPU drivers
    "nvdisplay.container.exe", "nvidia web helper.exe",
    "nvcontainer.exe", "nvsphelper64.exe",
    "atiesrxx.exe", "atieclxx.exe", "amdow.exe",
    # Intel
    "igfxtray.exe", "igfxem.exe", "igfxhk.exe",
    # Audio/hardware
    "ravcpl64.exe", "rvxaux64.exe",
    "nahimic.exe", "nahimicservice.exe",
    "rtkaudioservice64.exe",
}


def scan_active_processes() -> list[dict]:
    """
    Quét TẤT CẢ tiến trình đang chạy trên máy tính (không chỉ ứng dụng có cửa sổ).
    Loại bỏ các tiến trình hệ thống/driver/background-noise.
    Trả về danh sách sắp xếp: VPN → Game quen → ứng dụng khác (A-Z).
    """
    try:
        my_pid = os.getpid()
        my_name = ""
        try:
            if PSUTIL_AVAILABLE:
                my_name = psutil.Process(my_pid).name().lower()
        except Exception:
            pass

        result = []
        seen_names: set[str] = set()

        if PSUTIL_AVAILABLE:
            for p in psutil.process_iter(['pid', 'name']):
                try:
                    pid  = p.info['pid']
                    name = (p.info['name'] or "").strip()
                    if not name or pid == my_pid:
                        continue
                    name_lower = name.lower()
                    if name_lower == my_name:
                        continue
                    if name_lower in _PROCESS_BLACKLIST:
                        continue
                    if name_lower in seen_names:
                        continue
                    seen_names.add(name_lower)

                    # Choose icon
                    icon = "🖥️"
                    for _vname, vinfo in KNOWN_VPNS.items():
                        if name_lower in {e.lower() for e in vinfo["exe"]}:
                            icon = vinfo["icon"]
                            break
                    else:
                        for _gname, ginfo in KNOWN_GAMES.items():
                            if name_lower in {e.lower() for e in ginfo["exe"]}:
                                icon = ginfo["icon"]
                                break

                    # Friendly name: strip .exe, capitalize
                    display = name
                    if display.lower().endswith(".exe"):
                        display = display[:-4]
                    display = display.replace("_", " ").replace("-", " ").strip()
                    if display:
                        display = display[0].upper() + display[1:]

                    result.append({
                        "name": display or name,
                        "exes": [name],
                        "icon": icon,
                        "type": "process",
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                except Exception:
                    continue
        else:
            # Fallback: windows with visible titles via EnumWindows
            win_pids = get_processes_with_windows()
            for pid, title in win_pids.items():
                if pid == my_pid:
                    continue
                proc_name = get_process_name_by_pid(pid)
                if not proc_name:
                    continue
                name_lower = proc_name.lower()
                if name_lower in _PROCESS_BLACKLIST or name_lower in seen_names:
                    continue
                seen_names.add(name_lower)
                clean_t = clean_title(title) or proc_name.replace(".exe", "").capitalize()
                result.append({
                    "name": clean_t,
                    "exes": [proc_name],
                    "icon": "🖥️",
                    "type": "process",
                })

        # Sort: VPNs (⚡/🔒) → known games → everything else (A-Z)
        vpn_icons = {"⚡", "🔒"}
        game_icons = {"🟠", "🔴", "🟡", "🔵", "💜", "🟤", "⚫", "🟣", "🟢"}

        def _sort_key(item):
            if item["icon"] in vpn_icons:   return (0, item["name"].lower())
            if item["icon"] in game_icons:  return (1, item["name"].lower())
            return (2, item["name"].lower())

        result.sort(key=_sort_key)
        return result

    except Exception as exc:
        import traceback
        try:
            with open("d:/fakelag/scan_error.log", "w", encoding="utf-8") as f:
                f.write(f"Error: {exc}\n")
                f.write(traceback.format_exc())
        except Exception:
            pass
        return []


def get_ports_for_exes(exes: set[str]) -> set[int]:
    """
    Finds all active local and remote UDP ports for the specified executable names.
    Uses psutil.net_connections which is extremely fast.
    """
    ports = set()
    if not PSUTIL_AVAILABLE or not exes:
        return ports

    exes_lower = {e.lower() for e in exes}
    try:
        pid_to_name = {}
        for p in psutil.process_iter(['pid', 'name']):
            try:
                pid_to_name[p.info['pid']] = p.info['name'].lower()
            except Exception:
                pass

        conns = psutil.net_connections(kind='udp')
        for conn in conns:
            if conn.pid and conn.pid in pid_to_name:
                proc_name = pid_to_name[conn.pid]
                if proc_name in exes_lower:
                    if conn.laddr:
                        ports.add(conn.laddr.port)
                    if conn.raddr:
                        ports.add(conn.raddr.port)
    except Exception:
        pass
    return ports


# ─────────────────────────────────────────────────────────────────────────────
# Workers
# ─────────────────────────────────────────────────────────────────────────────

MAX_RESTARTS = 5


class DropWorker(QThread):
    status_signal = pyqtSignal(str)
    error_signal  = pyqtSignal(str)
    ports_signal  = pyqtSignal(str)
    FILTER = "udp and inbound and udp.PayloadLength >= 50 and udp.PayloadLength <= 250"

    def __init__(self, target_exes: set[str] | None):
        super().__init__()
        self._stop         = threading.Event()
        self._target_exes  = target_exes
        self._active_ports = set()

    def stop(self): self._stop.set()

    def run(self):
        try:
            import pydivert
        except ImportError:
            self.error_signal.emit("pydivert not installed"); return
        self._stop.clear()

        def _port_scanner():
            while not self._stop.is_set():
                if self._target_exes:
                    ports = get_ports_for_exes(self._target_exes)
                    self._active_ports = ports
                    if ports:
                        self.ports_signal.emit(f"✔ Can thiệp: {len(ports)} ports mạng")
                    else:
                        self.ports_signal.emit("⚠️ Game/VPN đang chạy nhưng chưa phát hiện port mạng")
                else:
                    self.ports_signal.emit("Can thiệp UDP chung")
                _time.sleep(3.0)

        if self._target_exes:
            threading.Thread(target=_port_scanner, daemon=True).start()

        dropped = 0
        retry   = 0
        while not self._stop.is_set() and retry < 3:
            try:
                with pydivert.WinDivert(self.FILTER) as w:
                    retry = 0
                    self.status_signal.emit("Đang drop inbound UDP…")
                    while not self._stop.is_set():
                        try:
                            pkt = w.recv(bufsize=65535)
                            is_target = True
                            if self._target_exes:
                                if pkt.src_port not in self._active_ports and pkt.dst_port not in self._active_ports:
                                    is_target = False
                            
                            if is_target:
                                dropped += 1
                                if dropped % 10 == 0:
                                    self.status_signal.emit(f"Dropped: {dropped} pkts")
                            else:
                                try: w.send(pkt)
                                except Exception: pass
                        except OSError:
                            break
            except Exception as exc:
                if self._stop.is_set(): break
                retry += 1
                if retry >= 3: self.error_signal.emit(str(exc))
                else: _time.sleep(0.5)


class DelayWorker(QThread):
    status_signal = pyqtSignal(str)
    error_signal  = pyqtSignal(str)
    ports_signal  = pyqtSignal(str)

    def __init__(self, delay_ms: int, direction: str, target_exes: set[str] | None):
        super().__init__()
        self._stop         = threading.Event()
        self._delay_ms     = delay_ms
        self._direction    = direction
        self._target_exes  = target_exes
        self._active_ports = set()

    def stop(self): self._stop.set()

    def _filt(self) -> str:
        base = "udp and udp.PayloadLength >= 50 and udp.PayloadLength <= 250"
        if self._direction == "inbound":  return f"udp and inbound and {base}"
        if self._direction == "outbound": return f"udp and outbound and {base}"
        return f"udp and ({base})"

    def run(self):
        try:
            import pydivert
        except ImportError:
            self.error_signal.emit("pydivert not installed"); return
        self._stop.clear()

        def _port_scanner():
            while not self._stop.is_set():
                if self._target_exes:
                    ports = get_ports_for_exes(self._target_exes)
                    self._active_ports = ports
                    if ports:
                        self.ports_signal.emit(f"✔ Can thiệp: {len(ports)} ports mạng")
                    else:
                        self.ports_signal.emit("⚠️ Game/VPN đang chạy nhưng chưa phát hiện port mạng")
                else:
                    self.ports_signal.emit("Can thiệp UDP chung")
                _time.sleep(3.0)

        if self._target_exes:
            threading.Thread(target=_port_scanner, daemon=True).start()

        pkt_queue = _Q.Queue()
        count     = [0]
        dlbl = {"inbound": "↓ DL", "outbound": "↑ UL", "both": "↕"}[self._direction]
        retry = 0
        while not self._stop.is_set() and retry < 3:
            try:
                with pydivert.WinDivert(self._filt()) as w:
                    retry = 0
                    self.status_signal.emit(f"Delay {dlbl} {self._delay_ms}ms…")
                    def _send():
                        while not self._stop.is_set():
                            try: ts, pkt = pkt_queue.get(timeout=0.05)
                            except _Q.Empty: continue
                            wait = self._delay_ms / 1000.0 - (_time.monotonic() - ts)
                            if wait > 0: _time.sleep(wait)
                            if not self._stop.is_set():
                                try:
                                    w.send(pkt); count[0] += 1
                                    if count[0] % 10 == 0:
                                        self.status_signal.emit(f"Delayed {dlbl}: {count[0]}")
                                except Exception: pass
                    threading.Thread(target=_send, daemon=True).start()
                    while not self._stop.is_set():
                        try:
                            pkt = w.recv(bufsize=65535)
                            is_target = True
                            if self._target_exes:
                                if pkt.src_port not in self._active_ports and pkt.dst_port not in self._active_ports:
                                    is_target = False
                            
                            if is_target:
                                pkt_queue.put((_time.monotonic(), pkt))
                            else:
                                try: w.send(pkt)
                                except Exception: pass
                        except OSError:
                            break
            except Exception as exc:
                if self._stop.is_set(): break
                retry += 1
                if retry >= 3: self.error_signal.emit(str(exc))
                else: _time.sleep(0.5)


class DameJumpWorker(QThread):
    """
    Dame Jump Booster — single WinDivert handle.
    Dynamically targets active network connections (ports) of the selected game/VPN.
    """
    status_signal = pyqtSignal(str)
    error_signal  = pyqtSignal(str)
    ports_signal  = pyqtSignal(str)

    def __init__(self, target_exes: set[str] | None, upload_delay_ms: int = 100, drop_pct: int = 30):
        super().__init__()
        self._stop         = threading.Event()
        self._target_exes  = target_exes
        self._delay_ms     = max(10, upload_delay_ms)
        self._drop_pct     = max(0, min(90, drop_pct))
        self._active_ports = set()

    def stop(self): self._stop.set()

    def run(self):
        try:
            import pydivert
        except ImportError:
            self.error_signal.emit("pydivert not installed"); return
        self._stop.clear()

        # Scanner thread
        def _port_scanner():
            while not self._stop.is_set():
                if self._target_exes:
                    ports = get_ports_for_exes(self._target_exes)
                    self._active_ports = ports
                    if ports:
                        self.ports_signal.emit(f"✔ Can thiệp: {len(ports)} ports mạng")
                    else:
                        self.ports_signal.emit("⚠️ Game/VPN đang chạy nhưng chưa phát hiện port mạng")
                else:
                    self.ports_signal.emit("Can thiệp UDP chung")
                _time.sleep(3.0)

        if self._target_exes:
            threading.Thread(target=_port_scanner, daemon=True).start()

        pkt_queue  = _Q.Queue(maxsize=2000)
        ul_delayed = [0]
        dl_dropped = [0]
        dl_ctr     = [0]

        # Broad filter to catch UDP traffic
        broad_filter = "udp and udp.PayloadLength >= 20 and udp.PayloadLength <= 1000"

        retry = 0
        while not self._stop.is_set() and retry < 3:
            try:
                with pydivert.WinDivert(broad_filter) as w:
                    retry = 0
                    self.status_signal.emit(
                        f"⚡ DAME JUMP  UL +{self._delay_ms}ms  "
                        f"DL -{self._drop_pct}%…"
                    )

                    def _sender():
                        while not self._stop.is_set():
                            try:
                                ts, pkt = pkt_queue.get(timeout=0.05)
                            except _Q.Empty:
                                continue
                            wait = self._delay_ms / 1000.0 - (_time.monotonic() - ts)
                            if wait > 0:
                                _time.sleep(wait)
                            if not self._stop.is_set():
                                try:
                                    w.send(pkt)
                                    ul_delayed[0] += 1
                                except Exception:
                                    pass

                    threading.Thread(target=_sender, daemon=True).start()

                    last_report = _time.monotonic()
                    while not self._stop.is_set():
                        try:
                            pkt = w.recv(bufsize=65535)
                        except OSError:
                            break

                        # Check if packet matches target game/VPN ports
                        src_p = pkt.src_port
                        dst_p = pkt.dst_port
                        
                        is_target = False
                        if self._target_exes:
                            # If target exes are set, we strictly filter matching active ports
                            if src_p in self._active_ports or dst_p in self._active_ports:
                                is_target = True
                        else:
                            # Fallback generic game UDP size range
                            if 20 <= len(pkt.payload) <= 512:
                                is_target = True

                        if not is_target:
                            # Pass instantly untouched
                            try: w.send(pkt)
                            except Exception: pass
                            continue

                        # Direction detection (works across pydivert versions)
                        try:
                            is_out = bool(pkt.is_outbound)
                        except AttributeError:
                            try:
                                is_out = (int(pkt.meta.Direction) == 0)
                            except Exception:
                                is_out = True

                        if is_out:
                            try:
                                pkt_queue.put_nowait((_time.monotonic(), pkt))
                            except _Q.Full:
                                try: w.send(pkt)
                                except Exception: pass
                        else:
                            dl_ctr[0] = (dl_ctr[0] + 1) % 100
                            if dl_ctr[0] < self._drop_pct:
                                dl_dropped[0] += 1
                            else:
                                try: w.send(pkt)
                                except Exception: pass

                        now = _time.monotonic()
                        if now - last_report >= 2.0:
                            last_report = now
                            self.status_signal.emit(
                                f"⚡ UL:{ul_delayed[0]} delayed  "
                                f"DL:{dl_dropped[0]} blocked"
                            )

            except Exception as exc:
                if self._stop.is_set(): break
                retry += 1
                if retry >= 3:
                    self.error_signal.emit(str(exc))
                else:
                    self.status_signal.emit(f"Thử lại ({retry}/3)…")
                    _time.sleep(0.5)


class KeyVerifyWorker(QThread):
    result_signal = pyqtSignal(bool, str)
    def __init__(self, key: str):
        super().__init__(); self._key = key
    def run(self):
        self.result_signal.emit(*verify_key(self._key))


# ─────────────────────────────────────────────────────────────────────────────
# Constants & Colours
# ─────────────────────────────────────────────────────────────────────────────

BG         = "#111113"
PANEL      = "#1a1a1e"
BORDER     = "#2e2e38"
TXT        = "#dcdcec"
TXT_DIM    = "#888899"
TXT_MUTED  = "#55556a"
BTN_BG     = "#252530"
BTN_HVR    = "#303040"
GREEN      = "#00e06a"
GREEN_BG   = "#0a3d20"
BLUE       = "#4ab8ff"
BLUE_BG    = "#0a1e36"
BLUE_ACC   = "#3a7bd5"
RED        = "#ff5555"
GOLD       = "#f5c542"
GOLD_DIM   = "#7a6010"
GOLD_HVR   = "#a88020"
PURPLE     = "#c084fc"
PURPLE_BG  = "#1e0a36"
PURPLE_ACC = "#7c3aed"
ORANGE     = "#fb923c"

MODE_DROP  = "drop"
MODE_DELAY = "delay"
MODE_DAME  = "dame"
DIR_IN     = "inbound"
DIR_OUT    = "outbound"
DIR_BOTH   = "both"

DEFAULT_DELAY        = 200
MIN_DELAY            = 20
MAX_DELAY            = 2000
DEFAULT_UPLOAD_DELAY = 100
MIN_UPLOAD_DELAY     = 20
MAX_UPLOAD_DELAY     = 500
DEFAULT_DROP_PCT     = 30

WIN_W         = 500
WIN_H_COMPACT = 450
WIN_H_FULL    = 550
WIN_H_DAME    = 660
LOGIN_H       = 340


# ─────────────────────────────────────────────────────────────────────────────
# Stylesheet
# ─────────────────────────────────────────────────────────────────────────────

STYLE = f"""
/* ─ Base ─ */
QWidget {{
    color: {TXT};
    font-family: "Segoe UI", Consolas, sans-serif;
    font-size: 12px;
}}
QLabel {{
    background: transparent;
}}

/* ─ Toggle button ─ */
QPushButton#toggleBtn {{
    border-radius: 10px;
    border: 2px solid {BORDER};
    font-size: 22px;
    font-weight: 700;
    letter-spacing: 2px;
    padding: 16px 0;
    color: {TXT_DIM};
    background-color: {BTN_BG};
}}
QPushButton#toggleBtn:hover {{
    background: {BTN_HVR};
    border-color: #555565;
}}
QPushButton#toggleBtn[active="true"][mode="drop"] {{
    color: {GREEN};
    background: {GREEN_BG};
    border-color: {GREEN};
}}
QPushButton#toggleBtn[active="true"][mode="delay"] {{
    color: {BLUE};
    background: {BLUE_BG};
    border-color: {BLUE};
}}
QPushButton#toggleBtn[active="true"][mode="dame"] {{
    color: {PURPLE};
    background: {PURPLE_BG};
    border-color: {PURPLE};
}}

/* ─ Status label ─ */
QLabel#statusLbl {{
    color: {TXT_MUTED};
    font-size: 11px;
    letter-spacing: 1px;
}}
QLabel#statusLbl[s="drop"]  {{ color: {GREEN};  }}
QLabel#statusLbl[s="delay"] {{ color: {BLUE};   }}
QLabel#statusLbl[s="dame"]  {{ color: {PURPLE}; }}
QLabel#statusLbl[s="error"] {{ color: {RED};    }}

/* ─ Title bar labels ─ */
QLabel#titleLbl {{
    color: {TXT};
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 4px;
}}
QLabel#adminLbl {{
    color: #2a8a2a;
    font-size: 10px;
    letter-spacing: 1px;
}}
QLabel#restartLbl {{
    color: {ORANGE};
    font-size: 10px;
    letter-spacing: 1px;
    background: #1e1000;
    border: 1px solid #6a3000;
    border-radius: 4px;
    padding: 2px 8px;
    qproperty-alignment: AlignCenter;
}}

/* ─ Separator ─ */
QFrame#sep {{
    background: {BORDER};
    max-height: 1px;
    min-height: 1px;
}}

/* ─ Panel frames ─ */
QFrame#modeFrame {{
    background: #141418;
    border: 1px solid #252530;
    border-radius: 8px;
}}
QFrame#delayFrame {{
    background: #101016;
    border: 1px solid #202030;
    border-radius: 8px;
}}
QFrame#hotkeyFrame {{
    background: #141418;
    border: 1px solid {BORDER};
    border-radius: 8px;
}}
QFrame#dameFrame {{
    background: #120a1e;
    border: 1px solid {PURPLE_ACC};
    border-radius: 8px;
}}
QFrame#gameFrame {{
    background: #0e0818;
    border: 1px solid #3a1a5e;
    border-radius: 6px;
}}

/* ─ Generic row labels ─ */
QLabel#rowLbl {{
    color: {TXT_DIM};
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 2px;
    min-width: 60px;
}}

/* ─ Dame panel row labels ─ */
QLabel#dameRowLbl {{
    color: {TXT};
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
    min-width: 90px;
    padding: 2px 0;
}}

/* ─ Mode buttons ─ */
QPushButton#modeBtn {{
    background: {BTN_BG};
    color: {TXT_DIM};
    border: 1px solid {BORDER};
    border-radius: 6px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    padding: 6px 8px;
    min-width: 78px;
}}
QPushButton#modeBtn:hover {{ background: {BTN_HVR}; color: {TXT}; }}
QPushButton#modeBtn[sel="drop"]  {{
    color: {RED};    background: #200a0a;    border-color: #6a2020;
}}
QPushButton#modeBtn[sel="delay"] {{
    color: {BLUE};   background: {BLUE_BG};  border-color: {BLUE_ACC};
}}
QPushButton#modeBtn[sel="dame"]  {{
    color: {PURPLE}; background: {PURPLE_BG}; border-color: {PURPLE_ACC};
}}
QPushButton#modeBtn:disabled {{ color: {TXT_MUTED}; }}

/* ─ Direction buttons ─ */
QPushButton#dirBtn {{
    background: {BTN_BG};
    color: {TXT_DIM};
    border: 1px solid {BORDER};
    border-radius: 5px;
    font-size: 10px;
    font-weight: 700;
    padding: 5px 6px;
    min-width: 80px;
}}
QPushButton#dirBtn:hover {{ background: {BTN_HVR}; color: {TXT}; border-color: #444455; }}
QPushButton#dirBtn[sel="1"] {{ color: {BLUE}; background: #081420; border-color: {BLUE_ACC}; }}
QPushButton#dirBtn:disabled {{ color: #333340; border-color: #202028; background: #0e0e14; }}

/* ─ Value labels ─ */
QLabel#delayVal {{
    color: {BLUE};
    font-size: 13px;
    font-weight: 700;
    min-width: 68px;
    background: transparent;
    qproperty-alignment: AlignRight;
}}
QLabel#ulVal {{
    color: {PURPLE};
    font-size: 13px;
    font-weight: 700;
    min-width: 62px;
    background: transparent;
    qproperty-alignment: AlignRight;
}}
QLabel#dlVal {{
    color: {PURPLE};
    font-size: 13px;
    font-weight: 700;
    min-width: 46px;
    background: transparent;
    qproperty-alignment: AlignRight;
}}

/* ─ Blue slider (delay mode) ─ */
QSlider#slider {{
    height: 30px;
    background: transparent;
}}
QSlider#slider::groove:horizontal {{
    background: #202030; height: 5px; border-radius: 3px;
}}
QSlider#slider::handle:horizontal {{
    background: {BLUE}; width: 16px; height: 16px;
    margin: -6px 0; border-radius: 8px;
}}
QSlider#slider::sub-page:horizontal {{
    background: {BLUE_ACC}; height: 5px; border-radius: 3px;
}}
QSlider#slider:disabled::handle:horizontal    {{ background: #333340; }}
QSlider#slider:disabled::sub-page:horizontal  {{ background: #202030; }}

/* ─ Purple slider (dame mode) ─ */
QSlider#dameSlider {{
    height: 30px;
    background: transparent;
}}
QSlider#dameSlider::groove:horizontal {{
    background: #2a1040; height: 6px; border-radius: 3px;
}}
QSlider#dameSlider::handle:horizontal {{
    background: {PURPLE};
    width: 18px; height: 18px;
    margin: -6px 0;
    border-radius: 9px;
    border: 2px solid {PURPLE_BG};
}}
QSlider#dameSlider::sub-page:horizontal {{
    background: {PURPLE_ACC}; height: 6px; border-radius: 3px;
}}
QSlider#dameSlider:disabled::handle:horizontal   {{ background: #333340; border-color: #1a0a36; }}
QSlider#dameSlider:disabled::sub-page:horizontal {{ background: #2a1040; }}

/* ─ Game selector label ─ */
QLabel#gameSectionLbl {{
    color: {PURPLE};
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 2px;
    background: transparent;
}}

/* ─ Scan status label ─ */
QLabel#scanStatusLbl {{
    color: {TXT_DIM};
    font-size: 10px;
    letter-spacing: 1px;
    background: transparent;
    qproperty-alignment: AlignCenter;
}}

/* ─ Dame hint label ─ */
QLabel#dameHintLbl {{
    color: {TXT_DIM};
    font-size: 10px;
    letter-spacing: 1px;
    background: transparent;
    qproperty-alignment: AlignCenter;
}}

/* ─ Game ComboBox ─ */
QComboBox#gameCombo {{
    background: #140c24;
    color: {PURPLE};
    border: 1px solid {PURPLE_ACC};
    border-radius: 6px;
    padding: 5px 10px;
    font-size: 11px;
    font-weight: 600;
    min-height: 26px;
}}
QComboBox#gameCombo::drop-down {{ border: none; width: 20px; }}
QComboBox#gameCombo::down-arrow {{
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {PURPLE};
    width: 0; height: 0; margin-right: 6px;
}}
QComboBox#gameCombo:disabled {{
    color: #555565;
    border-color: #2e1a50;
    background: #0e0818;
}}
QComboBox QAbstractItemView {{
    background: #1a0a30;
    color: {TXT};
    border: 1px solid {PURPLE_ACC};
    selection-background-color: {PURPLE_ACC};
    selection-color: white;
    padding: 4px;
}}

/* ─ Scan button ─ */
QPushButton#scanBtn {{
    background: #1a0a30;
    color: {PURPLE};
    border: 1px solid {PURPLE_ACC};
    border-radius: 6px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    padding: 5px 12px;
}}
QPushButton#scanBtn:hover    {{ background: {PURPLE_ACC}; color: white; }}
QPushButton#scanBtn:disabled {{ color: #444; border-color: #2a1040; background: #0e0818; }}

/* ─ Hotkey badge ─ */
QLabel#keyBadge {{
    color: {TXT};
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 2px;
    background: #22222e;
    border: 1px solid #3a3a4e;
    border-radius: 5px;
    padding: 4px 14px;
    min-width: 44px;
    qproperty-alignment: AlignCenter;
}}
QLabel#keyBadge[s="drop"]  {{ color: {GREEN};  border-color: #0a5020; background: #0a1810; }}
QLabel#keyBadge[s="delay"] {{ color: {BLUE};   border-color: #1a3a5a; background: {BLUE_BG}; }}
QLabel#keyBadge[s="dame"]  {{ color: {PURPLE}; border-color: {PURPLE_ACC}; background: {PURPLE_BG}; }}
QLabel#hotkeyDesc {{ color: {TXT_DIM}; font-size: 10px; letter-spacing: 1px; }}

/* ─ Change hotkey button ─ */
QPushButton#changeBtn {{
    background: #1e1e2a;
    color: {TXT_DIM};
    border: 1px solid #2e2e3e;
    border-radius: 5px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    padding: 5px 12px;
}}
QPushButton#changeBtn:hover {{
    color: {PURPLE};
    border-color: {PURPLE_ACC};
    background: #1a0a30;
}}

/* ─ Info bar ─ */
QLabel#infoLbl {{ color: #2a2a3a; font-size: 10px; letter-spacing: 1px; }}

/* ═ LOGIN ══════════════════════════════════════════════════════════════════ */
QLabel#loginLogo {{
    font-size: 40px;
    background: transparent;
    qproperty-alignment: AlignCenter;
}}
QLabel#loginAppName {{
    color: {GOLD};
    font-size: 18px;
    font-weight: 700;
    letter-spacing: 6px;
    background: transparent;
    qproperty-alignment: AlignCenter;
}}
QLabel#loginTagline {{
    color: {TXT_MUTED};
    font-size: 10px;
    letter-spacing: 3px;
    background: transparent;
    qproperty-alignment: AlignCenter;
}}
QLabel#hwidLbl {{
    color: #44445a;
    font-size: 9px;
    letter-spacing: 1px;
    background: #101014;
    padding: 5px 12px;
    border: 1px solid #1e1e28;
    border-radius: 5px;
    qproperty-alignment: AlignCenter;
}}
QLineEdit#keyInput {{
    background: #111118;
    color: {GOLD};
    border: 1px solid {GOLD_DIM};
    border-radius: 8px;
    padding: 11px 14px;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 2px;
}}
QLineEdit#keyInput:focus    {{ border-color: {GOLD};  }}
QLineEdit#keyInput[s="err"] {{ border-color: {RED};   color: {RED};   }}
QLineEdit#keyInput[s="ok"]  {{ border-color: {GREEN}; color: {GREEN}; }}
QPushButton#loginBtn {{
    background: {GOLD_DIM};
    color: {GOLD};
    border: 1px solid {GOLD};
    border-radius: 8px;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 3px;
    padding: 11px;
}}
QPushButton#loginBtn:hover    {{ background: {GOLD_HVR}; color: white; }}
QPushButton#loginBtn:disabled {{ background: #1e1e1e; color: #444; border-color: #2a2a2a; }}
QLabel#loginStatus {{
    font-size: 11px;
    letter-spacing: 1px;
    min-height: 18px;
    background: transparent;
    qproperty-alignment: AlignCenter;
    color: {TXT_MUTED};
}}
QLabel#loginStatus[s="err"]  {{ color: {RED};   }}
QLabel#loginStatus[s="ok"]   {{ color: {GREEN}; }}
QLabel#loginStatus[s="wait"] {{ color: {BLUE};  }}
QLabel#loginFooter {{
    color: #252535;
    font-size: 9px;
    background: transparent;
    qproperty-alignment: AlignCenter;
}}
"""


def _rf(w):
    w.style().unpolish(w)
    w.style().polish(w)


# ─────────────────────────────────────────────────────────────────────────────
# Login Page
# ─────────────────────────────────────────────────────────────────────────────

class LoginPage(QWidget):
    login_success = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self._init_ui()

    def _init_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 26, 28, 22)
        lay.setSpacing(10)

        logo = QLabel("🔐"); logo.setObjectName("loginLogo"); lay.addWidget(logo)
        name = QLabel("NOVA  DELAY"); name.setObjectName("loginAppName"); lay.addWidget(name)
        sub  = QLabel("LICENSE  VERIFICATION"); sub.setObjectName("loginTagline"); lay.addWidget(sub)
        lay.addSpacing(8)
        hwid = QLabel(f"HWID :  {_get_hwid()}"); hwid.setObjectName("hwidLbl"); lay.addWidget(hwid)
        lay.addSpacing(4)

        self.key_in = QLineEdit()
        self.key_in.setObjectName("keyInput")
        self.key_in.setPlaceholderText("Nhập license key...")
        self.key_in.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_in.returnPressed.connect(self._login)
        lay.addWidget(self.key_in)
        lay.addSpacing(2)

        self.btn = QPushButton("🚀   XÁC THỰC KEY")
        self.btn.setObjectName("loginBtn")
        self.btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn.clicked.connect(self._login)
        lay.addWidget(self.btn)

        self.status_lbl = QLabel(""); self.status_lbl.setObjectName("loginStatus")
        lay.addWidget(self.status_lbl)
        lay.addStretch()
        foot = QLabel("Nova Delay Tool  •  v1.6  •  2025")
        foot.setObjectName("loginFooter"); lay.addWidget(foot)

    def _login(self):
        key = self.key_in.text().strip()
        if not key: self._status("Vui lòng nhập key!", "err"); return
        self.btn.setEnabled(False)
        self._set_key_s("")
        self._status("⏳  Đang kết nối server...", "wait")
        self._worker = KeyVerifyWorker(key)
        self._worker.result_signal.connect(self._on_done)
        self._worker.start()

    def _on_done(self, ok: bool, msg: str):
        self.btn.setEnabled(True)
        if ok:
            self._set_key_s("ok"); self._status(msg, "ok")
            beep_async(880, 100)
            QTimer.singleShot(900, self.login_success.emit)
        else:
            self._set_key_s("err"); self._status("✘  " + msg, "err")
            beep_async(300, 200)

    def _set_key_s(self, s): self.key_in.setProperty("s", s); _rf(self.key_in)
    def _status(self, msg, s):
        self.status_lbl.setText(msg)
        self.status_lbl.setProperty("s", s); _rf(self.status_lbl)


# ─────────────────────────────────────────────────────────────────────────────
# FakeLag Page
# ─────────────────────────────────────────────────────────────────────────────

class FakeLagPage(QWidget):
    _hk_sig = pyqtSignal()   # fired by WinHotkeyManager from background thread
    _scan_done_sig = pyqtSignal(list, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active        = False
        self._worker        = None
        self._mode          = MODE_DROP
        self._dir           = DIR_IN
        self._delay         = DEFAULT_DELAY
        self._upload_delay  = DEFAULT_UPLOAD_DELAY
        self._drop_pct      = DEFAULT_DROP_PCT
        self._game_exes     = None
        self._game_list:    list[dict] = []
        self._drag_pos      = None
        self._restart_count = 0
        self._restarting    = False

        self._scan_done_sig.connect(self._on_scan_done)

        # Hotkey system — works without keyboard library
        hk_name, hk_vk = _default_hk()
        self._hk_name = hk_name
        self._hk_vk   = hk_vk
        self._hk_mgr  = WinHotkeyManager(self._hk_sig.emit)
        self._hk_mgr.register(hk_vk)

        # Also register via keyboard lib if available
        if KEYBOARD_AVAILABLE:
            try: keyboard.add_hotkey(hk_name, self._hk_sig.emit, suppress=False)
            except Exception: pass

        self._pulse = QTimer(self)
        self._pulse.setInterval(800)
        self._pulse.timeout.connect(self._pulse_tick)
        self._p_state = False

        self._watchdog = QTimer(self)
        self._watchdog.setInterval(5000)
        self._watchdog.timeout.connect(self._watchdog_tick)

        self._ui_scan_timer = QTimer(self)
        self._ui_scan_timer.setInterval(3000)
        self._ui_scan_timer.timeout.connect(self._on_ui_scan_tick)

        self._build()
        self._set_mode(MODE_DROP, force=True)

        self._hk_sig.connect(self._toggle)

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(9)
        self._root = root

        self._build_title()

        sep = QFrame(); sep.setObjectName("sep")
        sep.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(sep)

        self.toggle = QPushButton("FAKE LAG : OFF")
        self.toggle.setObjectName("toggleBtn")
        self.toggle.setProperty("active", False)
        self.toggle.setProperty("mode", MODE_DROP)
        self.toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle.clicked.connect(self._toggle)
        root.addWidget(self.toggle)

        self.status = QLabel("IDLE  —  UDP DROP MODE")
        self.status.setObjectName("statusLbl")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status.setProperty("s", "idle")
        root.addWidget(self.status)

        self.restart_lbl = QLabel("")
        self.restart_lbl.setObjectName("restartLbl")
        self.restart_lbl.setVisible(False)
        root.addWidget(self.restart_lbl)

        self._build_mode_row()
        self._build_game_selector_panel()
        self._build_delay_panel()
        self._build_dame_panel()
        self._build_hotkey_row()
        self._root.addStretch()
        self._build_info()

    def _build_title(self):
        row = QHBoxLayout()
        t = QLabel("FAKE LAG TOOL"); t.setObjectName("titleLbl")
        row.addWidget(t); row.addStretch()
        a = QLabel("▲ ADMIN"); a.setObjectName("adminLbl"); row.addWidget(a)
        row.addSpacing(6)

        ss_min = ("QPushButton{background:#2a2a35;color:#888;font-size:13px;"
                  "border:1px solid #3a3a45;border-radius:5px;}"
                  "QPushButton:hover{color:#4ab8ff;background:#0a1e36;border-color:#4ab8ff;}")
        m = QPushButton("−"); m.setFixedSize(26, 26)
        m.setCursor(Qt.CursorShape.PointingHandCursor)
        m.setStyleSheet(ss_min); m.setToolTip("Ẩn xuống khay")
        m.clicked.connect(self._hide_to_tray); row.addWidget(m); row.addSpacing(4)

        ss_cls = ("QPushButton{background:#2a2a35;color:#888;font-size:13px;"
                  "border:1px solid #3a3a45;border-radius:5px;}"
                  "QPushButton:hover{color:#ff5555;background:#3a1010;border-color:#ff3333;}")
        x = QPushButton("✕"); x.setFixedSize(26, 26)
        x.setCursor(Qt.CursorShape.PointingHandCursor)
        x.setStyleSheet(ss_cls); x.clicked.connect(QApplication.quit)
        row.addWidget(x)
        self._root.addLayout(row)

    def _hide_to_tray(self):
        win = self.window()
        if hasattr(win, 'hide_to_tray'): win.hide_to_tray()

    def _build_mode_row(self):
        fr = QFrame(); fr.setObjectName("modeFrame")
        lay = QHBoxLayout(fr)
        lay.setContentsMargins(12, 7, 12, 7); lay.setSpacing(6)

        lbl = QLabel("MODE"); lbl.setObjectName("rowLbl"); lay.addWidget(lbl)
        lay.addStretch()

        self.mdrop  = QPushButton("✂  DROP")
        self.mdelay = QPushButton("⏱  DELAY")
        self.mdame  = QPushButton("⚡ DAME JUMP")
        for btn, m in [(self.mdrop, MODE_DROP), (self.mdelay, MODE_DELAY), (self.mdame, MODE_DAME)]:
            btn.setObjectName("modeBtn"); btn.setProperty("sel", "")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, _m=m: self._set_mode(_m))
            lay.addWidget(btn)

        self._root.addWidget(fr)

    def _build_game_selector_panel(self):
        gf = QFrame(); gf.setObjectName("gameFrame")
        glay = QVBoxLayout(gf)
        glay.setContentsMargins(10, 8, 10, 8); glay.setSpacing(6)

        gr = QHBoxLayout()
        game_lbl = QLabel("🎮  CHỌN TIẾN TRÌNH GAME / VPN"); game_lbl.setObjectName("gameSectionLbl")
        gr.addWidget(game_lbl); gr.addStretch()
        self.scan_btn = QPushButton("🔍  SCAN RUNNING GAMES")
        self.scan_btn.setObjectName("scanBtn")
        self.scan_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.scan_btn.clicked.connect(self._on_scan_games)
        gr.addWidget(self.scan_btn)
        glay.addLayout(gr)

        self.game_combo = QComboBox(); self.game_combo.setObjectName("gameCombo")
        self.game_combo.addItem("🎮  All Games (Generic)", GENERIC_FILTER)
        self.game_combo.currentIndexChanged.connect(self._on_game_selected)
        glay.addWidget(self.game_combo)

        self.scan_status = QLabel("Nhấn SCAN để phát hiện game đang chạy")
        self.scan_status.setObjectName("scanStatusLbl")
        glay.addWidget(self.scan_status)
        self._root.addWidget(gf)

    def _build_delay_panel(self):
        self.delay_frame = QFrame(); self.delay_frame.setObjectName("delayFrame")
        lay = QVBoxLayout(self.delay_frame)
        lay.setContentsMargins(12, 8, 12, 8); lay.setSpacing(8)

        # Direction row
        dr = QHBoxLayout(); dr.setSpacing(6)
        dl = QLabel("DIRECTION"); dl.setObjectName("rowLbl"); dr.addWidget(dl); dr.addStretch()
        self.din   = QPushButton("↓ DOWNLOAD")
        self.dout  = QPushButton("↑ UPLOAD")
        self.dboth = QPushButton("↕ BOTH")
        for btn, d, sel in [(self.din, DIR_IN, "1"), (self.dout, DIR_OUT, ""), (self.dboth, DIR_BOTH, "")]:
            btn.setObjectName("dirBtn"); btn.setProperty("sel", sel)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, _d=d: self._set_dir(_d))
            dr.addWidget(btn)
        lay.addLayout(dr)

        # Delay slider row
        sr = QHBoxLayout(); sr.setSpacing(10)
        sl_lbl = QLabel("DELAY"); sl_lbl.setObjectName("rowLbl"); sr.addWidget(sl_lbl)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setObjectName("slider")
        self.slider.setRange(MIN_DELAY, MAX_DELAY)
        self.slider.setValue(DEFAULT_DELAY)
        self.slider.valueChanged.connect(self._on_delay)
        sr.addWidget(self.slider)
        self.delay_val = QLabel(f"{DEFAULT_DELAY} ms"); self.delay_val.setObjectName("delayVal")
        sr.addWidget(self.delay_val)
        lay.addLayout(sr)

        self.delay_frame.setVisible(False)
        self._root.addWidget(self.delay_frame)

    def _build_dame_panel(self):
        self.dame_frame = QFrame(); self.dame_frame.setObjectName("dameFrame")
        outer = QVBoxLayout(self.dame_frame)
        outer.setContentsMargins(12, 10, 12, 10)
        outer.setSpacing(8)

        # ── Upload Delay slider ───────────────────────────────────────────────
        ur = QHBoxLayout()
        ur.setContentsMargins(0, 4, 0, 4)
        ur.setSpacing(12)
        ul_lbl = QLabel("DELAY  UL")
        ul_lbl.setObjectName("dameRowLbl")
        ur.addWidget(ul_lbl)
        self.ul_slider = QSlider(Qt.Orientation.Horizontal)
        self.ul_slider.setObjectName("dameSlider")
        self.ul_slider.setRange(MIN_UPLOAD_DELAY, MAX_UPLOAD_DELAY)
        self.ul_slider.setValue(DEFAULT_UPLOAD_DELAY)
        self.ul_slider.setMinimumHeight(28)
        self.ul_slider.valueChanged.connect(self._on_upload_delay)
        ur.addWidget(self.ul_slider, stretch=1)
        self.ul_val = QLabel(f"{DEFAULT_UPLOAD_DELAY} ms")
        self.ul_val.setObjectName("ulVal")
        ur.addWidget(self.ul_val)
        outer.addLayout(ur)

        # ── Download Block slider ─────────────────────────────────────────────
        dr2 = QHBoxLayout()
        dr2.setContentsMargins(0, 4, 0, 4)
        dr2.setSpacing(12)
        dl_lbl = QLabel("BLOCK  DL")
        dl_lbl.setObjectName("dameRowLbl")
        dr2.addWidget(dl_lbl)
        self.dl_slider = QSlider(Qt.Orientation.Horizontal)
        self.dl_slider.setObjectName("dameSlider")
        self.dl_slider.setRange(0, 90)
        self.dl_slider.setValue(DEFAULT_DROP_PCT)
        self.dl_slider.setMinimumHeight(28)
        self.dl_slider.valueChanged.connect(self._on_drop_pct)
        dr2.addWidget(self.dl_slider, stretch=1)
        self.dl_val = QLabel(f"{DEFAULT_DROP_PCT}%")
        self.dl_val.setObjectName("dlVal")
        dr2.addWidget(self.dl_val)
        outer.addLayout(dr2)

        # ── Hint ──────────────────────────────────────────────────────────────
        hint = QLabel("⚡ Delay UL = vị trí lên server trễ  →  hitbox desync  →  dame nhảy")
        hint.setObjectName("dameHintLbl")
        hint.setWordWrap(True)
        outer.addWidget(hint)

        self.dame_frame.setVisible(False)
        self._root.addWidget(self.dame_frame)

    def _build_hotkey_row(self):
        fr = QFrame(); fr.setObjectName("hotkeyFrame")
        lay = QHBoxLayout(fr)
        lay.setContentsMargins(12, 9, 12, 9); lay.setSpacing(10)

        self.hk_desc = QLabel("⌨  TOGGLE HOTKEY")
        self.hk_desc.setObjectName("hotkeyDesc")
        lay.addWidget(self.hk_desc); lay.addStretch()

        self.badge = QLabel(self._hk_name)
        self.badge.setObjectName("keyBadge"); self.badge.setProperty("s", "")
        lay.addWidget(self.badge)

        # CHANGE KEY button — always enabled (uses Win32, no external lib needed)
        self.change_btn = QPushButton("🔑  CHANGE KEY")
        self.change_btn.setObjectName("changeBtn")
        self.change_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.change_btn.clicked.connect(self._on_change_key)
        lay.addWidget(self.change_btn)

        self._root.addWidget(fr)

    def _build_info(self):
        row = QHBoxLayout()
        l = QLabel("PyDivert  •  WinDivert  •  Win32 Hotkey"); l.setObjectName("infoLbl")
        r = QLabel("v1.6"); r.setObjectName("infoLbl")
        row.addWidget(l); row.addStretch(); row.addWidget(r)
        self._root.addLayout(row)

    # ── Drag ──────────────────────────────────────────────────────────────────

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint()
    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() & Qt.MouseButton.LeftButton:
            self.window().move(
                self.window().pos() + e.globalPosition().toPoint() - self._drag_pos
            )
            self._drag_pos = e.globalPosition().toPoint()
    def mouseReleaseEvent(self, e): self._drag_pos = None

    # ── Mode / dir / sliders ──────────────────────────────────────────────────
    def _set_mode(self, mode: str, force: bool = False):
        if self._active and not force: return
        self._mode = mode

        for btn, m in [(self.mdrop, MODE_DROP), (self.mdelay, MODE_DELAY), (self.mdame, MODE_DAME)]:
            btn.setProperty("sel", m if mode == m else ""); _rf(btn)

        self.toggle.setProperty("mode", mode); _rf(self.toggle)
        self.delay_frame.setVisible(mode == MODE_DELAY)
        self.dame_frame.setVisible(mode == MODE_DAME)

        h = {MODE_DROP: WIN_H_COMPACT, MODE_DELAY: WIN_H_FULL, MODE_DAME: WIN_H_DAME}[mode]
        win = self.window()
        if win and win != self:
            win.setFixedSize(WIN_W, h)

        self._on_ui_scan_tick()
        if not self._ui_scan_timer.isActive():
            self._ui_scan_timer.start()

        if mode == MODE_DROP:
            self.status.setText("IDLE  —  UDP DROP MODE")
        elif mode == MODE_DELAY:
            self._refresh_delay_status()
        else:
            self.status.setText("IDLE  —  DAME JUMP MODE")
            self.status.setProperty("s", "idle"); _rf(self.status)

        if not self._game_list:
            QTimer.singleShot(100, self._on_scan_games)
    def _set_dir(self, d: str):
        if self._active: return
        self._dir = d
        for btn, _d in [(self.din, DIR_IN), (self.dout, DIR_OUT), (self.dboth, DIR_BOTH)]:
            btn.setProperty("sel", "1" if _d == d else ""); _rf(btn)
        self._refresh_delay_status()

    def _on_delay(self, v: int):
        self._delay = v
        self.delay_val.setText(f"{v} ms")
        if not self._active and self._mode == MODE_DELAY:
            self._refresh_delay_status()

    def _on_upload_delay(self, v: int):
        self._upload_delay = v
        self.ul_val.setText(f"{v} ms")

    def _on_drop_pct(self, v: int):
        self._drop_pct = v
        self.dl_val.setText(f"{v}%")

    def _refresh_delay_status(self):
        names = {DIR_IN: "↓ DL", DIR_OUT: "↑ UL", DIR_BOTH: "↕"}
        self.status.setText(f"IDLE  —  DELAY  {names[self._dir]}  {self._delay} ms")

    # ── Hotkey change ─────────────────────────────────────────────────────────

    def _on_change_key(self):
        if self._active: return          # don't allow change while running
        dlg = KeyCaptureDialog(self._hk_name, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        name = dlg.key_name
        vk   = dlg.key_vk
        if not name or not vk:
            return

        # Unregister old hotkey
        self._hk_mgr.unregister()
        if KEYBOARD_AVAILABLE:
            try: keyboard.remove_hotkey(self._hk_name)
            except Exception: pass

        # Register new hotkey
        self._hk_name = name
        self._hk_vk   = vk
        self._hk_mgr.register(vk)
        if KEYBOARD_AVAILABLE:
            try: keyboard.add_hotkey(name, self._hk_sig.emit, suppress=False)
            except Exception: pass

        self.badge.setText(name)
        self.badge.setProperty("s", self._badge_s()); _rf(self.badge)
        beep_async(880, 80)

    # ── Game scanner (cross-thread safe via signal) ───────────────────────────

    def _on_scan_games(self):
        if self._active: return
        self.scan_btn.setEnabled(False)
        self.scan_btn.setText("⏳  SCANNING…")
        self.scan_status.setText("Đang quét tiến trình…")
        self.scan_status.setStyleSheet("")

        def _worker():
            detected = scan_active_processes()
            self._scan_done_sig.emit(detected, True)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_ui_scan_tick(self):
        if self._active:
            return
        def _worker():
            detected = scan_active_processes()
            self._scan_done_sig.emit(detected, False)
        threading.Thread(target=_worker, daemon=True).start()

    def _on_scan_done(self, detected: list, is_manual: bool):
        if is_manual:
            self._game_list = detected
            self._populate_game_combo(auto_select_running=True)
            self.scan_btn.setEnabled(True)
            self.scan_btn.setText("🔍  SCAN RUNNING GAMES")
        else:
            running_names = {g['name'] for g in detected}
            current_games = []
            for i in range(self.game_combo.count()):
                txt = self.game_combo.itemText(i)
                if "All Processes" not in txt:
                    parts = txt.split("  ")
                    if len(parts) >= 2:
                        current_games.append(parts[1])
            if set(current_games) != running_names:
                self._game_list = detected
                self._populate_game_combo(auto_select_running=False)

    def _populate_game_combo(self, auto_select_running: bool = False):
        self.game_combo.blockSignals(True)
        current_selection = self.game_combo.currentText()
        self.game_combo.clear()

        running_count = 0
        for g in self._game_list:
            label = f"{g['icon']}  {g['name']}"
            self.game_combo.addItem(label, g['exes'])
            running_count += 1

        # Always add fallback Generic option
        self.game_combo.addItem("🌐  All Processes (Generic UDP)", "generic")
        self.game_combo.blockSignals(False)

        # Restore selection if possible and we are not forcing auto-select
        index = -1
        if not auto_select_running:
            index = self.game_combo.findText(current_selection)

        if index >= 0:
            self.game_combo.setCurrentIndex(index)
        else:
            self.game_combo.setCurrentIndex(0)
            self._on_game_selected(0)

        if running_count > 0:
            self.scan_status.setText(f"✔  Tìm thấy {running_count} tiến trình — chọn ứng dụng muốn can thiệp")
            self.scan_status.setStyleSheet(f"color: #00e06a; font-size:10px;")
        else:
            self.scan_status.setText("Không tìm thấy tiến trình nào (dùng All Processes)")
            self.scan_status.setStyleSheet(f"color: #fb923c; font-size:10px;")

    def _on_game_selected(self, idx: int):
        data = self.game_combo.itemData(idx)
        if isinstance(data, list) or isinstance(data, set):
            self._game_exes = set(data)
        else:
            self._game_exes = None

    # ── Worker factory ─────────────────────────────────────────────────────────

    def _make_worker(self):
        if self._mode == MODE_DAME:
            return DameJumpWorker(self._game_exes, self._upload_delay, self._drop_pct)
        elif self._mode == MODE_DELAY:
            return DelayWorker(self._delay, self._dir, self._game_exes)
        else:
            return DropWorker(self._game_exes)

    # ── Watchdog + Auto-restart ────────────────────────────────────────────────

    def _watchdog_tick(self):
        if self._active and self._worker and not self._worker.isRunning():
            self._check_worker_alive()

    def _check_worker_alive(self):
        if self._restarting or not self._active: return
        if self._restart_count < MAX_RESTARTS:
            self._restarting    = True
            self._restart_count += 1
            self.restart_lbl.setText(f"↺  Auto-restart {self._restart_count}/{MAX_RESTARTS}…")
            self.restart_lbl.setVisible(True)
            QTimer.singleShot(600, self._do_restart)
        else:
            self._active = False
            self._watchdog.stop(); self._pulse.stop()
            self.toggle.setText("FAKE LAG : OFF")
            self.toggle.setProperty("active", False); _rf(self.toggle)
            self.status.setText("❌ WORKER THẤT BẠI — THỬ BẬT LẠI")
            self.status.setProperty("s", "error"); _rf(self.status)
            self.badge.setProperty("s", ""); _rf(self.badge)
            self._enable_controls(True)
            beep_async(300, 500)

    def _do_restart(self):
        self._restarting = False
        if not self._active:
            self.restart_lbl.setVisible(False); return
        self._worker = self._make_worker()
        self._worker.status_signal.connect(self._on_status)
        self._worker.error_signal.connect(self._on_error)
        if hasattr(self._worker, 'ports_signal'):
            self._worker.ports_signal.connect(self.scan_status.setText)
        self._worker.finished.connect(self._check_worker_alive)
        self._worker.start()

    # ── Toggle ────────────────────────────────────────────────────────────────

    def _toggle(self):
        if not self._active: self._start()
        else: self._stop()

    def _start(self):
        self._active        = True
        self._restart_count = 0
        self._restarting    = False
        self.restart_lbl.setVisible(False)

        self.toggle.setText("FAKE LAG : ON")
        self.toggle.setProperty("active", True)
        self.toggle.setProperty("mode", self._mode); _rf(self.toggle)
        self._enable_controls(False)

        names = {DIR_IN: "↓ DL", DIR_OUT: "↑ UL", DIR_BOTH: "↕"}
        if self._mode == MODE_DELAY:
            self.status.setText(f"STARTING  {names[self._dir]}  +{self._delay}ms…")
            self.status.setProperty("s", "delay")
        elif self._mode == MODE_DAME:
            gname = self.game_combo.currentText().replace("✔", "").strip()
            self.status.setText(f"⚡ STARTING  {gname}…")
            self.status.setProperty("s", "dame")
        else:
            self.status.setText("DROPPING INBOUND UDP…")
            self.status.setProperty("s", "drop")
        _rf(self.status)
        self.badge.setProperty("s", self._badge_s()); _rf(self.badge)

        beep_async(600)
        self._pulse.start()
        self._watchdog.start()

        self._worker = self._make_worker()
        self._worker.status_signal.connect(self._on_status)
        self._worker.error_signal.connect(self._on_error)
        if hasattr(self._worker, 'ports_signal'):
            self._worker.ports_signal.connect(self.scan_status.setText)
        self._worker.finished.connect(self._check_worker_alive)
        self._worker.start()

    def _stop(self):
        self._active     = False
        self._restarting = False
        self._watchdog.stop(); self._pulse.stop(); self._p_state = False
        self.status.setStyleSheet("")
        self.restart_lbl.setVisible(False)
        if self._worker: self._worker.stop(); self._worker = None
        self._enable_controls(True)
        self.toggle.setText("FAKE LAG : OFF")
        self.toggle.setProperty("active", False); _rf(self.toggle)
        self.status.setProperty("s", "idle")
        if self._mode == MODE_DELAY:  self._refresh_delay_status()
        elif self._mode == MODE_DAME:
            self.status.setText("IDLE  —  DAME JUMP MODE")
            self._on_ui_scan_tick()
        else:                          self.status.setText("IDLE  —  UDP DROP MODE")
        _rf(self.status)
        self.badge.setProperty("s", ""); _rf(self.badge)
        beep_async(400)

    def _enable_controls(self, enabled: bool):
        for w in [self.mdrop, self.mdelay, self.mdame,
                  self.din, self.dout, self.dboth,
                  self.slider, self.ul_slider, self.dl_slider,
                  self.game_combo, self.scan_btn]:
            w.setEnabled(enabled)
        # change_btn: only enable when not active
        self.change_btn.setEnabled(enabled)

    def _on_status(self, msg: str):
        self.status.setText(msg if self._mode == MODE_DAME else msg.upper())

    def _on_error(self, msg: str):
        self.status.setStyleSheet("")
        self.status.setText(f"ERR: {msg[:55]}")
        self.status.setProperty("s", "error"); _rf(self.status)
        beep_async(300, 200)

    def _pulse_tick(self):
        self._p_state = not self._p_state
        self.status.setStyleSheet("color: rgba(255,255,255,0.3);" if self._p_state else "")

    def _badge_s(self) -> str:
        if not self._active: return ""
        return {"drop": "drop", "delay": "delay", "dame": "dame"}.get(self._mode, "")

    def cleanup(self):
        self._hk_mgr.unregister()
        if KEYBOARD_AVAILABLE:
            try: keyboard.remove_hotkey(self._hk_name)
            except Exception: pass
        if self._worker: self._worker.stop()


# ─────────────────────────────────────────────────────────────────────────────
# Main Window
# ─────────────────────────────────────────────────────────────────────────────

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Nova Delay Tool")
        self.setFixedSize(WIN_W, LOGIN_H)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        p = self.palette()
        p.setColor(QPalette.ColorRole.Window, QColor(BG))
        self.setPalette(p); self.setAutoFillBackground(True)
        self._drag_pos = None
        self._build(); self._build_tray()

    def _build_tray(self):
        icon_path = os.path.join(os.path.dirname(os.path.abspath(
            sys.executable if getattr(sys, 'frozen', False) else __file__
        )), "icon.ico")
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
        else:
            pix = QPixmap(32, 32); pix.fill(Qt.GlobalColor.transparent)
            p = QPainter(pix); p.setBrush(QColor(GOLD))
            p.setPen(Qt.PenStyle.NoPen); p.drawRoundedRect(2, 2, 28, 28, 6, 6); p.end()
            icon = QIcon(pix)

        self._tray = QSystemTrayIcon(icon, self)
        self._tray.setToolTip("Nova Delay Tool")
        menu = QMenu()
        menu.setStyleSheet(f"""
            QMenu {{ background:#1a1a1e; border:1px solid #2e2e38; border-radius:6px;
                     color:{TXT}; font-size:12px; padding:4px 0; }}
            QMenu::item {{ padding:6px 18px; }}
            QMenu::item:selected {{ background:#252530; color:{GOLD}; }}
            QMenu::separator {{ height:1px; background:#2e2e38; margin:3px 8px; }}
        """)
        menu.addAction("🖥  Hiện cửa sổ").triggered.connect(self.restore_from_tray)
        menu.addSeparator()
        menu.addAction("✕  Thoát").triggered.connect(QApplication.quit)
        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

    def hide_to_tray(self):
        self.hide()
        if self._tray.isSystemTrayAvailable():
            self._tray.showMessage("Nova Delay Tool",
                "Đã ẩn xuống khay. Nhấn đúp icon để hiện lại.",
                QSystemTrayIcon.MessageIcon.Information, 2500)

    def restore_from_tray(self):
        self.show(); self.raise_(); self.activateWindow()

    def _on_tray_activated(self, r):
        if r == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.restore_from_tray()

    def _build(self):
        root = QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0)
        self.stack = QStackedWidget(); root.addWidget(self.stack)
        self.login_page   = LoginPage()
        self.fakelag_page = FakeLagPage()
        self.stack.addWidget(self.login_page)
        self.stack.addWidget(self.fakelag_page)
        self.stack.setCurrentWidget(self.login_page)
        self.login_page.login_success.connect(self._slide)

    def _slide(self):
        self.setFixedSize(WIN_W, WIN_H_COMPACT)
        self.fakelag_page.setGeometry(WIN_W, 0, WIN_W, WIN_H_COMPACT)
        self.fakelag_page.show()
        ao = QPropertyAnimation(self.login_page, b"pos")
        ao.setDuration(420); ao.setStartValue(QPoint(0, 0))
        ao.setEndValue(QPoint(-WIN_W, 0)); ao.setEasingCurve(QEasingCurve.Type.InOutCubic)
        ai = QPropertyAnimation(self.fakelag_page, b"pos")
        ai.setDuration(420); ai.setStartValue(QPoint(WIN_W, 0))
        ai.setEndValue(QPoint(0, 0)); ai.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._anim = QParallelAnimationGroup()
        self._anim.addAnimation(ao); self._anim.addAnimation(ai)
        self._anim.finished.connect(self._done_slide); self._anim.start()

    def _done_slide(self):
        self.stack.setCurrentWidget(self.fakelag_page)
        self.fakelag_page.move(0, 0); self.login_page.hide()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint()
    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() & Qt.MouseButton.LeftButton:
            self.move(self.pos() + e.globalPosition().toPoint() - self._drag_pos)
            self._drag_pos = e.globalPosition().toPoint()
    def mouseReleaseEvent(self, e): self._drag_pos = None
    def closeEvent(self, e):
        self.fakelag_page.cleanup()
        if hasattr(self, '_tray'): self._tray.hide()
        e.accept()


# ─────────────────────────────────────────────────────────────────────────────
# Entry
# ─────────────────────────────────────────────────────────────────────────────

def main():
    if not is_admin():
        request_elevation(); return

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)

    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window,          QColor(BG))
    pal.setColor(QPalette.ColorRole.WindowText,      QColor(TXT))
    pal.setColor(QPalette.ColorRole.Base,            QColor(PANEL))
    pal.setColor(QPalette.ColorRole.AlternateBase,   QColor(BG))
    pal.setColor(QPalette.ColorRole.Text,            QColor(TXT))
    pal.setColor(QPalette.ColorRole.Button,          QColor(BTN_BG))
    pal.setColor(QPalette.ColorRole.ButtonText,      QColor(TXT))
    pal.setColor(QPalette.ColorRole.Highlight,       QColor(GREEN_BG))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor(GREEN))
    app.setPalette(pal)

    win = MainWindow()
    win.show()

    # .NET check (non-blocking, 500 ms after UI shows)
    def _start_dotnet_check():
        w = DotNetCheckWorker()
        w.result_signal.connect(
            lambda ok, msg: (None if ok else show_dotnet_prompt(win, msg))
        )
        w.start()
        win._dotnet_worker = w   # keep alive

    QTimer.singleShot(500, _start_dotnet_check)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
