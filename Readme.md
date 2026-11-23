# C2 - Command and Control


> **Projet purement éducatif** Ce code est destiné à l'apprentissage et à la compréhension des mécanismes de Command and Control. Toute utilisation en dehors d'un cadre légal et autorisé est interdite.


**Groupe** : Paul Goujet & Quentin Labourdette


Projet C2 en Python permettant de piloter des agents distants depuis un serveur


## Architecture


Le projet est composé de 3 blocs :


- **Serveur C2** (`src/C2.py`) : serveur TCP multi-threadé avec un interpréteur de commandes. Il gère:
    - connexions des agents
    - envoie des ordres
    - affichage des résultats


- **Client** (`src/client.py`) : commun aux deux OS. Se connecte au serveur, envoie ses infos puis écoute les commandes en boucle. Se reconnecte automatiquement en cas de perte de connexion.


- **Modules en fonction de l’OS** (`src/modules/`) : fonctions spécifiques à chaque OS


## Communication


Tous les échanges sont basé sur TCP :


1. Les 4 premiers octets contiennent la taille du message
2. Les octets suivants contiennent le message lui-même


Les messages texte sont des JSON encodés en UTF-8. Les données binaires suivent le même format 4 octets + contenu.


## Commandes


### Gestion des agents
| Commande | Description |
|---|---|
| `agents` | Liste les agents connectés avec leurs infos |
| `use <id>` | Sélectionne un agent par son ID |
| `kill <id>` | Déconnecte un agent |


### Commandes sur un agent (necessite d’avoir selectionné un agent avec `use <id>`)
| Commande | Description |
|---|---|
| `shell <cmd>` | Execute une commande shell/powershell |
| `screenshot` | Prend une capture d'écran (nécessite une interface graphique, ne fonctionne pas sur un serveur Linux sans écran) |
| `sysinfo` | Récupère les infos système |
| `ip` | Récupère l'adresse IP réelle |
| `list_users` | Liste les utilisateurs de la machine |
| `persistence` | Installe la persistance au démarrage |
| `upload <fichier> <dest>` | Envoie un fichier local vers l'agent |


### Commandes Windows uniquement
| Commande | Description |
|---|---|
| `sam` | Sauvegarde la base SAM. Necessite que le client soit lancé en administrateur |
| `registry` | Ajoute une clef de registre |


### Commandes Linux uniquement
| Commande | Description |
|---|---|
| `shadow` | Recupere /etc/passwd et /etc/shadow |
| `list_home` | Liste le contenu de /root et /home récursivement |


### Commandes globales
| Commande | Description |
|---|---|
| `broadcast <cmd>` | Envoie une commande à tous les agents |
| `help` | Affiche l'aide |
| `exit` | Arrête le serveur |


## Prérequis


- Python 3.10+
- Modules Python : `mss`


```bash
pip install mss Pillow
```


Sur Windows, le module `winreg` est inclus dans la bibliothèque standard. Sur Linux, `mss` nécessite un serveur X ou Wayland pour les screenshots.


## Utilisation


### Lancer le serveur C2
```bash
python src/C2.py
```
Le serveur écoute par défaut sur `0.0.0.0:8080`.


### Lancer un client
```bash
python src/client.py -ip <IP_DU_SERVEUR> -port 8080
```


## Choix techniques


### Pourquoi TCP et les sockets ?


On aurait pu partir sur du HTTP ou des WebSockets, mais avec TCP on a un contrôle total sur ce qui transite, pas de headers inutiles, pas d'overhead et le serveur et le client communiquent dans les deux sens, sans polling. 


### Pourquoi les threads et pas des processus (fork) ?


On a choisi les threads principalement pour une raison : tous les threads partagent la même mémoire. Concrètement, ils accèdent tous au même dictionnaire agents, ce qui rend le listing, la sélection et le broadcast simples à implémenter. Avec des processus séparés, faire communiquer tout ça ensemble aurait été plus compliqué. 


### Pourquoi `mss` pour les screenshots ?


- **Cross-plateforme** : fonctionne sur windows et linux avec la même API
- **Pas de dépendance lourde** : `mss` est un module full python


