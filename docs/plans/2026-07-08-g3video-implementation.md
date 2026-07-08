# G3Video Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a server that lets an iMac G3 (Classilla/IE5/Netscape) search YouTube and watch videos in QuickTime 5 via transcoded .mov files served over Ethernet.

**Architecture:** Python Flask server on Linux. yt-dlp for YouTube search/download. ffmpeg to transcode to Sorenson Video 3 + QDesign Music 2 in .mov container with faststart. HTML 4.01 pages with `<meta http-equiv="refresh">` polling. No JavaScript, no CSS frameworks.

**Tech Stack:** Python 3, Flask, yt-dlp, ffmpeg, Werkzeug (dev server)

---

### Task 1: Project scaffolding + Flask skeleton

**Files:**
- Create: `requirements.txt`
- Create: `app/server.py`
- Create: `app/__init__.py`
- Create: `app/templates/__init__.py`
- Create: `app/templates/base.html`

**Step 1: Create requirements.txt**

```
flask>=3.0
yt-dlp>=2024.0
wheel
```

**Step 2: Create app/__init__.py**

Empty file.

**Step 3: Create app/server.py**

```python
import os
import subprocess
import tempfile
from flask import Flask, render_template, request, send_from_directory, jsonify

app = Flask(__name__)
app.config["VIDEO_DIR"] = os.path.join(tempfile.gettempdir(), "g3video")
os.makedirs(app.config["VIDEO_DIR"], exist_ok=True)

tasks = {}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/search")
def search():
    query = request.args.get("q", "")
    return render_template("search.html", query=query, results=[])

@app.route("/watch")
def watch():
    video_id = request.args.get("id", "")
    return render_template("watch.html", video_id=video_id)

@app.route("/status/<video_id>")
def status(video_id):
    task = tasks.get(video_id, {"status": "unknown"})
    return jsonify(task)

@app.route("/videos/<video_id>.mov")
def serve_video(video_id):
    return send_from_directory(app.config["VIDEO_DIR"], f"{video_id}.mov")

@app.route("/videos/<video_id>.qtl")
def serve_qtl(video_id):
    content = f'''<?xml version="1.0"?>
<?quicktime type="application/x-quicktime-media-link"?>
<embed src="http://{request.host}/videos/{video_id}.mov"
       autoplay="true"
       cache="false" />
'''
    return content, 200, {"Content-Type": "application/x-quicktime-media-link"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
```

**Step 4: Create app/templates/__init__.py**

Empty file.

**Step 5: Create app/templates/base.html**

```html
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
<title>G3Video - {% block title %}Accueil{% endblock %}</title>
<style type="text/css">
body { font-family: "Chicago", sans-serif; background: #fff; color: #000; margin: 20px; }
a { color: #00f; }
input, button { font-size: 16px; }
.result { margin: 10px 0; padding: 10px; border: 1px solid #ccc; }
</style>
</head>
<body>
<div id="header">
<h1><a href="/">G3Video</a></h1>
</div>
<div id="content">
{% block content %}{% endblock %}
</div>
</body>
</html>
```

**Step 6: Create app/templates/index.html**

```html
{% extends "base.html" %}
{% block title %}Accueil{% endblock %}
{% block content %}
<form method="get" action="/search">
<label for="q">Rechercher sur YouTube :</label><br>
<input type="text" name="q" id="q" size="40">
<button type="submit">Chercher</button>
</form>
{% endblock %}
```

**Step 7: Create app/templates/search.html**

```html
{% extends "base.html" %}
{% block title %}Résultats{% endblock %}
{% block content %}
<h2>Résultats pour "{{ query }}"</h2>
{% if results %}
  {% for r in results %}
  <div class="result">
    <a href="/watch?id={{ r.id }}">{{ r.title }}</a><br>
    <small>{{ r.channel }} &mdash; {{ r.duration }}</small>
  </div>
  {% endfor %}
{% else %}
  <p>Aucun résultat.</p>
{% endif %}
<p><a href="/">Nouvelle recherche</a></p>
{% endblock %}
```

**Step 8: Create app/templates/watch.html**

```html
{% extends "base.html" %}
{% block title %}Vidéo{% endblock %}
{% block content %}
<h2>{{ title }}</h2>
<p>{{ description }}</p>
<div id="status">
{% if status == "ready" %}
  <p><a href="/videos/{{ video_id }}.qtl">Regarder dans QuickTime</a></p>
  <p>Alternative : <a href="/videos/{{ video_id }}.mov">Télécharger le .mov</a></p>
{% elif status == "processing" %}
  <p>Transcodage en cours... {{ progress }}%</p>
  <meta http-equiv="refresh" content="3">
{% elif status == "queued" %}
  <p>Vidéo en attente de traitement...</p>
  <meta http-equiv="refresh" content="3">
{% else %}
  <p>Erreur : {{ error }}</p>
{% endif %}
</div>
<p><a href="javascript:history.back()">Retour</a></p>
{% endblock %}
```

**Step 9: Run to verify server starts**

Run: `pip install -r requirements.txt && python app/server.py`
Expected: Flask dev server starts on port 5000

**Step 10: Commit**

```bash
git add requirements.txt app/
git commit -m "feat: initial Flask skeleton with HTML templates"
```

---

### Task 2: YouTube search integration

**Files:**
- Modify: `app/server.py`
- Create: `app/youtube.py`

**Step 1: Create app/youtube.py**

```python
import subprocess
import json
import re

def search_youtube(query, max_results=10):
    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--dump-json",
        f"ytsearch{max_results}:{query}",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    results = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        data = json.loads(line)
        duration = data.get("duration", 0)
        minutes = duration // 60
        seconds = duration % 60
        results.append({
            "id": data["id"],
            "title": data.get("title", "Sans titre"),
            "channel": data.get("channel", data.get("uploader", "Inconnu")),
            "duration": f"{minutes}:{seconds:02d}",
        })
    return results
```

**Step 2: Modify server.py search route**

Replace the search route:

```python
from app.youtube import search_youtube

@app.route("/search")
def search():
    query = request.args.get("q", "")
    if not query:
        return render_template("search.html", query="", results=[])
    try:
        results = search_youtube(query)
    except Exception as e:
        return render_template("search.html", query=query, results=[], error=str(e))
    return render_template("search.html", query=query, results=results)
```

**Step 3: Test manually**

Run: `python -c "from app.youtube import search_youtube; print(search_youtube('test'))"`
Expected: List of 10 video dicts

**Step 4: Commit**

```bash
git add app/youtube.py app/server.py
git commit -m "feat: YouTube search via yt-dlp"
```

---

### Task 3: Download + transcode pipeline

**Files:**
- Create: `app/transcoder.py`
- Modify: `app/server.py`

**Step 1: Create app/transcoder.py**

```python
import os
import subprocess
import threading
import json

def download_and_transcode(video_id, output_dir, tasks):
    output_path = os.path.join(output_dir, f"{video_id}.mov")
    tasks[video_id] = {"status": "downloading", "progress": 0}

    def _run():
        try:
            # Step 1: Get best format info
            tasks[video_id] = {"status": "downloading", "progress": 5}
            subprocess.run(
                ["yt-dlp", "-f", "best[height<=480]", "-o",
                 os.path.join(output_dir, f"{video_id}.mp4"), video_id],
                capture_output=True, text=True, timeout=300
            )

            tasks[video_id] = {"status": "transcoding", "progress": 30}

            # Step 2: Transcode to .mov
            cmd = [
                "ffmpeg", "-y",
                "-i", os.path.join(output_dir, f"{video_id}.mp4"),
                "-c:v", "svq3",
                "-b:v", "500k",
                "-s", "320x240",
                "-c:a", "qdm2",
                "-b:a", "32k",
                "-ar", "22050",
                "-ac", "1",
                "-movflags", "+faststart",
                output_path,
            ]
            subprocess.run(cmd, capture_output=True, text=True, timeout=600)

            # Cleanup intermediary file
            intermediary = os.path.join(output_dir, f"{video_id}.mp4")
            if os.path.exists(intermediary):
                os.remove(intermediary)

            tasks[video_id] = {"status": "ready", "progress": 100}

        except Exception as e:
            tasks[video_id] = {"status": "error", "error": str(e)}

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
```

**Step 2: Add start_download route in server.py**

```python
from app.transcoder import download_and_transcode

@app.route("/start/<video_id>")
def start_download(video_id):
    if video_id not in tasks or tasks[video_id]["status"] in ("error",):
        tasks[video_id] = {"status": "queued", "progress": 0}
        download_and_transcode(video_id, app.config["VIDEO_DIR"], tasks)
    return render_template("watch.html", video_id=video_id,
                          status=tasks[video_id]["status"],
                          progress=tasks[video_id].get("progress", 0),
                          title=request.args.get("title", "Vidéo"),
                          description="")
```

**Step 3: Commit**

```bash
git add app/transcoder.py app/server.py
git commit -m "feat: download and transcode pipeline"
```

---

### Task 4: Static files and running

**Files:**
- Create: `run.py`

**Step 1: Create run.py at project root**

```python
#!/usr/bin/env python3
from app.server import app

if __name__ == "__main__":
    print("G3Video server starting on http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
```

**Step 2: Create .gitignore**

```
__pycache__/
*.pyc
*.mov
*.mp4
venv/
```

**Step 3: Commit**

```bash
git add run.py .gitignore
git commit -m "chore: add run script and gitignore"
```

---

### Task 5: Cleanup mechanism + video info

**Files:**
- Modify: `app/server.py`

**Step 1: Add cleanup function + fetch video metadata**

```python
import time
import atexit

def cleanup_old_files():
    while True:
        now = time.time()
        for fname in os.listdir(app.config["VIDEO_DIR"]):
            fpath = os.path.join(app.config["VIDEO_DIR"], fname)
            if os.path.isfile(fpath) and now - os.path.getmtime(fpath) > 3600:
                os.remove(fpath)
        time.sleep(300)

cleanup_thread = threading.Thread(target=cleanup_old_files, daemon=True)
cleanup_thread.start()
```

**Step 2: Fetch video title/description from yt-dlp**

```python
def fetch_video_info(video_id):
    try:
        result = subprocess.run(
            ["yt-dlp", "--dump-json", video_id],
            capture_output=True, text=True, timeout=15
        )
        data = json.loads(result.stdout)
        return {
            "title": data.get("title", "Vidéo"),
            "description": data.get("description", "")[:200],
        }
    except:
        return {"title": "Vidéo", "description": ""}
```

**Step 3: Commit**

```bash
git add app/server.py
git commit -m "feat: auto-cleanup and video metadata fetching"
```

---

## Testing with iMac

1. Run `python run.py` on the Linux machine
2. Note the IP: `ip addr show | grep 192.168`
3. On iMac G3, open Classilla and go to `http://192.168.X.X:5000/`
4. Search for a short video (<3 min) to test
5. Click "Regarder" → wait for transcoding → click .qtl link
6. QuickTime Player should launch and play

## Known limitations

- qdm2 codec may not be available in all ffmpeg builds. Fallback: `-c:a adpcm_ima_qt` or `pcm_s16le`
- yt-dlp search may be slow on the first run (needs to fetch page)
- svq3 encoding is slow (not hardware-accelerated) → small videos only for now
- Classilla may not auto-associate .qtl → the fallback link is essential
