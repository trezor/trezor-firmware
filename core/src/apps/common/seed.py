import storage
from storage import cache
from trezor import wire
from trezor.crypto import bip32, hashlib, hmac

from apps.common import HARDENED, mnemonic
from apps.common.passphrase import get as get_passphrase

if False:
    from typing import (
        Any,
        Awaitable,
        Callable,
        Dict,
        List,
        Sequence,
        Tuple,
        TypeVar,
    )
    from typing_extensions import Protocol

    Bip32Path = List[int]
    Slip21Path = List[bytes]
    PathType = TypeVar("PathType", Bip32Path, Slip21Path)

    Namespace = Tuple[str, PathType]

    T = TypeVar("T")

    class NodeType(Protocol[PathType]):
        def __del__(self) -> None:
            ...

        def derive_path(self, path: PathType) -> None:
            ...

        def clone(self: T) -> T:
            ...


class Slip21Node:
    def __init__(self, seed: bytes = None, data: bytes = None) -> None:
        assert seed is None or data is None, "Specify exactly one of: seed, data"
        if data is not None:
            self.data = data
        elif seed is not None:
            self.data = hmac.new(b"Symmetric key seed", seed, hashlib.sha512).digest()
        else:
            raise ValueError  # neither seed nor data specified

    def __del__(self) -> None:
        del self.data

    def derive_path(self, path: Slip21Path) -> None:
        for label in path:
            h = hmac.new(self.data[0:32], b"\x00", hashlib.sha512)
            h.update(label)
            self.data = h.digest()

    def key(self) -> bytes:
        return self.data[32:64]

    def clone(self) -> "Slip21Node":
        return Slip21Node(data=self.data)


class Keychain:
    def __init__(self, seed: bytes, namespaces: Sequence[Namespace]) -> None:
        self.seed = seed
        self.namespaces = namespaces  # type: Sequence[Namespace]
        self.roots = {}  # type: Dict[int, NodeType]

    def __del__(self) -> None:
        for root in self.roots.values():
            root.__del__()
        del self.roots
        del self.seed

    def match_path(self, path: PathType) -> Tuple[int, PathType]:
        for i, (curve, ns) in enumerate(self.namespaces):
            if path[: len(ns)] == ns:
                if "ed25519" in curve and not _path_hardened(path):
                    raise wire.DataError("Forbidden key path")
                return i, path[len(ns) :]

        raise wire.DataError("Forbidden key path")

    def _new_root(self, curve: str) -> NodeType:
        if curve == "slip21":
            return Slip21Node(self.seed)
        else:
            return bip32.from_seed(self.seed, curve)

    def derive(self, path: PathType) -> NodeType:
        root_index, suffix = self.match_path(path)

        if root_index not in self.roots:
            curve, prefix = self.namespaces[root_index]
            root = self._new_root(curve)
            root.derive_path(prefix)
            self.roots[root_index] = root

        node = self.roots[root_index].clone()
        node.derive_path(suffix)
        return node

    def __enter__(self) -> "Keychain":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, tb: Any) -> None:
        self.__del__()


@cache.stored_async(cache.APP_COMMON_SEED)
async def _get_seed(ctx: wire.Context) -> bytes:
    if not storage.is_initialized():
        raise wire.NotInitialized("Device is not initialized")
    passphrase = await get_passphrase(ctx)
    return mnemonic.get_seed(passphrase)


@cache.stored(cache.APP_COMMON_SEED_WITHOUT_PASSPHRASE)
def _get_seed_without_passphrase() -> bytes:
    if not storage.is_initialized():
        raise Exception("Device is not initialized")
    return mnemonic.get_seed(progress_bar=False)


async def get_keychain(ctx: wire.Context, namespaces: Sequence[Namespace]) -> Keychain:
    seed = await _get_seed(ctx)
    keychain = Keychain(seed, namespaces)
    return keychain


def derive_node_without_passphrase(
    path: Bip32Path, curve_name: str = "secp256k1"
) -> bip32.HDNode:
    seed = _get_seed_without_passphrase()
    node = bip32.from_seed(seed, curve_name)
    node.derive_path(path)
    return node


def derive_slip21_node_without_passphrase(path: Slip21Path) -> Slip21Node:
    seed = _get_seed_without_passphrase()
    node = Slip21Node(seed)
    node.derive_path(path)
    return node


def remove_ed25519_prefix(pubkey: bytes) -> bytes:
    # 0x01 prefix is not part of the actual public key, hence removed
    return pubkey[1:]


def _path_hardened(path: list) -> bool:
    return all(i & HARDENED for i in path)


if False:
    from protobuf import MessageType

    MsgIn = TypeVar("MsgIn", bound=MessageType)
    MsgOut = TypeVar("MsgOut", bound=MessageType)

    Handler = Callable[[wire.Context, MsgIn], Awaitable[MsgOut]]
    HandlerWithKeychain = Callable[[wire.Context, MsgIn, Keychain], Awaitable[MsgOut]]


def with_slip44_keychain(
    slip44: int, curve: str = "secp256k1", allow_testnet: bool = False
) -> Callable[[HandlerWithKeychain[MsgIn, MsgOut]], Handler[MsgIn, MsgOut]]:
    namespaces = [(curve, [44 | HARDENED, slip44 | HARDENED])]
    if allow_testnet:
        namespaces.append((curve, [44 | HARDENED, 1 | HARDENED]))

    def decorator(func: HandlerWithKeychain[MsgIn, MsgOut]) -> Handler[MsgIn, MsgOut]:
        async def wrapper(ctx: wire.Context, msg: MsgIn) -> MsgOut:
            keychain = await get_keychain(ctx, namespaces)
            with keychain:
                return await func(ctx, msg, keychain)

        return wrapper

    return decorator
