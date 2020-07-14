from storage import cache, device
from trezor import wire
from trezor.crypto import bip32, hashlib, hmac

from . import mnemonic
from .passphrase import get as get_passphrase

if False:
    from .paths import Bip32Path, Slip21Path


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


@cache.stored_async(cache.APP_COMMON_SEED)
async def get_seed(ctx: wire.Context) -> bytes:
    if not device.is_initialized():
        raise wire.NotInitialized("Device is not initialized")
    passphrase = await get_passphrase(ctx)
    return mnemonic.get_seed(passphrase)


@cache.stored(cache.APP_COMMON_SEED_WITHOUT_PASSPHRASE)
def _get_seed_without_passphrase() -> bytes:
    if not device.is_initialized():
        raise Exception("Device is not initialized")
    return mnemonic.get_seed(progress_bar=False)


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
