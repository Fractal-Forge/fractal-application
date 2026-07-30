from abc import ABC

from fractal_core import FractalException, Settings

from fractal_application.application_context import ApplicationContext


class Fractal(ABC):  # noqa: B024 - no abstract methods; ABC signals "subclass me"
    """A service's handle on its own settings and context.

    Subclass it, assign both class attributes, and instantiating it becomes the
    assertion that the service was wired: a Fractal without settings or without
    a context refuses to be constructed rather than failing later on the first
    attribute nobody set.
    """

    settings: Settings = None
    context: ApplicationContext = None

    def __init__(self):
        if not self.settings:
            raise FractalException(
                "Fractal service doesn't provide a 'settings' object."
            )
        if not self.context:
            raise FractalException(
                "Fractal service doesn't provide a 'context' object."
            )
