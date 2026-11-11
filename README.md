# tts-server

Petit serveur local qui joue le rôle d'Azure Speech ou d'AWS Polly pour le MVP : on lui donne
du texte, il renvoie de l'audio et de vrais visèmes. Voir `docs/visemes-architecture-tts-stt.md`
à la racine du dépôt pour le contexte complet (pourquoi ce serveur existe, les 3 solutions
possibles, et pourquoi celle-ci est recommandée pour le MVP).

**Statut : implémenté et testé bout en bout** (vrai audio généré, vraie analyse Rhubarb, 8
tests automatisés qui passent).

---

## 1. Principe

Le `brain` appelle ce serveur exactement comme il appellerait Azure ou AWS : une seule
requête HTTP, texte en entrée, audio + visèmes en sortie, protégée par une clé. Plus tard,
passer à un vrai service payant ne demande qu'un changement de configuration côté `brain`,
pas de changement de logique.

En interne, le serveur enchaîne deux outils :
1. **edge-tts** (bibliothèque Python, gratuite, sans compte) génère l'audio à partir du texte,
   avec `en-US-AnaNeural` (voix "Cartoon/Conversation" conçue par Microsoft pour le contenu
   enfants) à un débit légèrement ralenti (`-12%`) pour des pauses plus naturelles — voir
   `DEFAULT_VOICE`/`DEFAULT_RATE` dans `app/tts.py`.
2. **Rhubarb Lip Sync** (binaire externe, gratuit, hors ligne) analyse cet audio et détecte les
   vraies positions de bouche.

Le résultat de Rhubarb est converti vers notre format habituel de visèmes (id 0-21, voir
`visemes.md`), pour que ce soit directement compatible avec le message `visemes` déjà utilisé
partout dans le projet.

---

## 2. Installation

### 2.1 Créer un environnement virtuel Python isolé

Pour ne pas installer les dépendances du serveur dans ton Python global :

```bash
cd pixo-mascot/tools/tts-server
python -m venv .venv
```

Activer l'environnement (à refaire à chaque nouvelle session de terminal) :

```powershell
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

```bash
# Windows (Git Bash) / Linux / macOS
source .venv/Scripts/activate   # Git Bash sur Windows
source .venv/bin/activate       # Linux / macOS
```

Le terminal affiche `(.venv)` devant l'invite une fois activé. Pour sortir de l'environnement :
`deactivate`.

### 2.2 Installer les dépendances du serveur

Une fois l'environnement activé :

```bash
pip install -e ".[dev]"
```

### 2.3 Installer ffmpeg

Nécessaire car Rhubarb ne lit pas le mp3 directement (seulement wav/ogg) — edge-tts ne produit
que du mp3, donc une conversion est obligatoire.

```powershell
# Windows
winget install --id Gyan.FFmpeg -e
```

```bash
# macOS (avec Homebrew)
brew install ffmpeg

# Linux (Debian/Ubuntu)
sudo apt install ffmpeg

# Linux (Fedora)
sudo dnf install ffmpeg
```

**Piège fréquent sur Windows** : `winget` ajoute bien `ffmpeg` au PATH utilisateur, mais un
terminal (ou VS Code) déjà ouvert **avant** l'installation ne voit pas cette mise à jour tant
qu'il n'est pas redémarré — la commande `/synthesize` échoue alors avec une erreur
`FileNotFoundError: [WinError 2]`. Deux solutions : redémarrer le terminal/VS Code, ou (plus
fiable, pas besoin d'attendre) renseigner `FFMPEG_PATH` dans `.env` avec le chemin complet
(affiché par `winget list --id Gyan.FFmpeg` ou cherché dans
`%LOCALAPPDATA%\Microsoft\WinGet\Packages\`) — voir §5.

### 2.4 Installer Rhubarb Lip Sync

Télécharger le zip correspondant à ton système depuis les
[releases GitHub officielles](https://github.com/DanielSWolf/rhubarb-lip-sync/releases/latest)
(`Rhubarb-Lip-Sync-*-Windows.zip`, `-macOS.zip` ou `-Linux.zip`), puis extraire l'exécutable
(`rhubarb.exe` sur Windows, `rhubarb` sur macOS/Linux) dans `tools/tts-server/bin/` — ce dossier
est ignoré par git (voir `.gitignore`), chacun le récupère de son côté, une seule fois.

Vérifier que ça fonctionne :

```bash
./bin/rhubarb.exe --version   # Windows
./bin/rhubarb --version       # macOS / Linux
```

`bin/` n'est jamais ajouté au PATH système : `.env.example` fixe déjà `RHUBARB_PATH` en
conséquence (voir §5), rien à faire de plus ici. Si `ffmpeg` n'est pas non plus dans le PATH
système, indiquer son chemin complet via `FFMPEG_PATH` dans `.env`.

---

## 3. Architecture des fichiers

```text
tts-server/
├── pyproject.toml            # dépendances (fastapi, uvicorn, edge-tts) et métadonnées
├── README.md                 # ce fichier
├── Dockerfile                 # image Linux pour déployer (Render, etc.) — voir §9
├── .dockerignore               # exclut .venv/bin/tests/.env de l'image
├── .env.example               # modèle de variables d'environnement (clé API, port, chemins)
├── bin/                        # binaire Rhubarb Windows téléchargé localement — PAS commité (.gitignore)
├── app/
│   ├── __init__.py
│   ├── main.py                 # point d'entrée FastAPI : déclare /synthesize, /analyze, /health
│   ├── settings.py              # lit la config depuis l'environnement (.env)
│   ├── auth.py                  # vérifie la clé API reçue dans l'en-tête X-API-Key
│   ├── tts.py                   # appelle edge-tts, génère l'audio à partir du texte
│   ├── rhubarb.py               # convertit le mp3 en wav (ffmpeg), lance Rhubarb, lit son JSON
│   └── viseme_mapping.py        # table de correspondance formes Rhubarb (A, B, C... X) -> ids 0-21
└── tests/
    ├── conftest.py              # fixe une clé API de test avant l'import de l'app
    ├── test_auth.py             # requête sans clé / avec mauvaise clé -> rejetée
    ├── test_viseme_mapping.py   # chaque forme Rhubarb se traduit vers le bon id
    └── test_main.py             # /health, /synthesize, /analyze répondent (edge-tts/Rhubarb mockés)
```

Chaque fichier a une seule responsabilité : `tts.py` ne connaît rien de Rhubarb, `rhubarb.py`
ne connaît rien d'edge-tts, `main.py` se contente d'assembler les deux et de répondre. Les
tests mockent `tts.py`/`rhubarb.py` plutôt que d'appeler les vrais outils externes — rapides et
fiables même sans edge-tts/ffmpeg/Rhubarb installés (voir §6 pour le vrai test bout en bout).

---

## 4. Forme de l'API

### `POST /synthesize`

Requête :

```http
POST /synthesize HTTP/1.1
Content-Type: application/json
X-API-Key: <clé secrète>

{
  "text": "Hello Pixo"
}
```

Réponse si la clé est valide (`200 OK`) :

```json
{
  "audio_base64": "SUQzBAAAAAAA...",
  "frames": [
    { "id": 20, "offset_ms": 6 },
    { "id": 1, "offset_ms": 81 },
    { "id": 19, "offset_ms": 137 },
    { "id": 0, "offset_ms": 1530 }
  ]
}
```

- `audio_base64` : l'audio généré (mp3), encodé en base64.
- `frames` : exactement le même format que le message `visemes` existant (`id` 0-21,
  `offset_ms` en millisecondes depuis le début de l'audio) — aucune conversion nécessaire côté
  appelant.

Réponse si la clé est absente ou invalide (`401 Unauthorized`) :

```json
{ "detail": "Clé API invalide ou manquante." }
```

### `POST /analyze`

Même analyse Rhubarb que `/synthesize`, mais sur un audio **déjà existant** (pas de synthèse) —
pour un cas comme `sing_with_me` où le son (une chanson, pas de la parole synthétisée) existe
déjà en fichier.

Requête (`multipart/form-data`, champ `file`) :

```http
POST /analyze HTTP/1.1
Content-Type: multipart/form-data; boundary=...
X-API-Key: <clé secrète>

--...
Content-Disposition: form-data; name="file"; filename="song_hello.mp3"
Content-Type: audio/mpeg

<octets du fichier audio>
--...--
```

Réponse si la clé est valide (`200 OK`) :

```json
{
  "frames": [
    { "id": 20, "offset_ms": 6 },
    { "id": 1, "offset_ms": 81 }
  ]
}
```

Mêmes erreurs que `/synthesize` : `401` si la clé est absente/invalide, `502` si
ffmpeg/Rhubarb échouent.

### `GET /health`

Simple vérification que le serveur tourne, sans authentification :

```json
{ "status": "ok" }
```

---

## 5. Configuration (clé API)

- La clé attendue est lue depuis la variable d'environnement `TTS_SERVER_API_KEY`, jamais
  écrite en dur dans le code.
- Copier `.env.example` vers `.env` (ce dernier n'est **jamais** commité, déjà dans
  `.gitignore`), puis y mettre une vraie clé :

  ```env
  TTS_SERVER_API_KEY=change-moi
  PORT=8080
  # rhubarb.exe vit dans bin/ (§2.4), jamais sur le PATH système : nécessaire, pas optionnel.
  RHUBARB_PATH=./bin/rhubarb.exe
  # Si "winget install" vient d'être lancé dans un AUTRE terminal que celui-ci, ce terminal-ci
  # ne voit pas encore le nouveau PATH (voir le piège décrit en §2.3) : mets le chemin complet
  # ici plutôt que d'attendre un redémarrage.
  # FFMPEG_PATH=C:\chemin\vers\ffmpeg.exe
  ```

- Générer une clé aléatoire :

  ```bash
  python -c "import secrets; print(secrets.token_hex(32))"
  ```

- Le client (le `brain`, ou le simulateur pour tester) doit envoyer cette même valeur dans
  l'en-tête `X-API-Key` à chaque requête.

---

## 6. Tester manuellement

Toutes les commandes ci-dessous, dans l'ordre, depuis `pixo-mascot/tools/tts-server` (environnement
virtuel activé, voir §2.1) :

```bash
# 1. Installer les dépendances (si pas déjà fait)
pip install -e ".[dev]"

# 2. Configurer la clé API
cp .env.example .env
# puis éditer .env et remplacer "change-moi" par une vraie clé

# 3. Démarrer le serveur (reste ouvert dans ce terminal)
uvicorn app.main:app --reload --port 8080
```

Dans un **second terminal**, toujours depuis `pixo-mascot/tools/tts-server` :

```bash
# Vérifier que le serveur répond
curl http://localhost:8080/health

# Demander une vraie synthèse (remplacer la clé par la tienne)
curl -X POST http://localhost:8080/synthesize \
  -H "X-API-Key: ta-cle-ici" \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello Pixo"}'

# Vérifier que ça refuse bien sans clé (doit renvoyer 401)
curl -i -X POST http://localhost:8080/synthesize \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello Pixo"}'
```

La réponse de `/synthesize` contient `audio_base64` (très long) et `frames` (la liste des
visèmes avec leur instant en millisecondes) — si tu vois une liste de plusieurs `frames` avec
des `id` variés (pas juste des `0`), le pipeline complet (edge-tts + ffmpeg + Rhubarb) fonctionne.

---

## 7. Lancer les tests automatisés

```bash
pytest -v
```

11 tests, tous mockés (pas besoin d'edge-tts/ffmpeg/Rhubarb installés pour les faire passer) —
complémentaire au test manuel du §6, qui lui vérifie le vrai pipeline.

---

## 8. Validation de bout en bout avec le frontend

Fait : `tools/frontend-simulator` a une commande `say_tts_server <texte>` qui appelle ce
serveur au lieu de faire la synthèse directement en Python — testée avec un vrai appel (audio +
visèmes réels reçus et rejoués). Voir le README du simulateur pour l'utiliser (nécessite ce
serveur déjà lancé, et `TTS_SERVER_API_KEY` dans l'environnement du simulateur).

Important : le son du microservice joue sur le PC (comme pour `say_azure`/`say_edge`), pas sur
le téléphone — l'audio réel passera par LiveKit une fois le `brain` intégré, pas par ce canal de
test. Voir `docs/visemes-architecture-tts-stt.md` pour l'architecture complète.

---

## 9. Déploiement (Docker / Render)

**Statut : testé réellement en local** — image construite, conteneur lancé, et les 3 endpoints
(`/health`, `/synthesize`, `/analyze`) appelés pour de vrai (pas mockés) à l'intérieur d'un
conteneur Linux, plus les 11 tests `pytest` qui passent dans ce même conteneur. Pas encore
déployé sur Render lui-même (pas testé) — seule la partie "ça tourne sur Linux" est validée.

### 9.1 Pourquoi un Dockerfile (pas juste "Python sur Render")

Le code Python (`app/`) est multiplateforme sans rien à changer. Le seul problème est
`bin/rhubarb.exe` (§2.4) : c'est un binaire **Windows**, inutilisable sur Render (Linux). Le
`Dockerfile` télécharge donc, pendant le build, le build **Linux officiel** de Rhubarb Lip Sync
— exactement la même version (1.14.0) que celle utilisée en dev Windows, pour un résultat
identique — plus `ffmpeg` via `apt-get`. Le reste (pip install, lancement d'uvicorn) est standard.

### 9.2 Construire et tester l'image en local

```bash
docker build -t tts-server .
docker run -d --name tts-server -p 8080:8080 -e TTS_SERVER_API_KEY=une-cle-de-test tts-server
curl http://localhost:8080/health
curl -X POST http://localhost:8080/synthesize \
  -H "X-API-Key: une-cle-de-test" -H "Content-Type: application/json" \
  -d '{"text": "Hello Pixo"}'
```

Si `frames` contient plusieurs visèmes avec des `id` variés (pas que des `0`), le pipeline
Linux complet (edge-tts + ffmpeg + Rhubarb Linux) fonctionne — exactement ce qui a été vérifié
aujourd'hui.

### 9.3 Déployer sur Render

1. Pousser ce dépôt sur GitHub.
2. Sur Render : **New → Web Service**, connecter le repo, choisir **Environment: Docker**
   (Render détecte le `Dockerfile` automatiquement, rien à configurer de plus côté build).
3. Dans **Environment Variables**, ajouter `TTS_SERVER_API_KEY` avec une vraie clé secrète
   (jamais celle de `.env` local, jamais commitée) — c'est la seule variable obligatoire,
   `PORT` est déjà fourni automatiquement par Render et lu par le `CMD` du Dockerfile.
4. Render fournit automatiquement une URL en HTTPS (`https://....onrender.com`) — pas de
   certificat à gérer.
5. Côté `brain`/simulateur : remplacer l'URL locale (`http://localhost:8080`) par l'URL Render,
   en gardant le même en-tête `X-API-Key`.

**Point important, pas encore fait** : aujourd'hui, `brain/` n'appelle ce serveur **nulle part**
(il utilise Speaches/Kokoro en local) — seul `tools/frontend-simulator` s'en sert. Déployer sur
Render le rend joignable depuis internet, mais ne branche pas automatiquement le `brain` dessus
: ça reste un développement séparé, à faire si le besoin réel est "le `brain` utilise ce serveur
en prod" plutôt que "pouvoir tester/démontrer sans dépendre de mon PC".

### 9.4 Sécurité

Le seul mécanisme de sécurité est la clé partagée `X-API-Key` (§5), vérifiée sur chaque route
sauf `/health`. Pour ce cas d'usage (service interne appelé par le `brain`, jamais par un
navigateur), c'est suffisant :
- Pas de secret dans le code ni dans l'image (clé lue depuis l'environnement Render,
  jamais commitée — voir `.dockerignore` qui exclut `.env`).
- HTTPS géré automatiquement par Render, rien à configurer.
- Pas de CORS nécessaire : un appel serveur-à-serveur (brain → tts-server), pas un appel
  navigateur.

Deux améliorations possibles plus tard, pas bloquantes pour une démo :
- `auth.py` compare la clé avec `!=` (pas en temps constant) — remplacer par
  `secrets.compare_digest` supprimerait un risque théorique d'attaque par timing.
- Aucune limite de taille sur `/analyze` (upload de fichier) — un appelant qui a la clé pourrait
  envoyer un fichier énorme. Pas un risque réel tant que la clé reste privée.
