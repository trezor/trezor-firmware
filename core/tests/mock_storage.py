from mock import patch

import storage.common

class MockStorage:
    PATCH_METHODS = ("get", "set", "delete")

    def __init__(self):
        self.namespace = {}
        self.patches = [
            patch(storage.common, method, getattr(self, method))
            for method in self.PATCH_METHODS
        ]

    def set(self, app: int, key: int, data: bytes, public: bool = False) -> None:
        self.namespace.setdefault(app, {})
        self.namespace[app][key] = data

    def get(self, app: int, key: int, public: bool = False) -> Optional[bytes]:
        self.namespace.setdefault(app, {})
        return self.namespace[app].get(key)

    def delete(self, app: int, key: int, public: bool = False) -> None:
        self.namespace.setdefault(app, {})
        self.namespace[app].pop(key, None)

    def __enter__(self):
        for patch in self.patches:
            patch.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, tb):
        for patch in self.patches:
            patch.__exit__(exc_type, exc_value, tb)


def mock_storage(func):
    def inner(*args, **kwargs):
        with MockStorage():
            return func(*args, **kwargs)

    return inner
