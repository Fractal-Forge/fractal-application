from fractal_events import EventStoreRepository, Message
from fractal_repositories.contrib.gcp.firestore.mixins import FirestoreRepositoryMixin


class FirestoreEventStoreRepository(
    EventStoreRepository, FirestoreRepositoryMixin[Message]
):
    pass
