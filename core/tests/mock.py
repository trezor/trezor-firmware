if False:
    from typing import Any


class Mock:
    def __init__(self, return_value: Any = None, raises: BaseException = None) -> None:
        self.attrs = {}
        self.calls = []
        self.return_value = return_value
        self.raises = raises

    def __getattr__(self, key: str) -> Any:
        self.attrs.setdefault(key, Mock())
        return self.attrs[key]

    def __setattr__(self, name: str, value: Any) -> Any:
        self.attrs[name] = value
        return value

    def __call__(self, *args, **kwargs) -> Any:
        self.calls.append((args, kwargs))
        if self.raises is not None:
            raise self.raises
        return self.return_value


class patch:
    MOCK_OBJECT = object()
    NO_VALUE = object()

    def __init__(self, obj: Any, attr: str, value: Any = MOCK_OBJECT) -> None:
        self.obj = obj
        self.attr = attr
        self.value = value
        self.orig_value = self.NO_VALUE

    def __enter__(self):
        if hasattr(self.obj, self.attr):
            self.orig_value = getattr(self.obj, self.attr)

        patch_value = self.value if self.value is not self.MOCK_OBJECT else Mock()
        setattr(self.obj, self.attr, patch_value)

    def __exit__(self, exc_type, exc_value, tb):
        if self.orig_value is self.NO_VALUE:
            delattr(self.obj, self.attr)
        else:
            setattr(self.obj, self.attr, self.orig_value)
