import pytest
from fractal_commands import Command, CommandBus, CommandHandler
from fractal_core import FractalException, Service, Settings

from fractal_application import ApplicationContext, Fractal


class AppSettings(Settings):
    def load(self):
        self.EVENT_STORE_PROJECTOR = False
        self.PRINT_PROJECTOR = False
        self.PUBSUB_PROJECTOR = False


class Mailer(Service):
    pass


class UnhealthyService(Service):
    def is_healthy(self) -> bool:
        return False


class Ping(Command):
    pass


class PingHandler(CommandHandler[Ping]):
    command = Ping
    handled: list = []

    def __init__(self, context):
        self.context = context

    @classmethod
    def install(cls, context):
        context.command_bus.add_handler(cls(context))

    def handle(self, command: Ping):
        PingHandler.handled.append(command)


@pytest.fixture
def make_context():
    """Build a fresh context class per test.

    Both ApplicationContext and Settings cache their instance on ``cls``, and
    the registries are class attributes on ApplicationContext itself, so
    anything registered in one test is visible in the next unless it is put
    back. Subclassing per test isolates the instance; the registries are saved
    and restored around it.
    """
    saved = {
        name: list(getattr(ApplicationContext, name))
        for name in (
            "registered_repositories",
            "registered_command_handlers",
            "registered_internal_services",
            "registered_egress_services",
            "registered_ingress_services",
        )
    }
    PingHandler.handled = []
    built = []

    def build():
        class Ctx(ApplicationContext):
            settings = type("S", (AppSettings,), {})(dotenv=False)

        built.append(Ctx)
        return Ctx(dotenv=False)

    yield build

    for name, value in saved.items():
        setattr(ApplicationContext, name, value)
    for cls in built:
        cls.instance = None
        type(cls.settings).instance = None
    ApplicationContext.instance = None
    Settings.instance = None


def test_loading_gives_a_command_bus_and_an_event_publisher(make_context):
    context = make_context()

    assert isinstance(context.command_bus, CommandBus)
    assert context.event_publisher is not None


def test_a_registered_handler_is_installed_on_the_bus(make_context):
    ApplicationContext.register_command_handler(PingHandler)

    context = make_context()
    context.command_bus.handle(Ping())

    assert len(PingHandler.handled) == 1


def test_a_healthy_service_is_reachable_by_name(make_context):
    ApplicationContext.register_internal_service("mailer")(Mailer)

    assert isinstance(make_context().mailer, Mailer)


def test_an_unhealthy_service_stops_startup(make_context):
    """A context that loaded is a context whose adapters answered."""
    ApplicationContext.register_internal_service("broken")(UnhealthyService)

    with pytest.raises(AssertionError):
        make_context()


def test_an_unknown_attribute_is_none_rather_than_an_error(make_context):
    """__getattr__ is a catch-all, which is how the optional settings lookups
    scattered through load() get away with bare getattr calls."""
    assert make_context().nothing_called_this is None


def test_get_parameters_returns_what_the_context_has(make_context):
    ApplicationContext.register_internal_service("mailer")(Mailer)
    context = make_context()

    (mailer,) = context.get_parameters(["mailer"])

    assert isinstance(mailer, Mailer)


def test_get_parameters_cannot_report_a_missing_one(make_context):
    """Pins down a known defect rather than the intended behaviour.

    get_parameters means to raise FractalException for anything the context
    does not provide, but the catch-all __getattr__ makes hasattr always true,
    so that branch is unreachable and a missing service comes back as None.
    Carried over from fractal-toolkit deliberately — see the docstring on
    get_parameters. If this test ever starts failing, the defect was fixed and
    the test should become the raising one.
    """
    context = make_context()

    assert context.get_parameters(["NEVER_REGISTERED"]) == (None,)


# --------------------------------------------------------------------------- #
# Fractal
# --------------------------------------------------------------------------- #
def test_fractal_requires_settings(make_context):
    class NoSettings(Fractal):
        context = make_context()

    with pytest.raises(FractalException, match="settings"):
        NoSettings()


def test_fractal_requires_a_context():
    class NoContext(Fractal):
        settings = AppSettings(dotenv=False)

    try:
        with pytest.raises(FractalException, match="context"):
            NoContext()
    finally:
        AppSettings.instance = None


def test_a_fully_wired_fractal_constructs(make_context):
    ctx = make_context()

    class Wired(Fractal):
        settings = ctx.settings
        context = ctx

    assert Wired()
