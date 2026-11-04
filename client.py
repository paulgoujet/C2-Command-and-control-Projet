#Client principal
import socket
import json
import struct
import platform

ENCODING ="utf-8"
SERVER_HOST = ""
SERVER_PORT= "8080"
RETRY_DELAY = 5
IS_WINDOWS = platform.system() == "Windows"

def send_msg(sock: socket.socket, payload: dict) -> None:
    """Pour envoyer un json"""
    data = json.dumps(payload).encode(ENCODING)
    sock.sendall(struct.pack(">I", len(data)) + data)

def send_bytes(sock: socket.socket, blob: bytes, meta: dict) -> None:
    """Pour envoyer un screnshot"""
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
        raise ConnectionError("connexion coupée par le serveur")
    (msg_len,) = struct.unpack(">I", raw_len)
    data = _receiveN(sock, msg_len)
    if data is None:
        raise ConnectionError("connexion interrompue en cours de message")
    return json.loads(data.decode(ENCODING))


