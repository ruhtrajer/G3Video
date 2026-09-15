import subprocess
import json
import shutil

YTDLP_TIMEOUT = 30


def _format_duration(seconds) -> str:
    try:
        seconds = int(seconds or 0)
    except (TypeError, ValueError):
        seconds = 0
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def search_youtube(query: str, max_results: int = 10) -> list[dict]:
    if not query or not query.strip():
        return []

    if not shutil.which("yt-dlp"):
        raise RuntimeError(
            "yt-dlp n'est pas installé. Installez-le avec : pip install yt-dlp"
        )

    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--dump-json",
        f"ytsearch{max_results}:{query}",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=YTDLP_TIMEOUT)

    if result.returncode != 0:
        stderr = result.stderr.strip() or "Erreur inconnue"
        raise RuntimeError(f"yt-dlp a échoué : {stderr}")

    results = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        duration = data.get("duration", 0)
        thumbnail = data.get("thumbnail", "")
        if not thumbnail:
            thumbnails = data.get("thumbnails", [])
            if thumbnails:
                thumbnail = thumbnails[-1].get("url", "")
        results.append({
            "id": data["id"],
            "title": data.get("title", "Sans titre"),
            "channel": data.get("channel", data.get("uploader", "Inconnu")),
            "duration": _format_duration(duration),
            "thumbnail": f"/thumb/{data['id']}" if thumbnail else "",
        })
    return results
