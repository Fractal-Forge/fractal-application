"""The FastAPI app's CORS: a portal on another origin can read what a
download is called."""

from types import SimpleNamespace

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402
from starlette.responses import Response  # noqa: E402

from fractal_application.contrib.fastapi.install import install_fastapi  # noqa: E402


def test_a_download_name_is_readable_across_origins():
    app = install_fastapi(SimpleNamespace(ALLOW_ORIGINS="https://portal.example"))

    @app.get("/file")
    def file():
        return Response(
            b"zip",
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=site.zip"},
        )

    response = TestClient(app).get("/file", headers={"Origin": "https://portal.example"})
    assert "content-disposition" in response.headers[
        "access-control-expose-headers"
    ].lower()
