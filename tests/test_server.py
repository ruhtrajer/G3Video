import os
import tempfile
import pytest


@pytest.fixture
def app():
    from app.server import app
    app.config.update({"TESTING": True})
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def seed_video_file():
    video_dir = os.path.join(tempfile.gettempdir(), "g3video")
    os.makedirs(video_dir, exist_ok=True)
    filepath = os.path.join(video_dir, "abc123.mov")
    if not os.path.exists(filepath):
        with open(filepath, "wb") as f:
            f.write(b"fake video content")


def test_serve_video_with_title(client, mocker):
    mocker.patch.dict("app.server.tasks", {
        "abc123": {"title": "Super Vidéo!", "status": "ready"}
    })
    resp = client.get("/videos/abc123.mov")
    assert resp.status_code == 200
    cd = resp.headers.get("Content-Disposition", "")
    assert "super_video.mov" in cd


def test_serve_video_no_title(client, mocker):
    mocker.patch.dict("app.server.tasks", {
        "abc123": {"status": "ready"}
    })
    resp = client.get("/videos/abc123.mov")
    assert resp.status_code == 200
    cd = resp.headers.get("Content-Disposition", "")
    assert "abc123.mov" in cd


def test_serve_video_empty_title(client, mocker):
    mocker.patch.dict("app.server.tasks", {
        "abc123": {"title": "", "status": "ready"}
    })
    resp = client.get("/videos/abc123.mov")
    assert resp.status_code == 200
    cd = resp.headers.get("Content-Disposition", "")
    assert "abc123.mov" in cd


def test_qtl_route_unchanged(client, mocker):
    mocker.patch.dict("app.server.tasks", {
        "abc123": {"title": "Super Vidéo!", "status": "ready"}
    })
    resp = client.get("/videos/abc123.qtl")
    assert resp.status_code == 200
    cd = resp.headers.get("Content-Disposition", "")
    assert cd is None or not cd.startswith("attachment")


def test_watch_default_format(client, mocker):
    mocker.patch("app.server.start_transcode")
    resp = client.get("/watch?id=abc123def45")
    assert resp.status_code == 200


def test_watch_with_format_crop(client, mocker):
    mock_start = mocker.patch("app.server.start_transcode")
    client.get("/watch?id=abc123def45&format=crop")
    mock_start.assert_called_once()
    _, kwargs = mock_start.call_args
    assert kwargs.get("format_mode") == "crop"


def test_watch_with_format_original(client, mocker):
    mock_start = mocker.patch("app.server.start_transcode")
    client.get("/watch?id=abc123def45&format=original")
    mock_start.assert_called_once()
    _, kwargs = mock_start.call_args
    assert kwargs.get("format_mode") == "original"


def test_watch_invalid_format_defaults_to_crop(client, mocker):
    mock_start = mocker.patch("app.server.start_transcode")
    client.get("/watch?id=abc123def45&format=stretch")
    mock_start.assert_called_once()
    _, kwargs = mock_start.call_args
    assert kwargs.get("format_mode") == "crop"


def test_watch_empty_format_defaults_to_crop(client, mocker):
    mock_start = mocker.patch("app.server.start_transcode")
    client.get("/watch?id=abc123def45&format=")
    mock_start.assert_called_once()
    _, kwargs = mock_start.call_args
    assert kwargs.get("format_mode") == "crop"


def test_watch_with_back_search(client, mocker):
    mocker.patch("app.server.start_transcode")
    resp = client.get("/watch?id=abc123def45&back=%2Fsearch%3Fq%3Dtest")
    assert resp.status_code == 200
    assert b"Retour \xc3\xa0 la liste des r" in resp.data


def test_watch_with_back_channel(client, mocker):
    mocker.patch("app.server.start_transcode")
    resp = client.get("/watch?id=abc123def45&back=%2Fchannel%3Fid%3DUCe3AtG3ApDIi6KT42icp8TQ")
    assert resp.status_code == 200
    assert b"Retour \xc3\xa0 la liste des r" in resp.data


def test_watch_with_invalid_back_hides_link(client, mocker):
    mocker.patch("app.server.start_transcode")
    resp = client.get("/watch?id=abc123def45&back=https://evil.com")
    assert b"Retour \xc3\xa0 la liste des r" not in resp.data


def test_watch_no_back_shows_only_home(client, mocker):
    mocker.patch("app.server.start_transcode")
    resp = client.get("/watch?id=abc123def45")
    assert b"Retour \xc3\xa0 la liste des r" not in resp.data
    assert b"Retour \xc3\xa0 l" in resp.data


def test_channel_empty_id(client):
    resp = client.get("/channel")
    assert resp.status_code == 200
    assert b"Aucun identifiant de cha" in resp.data


def test_channel_invalid_id(client):
    resp = client.get("/channel?id=watch?v=abc")
    assert resp.status_code == 200
    assert b"Identifiant de cha" in resp.data


def test_channel_valid_id(client, mocker):
    mocker.patch("app.server.list_channel_videos", return_value=(
        "Ma Chaîne", [{"id": "aaa111aaa11", "title": "V1", "duration": "1:01", "thumbnail": ""}]
    ))
    resp = client.get("/channel?id=UCe3AtG3ApDIi6KT42icp8TQ")
    assert resp.status_code == 200
    assert b"Ma Cha" in resp.data
    assert b"V1" in resp.data


def test_channel_ytdlp_error(client, mocker):
    mocker.patch("app.server.list_channel_videos",
                 side_effect=RuntimeError("yt-dlp a échoué"))
    resp = client.get("/channel?id=UCe3AtG3ApDIi6KT42icp8TQ")
    assert resp.status_code == 200
    assert b"yt-dlp a" in resp.data


class FakeResp:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return b"\xff\xd8\xff" + b"0" * 100


def test_chanimg_invalid_id(client):
    resp = client.get("/chanimg/watch?v=abc")
    assert resp.status_code == 404


def test_chanimg_ytdlp_failure(client, mocker):
    mocker.patch("app.server.get_channel_avatar_url",
                 side_effect=RuntimeError("yt-dlp a échoué"))
    resp = client.get("/chanimg/UC1111111111111111111111")
    assert resp.status_code == 404


def test_chanimg_no_avatar(client, mocker):
    mocker.patch("app.server.get_channel_avatar_url", return_value="")
    resp = client.get("/chanimg/UC0000000000000000000000")
    assert resp.status_code == 404


def test_chanimg_fetches_and_serves(client, mocker):
    mocker.patch("app.server.get_channel_avatar_url",
                 return_value="https://yt3.googleusercontent.com/b=s96-c-k-no-rj")
    mocker.patch("app.server.urllib.request.urlopen", return_value=FakeResp())
    resp = client.get("/chanimg/UCe3AtG3ApDIi6KT42icp8TQ")
    assert resp.status_code == 200
    assert resp.headers.get("Content-Type") == "image/jpeg"
    assert resp.data == b"\xff\xd8\xff" + b"0" * 100


def test_chanimg_serves_cached(client, mocker):
    mocker.patch("app.server.get_channel_avatar_url",
                 return_value="https://yt3.googleusercontent.com/b=s96-c-k-no-rj")
    mocker.patch("app.server.urllib.request.urlopen", return_value=FakeResp())
    first = client.get("/chanimg/UC2222222222222222222222")
    assert first.status_code == 200
    mocker.patch("app.server.get_channel_avatar_url",
                 side_effect=AssertionError("ne doit plus appeler yt-dlp"))
    second = client.get("/chanimg/UC2222222222222222222222")
    assert second.status_code == 200
    assert second.data == first.data
