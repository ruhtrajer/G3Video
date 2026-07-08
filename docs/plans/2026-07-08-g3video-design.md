# G3Video — Design Document

## Contexte

Lire YouTube sur un iMac G3 (Mac OS 8.6 à 9) équipé de QuickTime 5, connecté en Ethernet à une machine Linux moderne. L'utilisateur doit pouvoir naviguer, chercher des vidéos YouTube depuis l'iMac et les lire dans QuickTime Player.

## Contraintes

- Navigateurs cibles : Classilla, IE 5, Netscape (HTML 4.01, pas de JS avancé)
- QuickTime 5 sur PowerPC G3
- Résolution max : 320×240 (décodage limité par le CPU G3)
- Communication via Ethernet local (IP privée)

## Architecture

```
Linux (serveur)
┌─────────────────────────────────────────┐
│  Serveur HTTP (Python Flask/FastAPI)    │◄──── iMac G3 (navigateur)
│  - Pages HTML SSR                       │
│  - API de statut (polling)              │
├─────────────────────────────────────────┤
│  Gestionnaire de tâches asynchrone      │
│  (queue, un processus à la fois)        │
├─────────────────────────────────────────┤
│  yt-dlp → téléchargement vidéo YouTube │
│  ffmpeg → transcodage .mov segmenté    │
│    ├─ Codec vidéo : Sorenson Video 3   │
│    ├─ Codec audio : QDesign Music 2    │
│    ├─ Résolution : 320×240             │
│    ├─ Débit vidéo : ~500 kbps          │
│    └─ faststart (moov en tête)         │
├─────────────────────────────────────────┤
│  Stockage temporaire (.mov)             │
│  + Nettoyage automatique                │
└─────────────────────────────────────────┘
```

## Flux utilisateur

1. Page d'accueil → champ de recherche
2. Résultats de recherche YouTube (via yt-dlp search ou Invidious API)
3. Page détail vidéo → clic "Regarder"
4. Lancement du téléchargement + transcodage en arrière-plan
5. Page de statut avec `meta http-equiv="refresh"` toutes les 3s
6. Une fois le .mov prêt → lien `.qtl` → QuickTime Player

## Format de sortie

| Propriété | Valeur |
|---|---|
| Conteneur | `.mov` |
| Codec vidéo | Sorenson Video 3 (svq3) |
| Codec audio | QDesign Music 2 (qdm2) |
| Résolution | 320×240 |
| Débit vidéo | ~500 kbps |
| Audio | 22 kHz mono, ~32 kbps |
| Faststart | `-movflags +faststart` |

## Interface

- HTML 4.01 Strict
- Polling via `<meta http-equiv="refresh">`
- Lien `.qtl` pour lancer QuickTime Player
- Fallback : URL `.mov` brute (copier-coller dans QuickTime "Open URL")

## Composants serveur

1. **Recherche** — interroge YouTube via yt-dlp search ou Invidious API
2. **Téléchargement** — yt-dlp dans un sous-processus
3. **Transcodage** — ffmpeg avec sortie segmentée
4. **Serveur HTTP** — Flask ou FastAPI, routes :
   - `GET /` — page d'accueil
   - `GET /search?q=...` — résultats
   - `GET /watch?id=...` — page détail/statut
   - `GET /videos/<id>.mov` — téléchargement du fichier
   - `GET /videos/<id>.qtl` — lien QuickTime
5. **Nettoyage** — suppression des fichiers après expiration
