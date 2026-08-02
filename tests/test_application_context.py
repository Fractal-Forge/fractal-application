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


def test_an_unknown_attribute_raises(make_context):
    """It used to answer None, for anything, forever.

    That silence is what made `hasattr` useless here, and it turned
    `getattr(context, name_from_a_payload)` into a None that failed somewhere
    else entirely. Ordinary attribute behaviour names the missing thing at the
    point it is asked for.
    """
    context = make_context()

    with pytest.raises(AttributeError, match="nothing_called_this"):
        _ = context.nothing_called_this


def test_get_parameters_returns_what_the_context_has(make_context):
    ApplicationContext.register_internal_service("mailer")(Mailer)
    context = make_context()

    (mailer,) = context.get_parameters(["mailer"])

    assert isinstance(mailer, Mailer)


def test_get_parameters_reports_a_missing_one(make_context):
    """The test this replaces pinned the defect instead of the intent.

    get_parameters could not fail: it asked hasattr, and __getattr__ answers
    None for everything, so a service that was never registered came back as
    (None,) and the caller carried a None around until something far away
    tried to use it.
    """
    context = make_context()

    with pytest.raises(FractalException, match="NEVER_REGISTERED"):
        context.get_parameters(["NEVER_REGISTERED"])


def test_get_parameters_fails_even_when_some_are_present(make_context):
    ApplicationContext.register_internal_service("mailer")(Mailer)
    context = make_context()

    with pytest.raises(FractalException, match="MISSING"):
        context.get_parameters(["mailer", "MISSING"])


# --------------------------------------------------------------------------- #
# provides() — the honest version of hasattr for this class
# --------------------------------------------------------------------------- #
def test_hasattr_and_provides_now_agree(make_context):
    """With the catch-all gone, hasattr is honest again.

    `provides` stays because it says what it means at the call site, but it no
    longer has to compensate for a __getattr__ that answered yes to everything.
    """
    context = make_context()

    assert not hasattr(context, "definitely_not_registered")
    assert not context.provides("definitely_not_registered")

    assert hasattr(context, "command_bus")
    assert context.provides("command_bus")


def test_provides_sees_an_installed_service(make_context):
    ApplicationContext.register_internal_service("mailer")(Mailer)

    assert make_context().provides("mailer")


def test_provides_sees_a_registered_repository(make_context):
    class ThingRepository:
        def is_healthy(self) -> bool:
            return True

    ApplicationContext.register_repository("thing_repository")(
        lambda settings: ThingRepository()
    )

    assert make_context().provides("thing_repository")


def test_provides_sees_what_load_sets_on_the_instance(make_context):
    context = make_context()

    assert context.provides("command_bus")
    assert context.provides("event_publisher")


def test_provides_sees_inherited_class_attributes(make_context):
    """Registration lands on ApplicationContext itself, not on the subclass."""
    context = make_context()

    assert context.provides("settings")
    assert context.provides("registered_command_handlers")


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


def test_a_fractal_subclass_can_enforce_its_own_abstract_methods(make_context):
    """What ABC on Fractal buys, and why it is not decoration.

    Fractal declares nothing abstract of its own — the wiring check lives in
    __init__ — but ABC puts ABCMeta in the MRO, which is what makes
    @abstractmethod work in subclasses. Same reasoning as fractal_core.Service.
    """
    from abc import abstractmethod

    ctx = make_context()

    class Reporting(Fractal):
        settings = ctx.settings
        context = ctx

        @abstractmethod
        def report(self) -> str:
            """Subclasses must provide this."""

    with pytest.raises(TypeError, match="report"):
        Reporting()
