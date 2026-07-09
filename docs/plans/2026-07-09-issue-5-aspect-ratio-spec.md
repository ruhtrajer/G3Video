# Issue #5 — Transcodage avec choix du format d'affichage

## Contexte

Lorsqu'une vidéo YouTube n'est pas en 4:3 (16:9, 18:9, cinemascope, etc.),
le transcodage actuel force `-s 320x240` ce qui déforme l'image.

## Design décidé

### Comportement
- Deux modes disponibles : `crop` (défaut) et `original`
- **crop** : remplit le cadre 320×240 en rognant les bords (`force_original_aspect_ratio=increase` + `crop=320:240`)
- **original** : letterbox/pillarbox avec bandes noires (`force_original_aspect_ratio=decrease` + `pad`)
- **Aucune déformation** — les filtres ffmpeg garantissent le ratio
- Paramètre passé dans l'URL : `?format=original` ou `?format=crop` (défaut)

### Flux utilisateur
1. Résultats de recherche : deux liens par vidéo → "Regarder (4:3)" et "Format original"
2. Page watch : affiche le format choisi dans le statut
3. Rétrocompatibilité : vidéos déjà dans `tasks` sans `format_mode` ne plantent pas

## Tâches

### Tâche unique : Ajout du support du format d'affichage
- **Fichiers source** : `app/transcoder.py`, `app/server.py`, `app/templates/search.html`, `app/templates/watch.html`, `tests/test_transcoder.py`, `tests/test_server.py`

## Conventions et contraintes
- Validation stricte du paramètre `format` : uniquement `"crop"` ou `"original"`
- Thread safety via `tasks_lock` existant
- Toujours utiliser `tasks_lock` pour lire/écrire `tasks`
- Les templates Jinja2 utilisent HTML 4.01 Strict

## Critères de relecture
1. **Aucune déformation** — l'image ne doit jamais être stretchée/comprimée
2. **Rétrocompatibilité** — les vidéos déjà dans `tasks` sans `format_mode` ne doivent pas planter
3. **Sécurité** — validation du paramètre `format` : uniquement `"crop"` ou `"original"`
4. **Clarté UI** — les deux options dans les résultats de recherche doivent être distinctes
5. **Thread safety** — `tasks[video_id]` protégé par `lock`
6. **Tests** — tests unitaires pour les filtres, tests de routage pour le paramètre `format`
