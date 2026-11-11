# G3Video

<div align="center">
  <img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/flask-3.0%2B-green" alt="Flask 3.0+">
  <img src="https://img.shields.io/badge/license-MIT-yellow" alt="MIT License">
</div>

<br>

<div align="center">
  <img src="logoG3Video.png" alt="G3Video logo">
  <p><em>Stream YouTube videos on your iMac G3 via QuickTime Player</em></p>
</div>

---

## Architecture

```
┌─ iMac G3 (Classilla / IE5 / Netscape) ─────────────────────┐
│  ┌──────────┐   ┌──────────────┐   ┌──────────────────┐    │
│  │ Recherche │──▶│ Page vidéo  │──▶│ QuickTime Player │    │
│  │ YouTube   │   │ (polling    │   │ (.qtl → .mov)    │    │
│  │           │   │  meta-refresh)  │                  │    │
│  └─────┬─────┘   └──────┬───────┘   └──────────────────┘    │
└────────┼────────────────┼───────────────────────────────────┘
         │                │
    HTTP │           HTTP │
         ▼                ▼
┌─ Serveur Linux (Python/Flask) ──────────────────────────────┐
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │              Flask (app/server.py)                   │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │    │
│  │  │ GET /    │  │ GET      │  │ GET /watch        │   │    │
│  │  │ Accueil  │  │ /search  │  │ (statut + polling)│   │    │
│  │  └──────────┘  └──────────┘  └────────┬─────────┘   │    │
│  │                                       │              │    │
│  │  ┌──────────┐  ┌──────────┐  ┌────────▼─────────┐   │    │
│  │  │ GET      │  │ GET      │  │ GET /status/<id> │   │    │
│  │  │ /videos/ │  │ /videos/ │  │ (JSON API)       │   │    │
│  │  │ <id>.mov │  │ <id>.qtl │  └──────────────────┘   │    │
│  │  └──────────┘  └──────────┘                          │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌──────────────────┐    ┌──────────────────┐               │
│  │ app/youtube.py   │    │ app/transcoder.py│               │
│  │ Recherche        │    │ File d'attente   │               │
│  │ YouTube via      │    │ + téléchargement │               │
│  │ yt-dlp           │    │ + transcodage    │               │
│  └────────┬─────────┘    └────────┬─────────┘               │
│           │                      │                          │
│           ▼                      ▼                          │
│  ┌──────────────────────────────────────────────┐           │
│  │           yt-dlp  +  ffmpeg                  │           │
│  │  YouTube ──▶ .mp4 (480p) ──▶ .mov (SV3+QDM2)│           │
│  │  (search/download)      (transcode)          │           │
│  └──────────────────────────────────────────────┘           │
│                                                              │
│  ┌──────────────────────────────────────────────┐           │
│  │  Stockage temporaire ( /tmp/g3video/ )       │           │
│  │  + nettoyage automatique (fichiers > 1h)     │           │
│  └──────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────┘
```

### Composants

| Module | Rôle |
|---|---|
| `app/server.py` | Serveur Flask — routes HTTP, templates, nettoyage automatique |
| `app/youtube.py` | Recherche YouTube via `yt-dlp --flat-playlist --dump-json` |
| `app/transcoder.py` | File d'attente asynchrone : download + transcodage .mov |
| `app/templates/` | Pages HTML 4.01 Transitional, style Mac OS 9 Platinum (compatibles Classilla/IE5/Netscape) |
| `run.py` | Point d'entrée du serveur |

### Format de sortie

| Propriété | Valeur |
|---|---|
| Conteneur | `.mov` |
| Codec vidéo | `svq3` (Sorenson Video 3) ou `mpeg4` (fallback) |
| Codec audio | `qdm2` (QDesign Music 2) ou `adpcm_ima_qt` (fallback) |
| Résolution | 320×240 |
| Débit vidéo | ~500 kbps |
| Audio | 22 kHz mono, ~32 kbps |
| Faststart | `-movflags +faststart` |

Les encodeurs sont détectés automatiquement au premier transcodage. Si `svq3` ou `qdm2` ne sont pas disponibles dans votre build ffmpeg, le serveur bascule sur `mpeg4` + `adpcm_ima_qt` sans intervention manuelle.

---

## Prérequis

- **Python 3.10+**
- **ffmpeg** — avec les codecs `svq3` et `qdm2` (vérifier avec `ffmpeg -encoders \| grep -E 'svq3\|qdm2'`)
- **yt-dlp** — installé automatiquement via `pip`
- **Réseau local** — le serveur doit être accessible depuis l'iMac G3

## Installation

```bash
git clone <repo>
cd G3Video
pip install -r requirements.txt
```

## Lancement

```bash
python3 run.py
```

Par défaut le serveur écoute sur `http://0.0.0.0:5000`.

**Variables d'environnement :**

| Variable | Défaut | Description |
|---|---|---|
| `G3VIDEO_HOST` | `0.0.0.0` | Adresse d'écoute |
| `G3VIDEO_PORT` | `5000` | Port d'écoute |
| `FLASK_DEBUG` | `false` | Mode debug (`1` ou `true`) |

### Utilisation

1. Lancer `python3 run.py` sur la machine Linux
2. Trouver l'IP : `ip addr show | grep 192.168`
3. Sur l'iMac G3, ouvrir Classilla et aller à `http://192.168.X.X:5000/`
4. Chercher une vidéo courte (< 3 min) pour tester
5. Cliquer "Regarder" → attendre le transcodage → cliquer le lien `.qtl`
6. QuickTime Player se lance et lit la vidéo

---

## Limitations connues

- **qdm2** peut ne pas être disponible dans certains builds ffmpeg (fallback : `adpcm_ima_qt` ou `pcm_s16le`)
- **svq3** est lent (pas d'accélération matérielle) → privilégier les vidéos courtes
- Classilla peut ne pas associer automatiquement `.qtl` → le lien `.mov` direct est toujours disponible
- Un seul transcodage à la fois (file d'attente séquentielle)
