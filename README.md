# Fractal Application

> Fractal Application is the top of the Fractal stack: the application context that installs an application's repositories and services, wires its command bus and event publisher, and health-checks them on startup.

[![PyPI Version][pypi-image]][pypi-url]
[![Build Status][build-image]][build-url]

<!-- Badges -->

[pypi-image]: https://img.shields.io/pypi/v/fractal-application
[pypi-url]: https://pypi.org/project/fractal-application/
[build-image]: https://github.com/Fractal-Forge/fractal-application/actions/workflows/build.yml/badge.svg
[build-url]: https://github.com/Fractal-Forge/fractal-application/actions/workflows/build.yml

## Not on PyPI yet

`fractal-core`, `fractal-commands` and `fractal-events` are pinned to their git
repositories in `pyproject.toml`, because none of them is published yet. PyPI
rejects direct URL dependencies, so those lines must become plain names before
this package can be released.

## Installation

```sh
pip install fractal-application
pip install fractal-application[fastapi]        # FastAPI ingress
pip install fractal-application[gcp]            # Firestore event store, Pub/Sub projector
pip install fractal-application[processes]      # event → Process mappers
```

## Background

This is the layer that knows about all the others.
[fractal-core](https://github.com/Fractal-Forge/fractal-core),
[fractal-commands](https://github.com/Fractal-Forge/fractal-commands),
[fractal-events](https://github.com/Fractal-Forge/fractal-events) and
[fractal-processes](https://github.com/Fractal-Forge/fractal-processes) are all
deliberately ignorant of it, which is what lets any of them be used on their
own. Everything that has to know how the pieces fit together lives here.

## The application context

```python
from fractal_application import ApplicationContext
from fractal_core import Settings


class AppSettings(Settings):
    def load(self):
        self.EVENT_STORE_BACKEND = os.getenv("EVENT_STORE_BACKEND", "memory")


class Context(ApplicationContext):
    settings = AppSettings()


@ApplicationContext.register_repository("user_repository")
def select_user_repository(settings):
    return MongoUserRepository(settings.MONGO_URL)


@ApplicationContext.register_command_handler
class AddUserCommandHandler(CommandHandler):
    ...


context = Context()          # loads services, repositories, bus, publisher
context.user_repository      # installed and health-checked
context.command_bus          # every registered handler already on it
```

Construction *is* the wiring check. `load()` installs internal services,
repositories, egress services, the event publisher, the command bus and ingress
services, then asserts every repository and service reports itself healthy. A
context that constructed is a context whose adapters answered.

Registration happens through decorators at import time, which means it is a
side effect of the import graph — if a module holding handlers is never
imported, its handlers are never registered. `fractal-commands` raises on a
command with no handler precisely because that failure is otherwise silent.

## Fractal

```python
from fractal_application import Fractal


class MyService(Fractal):
    settings = AppSettings()
    context = Context()
```

Instantiating it asserts the service was wired: a `Fractal` without settings or
without a context refuses to construct rather than failing later on the first
attribute nobody set.

## contrib

### FastAPI

```python
from fractal_application.contrib.fastapi.install import install_fastapi

app = install_fastapi(context, title="My Service")
```

Also provides the default REST routers, token/role dependencies, an error
response model and a JSON encoder that understands pydantic models.

### Google Cloud

`FirestoreEventStoreRepository` backs the event store with Firestore (selected
by `EVENT_STORE_BACKEND=firestore`), and `PubSubEventBusProjector` publishes
events onto a Pub/Sub topic when `GCP_PROJECT_ID` is set.

### Processes

Event → Process mappers need
[fractal-processes](https://github.com/Fractal-Forge/fractal-processes). The
context passes itself to the projector as `context_func`, so the process engine
gets an application context without fractal-events ever importing this package.

## Development

```sh
make dev-install
make test
make lint
make format
```
