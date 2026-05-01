"""Tests für m03_link_resolver."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
import requests

from modules import m03_link_resolver as resolver


@pytest.fixture(autouse=True)
def _reset_renderer():
    """Setzt den Webseiten-Renderer nach jedem Test auf Default zurück."""
    yield
    resolver.set_webpage_renderer(None)


def _mock_response(*, content_type: str, body: bytes = b"%PDF fake", status: int = 200):
    resp = MagicMock()
    resp.status_code = status
    resp.headers = {"Content-Type": content_type}
    resp.raise_for_status = MagicMock()
    if status >= 400:
        resp.raise_for_status.side_effect = requests.HTTPError(f"{status}")
    resp.iter_content = MagicMock(return_value=[body])
    resp.close = MagicMock()
    return resp


# ---------------------------------------------------------------------------
# Direkter PDF-Download
# ---------------------------------------------------------------------------


def test_direkter_pdf_download(tmp_path, monkeypatch):
    head = _mock_response(content_type="application/pdf")
    get = _mock_response(content_type="application/pdf", body=b"%PDF-1.4 content")
    monkeypatch.setattr(requests, "head", MagicMock(return_value=head))
    monkeypatch.setattr(requests, "get", MagicMock(return_value=get))

    paths = resolver.resolve(["https://makler.de/expose.pdf"], target_dir=tmp_path)

    assert len(paths) == 1
    assert paths[0].read_bytes() == b"%PDF-1.4 content"
    assert paths[0].suffix == ".pdf"


def test_direkter_pdf_download_filename_aus_url(tmp_path, monkeypatch):
    head = _mock_response(content_type="application/pdf")
    get = _mock_response(content_type="application/pdf")
    monkeypatch.setattr(requests, "head", MagicMock(return_value=head))
    monkeypatch.setattr(requests, "get", MagicMock(return_value=get))

    paths = resolver.resolve(["https://makler.de/objekte/foo-12345.pdf"], target_dir=tmp_path)

    assert paths[0].name == "foo-12345.pdf"


# ---------------------------------------------------------------------------
# Fehlerfälle
# ---------------------------------------------------------------------------


def test_404_kein_crash_kein_ergebnis(tmp_path, monkeypatch):
    head = _mock_response(content_type="application/pdf", status=404)
    get = _mock_response(content_type="text/html", status=404)
    monkeypatch.setattr(requests, "head", MagicMock(return_value=head))
    monkeypatch.setattr(requests, "get", MagicMock(return_value=get))

    paths = resolver.resolve(["https://makler.de/weg.pdf"], target_dir=tmp_path)

    assert paths == []


def test_connection_error_kein_crash(tmp_path, monkeypatch):
    monkeypatch.setattr(
        requests, "head", MagicMock(side_effect=requests.ConnectionError("boom"))
    )
    monkeypatch.setattr(
        requests, "get", MagicMock(side_effect=requests.ConnectionError("boom"))
    )

    paths = resolver.resolve(["https://offline.example/x"], target_dir=tmp_path)

    assert paths == []


# ---------------------------------------------------------------------------
# HTML / Webseiten-Renderer
# ---------------------------------------------------------------------------


def test_html_ohne_renderer_wird_uebersprungen(tmp_path, monkeypatch):
    head = _mock_response(content_type="text/html; charset=utf-8")
    monkeypatch.setattr(requests, "head", MagicMock(return_value=head))
    # Default-Renderer ist aktiv → loggt Warning, returns None

    paths = resolver.resolve(["https://makler.de/expose-page"], target_dir=tmp_path)

    assert paths == []


def test_html_mit_custom_renderer(tmp_path, monkeypatch):
    head = _mock_response(content_type="text/html")
    monkeypatch.setattr(requests, "head", MagicMock(return_value=head))

    def fake_renderer(url: str, target_dir: Path) -> list[Path]:
        # Renderer kann mehrere PDFs liefern (Exposé + Mietmatrix)
        out = []
        for name in ("expose.pdf", "mietmatrix.pdf"):
            p = target_dir / name
            p.write_bytes(b"%PDF " + name.encode() + b" " + url.encode())
            out.append(p)
        return out

    resolver.set_webpage_renderer(fake_renderer)

    paths = resolver.resolve(["https://makler.de/web-expose"], target_dir=tmp_path)

    assert len(paths) == 2
    assert all(p.read_bytes().startswith(b"%PDF") for p in paths)


def test_renderer_exception_kein_crash(tmp_path, monkeypatch):
    head = _mock_response(content_type="text/html")
    monkeypatch.setattr(requests, "head", MagicMock(return_value=head))

    def boom_renderer(url, target):
        raise RuntimeError("renderer crashed")

    resolver.set_webpage_renderer(boom_renderer)

    paths = resolver.resolve(["https://makler.de/x"], target_dir=tmp_path)

    assert paths == []


def test_renderer_meldet_erfolg_aber_datei_fehlt(tmp_path, monkeypatch):
    head = _mock_response(content_type="text/html")
    monkeypatch.setattr(requests, "head", MagicMock(return_value=head))

    def lying_renderer(url, target_dir):
        # Behauptet Erfolg, aber Datei existiert nicht
        return [target_dir / "phantom.pdf"]

    resolver.set_webpage_renderer(lying_renderer)

    paths = resolver.resolve(["https://makler.de/x"], target_dir=tmp_path)

    assert paths == []


# ---------------------------------------------------------------------------
# Mehrere URLs / Fallbacks
# ---------------------------------------------------------------------------


def test_mehrere_urls_gemischt(tmp_path, monkeypatch):
    pdf_head = _mock_response(content_type="application/pdf")
    pdf_get = _mock_response(content_type="application/pdf", body=b"%PDF-A")
    html_head = _mock_response(content_type="text/html")

    def head_router(url, **kw):
        return pdf_head if url.endswith(".pdf") else html_head

    def get_router(url, **kw):
        return pdf_get  # nur PDF-URL kommt hier an

    monkeypatch.setattr(requests, "head", MagicMock(side_effect=head_router))
    monkeypatch.setattr(requests, "get", MagicMock(side_effect=get_router))

    def fake_renderer(url, target_dir):
        p = target_dir / "rendered.pdf"
        p.write_bytes(b"%PDF rendered")
        return [p]

    resolver.set_webpage_renderer(fake_renderer)

    paths = resolver.resolve(
        [
            "https://makler.de/a.pdf",
            "https://makler.de/web-expose",
        ],
        target_dir=tmp_path,
    )

    assert len(paths) == 2


def test_unbekannter_content_type_versucht_get_trotzdem(tmp_path, monkeypatch):
    """Wenn HEAD keinen PDF-Hinweis gibt, GET probieren — manche Server lügen im HEAD."""
    head = _mock_response(content_type="application/octet-stream")
    get = _mock_response(content_type="application/pdf", body=b"%PDF-real")
    monkeypatch.setattr(requests, "head", MagicMock(return_value=head))
    monkeypatch.setattr(requests, "get", MagicMock(return_value=get))

    paths = resolver.resolve(["https://makler.de/lying-server"], target_dir=tmp_path)

    assert len(paths) == 1
    assert paths[0].read_bytes() == b"%PDF-real"


# ---------------------------------------------------------------------------
# Filename-Kollisionen
# ---------------------------------------------------------------------------


def test_doppelter_filename_wird_eindeutig(tmp_path, monkeypatch):
    head = _mock_response(content_type="application/pdf")
    get1 = _mock_response(content_type="application/pdf", body=b"%PDF-A")
    get2 = _mock_response(content_type="application/pdf", body=b"%PDF-B")

    monkeypatch.setattr(requests, "head", MagicMock(return_value=head))
    monkeypatch.setattr(
        requests, "get", MagicMock(side_effect=[get1, get2])
    )

    paths = resolver.resolve(
        [
            "https://makler-a.de/expose.pdf",
            "https://makler-b.de/expose.pdf",
        ],
        target_dir=tmp_path,
    )

    assert len(paths) == 2
    names = sorted(p.name for p in paths)
    assert names == ["expose.pdf", "expose_2.pdf"]


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


def test_run_alias(tmp_path, monkeypatch):
    head = _mock_response(content_type="application/pdf")
    get = _mock_response(content_type="application/pdf")
    monkeypatch.setattr(requests, "head", MagicMock(return_value=head))
    monkeypatch.setattr(requests, "get", MagicMock(return_value=get))

    paths = resolver.run(["https://x.de/y.pdf"], target_dir=tmp_path)
    assert len(paths) == 1


def test_run_ohne_urls_raises():
    with pytest.raises(ValueError, match="urls"):
        resolver.run()


def test_set_renderer_none_setzt_default():
    resolver.set_webpage_renderer(lambda u, t: None)
    resolver.set_webpage_renderer(None)
    assert resolver._renderer is resolver._default_webpage_renderer
