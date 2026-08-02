from abc import ABC

from fractal_core import FractalException, Settings

from fractal_application.application_context import ApplicationContext


class Fractal(ABC):  # noqa: B024 - not decorative; see below
    """A service's handle on its own settings and context.

    Subclass it, assign both class attributes, and instantiating it becomes the
    assertion that the service was wired: a Fractal without settings or without
    a context refuses to be constructed rather than failing later on the first
    attribute nobody set.

    It declares nothing abstract — the wiring check lives in ``__init__``, so
    there is no method a subclass must supply — and linters read the ``ABC`` as
    decoration. It is not. ``ABC`` puts ABCMeta in the MRO, which is what makes
    ``@abstractmethod`` work in *subclasses*: a service that declares an
    abstract method of its own gets it enforced. Without ABC here that
    declaration would be silently ignored, the class would stay instantiable,
    and the missing implementation would surface whenever something first
    called it. Same reasoning as ``fractal_core.Service``.
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
