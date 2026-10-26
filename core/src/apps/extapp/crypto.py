from micropython import const
from typing import TYPE_CHECKING

import trezorcrypto_api
from trezor.wire import context
from trezor.wire.errors import DataError

from apps.common import paths
from apps.common.keychain import get_keychain

from .session import MSG_ID_ERROR, SERVICE_CRYPTO, describe

if __debug__:
    from trezor import log

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from trezorio import IpcMessage
    from typing import Any

    from apps.common.keychain import Keychain

    from .session import Session

    CryptoHandler = Callable[[Session, Any], Awaitable[Any]]

_GET_XPUB = const(0)
_GET_PUBLIC_KEY = const(1)
_SIGN_DIGEST = const(2)
_GET_ADDRESS_MAC = const(3)
_CHECK_ADDRESS_MAC = const(4)
_VERIFY_NONCE_CACHE = const(5)

# `CanonicalSig` values in the SDK.
_CANONICAL_ANY = const(0)
_CANONICAL_ETHEREUM = const(1)

_SLIP24_NAMESPACE = [b"SLIP-0024"]


async def handle(session: Session, msg: IpcMessage) -> None:
    """Run a crypto operation requested by the app and send it the result.

    A failed operation is reported to the app as `MSG_ID_ERROR`; only an
    unknown operation or a failure to reply kills the app.
    """
    handler = _HANDLERS.get(msg.message_id)
    if handler is None:
        session.die(DataError("Unknown crypto operation"))

    try:
        obj = trezorcrypto_api.deserialize_crypto_message(data=bytes(msg.data))
        result = await handler(session, obj)
    except Exception as e:
        if __debug__:
            log.error(
                __name__, f"Crypto operation {msg.message_id} failed: {describe(e)}"
            )
        try:
            session.send(SERVICE_CRYPTO, MSG_ID_ERROR, b"")
        except Exception:
            session.die(DataError("Failed to send crypto error"))
        return

    def send(data: bytes) -> None:
        session.send(SERVICE_CRYPTO, msg.message_id, data)

    try:
        trezorcrypto_api.send_crypto_result(result=result, ipc_cb=send)
    except Exception:
        session.die(DataError("Failed to serialize or send crypto result"))


def _check_not_slip25(address_n: list[int]) -> None:
    from apps.common.keychain import ForbiddenKeyPath

    if address_n and address_n[0] == paths.SLIP25_PURPOSE:
        # UnlockPath is required to access SLIP25 paths.
        raise ForbiddenKeyPath()


async def _get_xpub(session: Session, obj: Any) -> str:
    address_n, xpub_magic = obj
    _check_not_slip25(address_n)
    keychain = await get_keychain(session.curve, [paths.AlwaysMatchingSchema])
    return keychain.derive(address_n).serialize_public(xpub_magic)


async def _get_public_key(session: Session, obj: Any) -> bytes:
    address_n, compressed = obj
    _check_not_slip25(address_n)
    keychain = await get_keychain(session.curve, [paths.AlwaysMatchingSchema])
    private_key = keychain.derive(address_n).private_key()

    curve = session.curve
    if curve == "secp256k1":
        from trezor.crypto.curve import secp256k1

        public_key = secp256k1.publickey(private_key, compressed)
    elif curve == "nist256p1":
        from trezor.crypto.curve import nist256p1

        public_key = nist256p1.publickey(private_key, compressed)
    elif curve == "ed25519":
        from trezor.crypto.curve import ed25519

        public_key = ed25519.publickey(private_key)
    elif curve == "curve25519":
        from trezor.crypto.curve import curve25519

        public_key = curve25519.publickey(private_key)
    elif curve == "bip340":
        from trezor.crypto.curve import bip340

        public_key = bip340.publickey(private_key)
    else:
        raise DataError(f"Unsupported curve: {curve}")
    return public_key


async def _sign_digest(session: Session, obj: Any) -> bytes:
    address_n, digest, compressed, canonical = obj
    keychain = await get_keychain(session.curve, session.schemas, [_SLIP24_NAMESPACE])
    await paths.validate_path(keychain, address_n)
    private_key = keychain.derive(address_n).private_key()

    curve = session.curve
    if curve == "secp256k1":
        from trezor.crypto.curve import secp256k1

        if canonical == _CANONICAL_ANY:
            return secp256k1.sign(private_key, digest, compressed)
        if canonical == _CANONICAL_ETHEREUM:
            return secp256k1.sign(
                private_key, digest, compressed, secp256k1.CANONICAL_SIG_ETHEREUM
            )
        raise DataError("Unsupported canonical signature type")

    if canonical != _CANONICAL_ANY:
        raise DataError(f"Canonical signatures are not supported on {curve}")
    if curve == "nist256p1":
        from trezor.crypto.curve import nist256p1

        return nist256p1.sign(private_key, digest, compressed)
    elif curve == "ed25519":
        from trezor.crypto.curve import ed25519

        # The app expects a fixed 65-byte signature shared by all curves (see
        # `sign_digest` in the SDK), so the 64-byte Ed25519 signature is
        # zero-padded; the app uses the first 64 bytes.
        return ed25519.sign(private_key, digest) + b"\x00"
    elif curve == "bip340":
        from trezor.crypto.curve import bip340

        return bip340.sign(private_key, digest)
    else:
        raise DataError(f"Unsupported curve: {curve} for signing digest")


async def _address_mac_keychain(session: Session, address_n: list[int]) -> Keychain:
    keychain = await get_keychain(session.curve, session.schemas, [_SLIP24_NAMESPACE])
    await paths.validate_path(keychain, address_n)
    return keychain


async def _get_address_mac(session: Session, obj: Any) -> bytes:
    from apps.common.address_mac import get_address_mac

    address_n, address, slip44 = obj
    keychain = await _address_mac_keychain(session, address_n)
    return get_address_mac(address, slip44, address_n, keychain)


async def _check_address_mac(session: Session, obj: Any) -> bool:
    from apps.common.address_mac import check_address_mac

    address_n, mac, address, slip44 = obj
    keychain = await _address_mac_keychain(session, address_n)
    check_address_mac(address, mac, slip44, address_n, keychain)
    return True


async def _verify_nonce_cache(session: Session, obj: Any) -> bool:
    from storage.cache_common import APP_COMMON_NONCE

    result = context.cache_get(APP_COMMON_NONCE) == bytes(obj)
    if result:
        context.cache_delete(APP_COMMON_NONCE)
    return result


_HANDLERS: dict[int, CryptoHandler] = {
    _GET_XPUB: _get_xpub,
    _GET_PUBLIC_KEY: _get_public_key,
    _SIGN_DIGEST: _sign_digest,
    _GET_ADDRESS_MAC: _get_address_mac,
    _CHECK_ADDRESS_MAC: _check_address_mac,
    _VERIFY_NONCE_CACHE: _verify_nonce_cache,
}
