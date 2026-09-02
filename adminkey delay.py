import os
import sys
import requests
import hashlib
import base64
import time
import json
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich.align import Align
    from rich import box
    from rich.prompt import Prompt
except ImportError:
    os.system("pip install rich pycryptodome requests")
    print("Đã cài thư viện xong. Vui lòng chạy lại tool!")
    sys.exit()

API_URL = "https://script.google.com/macros/s/AKfycbzyGT_Q9eSVQm8NruSTP-DUak3dvTL2wpuJbeBrkJB5O9G8IbIHKSPmWTpswG98Ah7cbA/exec"
ADMIN_PASSWORD = "Lebao@" 
MASTER_PASSWORD = "Lebao@" 

console = Console()

class Security:
    def __init__(self):
        self.key = hashlib.sha256(MASTER_PASSWORD.encode()).digest()
        self.iv = b'1234567890123456'
    def encrypt(self, raw_data):
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        encrypted_bytes = cipher.encrypt(pad(raw_data.encode(), AES.block_size))
        return base64.urlsafe_b64encode(encrypted_bytes).decode()
    def decrypt(self, enc_data):
        try:
            cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
            decrypted_bytes = unpad(cipher.decrypt(base64.urlsafe_b64decode(enc_data)), AES.block_size)
            return decrypted_bytes.decode()
        except: return "Decryption Error"

sec = Security()

def send_request(params):
    try:
        params['admin_pass'] = ADMIN_PASSWORD
        with console.status("[bold cyan]Đang kết nối tới server...", spinner="dots"):
            resp = requests.post(API_URL, params=params, timeout=15)
            return resp.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}

def func_list_keys():
    result = send_request({"action": "get_all_keys"})
    if result and result.get('status') == 'success':
        try:
            keys_list = json.loads(result.get('message'))
            table = Table(title="DANH SÁCH LICENSE KEY", box=box.ROUNDED, header_style="bold magenta")
            table.add_column("Key Gốc", style="cyan"); table.add_column("Thời hạn", justify="center"); table.add_column("Trạng thái", justify="center"); table.add_column("HWID", style="dim"); table.add_column("Ngày hết hạn", style="yellow")
            for k in keys_list:
                key_raw = sec.decrypt(k['enc'])
                table.add_row(key_raw, str(k['duration']), k['status'], k['hwid'], k['expiry'])
            console.print(table)
        except: console.print("[red]Lỗi hiển thị dữ liệu.[/]")
    else: console.print("[red]Không thể lấy danh sách.[/]")

def func_create_key():
    console.print(Panel.fit("[bold magenta]TẠO KEY MỚI[/]", border_style="magenta"))
    raw_key = Prompt.ask("[bold yellow]➤ Nhập tên Key Gốc[/]").strip()
    if not raw_key: return
    duration = Prompt.ask("[bold yellow]➤ Thời hạn (Số ngày hoặc LIFETIME)[/]", default="30")
    res = send_request({"action": "create_key", "enc_key": sec.encrypt(raw_key), "duration": duration})
    if res.get('status') == 'success': console.print(f"[green]{res.get('message')}[/]")
    else: console.print(f"[red]{res.get('message')}[/]")

def func_reset_hwid():
    raw_key = Prompt.ask("[bold cyan]➤ Nhập Key Gốc cần RESET HWID[/]").strip()
    if not raw_key: return
    res = send_request({"action": "reset_hwid", "enc_key": sec.encrypt(raw_key)})
    if res.get('status') == 'success': console.print(f"[bold green]✔ {res.get('message')}[/]")
    else: console.print(f"[bold red]✘ {res.get('message')}[/]")

def func_delete_key():
    raw_key = Prompt.ask("[bold red]➤ Nhập Key Gốc cần XÓA[/]").strip()
    if not raw_key: return
    res = send_request({"action": "delete_key", "enc_key": sec.encrypt(raw_key)})
    if res.get('status') == 'success': console.print(f"[green]{res.get('message')}[/]")
    else: console.print(f"[red]{res.get('message')}[/]")

def main_menu():
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        console.print(Align.center("[bold red]NOVA DELAYDAME - ADMIN SYSTEM[/]\n"))
        console.print("[1] Xem danh sách Key")
        console.print("[2] Tạo Key mới")
        console.print("[3] RESET HWID")
        console.print("[4] Xóa Key")
        console.print("[0] Thoát")
        choice = Prompt.ask("\n[bold yellow]➤ Lựa chọn[/]", choices=["1", "2", "3", "4", "0"], default="1")
        if choice == "1": func_list_keys()
        elif choice == "2": func_create_key()
        elif choice == "3": func_reset_hwid()
        elif choice == "4": func_delete_key()
        elif choice == "0": break
        Prompt.ask("\nNhấn Enter để quay lại...")

if __name__ == "__main__":
    main_menu()
