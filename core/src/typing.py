TYPE_CHECKING = False


class _GenericTypingObject:
    def __init__(self, *args, **kwargs):
        pass

    def __getattr__(self, key):
        # property access: P.kwargs
        return object

    def __getitem__(self, key):
        # dict-like access: Generic[T], Generic[K, V]
        return self


_TYPING_OBJECT = _GenericTypingObject()


def __getattr__(key):
    return _TYPING_OBJECT
