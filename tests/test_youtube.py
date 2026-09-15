import subprocess
import pytest
from app.youtube import (
    search_youtube,
    list_channel_videos,
    get_channel_avatar_url,
    _pick_channel_avatar_url,
    _resize_avatar_url,
    CHANNEL_ID_PATTERN,
)


def test_channel_id_pattern_valid():
    assert CHANNEL_ID_PATTERN.match("UCe3AtG3ApDIi6KT42icp8TQ")
    assert CHANNEL_ID_PATTERN.match("@BlindTestsdeLéo-d2n")


def test_channel_id_pattern_invalid():
    assert not CHANNEL_ID_PATTERN.match("watch?v=abc")
    assert not CHANNEL_ID_PATTERN.match("")
    assert not CHANNEL_ID_PATTERN.match("UCshort")


def test_search_youtube_empty_query(mocker):
    mocker.patch("app.youtube.shutil.which", return_value="/usr/bin/yt-dlp")
    assert search_youtube("") == []


def test_search_youtube_extracts_channel_id(mocker):
    mocker.patch("app.youtube.shutil.which", return_value="/usr/bin/yt-dlp")
    fake = subprocess.CompletedProcess([], 0, stdout=(
        '{"id": "abc123def45", "title": "T", "channel": "Chan", '
        '"channel_id": "UCe3AtG3ApDIi6KT42icp8TQ", "duration": 65}\n'
    ), stderr="")
    mocker.patch("app.youtube.subprocess.run", return_value=fake)
    results = search_youtube("test")
    assert results[0]["channel_id"] == "UCe3AtG3ApDIi6KT42icp8TQ"


class TestListChannelVideos:
    def test_empty_channel_id_raises(self):
        with pytest.raises(ValueError, match="ne peut pas être vide"):
            list_channel_videos("")

    def test_invalid_channel_id_raises(self):
        with pytest.raises(ValueError, match="channel_id invalide"):
            list_channel_videos("watch?v=abc")

    def test_no_ytdlp_raises(self, mocker):
        mocker.patch("app.youtube.shutil.which", return_value=None)
        with pytest.raises(RuntimeError, match="yt-dlp n'est pas installé"):
            list_channel_videos("UCe3AtG3ApDIi6KT42icp8TQ")

    def test_ytdlp_failure_raises(self, mocker):
        mocker.patch("app.youtube.shutil.which", return_value="/usr/bin/yt-dlp")
        fake = subprocess.CompletedProcess([], 1, stdout="", stderr="boom")
        mocker.patch("app.youtube.subprocess.run", return_value=fake)
        with pytest.raises(RuntimeError, match="yt-dlp a échoué"):
            list_channel_videos("UCe3AtG3ApDIi6KT42icp8TQ")

    def test_returns_channel_name_and_videos(self, mocker):
        mocker.patch("app.youtube.shutil.which", return_value="/usr/bin/yt-dlp")
        fake = subprocess.CompletedProcess([], 0, stdout=(
            '{"id": "aaa111aaa11", "title": "V1", "duration": 61, '
            '"playlist_channel": "Ma Chaîne", "thumbnails": [{"url": "https://x/y.jpg"}]}\n'
            '{"id": "bbb222bbb22", "title": "V2", "duration": 122, '
            '"playlist_channel": "Ma Chaîne", "thumbnails": []}\n'
        ), stderr="")
        mocker.patch("app.youtube.subprocess.run", return_value=fake)
        channel_name, results = list_channel_videos("UCe3AtG3ApDIi6KT42icp8TQ")

        assert channel_name == "Ma Chaîne"
        assert len(results) == 2
        assert results[0]["id"] == "aaa111aaa11"
        assert results[0]["duration"] == "1:01"
        assert results[0]["thumbnail"] == "/thumb/aaa111aaa11"
        assert results[1]["thumbnail"] == ""

    def test_max_results_respected(self, mocker):
        mocker.patch("app.youtube.shutil.which", return_value="/usr/bin/yt-dlp")
        lines = "".join(
            '{"id": "aaa111aaa1%d", "title": "V%d", "duration": 1, "playlist_channel": "C"}\n' % (i, i)
            for i in range(10)
        )
        fake = subprocess.CompletedProcess([], 0, stdout=lines, stderr="")
        result = mocker.patch("app.youtube.subprocess.run", return_value=fake)
        _, results = list_channel_videos("UCe3AtG3ApDIi6KT42icp8TQ", max_results=3)
        assert len(results) == 3
        cmd = result.call_args.args[0]
        assert "https://www.youtube.com/channel/UCe3AtG3ApDIi6KT42icp8TQ/videos" in cmd

    def test_handle_url_uses_at_handle(self, mocker):
        mocker.patch("app.youtube.shutil.which", return_value="/usr/bin/yt-dlp")
        fake = subprocess.CompletedProcess([], 0, stdout="", stderr="")
        result = mocker.patch("app.youtube.subprocess.run", return_value=fake)
        list_channel_videos("@maChaine", max_results=1)
        cmd = result.call_args.args[0]
        assert "https://www.youtube.com/@maChaine/videos" in cmd


def test_pick_avatar_url_prefers_square():
    thumbs = [
        {"url": "https://yt3.googleusercontent.com/a=w1060-fcrop64=1,x-no-nd-rj"},
        {"url": "https://yt3.googleusercontent.com/b=s900-c-k-c0x00ffffff-no-rj"},
    ]
    assert _pick_channel_avatar_url(thumbs) == "https://yt3.googleusercontent.com/b=s900-c-k-c0x00ffffff-no-rj"


def test_pick_avatar_url_fallback_first():
    thumbs = [{"url": "https://yt3.googleusercontent.com/a=w1060-fcrop64=1,x"}]
    assert _pick_channel_avatar_url(thumbs) == "https://yt3.googleusercontent.com/a=w1060-fcrop64=1,x"


def test_pick_avatar_url_empty():
    assert _pick_channel_avatar_url([]) == ""


def test_resize_avatar_url_s_size():
    url = "https://yt3.googleusercontent.com/b=s900-c-k-c0x00ffffff-no-rj"
    assert _resize_avatar_url(url, 96) == "https://yt3.googleusercontent.com/b=s96-c-k-c0x00ffffff-no-rj"


def test_resize_avatar_url_w_size():
    url = "https://yt3.googleusercontent.com/a=w1058-fcrop64=1,x"
    assert _resize_avatar_url(url, 96) == "https://yt3.googleusercontent.com/a=w96-fcrop64=1,x"


def test_resize_avatar_url_without_size():
    url = "https://example.com/photo.jpg"
    assert _resize_avatar_url(url, 96) == url


class TestGetChannelAvatarUrl:
    def test_empty_channel_id_raises(self):
        with pytest.raises(ValueError, match="ne peut pas être vide"):
            get_channel_avatar_url("")

    def test_invalid_channel_id_raises(self):
        with pytest.raises(ValueError, match="channel_id invalide"):
            get_channel_avatar_url("watch?v=abc")

    def test_no_ytdlp_raises(self, mocker):
        mocker.patch("app.youtube.shutil.which", return_value=None)
        with pytest.raises(RuntimeError, match="yt-dlp n'est pas installé"):
            get_channel_avatar_url("UCe3AtG3ApDIi6KT42icp8TQ")

    def test_ytdlp_failure_raises(self, mocker):
        mocker.patch("app.youtube.shutil.which", return_value="/usr/bin/yt-dlp")
        fake = subprocess.CompletedProcess([], 1, stdout="", stderr="boom")
        mocker.patch("app.youtube.subprocess.run", return_value=fake)
        with pytest.raises(RuntimeError, match="yt-dlp a échoué"):
            get_channel_avatar_url("UCe3AtG3ApDIi6KT42icp8TQ")

    def test_invalid_json_raises(self, mocker):
        mocker.patch("app.youtube.shutil.which", return_value="/usr/bin/yt-dlp")
        fake = subprocess.CompletedProcess([], 0, stdout="not json", stderr="")
        mocker.patch("app.youtube.subprocess.run", return_value=fake)
        with pytest.raises(RuntimeError, match="réponse invalide"):
            get_channel_avatar_url("UCe3AtG3ApDIi6KT42icp8TQ")

    def test_returns_resized_avatar(self, mocker):
        mocker.patch("app.youtube.shutil.which", return_value="/usr/bin/yt-dlp")
        fake = subprocess.CompletedProcess([], 0, stdout=(
            '{"thumbnails": ['
            '{"url": "https://yt3.googleusercontent.com/b=s900-c-k-c0x00ffffff-no-rj"},'
            '{"url": "https://yt3.googleusercontent.com/a=w1060-fcrop64=1,x"}'
            ']}'
        ), stderr="")
        mocker.patch("app.youtube.subprocess.run", return_value=fake)
        assert get_channel_avatar_url("UCe3AtG3ApDIi6KT42icp8TQ") == \
            "https://yt3.googleusercontent.com/b=s96-c-k-c0x00ffffff-no-rj"

    def test_no_thumbnails_returns_empty(self, mocker):
        mocker.patch("app.youtube.shutil.which", return_value="/usr/bin/yt-dlp")
        fake = subprocess.CompletedProcess([], 0, stdout='{"thumbnails": []}', stderr="")
        mocker.patch("app.youtube.subprocess.run", return_value=fake)
        assert get_channel_avatar_url("UCe3AtG3ApDIi6KT42icp8TQ") == ""

    def test_handle_uses_at_url(self, mocker):
        mocker.patch("app.youtube.shutil.which", return_value="/usr/bin/yt-dlp")
        fake = subprocess.CompletedProcess([], 0, stdout='{"thumbnails": []}', stderr="")
        result = mocker.patch("app.youtube.subprocess.run", return_value=fake)
        get_channel_avatar_url("@maChaine")
        cmd = result.call_args.args[0]
        assert "https://www.youtube.com/@maChaine/videos" in cmd