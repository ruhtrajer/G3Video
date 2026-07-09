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
