"""
Fractal Application

The top of the Fractal stack: the application context that installs an
application's repositories and services, wires its command bus and event
publisher, and health-checks the lot on startup.

This is the layer that knows about all the others. Every Fractal library below
it — core, commands, events, processes — is deliberately ignorant of this one,
which is what lets them be used on their own.

FastAPI and Google Cloud integrations live under ``contrib`` and are optional
extras: ``pip install fractal-application[fastapi,gcp]``.
"""

from fractal_application.application_context import ApplicationContext
from fractal_application.fractal import Fractal

__version__ = "2.0.0"

__all__ = [
    "ApplicationContext",
    "Fractal",
]
