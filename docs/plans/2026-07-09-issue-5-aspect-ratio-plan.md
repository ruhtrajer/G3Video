# Plan d'implémentation — Support du format d'affichage (Issue #5)

## 1. Résumé

Ajout d'un paramètre `format_mode` dans le pipeline de transcodage permettant
à l'utilisateur de choisir entre `"crop"` (remplir 320×240 en rognant les bords)
et `"original"` (letterbox/pillarbox avec bandes noires). Aucune déformation n'est
autorisée.

---

## 2. Modifications détaillées

### 2.1 `app/transcoder.py`

#### 2.1.1 Nouvelle fonction utilitaire : `_build_vf_filter(format_mode: str) -> str`

```python
def _build_vf_filter(format_mode: str) -> str:
    """Construit la chaîne -vf pour ffmpeg selon le format_mode demandé.

    Args:
        format_mode: "crop" ou "original".

    Returns:
        Chaîne à passer à -vf (ex: "scale=320:240:force_original_aspect_ratio=increase,crop=320:240").

    Raises:
        ValueError: si format_mode n'est ni "crop" ni "original".
    """
    if format_mode == "crop":
        return "scale=320:240:force_original_aspect_ratio=increase,crop=320:240"
    elif format_mode == "original":
        return "scale=320:240:force_original_aspect_ratio=decrease,pad=320:240:(ow-iw)/2:(oh-ih)/2:color=black"
    else:
        raise ValueError(f"format_mode invalide : {format_mode!r}. Accepté : 'crop' ou 'original'.")
```

#### 2.1.2 Modification de `_run_transcode` — ajout du paramètre `format_mode`

Signature devient :
```python
def _run_transcode(video_id, output_dir, tasks, lock, format_mode="crop"):
```

Changements dans le corps :

1. Initialisation de `tasks[video_id]` (ligne 91-92) : ajouter `"format_mode": format_mode`
2. Mise à jour de `tasks[video_id]` (ligne 98-99) : ajouter `"format_mode": format_mode`
3. Mise à jour de `tasks[video_id]` (ligne 108-109) : ajouter `"format_mode": format_mode`
4. Remplacement de `-s 320x240` (lignes 113-129) par `-vf` filter :

```python
        cmd = [
            "ffmpeg", "-y",
            "-i", intermediary,
            "-c:v", video_enc,
            "-b:v", "500k",
            "-vf", _build_vf_filter(format_mode),
        ]
        if video_enc == "mpeg4":
            cmd += ["-vtag", "mp4v"]
        cmd += [
            "-c:a", audio_enc,
            "-b:a", "32k",
            "-ar", "22050",
            "-ac", "1",
            "-movflags", "+faststart",
            output_path,
        ]
```

5. Mise à jour finale (ligne 137-141) : ajouter `"format_mode": format_mode`

```python
        with lock:
            tasks[video_id] = {
                "status": "ready", "progress": 100,
                "title": title, "description": description,
                "format_mode": format_mode,
            }
```

**Rétrocompatibilité** : les entrées `tasks` existantes (sans `format_mode`) sont
lues via `task.get("format_mode", "crop")` côté templates (voir §2.3).

#### 2.1.3 Modification de `start_transcode` — ajout du paramètre `format_mode`

Signature devient :
```python
def start_transcode(video_id, output_dir, tasks, lock, format_mode="crop"):
```

Changement dans le corps (ligne 160) :
```python
    thread = threading.Thread(
        target=_run_transcode,
        args=(video_id, output_dir, tasks, lock, format_mode),
        daemon=True
    )
    thread.start()
```

---

### 2.2 `app/server.py`

#### 2.2.1 Modification de la route `/watch` — lecture de `?format=`

```python
@app.route("/watch")
def watch():
    video_id = request.args.get("id", "")
    try:
        sanitize_video_id(video_id)
    except ValueError as e:
        return render_template("watch.html", video_id=video_id, status="error", error=str(e))

    # Lecture et validation du paramètre format
    raw_format = request.args.get("format", "crop")
    if raw_format not in ("crop", "original"):
        raw_format = "crop"

    start_transcode(video_id, app.config["VIDEO_DIR"], tasks, tasks_lock, format_mode=raw_format)

    with tasks_lock:
        task = tasks.get(video_id, {})

    return render_template("watch.html",
                           video_id=video_id,
                           title=task.get("title", "Vidéo"),
                           description=task.get("description", ""),
                           status=task.get("status", ""),
                           progress=task.get("progress", 0),
                           error=task.get("error", ""),
                           format_mode=task.get("format_mode", raw_format),)
```

---

### 2.3 `app/templates/search.html`

Ajout de **deux liens** par résultat : "Regarder (4:3)" pour le mode crop,
"Format original" pour le mode original.

```html
{% extends "base.html" %}
{% block title %}Résultats{% endblock %}
{% block content %}
<h2>Résultats pour "{{ query }}"</h2>
{% if error %}
  <p class="error">Erreur : {{ error }}</p>
{% elif results %}
  {% for r in results %}
  <div class="result">
    <a href="/watch?id={{ r.id | urlencode }}&format=crop"><strong>{{ r.title }}</strong></a><br>
    <small>
      <a href="/watch?id={{ r.id | urlencode }}&format=crop">Regarder (4:3)</a>
      &nbsp;|&nbsp;
      <a href="/watch?id={{ r.id | urlencode }}&format=original">Format original</a>
      &mdash; {{ r.channel }} &mdash; {{ r.duration }}
    </small>
  </div>
  {% endfor %}
{% else %}
  <p>Aucun résultat.</p>
{% endif %}
<p><a href="/">Nouvelle recherche</a></p>
{% endblock %}
```

Le titre reste un lien cliquable mais mène maintenant vers le mode crop (défaut).

---

### 2.4 `app/templates/watch.html`

Ajout de l'affichage du `format_mode` dans le statut et le lien de téléchargement.

```html
{% extends "base.html" %}
{% block title %}Vidéo{% endblock %}
{% block head_extra %}
{% if status in ("processing", "queued", "downloading", "transcoding") %}
<meta http-equiv="refresh" content="3">
{% endif %}
{% endblock %}
{% block content %}
<h2>{{ title }}</h2>
<p>{{ description }}</p>
{% if format_mode %}
<p>Format : <strong>{{ "4:3 (recadré)" if format_mode == "crop" else "Original (bandes noires)" }}</strong></p>
{% endif %}
<div id="status">
{% if status == "ready" %}
  <p><a href="/videos/{{ video_id }}.qtl">Regarder dans QuickTime</a></p>
  <p>Alternative : <a href="/videos/{{ video_id }}.mov">Télécharger le .mov</a></p>
{% elif status in ("processing", "downloading", "transcoding") %}
  <p>{{ status }}... {{ progress }}%</p>
{% elif status == "queued" %}
  <p>Vidéo en attente de traitement...</p>
{% else %}
  {% if error %}<p>Erreur : {{ error }}</p>{% endif %}
{% endif %}
</div>
<p><a href="/">Retour à l'accueil</a></p>
{% endblock %}
```

Rétrocompatibilité : si `format_mode` n'est pas défini (entrée task préexistante),
la condition `{% if format_mode %}` est fausse (None ou chaîne vide), donc rien
ne s'affiche.

---

## 3. Tests

### 3.1 `tests/test_transcoder.py` — Nouveaux tests

Ajouter l'import de `_build_vf_filter` :

```python
from app.transcoder import sanitize_filename, _build_vf_filter
```

Tests à ajouter :

```python
class TestBuildVfFilter:
    def test_crop_filter(self):
        result = _build_vf_filter("crop")
        assert result == "scale=320:240:force_original_aspect_ratio=increase,crop=320:240"

    def test_original_filter(self):
        result = _build_vf_filter("original")
        assert result == "scale=320:240:force_original_aspect_ratio=decrease,pad=320:240:(ow-iw)/2:(oh-ih)/2:color=black"

    def test_invalid_format_raises(self):
        with pytest.raises(ValueError, match="format_mode invalide"):
            _build_vf_filter("invalid")

    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="format_mode invalide"):
            _build_vf_filter("")
```

### 3.2 `tests/test_server.py` — Nouveaux tests

Ajouter les tests de routage pour le paramètre `format` :

```python
def test_watch_default_format(client, mocker):
    """Sans ?format=, le format par défaut doit être 'crop'."""
    mocker.patch("app.server.start_transcode")
    resp = client.get("/watch?id=abc123def45")
    assert resp.status_code == 200


def test_watch_with_format_crop(client, mocker):
    """?format=crop doit être passé à start_transcode."""
    mock_start = mocker.patch("app.server.start_transcode")
    client.get("/watch?id=abc123def45&format=crop")
    mock_start.assert_called_once()
    _, kwargs = mock_start.call_args
    assert kwargs.get("format_mode") == "crop"


def test_watch_with_format_original(client, mocker):
    """?format=original doit être passé à start_transcode."""
    mock_start = mocker.patch("app.server.start_transcode")
    client.get("/watch?id=abc123def45&format=original")
    mock_start.assert_called_once()
    _, kwargs = mock_start.call_args
    assert kwargs.get("format_mode") == "original"


def test_watch_invalid_format_defaults_to_crop(client, mocker):
    """Un format invalide doit être silencieusement remplacé par 'crop'."""
    mock_start = mocker.patch("app.server.start_transcode")
    client.get("/watch?id=abc123def45&format=stretch")
    mock_start.assert_called_once()
    _, kwargs = mock_start.call_args
    assert kwargs.get("format_mode") == "crop"


def test_watch_empty_format_defaults_to_crop(client, mocker):
    """?format= vide doit être traité comme 'crop'."""
    mock_start = mocker.patch("app.server.start_transcode")
    client.get("/watch?id=abc123def45&format=")
    mock_start.assert_called_once()
    _, kwargs = mock_start.call_args
    assert kwargs.get("format_mode") == "crop"
```

---

## 4. Pipelines et flux de données

```
Navigateur → /watch?id=XXX&format=crop
                   │
                   ▼
            server.py:watch()
                   │
                   ├── lit request.args["format"] (défaut: "crop")
                   ├── valide : uniquement "crop" ou "original"
                   │
                   ▼
            start_transcode(video_id, output_dir, tasks, lock, format_mode)
                   │
                   ▼
            _run_transcode(..., format_mode)
                   │
                   ├── stocke format_mode dans tasks[video_id]
                   ├── _build_vf_filter(format_mode) → "-vf ..."
                   ├── ffmpeg ... -vf "scale=...:force_original_aspect_ratio=...,crop/pad..."
                   │
                   ▼
            tasks[video_id] = {"status": "ready", "format_mode": format_mode, ...}
                   │
                   ▼
            watch.html reçoit format_mode
                   │
                   └── affiche "Format : 4:3 (recadré)" ou "Format : Original (bandes noires)"
```

---

## 5. Cas limites / Edge cases

| Cas | Comportement attendu |
|-----|----------------------|
| `?format=` absent | Défaut à `"crop"` |
| `?format=crop` | Mode recadrage |
| `?format=original` | Mode letterbox/pillarbox |
| `?format=STRETCH` | Invalide → silencieusement `"crop"` |
| `?format=` (vide) | Traité comme `"crop"` |
| `?format=CROP` (majuscules) | Invalide → `"crop"` (comparaison stricte) |
| Entrée `tasks` sans clé `"format_mode"` (rétrocompatibilité) | `watch.html` : `{% if format_mode %}` → False, rien n'est affiché. Aucun crash. |
| `start_transcode` appelé sans `format_mode` | Signature avec valeur par défaut `"crop"` → pas d'erreur |
| Transcodage déjà en cours pour une vidéo (même video_id, format différent) | `start_transcode` vérifie `tasks[video_id].get("status")` — si pas "error", il ne relance pas. Le format_mode du premier appel est conservé. |

---

## 6. Critères de sortie / Definition of Done

1. `_build_vf_filter("crop")` retourne la chaîne de filtre crop correcte
2. `_build_vf_filter("original")` retourne la chaîne de filtre pad correcte
3. `_build_vf_filter("invalid")` lève `ValueError`
4. `ffmpeg` n'utilise plus `-s 320x240` mais `-vf` à la place
5. `start_transcode` accepte et propage `format_mode`
6. `/?format=stretch` est traité comme `"crop"` sans erreur
7. Les liens dans `search.html` passent `?format=crop` et `?format=original`
8. `watch.html` affiche le format_mode choisi
9. Une entrée tasks sans `format_mode` ne fait pas planter `watch.html`
10. Tous les tests passent (existants + nouveaux)
