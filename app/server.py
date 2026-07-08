import os
import subprocess
import tempfile
import threading
import logging
from flask import Flask, render_template, request, send_from_directory, jsonify
from app.youtube import search_youtube
from app.transcoder import start_transcode, sanitize_video_id

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config["VIDEO_DIR"] = os.path.join(tempfile.gettempdir(), "g3video")
os.makedirs(app.config["VIDEO_DIR"], exist_ok=True)

tasks = {}
tasks_lock = threading.Lock()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/search")
def search():
    query = request.args.get("q", "")
    if not query:
        return render_template("search.html", query="", results=[])
    try:
        results = search_youtube(query)
    except subprocess.TimeoutExpired:
        return render_template("search.html", query=query, results=[],
                              error="La recherche a pris trop de temps. Réessayez.")
    except RuntimeError as e:
        return render_template("search.html", query=query, results=[], error=str(e))
    except FileNotFoundError:
        return render_template("search.html", query=query, results=[],
                              error="yt-dlp introuvable. Vérifiez l'installation.")
    except Exception as e:
        return render_template("search.html", query=query, results=[],
                              error=f"Erreur inattendue : {e}")
    return render_template("search.html", query=query, results=results)


@app.route("/watch")
def watch():
    video_id = request.args.get("id", "")
    try:
        sanitize_video_id(video_id)
    except ValueError as e:
        return render_template("watch.html", video_id=video_id, status="error", error=str(e))

    start_transcode(video_id, app.config["VIDEO_DIR"], tasks, tasks_lock)

    with tasks_lock:
        task = tasks.get(video_id, {})

    return render_template("watch.html",
                           video_id=video_id,
                           title=task.get("title", "Vidéo"),
                           description=task.get("description", ""),
                           status=task.get("status", ""),
                           progress=task.get("progress", 0),
                           error=task.get("error", ""))


@app.route("/status/<video_id>")
def status(video_id):
    with tasks_lock:
        task = tasks.get(video_id, {"status": "unknown"})
    return jsonify(task)


@app.route("/videos/<video_id>.mov")
def serve_video(video_id):
    return send_from_directory(app.config["VIDEO_DIR"], f"{video_id}.mov")


@app.route("/videos/<video_id>.qtl")
def serve_qtl(video_id):
    content = f'''<?xml version="1.0"?>
<?quicktime type="application/x-quicktime-media-link"?>
<embed src="{request.host_url}videos/{video_id}.mov"
       autoplay="true"
       cache="false" />
'''
    return content, 200, {"Content-Type": "application/x-quicktime-media-link"}


if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "").lower() in ("1", "true")
    app.run(host="0.0.0.0", port=5000, debug=debug)
