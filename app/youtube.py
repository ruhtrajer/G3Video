import subprocess
import json
import re
import shutil

YTDLP_TIMEOUT = 30

CHANNEL_ID_PATTERN = re.compile(r"^(UC[a-zA-Z0-9_-]{22}|@[\w.-]+)$")


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
            "channel_id": data.get("channel_id", ""),
            "duration": _format_duration(duration),
            "thumbnail": f"/thumb/{data['id']}" if thumbnail else "",
        })
    return results


def _channel_api_url(channel_id: str) -> str:
    if channel_id.startswith("UC"):
        return f"https://www.youtube.com/channel/{channel_id}/videos"
    return f"https://www.youtube.com/{channel_id}/videos"


def _pick_channel_avatar_url(thumbnails: list) -> str:
    best = ""
    for t in thumbnails or []:
        url = t.get("url") if isinstance(t, dict) else str(t)
        if not url:
            continue
        if "-c-k-c0x00ffffff-no-rj" in url:
            return url
        if not best:
            best = url
    return best


def _resize_avatar_url(url: str, width: int = 96) -> str:
    m = re.search(r"=s\d+", url)
    if m:
        return url[: m.start() + 2] + str(width) + url[m.end():]
    m = re.search(r"=w\d+", url)
    if m:
        return url[: m.start() + 2] + str(width) + url[m.end():]
    return url


def get_channel_avatar_url(channel_id: str, width: int = 96) -> str:
    if not channel_id or not channel_id.strip():
        raise ValueError("channel_id ne peut pas être vide")

    if not CHANNEL_ID_PATTERN.match(channel_id):
        raise ValueError(f"channel_id invalide : {channel_id!r}")

    if not shutil.which("yt-dlp"):
        raise RuntimeError(
            "yt-dlp n'est pas installé. Installez-le avec : pip install yt-dlp"
        )

    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--playlist-items", "1",
        "--dump-single-json",
        _channel_api_url(channel_id),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=YTDLP_TIMEOUT)

    if result.returncode != 0:
        stderr = result.stderr.strip() or "Erreur inconnue"
        raise RuntimeError(f"yt-dlp a échoué : {stderr}")

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"yt-dlp a renvoyé une réponse invalide : {e}")

    avatar = _pick_channel_avatar_url(data.get("thumbnails", []))
    if not avatar:
        return ""
    return _resize_avatar_url(avatar, width)


def list_channel_videos(channel_id: str, max_results: int = 30) -> tuple[str, list[dict]]:
    if not channel_id or not channel_id.strip():
        raise ValueError("channel_id ne peut pas être vide")

    if not CHANNEL_ID_PATTERN.match(channel_id):
        raise ValueError(f"channel_id invalide : {channel_id!r}")

    if not shutil.which("yt-dlp"):
        raise RuntimeError(
            "yt-dlp n'est pas installé. Installez-le avec : pip install yt-dlp"
        )

    url = _channel_api_url(channel_id)

    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--dump-json",
        url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=YTDLP_TIMEOUT)

    if result.returncode != 0:
        stderr = result.stderr.strip() or "Erreur inconnue"
        raise RuntimeError(f"yt-dlp a échoué : {stderr}")

    channel_name = ""
    results = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not channel_name:
            channel_name = data.get("playlist_channel", data.get("playlist_uploader", ""))
        duration = data.get("duration", 0)
        thumbnail = ""
        thumbnails = data.get("thumbnails", [])
        if thumbnails:
            thumbnail = thumbnails[-1].get("url", "")
        results.append({
            "id": data["id"],
            "title": data.get("title", "Sans titre"),
            "duration": _format_duration(duration),
            "thumbnail": f"/thumb/{data['id']}" if thumbnail else "",
        })
        if len(results) >= max_results:
            break
    return channel_name, results
