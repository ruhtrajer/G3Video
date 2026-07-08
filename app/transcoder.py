import os
import re
import subprocess
import threading
import json
import logging

logger = logging.getLogger(__name__)

VIDEO_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{11}$")


def sanitize_video_id(video_id: str) -> str:
    if not VIDEO_ID_PATTERN.match(video_id):
        raise ValueError("ID de vidéo invalide")
    return video_id


def _fetch_title(video_id):
    try:
        result = subprocess.run(
            ["yt-dlp", "--dump-json", video_id],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode != 0:
            logger.warning("yt-dlp metadata fetch failed for %s: %s", video_id, result.stderr.strip())
            return "Vidéo", ""
        data = json.loads(result.stdout)
        desc = data.get("description", "")[:200]
        return data.get("title", "Vidéo"), desc
    except Exception as e:
        logger.error("Metadata fetch error for %s: %s", video_id, e)
        return "Vidéo", ""


def _run_transcode(video_id, output_dir, tasks, lock):
    try:
        with lock:
            tasks[video_id] = {"status": "downloading", "progress": 5, "title": "Vidéo", "description": ""}

        title, description = _fetch_title(video_id)
        intermediary = os.path.join(output_dir, f"{video_id}.mp4")
        output_path = os.path.join(output_dir, f"{video_id}.mov")

        with lock:
            tasks[video_id] = {"status": "downloading", "progress": 10, "title": title, "description": description}

        d = subprocess.run(
            ["yt-dlp", "-f", "best[height<=480]", "-o", intermediary, video_id],
            capture_output=True, text=True, timeout=300
        )
        if d.returncode != 0:
            raise RuntimeError(f"yt-dlp a échoué : {d.stderr.strip()}")

        with lock:
            tasks[video_id] = {"status": "transcoding", "progress": 40, "title": title, "description": description}

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
        f = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if f.returncode != 0:
            raise RuntimeError(f"ffmpeg a échoué : {f.stderr.strip()}")

        if os.path.exists(intermediary):
            os.remove(intermediary)

        with lock:
            tasks[video_id] = {"status": "ready", "progress": 100, "title": title, "description": description}

    except subprocess.TimeoutExpired:
        logger.error("Timeout during transcode for %s", video_id)
        with lock:
            tasks[video_id] = {"status": "error", "error": "Le téléchargement ou transcodage a pris trop de temps."}
        if os.path.exists(intermediary):
            os.remove(intermediary)
    except Exception as e:
        logger.error("Transcode error for %s: %s", video_id, e)
        with lock:
            tasks[video_id] = {"status": "error", "error": str(e)}


def start_transcode(video_id, output_dir, tasks, lock):
    with lock:
        if video_id in tasks and tasks[video_id].get("status") not in ("error",):
            return
        tasks[video_id] = {"status": "queued", "progress": 0}
    thread = threading.Thread(target=_run_transcode, args=(video_id, output_dir, tasks, lock), daemon=True)
    thread.start()
