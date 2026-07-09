# Review — Plan d'implémentation Support du format d'affichage (Issue #5)

## Review round: 1

## Methodology

Plan compared against actual source code files:
- `app/transcoder.py` (161 lines)
- `app/server.py` (124 lines)
- `app/templates/search.html` (18 lines)
- `app/templates/watch.html` (24 lines)
- `tests/test_transcoder.py` (51 lines)
- `tests/test_server.py` (65 lines)

---

## Findings

### Criterion 1: Aucune déformation ✅

Le plan supprime `-s 320x240` de la commande ffmpeg et le remplace par `-vf` avec des filtres qui préservent le ratio :
- Crop : `force_original_aspect_ratio=increase` + `crop=320:240`
- Original : `force_original_aspect_ratio=decrease` + `pad=320:240:(ow-iw)/2:(oh-ih)/2:color=black`

Aucun risque de stretching.

### Criterion 2: Rétrocompatibilité ✅

- Les accès à `tasks[video_id]` utilisent `.get("format_mode", raw_format)` dans `server.py`
- Le template `watch.html` utilise `{% if format_mode %}` — si la clé est absente, rien ne s'affiche
- `start_transcode` ne relance pas une vidéo déjà présente avec un statut non-error

### Criterion 3: Sécurité — Validation du paramètre format ✅

```python
raw_format = request.args.get("format", "crop")
if raw_format not in ("crop", "original"):
    raw_format = "crop"
```

- Toute valeur hors `"crop"`/`"original"` (incluant chaîne vide, majuscules, valeurs arbitraires) → silencieusement `"crop"`
- Impossible d'injecter des valeurs arbitraires dans la commande ffmpeg

### Criterion 4: Clarté UI ✅

- `search.html` : deux liens distincts par résultat — "Regarder (4:3)" et "Format original"
- `watch.html` : affiche clairement le format utilisé

### Criterion 5: Thread safety ✅

- Toute modification de `tasks` se fait sous `tasks_lock`
- Aucune nouvelle variable partagée introduite
- `_run_transcode` reçoit `tasks` et `lock` comme paramètres

### Criterion 6: Tests ✅

Tests `test_transcoder.py` :
- `test_crop_filter` — vérifie la chaîne ffmpeg crop
- `test_original_filter` — vérifie la chaîne ffmpeg original
- `test_invalid_format_raises` — ValueError pour valeur invalide
- `test_empty_string_raises` — ValueError pour chaîne vide

Tests `test_server.py` :
- `test_watch_default_format` — sans ?format=, comportement nominal
- `test_watch_with_format_crop` — vérifie que format_mode="crop" est passé
- `test_watch_with_format_original` — vérifie que format_mode="original" est passé
- `test_watch_invalid_format_defaults_to_crop` — format invalide → crop
- `test_watch_empty_format_defaults_to_crop` — format vide → crop

### SUGGESTION: Cohérence de `format_mode` dans l'entrée `queued`

Dans `start_transcode`, l'entrée initiale `tasks[video_id] = {"status": "queued", "progress": 0}` n'inclut pas `format_mode`. La clé n'est ajoutée que lorsque le thread `_run_transcode` atteint son premier verrou (lignes 91-92 de `transcoder.py`). Pendant la fenêtre entre l'initialisation et le premier verrou, la tâche n'a pas `format_mode`.

**Impact** : Faible — le template utilise `task.get("format_mode", raw_format)` donc l'affichage est correct. L'endpoint `/status/<video_id>` ne montrerait pas `format_mode` pendant cette fenêtre transitoire.

**Recommandation** : Ajouter `"format_mode": format_mode` à l'entrée `queued` dans `start_transcode` pour la cohérence.

---

## Verdict: **READY**

Le plan est complet, précis, et répond à tous les critères de relecture. Aucun BLOCKING ou REQUIRED. Une suggestion mineure pour la cohérence des données.
