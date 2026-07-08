import subprocess
import json

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
