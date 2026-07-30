"""Every contrib module must still import after the rename.

This extraction rewrote import paths across sixteen files; a typo in any of
them is invisible until the one deployment that happens to enable that backend
starts up. Importing each module is the cheapest possible check that the
rewrite was complete, and it is the check most likely to actually catch
something.
"""

import importlib

import pytest

FASTAPI_MODULES = [
    "fractal_application.contrib.fastapi.install",
    "fractal_application.contrib.fastapi.exceptions.error_message",
    "fractal_application.contrib.fastapi.routers",
    "fractal_application.contrib.fastapi.routers.default",
    "fractal_application.contrib.fastapi.routers.tokens",
    "fractal_application.contrib.fastapi.routers.domain.models",
    "fractal_application.contrib.fastapi.utils.json_encoder",
]

GCP_MODULES = [
    "fractal_application.contrib.gcp",
    "fractal_application.contrib.gcp.firestore.event_store",
    "fractal_application.contrib.gcp.pubsub.projectors",
]


@pytest.mark.parametrize("name", FASTAPI_MODULES)
def test_fastapi_contrib_imports(name):
    assert importlib.import_module(name)


@pytest.mark.parametrize("name", GCP_MODULES)
def test_gcp_contrib_imports(name):
    assert importlib.import_module(name)


def test_no_module_still_points_at_the_old_toolkit():
    """A rewritten import that resolves is not the same as a correct one.

    `fractal` is still installable, so a missed `from fractal.core...` would
    import cleanly wherever the old package happens to be present and only fail
    on a machine without it. Checking the source is the reliable version.
    """
    import pathlib

    import fractal_application

    root = pathlib.Path(fractal_application.__file__).parent
    offenders = [
        str(p.relative_to(root))
        for p in root.rglob("*.py")
        if "from fractal.core" in p.read_text()
        or "from fractal.contrib" in p.read_text()
        or "from fractal import" in p.read_text()
    ]

    assert offenders == []
