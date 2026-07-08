import os
import subprocess
import threading
import json


def _fetch_title(video_id):
    try:
        result = subprocess.run(
            ["yt-dlp", "--dump-json", video_id],
            capture_output=True, text=True, timeout=15
        )
        data = json.loads(result.stdout)
        return data.get("title", "Vidéo"), data.get("description", "")[:200]
    except Exception:
        return "Vidéo", ""


def _run_transcode(video_id, output_dir, tasks):
    try:
        tasks[video_id] = {"status": "downloading", "progress": 5, "title": "Vidéo", "description": ""}

        title, description = _fetch_title(video_id)
        intermediary = os.path.join(output_dir, f"{video_id}.mp4")
        output_path = os.path.join(output_dir, f"{video_id}.mov")

        tasks[video_id] = {"status": "downloading", "progress": 10, "title": title, "description": description}

        # Download best format up to 480p
        subprocess.run(
            ["yt-dlp", "-f", "best[height<=480]", "-o", intermediary, video_id],
            capture_output=True, text=True, timeout=300
        )

        tasks[video_id] = {"status": "transcoding", "progress": 40, "title": title, "description": description}

        # Transcode to .mov with Sorenson 3 + QDesign 2
        cmd = [
            "ffmpeg", "-y",
            "-i", intermediary,
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

        # Cleanup intermediary
        if os.path.exists(intermediary):
            os.remove(intermediary)

        tasks[video_id] = {"status": "ready", "progress": 100, "title": title, "description": description}

    except subprocess.TimeoutExpired:
        tasks[video_id] = {"status": "error", "error": "Le téléchargement ou transcodage a pris trop de temps."}
    except Exception as e:
        tasks[video_id] = {"status": "error", "error": str(e)}


def start_transcode(video_id, output_dir, tasks):
    tasks[video_id] = {"status": "queued", "progress": 0}
    thread = threading.Thread(target=_run_transcode, args=(video_id, output_dir, tasks), daemon=True)
    thread.start()
