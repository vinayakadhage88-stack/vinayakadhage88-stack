import subprocess
import json
import os
import customtkinter as ctk
from tkinter import messagebox, simpledialog
from cryptography.fernet import Fernet
import qrcode
from PIL import Image
import pystray


# =========================
# 🔐 ENCRYPTION VAULT
# =========================

KEY_FILE = "vault.key"
DATA_FILE = "vault.enc"


def load_key():
    if not os.path.exists(KEY_FILE):
        key = Fernet.generate_key()
        with open(KEY_FILE, "wb") as f:
            f.write(key)
    else:
        key = open(KEY_FILE, "rb").read()
    return key


fernet = Fernet(load_key())


def save_vault(data):
    enc = fernet.encrypt(json.dumps(data).encode())
    with open(DATA_FILE, "wb") as f:
        f.write(enc)


def load_vault():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "rb") as f:
        return json.loads(fernet.decrypt(f.read()).decode())


# =========================
# 🔑 AUTH SYSTEM
# =========================

ADMIN_PASS = "admin123"  # change this


def login():
    pwd = simpledialog.askstring("Login", "Enter Admin Password:", show="*")
    return pwd == ADMIN_PASS


# =========================
# 📡 WIFI FUNCTIONS
# =========================

def run_netsh(args):
    return subprocess.run(
        ["netsh", "wlan"] + args,
        capture_output=True,
        text=True,
        encoding="cp1252",
        errors="ignore"
    ).stdout


def get_profiles():
    out = run_netsh(["show", "profiles"])
    return [l.split(":")[1].strip() for l in out.splitlines() if "All User Profile" in l]


def get_password(profile):
    out = run_netsh(["show", "profile", f"name={profile}", "key=clear"])
    for l in out.splitlines():
        if "Key Content" in l:
            return l.split(":")[1].strip()
    return ""


def reconnect(profile):
    run_netsh(["connect", f"name={profile}"])


# =========================
# 📱 QR CODE GENERATOR
# =========================

def make_wifi_qr(ssid, password):
    data = f"WIFI:T:WPA;S:{ssid};P:{password};;"
    img = qrcode.make(data)
    path = f"{ssid}_qr.png"
    img.save(path)
    return path


# =========================
# 🪟 GUI APP
# =========================

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("WiFi Manager PRO v2")
        self.geometry("900x550")

        if not login():
            messagebox.showerror("Access Denied", "Wrong Password")
            self.destroy()
            return

        self.data = []

        ctk.set_appearance_mode("dark")

        # TOP BAR
        top = ctk.CTkFrame(self)
        top.pack(fill="x", padx=10, pady=10)

        ctk.CTkButton(top, text="Load WiFi", command=self.load).pack(side="left", padx=5)
        ctk.CTkButton(top, text="Backup Vault", command=self.backup).pack(side="left", padx=5)
        ctk.CTkButton(top, text="Restore Vault", command=self.restore).pack(side="left", padx=5)

        # LIST AREA
        self.frame = ctk.CTkScrollableFrame(self)
        self.frame.pack(fill="both", expand=True, padx=10, pady=10)

    # -------------------------
    # LOAD WIFI
    # -------------------------
    def load(self):
        self.data = []
        profiles = get_profiles()

        for p in profiles:
            pw = get_password(p)
            self.data.append({"ssid": p, "password": pw})

        self.render()

    # -------------------------
    # UI RENDER
    # -------------------------
    def render(self):
        for w in self.frame.winfo_children():
            w.destroy()

        for item in self.data:
            row = ctk.CTkFrame(self.frame)
            row.pack(fill="x", pady=5)

            ctk.CTkLabel(row, text=item["ssid"], width=200).pack(side="left", padx=10)
            ctk.CTkLabel(row, text=item["password"], width=200).pack(side="left")

            ctk.CTkButton(row, text="Reconnect",
                          command=lambda s=item["ssid"]: reconnect(s)).pack(side="right", padx=5)

            ctk.CTkButton(row, text="QR",
                          command=lambda i=item: self.qr(i)).pack(side="right", padx=5)

    # -------------------------
    # QR GENERATION
    # -------------------------
    def qr(self, item):
        path = make_wifi_qr(item["ssid"], item["password"])
        Image.open(path).show()

    # -------------------------
    # VAULT
    # -------------------------
    def backup(self):
        save_vault(self.data)
        messagebox.showinfo("Saved", "Encrypted backup created")

    def restore(self):
        self.data = load_vault()
        self.render()


# =========================
# 🧷 SYSTEM TRAY (MINIMIZE MODE)
# =========================

def tray_icon(app):
    def show():
        app.after(0, app.deiconify)

    def hide():
        app.withdraw()

    icon = pystray.Icon(
        "WiFiManager",
        None,
        menu=pystray.Menu(
            pystray.MenuItem("Open", show),
            pystray.MenuItem("Hide", hide),
            pystray.MenuItem("Exit", lambda: app.destroy())
        )
    )
    icon.run()


# =========================
# 🚀 RUN APP
# =========================

if __name__ == "__main__":
    app = App()

    # run tray in background
    import threading
    threading.Thread(target=tray_icon, args=(app,), daemon=True).start()

    app.mainloop()