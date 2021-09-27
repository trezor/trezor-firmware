from apps.common import cbor

if False:
    from typing import Any, Generic, TypeVar
    from trezor.utils import HashContext

    T = TypeVar("T")
    K = TypeVar("K")
    V = TypeVar("V")
else:
    T = 0  # type: ignore
    K = 0  # type: ignore
    V = 0  # type: ignore
    Generic = {T: object, (K, V): object}  # type: ignore


class HashBuilderCollection:
    def __init__(self, size: int) -> None:
        self.size = size
        self.remaining = size
        self.hash_fn: HashContext | None = None
        self.parent: "HashBuilderCollection" | None = None
        self.has_unfinished_child = False

    def start(self, hash_fn: HashContext) -> "HashBuilderCollection":
        self.hash_fn = hash_fn
        self.hash_fn.update(self._header_bytes())
        return self

    def _insert_child(self, child: "HashBuilderCollection") -> None:
        child.parent = self
        assert self.hash_fn is not None
        child.start(self.hash_fn)
        self.has_unfinished_child = True

    def _do_enter_item(self) -> None:
        assert self.hash_fn is not None
        assert self.remaining > 0
        if self.has_unfinished_child:
            raise RuntimeError  # can't add item until child is finished

        self.remaining -= 1

    def _hash_item(self, item: Any) -> None:
        assert self.hash_fn is not None
        for chunk in cbor.encode_streamed(item):
            self.hash_fn.update(chunk)

    def _header_bytes(self) -> bytes:
        raise NotImplementedError

    def finish(self) -> None:
        if self.remaining != 0:
            raise RuntimeError  # not all items were added
        if self.parent is not None:
            self.parent.has_unfinished_child = False
        self.hash_fn = None
        self.parent = None

    def __enter__(self) -> "HashBuilderCollection":
        assert self.hash_fn is not None
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_type is None:
            self.finish()


class HashBuilderList(HashBuilderCollection, Generic[T]):
    def append(self, item: T) -> T:
        self._do_enter_item()
        if isinstance(item, HashBuilderCollection):
            self._insert_child(item)
        else:
            self._hash_item(item)

        return item

    def _header_bytes(self) -> bytes:
        return cbor.create_array_header(self.size)


class HashBuilderDict(HashBuilderCollection, Generic[K, V]):
    def add(self, key: K, value: V) -> V:
        self._do_enter_item()
        # enter key, this must not nest
        assert not isinstance(key, HashBuilderCollection)
        self._hash_item(key)
        # enter value, this can nest
        if isinstance(value, HashBuilderCollection):
            self._insert_child(value)
        else:
            self._hash_item(value)

        return value

    def _header_bytes(self) -> bytes:
        return cbor.create_map_header(self.size)
