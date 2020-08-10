from storage import device
from trezor import wire
from trezor.crypto import bip32

from . import HARDENED, paths
from .seed import Slip21Node, get_seed

if False:
    from typing import (
        Any,
        Awaitable,
        Callable,
        Dict,
        List,
        Optional,
        Sequence,
        TypeVar,
    )
    from typing_extensions import Protocol

    from protobuf import MessageType

    T = TypeVar("T")

    class NodeProtocol(Protocol[paths.PathType]):
        def derive_path(self, path: paths.PathType) -> None:
            ...

        def clone(self: T) -> T:
            ...

        def __del__(self) -> None:
            ...

    NodeType = TypeVar("NodeType", bound=NodeProtocol)

    MsgIn = TypeVar("MsgIn", bound=MessageType)
    MsgOut = TypeVar("MsgOut", bound=MessageType)

    Handler = Callable[[wire.Context, MsgIn], Awaitable[MsgOut]]
    HandlerWithKeychain = Callable[[wire.Context, MsgIn, "Keychain"], Awaitable[MsgOut]]

    class Deletable(Protocol):
        def __del__(self) -> None:
            ...


FORBIDDEN_KEY_PATH = wire.DataError("Forbidden key path")


class LRUCache:
    def __init__(self, size: int) -> None:
        self.size = size
        self.cache_keys = []  # type: List[Any]
        self.cache = {}  # type: Dict[Any, Deletable]

    def insert(self, key: Any, value: Deletable) -> None:
        if key in self.cache_keys:
            self.cache_keys.remove(key)
        self.cache_keys.insert(0, key)
        self.cache[key] = value

        if len(self.cache_keys) > self.size:
            dropped_key = self.cache_keys.pop()
            self.cache[dropped_key].__del__()
            del self.cache[dropped_key]

    def get(self, key: Any) -> Any:
        if key not in self.cache:
            return None

        self.cache_keys.remove(key)
        self.cache_keys.insert(0, key)
        return self.cache[key]

    def __del__(self) -> None:
        for value in self.cache.values():
            value.__del__()
        self.cache.clear()
        self.cache_keys.clear()
        del self.cache


class Keychain:
    def __init__(
        self,
        seed: bytes,
        curve: str,
        namespaces: Sequence[paths.Bip32Path],
        slip21_namespaces: Sequence[paths.Slip21Path] = (),
    ) -> None:
        self.seed = seed
        self.curve = curve
        self.namespaces = namespaces
        self.slip21_namespaces = slip21_namespaces

        self._cache = LRUCache(10)

    def __del__(self) -> None:
        self._cache.__del__()
        del self._cache
        del self.seed

    def verify_path(self, path: paths.Bip32Path) -> None:
        if "ed25519" in self.curve and not paths.path_is_hardened(path):
            raise wire.DataError("Non-hardened paths unsupported on Ed25519")

        if device.unsafe_prompts_allowed():
            return

        if any(ns == path[: len(ns)] for ns in self.namespaces):
            return

        raise FORBIDDEN_KEY_PATH

    def _derive_with_cache(
        self, prefix_len: int, path: paths.PathType, new_root: Callable[[], NodeType],
    ) -> NodeType:
        cached_prefix = tuple(path[:prefix_len])
        cached_root = self._cache.get(cached_prefix)  # type: Optional[NodeType]
        if cached_root is None:
            cached_root = new_root()
            cached_root.derive_path(cached_prefix)
            self._cache.insert(cached_prefix, cached_root)

        node = cached_root.clone()
        node.derive_path(path[prefix_len:])
        return node

    def derive(self, path: paths.Bip32Path) -> bip32.HDNode:
        self.verify_path(path)
        return self._derive_with_cache(
            prefix_len=3,
            path=path,
            new_root=lambda: bip32.from_seed(self.seed, self.curve),
        )

    def derive_slip21(self, path: paths.Slip21Path) -> Slip21Node:
        if not device.unsafe_prompts_allowed() and not any(
            ns == path[: len(ns)] for ns in self.slip21_namespaces
        ):
            raise FORBIDDEN_KEY_PATH

        return self._derive_with_cache(
            prefix_len=1, path=path, new_root=lambda: Slip21Node(seed=self.seed),
        )

    def __enter__(self) -> "Keychain":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, tb: Any) -> None:
        self.__del__()


async def get_keychain(
    ctx: wire.Context,
    curve: str,
    namespaces: Sequence[paths.Bip32Path],
    slip21_namespaces: Sequence[paths.Slip21Path] = (),
) -> Keychain:
    seed = await get_seed(ctx)
    keychain = Keychain(seed, curve, namespaces, slip21_namespaces)
    return keychain


def with_slip44_keychain(
    slip44: int, curve: str = "secp256k1", allow_testnet: bool = False
) -> Callable[[HandlerWithKeychain[MsgIn, MsgOut]], Handler[MsgIn, MsgOut]]:
    namespaces = [[44 | HARDENED, slip44 | HARDENED]]
    if allow_testnet:
        namespaces.append([44 | HARDENED, 1 | HARDENED])

    def decorator(func: HandlerWithKeychain[MsgIn, MsgOut]) -> Handler[MsgIn, MsgOut]:
        async def wrapper(ctx: wire.Context, msg: MsgIn) -> MsgOut:
            keychain = await get_keychain(ctx, curve, namespaces)
            with keychain:
                return await func(ctx, msg, keychain)

        return wrapper

    return decorator
