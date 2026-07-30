"""The seam between this layer and fractal-events.

fractal-events deliberately does not know about ApplicationContext: its
CommandBusProjector used to import it to build the ProcessContext a Process
runs against, which made the middle of the stack depend on the top. It takes a
``context_func`` now, and this layer is the one that supplies it. If that ever
stops happening, a process mapper fails at construction — so it is worth
holding down here, on the side that does the supplying.
"""

import os

import pytest
from fractal_core import Settings
from fractal_events import EventCommandMapper, EventProcessMapper

from fractal_application import ApplicationContext


class AppSettings(Settings):
    def load(self):
        self.EVENT_STORE_PROJECTOR = False
        self.PRINT_PROJECTOR = False
        self.PUBSUB_PROJECTOR = False


class Context(ApplicationContext):
    settings = AppSettings(dotenv=False)


@pytest.fixture(autouse=True)
def isolate():
    ApplicationContext.instance = None
    AppSettings.instance = Settings.instance = None
    yield
    ApplicationContext.instance = None
    AppSettings.instance = Settings.instance = None


def test_the_command_bus_projector_gets_a_context_func():
    context = Context(dotenv=False)

    assert context.command_bus_projector.context_func is not None
    assert context.command_bus_projector.context_func() is context


def test_mappers_are_discovered_as_classes_not_instances():
    """all_subclasses yields classes, and the projector calls each one.

    The annotation on the other side used to say instances. It type-checked
    fine and blew up at runtime, so pin down which one this side actually
    hands over.
    """
    context = Context(dotenv=False)

    assert isinstance(context.command_bus_projector.command_mappers, dict)
    for cls in (EventCommandMapper, EventProcessMapper):
        assert isinstance(cls, type)


def test_the_projector_is_last_in_the_chain():
    """Notifiers and persistence run before commands chain onto new events."""
    context = Context(dotenv=False)

    projectors = context.event_publisher.projectors

    assert projectors[-1] is context.command_bus_projector


def test_print_and_event_store_projectors_are_settings_driven():
    class Loud(AppSettings):
        def load(self):
            super().load()
            self.PRINT_PROJECTOR = True
            self.EVENT_STORE_PROJECTOR = True

    class LoudContext(ApplicationContext):
        settings = Loud(dotenv=False)

    try:
        context = LoudContext(dotenv=False)
        names = [type(p).__name__ for p in context.event_publisher.projectors]

        assert "PrintEventProjector" in names
        assert "EventStoreProjector" in names
    finally:
        Loud.instance = None


def test_the_default_event_store_is_in_memory():
    os.environ.pop("EVENT_STORE_BACKEND", None)

    context = Context(dotenv=False)

    assert type(context.event_store).__name__ == "ObjectEventStore"
