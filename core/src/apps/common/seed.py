import storage
from storage import cache
from trezor import wire
from trezor.crypto import bip32, hashlib, hmac
from trezor.crypto.curve import secp256k1

from apps.common import HARDENED, mnemonic
from apps.common.passphrase import get as get_passphrase

if False:
    from typing import List, Union


class Slip21Node:
    def __init__(self, seed: bytes = None) -> None:
        if seed is not None:
            self.data = hmac.new(b"Symmetric key seed", seed, hashlib.sha512).digest()
        else:
            self.data = b""

    def __del__(self) -> None:
        del self.data

    def derive_path(self, path: list) -> None:
        for label in path:
            h = hmac.new(self.data[0:32], b"\x00", hashlib.sha512)
            h.update(label)
            self.data = h.digest()

    def key(self) -> bytes:
        return self.data[32:64]

    def clone(self) -> "Slip21Node":
        node = Slip21Node()
        node.data = self.data
        return node


class Keychain:
    """
    Keychain provides an API for deriving HD keys from previously allowed
    key-spaces.
    """

    def __init__(self, seed: bytes, namespaces: list):
        self.seed = seed
        self.namespaces = namespaces
        self.roots = [None] * len(
            namespaces
        )  # type: List[Union[bip32.HDNode, Slip21Node, None]]

    def __del__(self) -> None:
        for root in self.roots:
            if root is not None and hasattr(root, "__del__"):
                root.__del__()
        del self.roots
        del self.seed

    def validate_path(self, checked_path: list, checked_curve: str) -> None:
        for curve, *path in self.namespaces:
            if path == checked_path[: len(path)] and curve == checked_curve:
                if "ed25519" in curve and not _path_hardened(checked_path):
                    break
                return
        raise wire.DataError("Forbidden key path")

    def derive(
        self, node_path: list, curve_name: str = "secp256k1"
    ) -> Union[bip32.HDNode, Slip21Node]:
        if "ed25519" in curve_name and not _path_hardened(node_path):
            raise wire.DataError("Forbidden key path")

        # find the root node index
        root_index = 0
        for curve, *path in self.namespaces:
            prefix = node_path[: len(path)]
            suffix = node_path[len(path) :]
            if curve == curve_name and path == prefix:
                break
            root_index += 1
        else:
            raise wire.DataError("Forbidden key path")

        # create the root node if not cached
        root = self.roots[root_index]
        if root is None:
            if curve_name != "slip21":
                root = bip32.from_seed(self.seed, curve_name)
            else:
                root = Slip21Node(self.seed)
            root.derive_path(path)
            self.roots[root_index] = root

        # derive child node from the root
        node = root.clone()
        node.derive_path(suffix)
        return node

    def derive_slip77_blinding_private_key(self, script: bytes) -> bytes:
        """Following the derivation by Elements/Liquid."""
        master_node = self.derive(node_path=[b"SLIP-0077"], curve_name="slip21")
        assert isinstance(master_node, Slip21Node)
        return hmac.new(
            key=master_node.key(), msg=script, digestmod=hashlib.sha256
        ).digest()

    def derive_slip77_blinding_public_key(self, script: bytes) -> bytes:
        private_key = self.derive_slip77_blinding_private_key(script)
        return secp256k1.publickey(private_key)


async def get_keychain(ctx: wire.Context, namespaces: list) -> Keychain:
    if not storage.is_initialized():
        raise wire.NotInitialized("Device is not initialized")
    seed = cache.get(cache.APP_COMMON_SEED)
    if seed is None:
        passphrase = await get_passphrase(ctx)
        seed = mnemonic.get_seed(passphrase)
        cache.set(cache.APP_COMMON_SEED, seed)
    keychain = Keychain(seed, namespaces)
    return keychain


def derive_node_without_passphrase(
    path: list, curve_name: str = "secp256k1"
) -> bip32.HDNode:
    if not storage.is_initialized():
        raise Exception("Device is not initialized")
    seed = cache.get(cache.APP_COMMON_SEED_WITHOUT_PASSPHRASE)
    if seed is None:
        seed = mnemonic.get_seed(progress_bar=False)
        cache.set(cache.APP_COMMON_SEED_WITHOUT_PASSPHRASE, seed)
    node = bip32.from_seed(seed, curve_name)
    node.derive_path(path)
    return node


def derive_slip21_node_without_passphrase(path: list) -> Slip21Node:
    if not storage.is_initialized():
        raise Exception("Device is not initialized")
    seed = cache.get(cache.APP_COMMON_SEED_WITHOUT_PASSPHRASE)
    if seed is None:
        seed = mnemonic.get_seed(progress_bar=False)
        cache.set(cache.APP_COMMON_SEED_WITHOUT_PASSPHRASE, seed)
    node = Slip21Node(seed)
    node.derive_path(path)
    return node


def remove_ed25519_prefix(pubkey: bytes) -> bytes:
    # 0x01 prefix is not part of the actual public key, hence removed
    return pubkey[1:]


def _path_hardened(path: list) -> bool:
    return all(i & HARDENED for i in path)
