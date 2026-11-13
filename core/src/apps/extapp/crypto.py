from typing import TYPE_CHECKING

import trezorcrypto_api
from trezor.wire.errors import DataError

from apps.common import paths

from .session import _SLIP24_NAMESPACE, MSG_ID_ERROR, SERVICE_CRYPTO, describe

if __debug__:
    from trezor import log

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from trezorio import IpcMessage
    from typing import Any

    from apps.common.keychain import Keychain

    from .session import Session

    CryptoHandler = Callable[[Session, Any], Awaitable[Any]]

_GET_XPUB = 0
_GET_PUBLIC_KEY = 1
_ECDSA_SIGN_DIGEST = 2
_ED25519_SIGN = 3
_GET_ADDRESS_MAC = 4
_CHECK_ADDRESS_MAC = 5

# `CanonicalSig` values in the SDK.
_CANONICAL_ANY = 0
_CANONICAL_ETHEREUM = 1

# `Curve` values in the SDK; `EcdsaCurve` has the first two.
_CURVES = ("secp256k1", "nist256p1", "ed25519", "curve25519")
_ECDSA_CURVES = _CURVES[:2]


async def handle(session: Session, msg: IpcMessage) -> None:
    """Run a crypto operation requested by the app and send it the result.

    A failed operation is reported to the app as `MSG_ID_ERROR`; only an
    unknown operation or a failure to reply kills the app.
    """
    handler = _HANDLERS.get(msg.message_id)
    if handler is None:
        session.die("Unknown crypto operation")

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
            session.die("Failed to send crypto error")
        return

    try:
        data = trezorcrypto_api.serialize_crypto_result(result=result)
        session.send(SERVICE_CRYPTO, msg.message_id, data)
    except Exception:
        session.die("Failed to serialize or send crypto result")


def _curve(value: int, curves: tuple[str, ...] = _CURVES) -> str:
    if not 0 <= value < len(curves):
        raise DataError("Unknown curve")
    return curves[value]


def _check_not_slip25(address_n: list[int]) -> None:
    from apps.common.keychain import ForbiddenKeyPath

    if address_n and address_n[0] == paths.SLIP25_PURPOSE:
        # UnlockPath is required to access SLIP25 paths.
        raise ForbiddenKeyPath


def _check_path(session: Session, address_n: list[int]) -> None:
    from apps.common.keychain import ForbiddenKeyPath

    # the manifest's paths on any curve; apps only run with strict checks
    if not any(schema.match(address_n) for schema in session.schemas):
        raise ForbiddenKeyPath


async def _get_xpub(session: Session, obj: Any) -> bytes:
    # a serialized xpub without its version, the app adds it
    curve, address_n = obj
    _check_not_slip25(address_n)
    _check_path(session, address_n)
    keychain = await session.keychain(_curve(curve))
    node = keychain.derive(address_n)
    return (
        node.depth().to_bytes(1, "big")
        + node.fingerprint().to_bytes(4, "big")
        + node.child_num().to_bytes(4, "big")
        + node.chain_code()
        + node.public_key()
    )


async def _get_public_key(session: Session, obj: Any) -> bytes:
    curve, address_n, compressed = obj
    _check_not_slip25(address_n)
    _check_path(session, address_n)
    curve = _curve(curve)
    keychain = await session.keychain(curve)
    private_key = keychain.derive(address_n).private_key()

    if curve == "secp256k1":
        from trezor.crypto.curve import secp256k1

        public_key = secp256k1.publickey(private_key, compressed)
    elif curve == "nist256p1":
        from trezor.crypto.curve import nist256p1

        public_key = nist256p1.publickey(private_key, compressed)
    elif curve == "ed25519":
        from trezor.crypto.curve import ed25519

        public_key = ed25519.publickey(private_key)
    else:
        from trezor.crypto.curve import curve25519

        public_key = curve25519.publickey(private_key)
    return public_key


async def _ecdsa_sign_digest(session: Session, obj: Any) -> bytes:
    curve, address_n, digest, compressed, canonical = obj
    curve = _curve(curve, _ECDSA_CURVES)
    _check_path(session, address_n)
    keychain = await session.keychain(curve)
    private_key = keychain.derive(address_n).private_key()

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
    from trezor.crypto.curve import nist256p1

    return nist256p1.sign(private_key, digest, compressed)


async def _ed25519_sign(session: Session, obj: Any) -> bytes:
    from trezor.crypto.curve import ed25519

    address_n, message = obj
    _check_path(session, address_n)
    keychain = await session.keychain("ed25519")
    private_key = keychain.derive(address_n).private_key()
    return ed25519.sign(private_key, message)


async def _address_mac_keychain() -> Keychain:
    from apps.common.keychain import get_keychain

    # SLIP-21 only: the MAC key depends on no curve and no path
    return await get_keychain("", [], [_SLIP24_NAMESPACE])


async def _get_address_mac(session: Session, obj: Any) -> bytes:
    from apps.common.address_mac import get_address_mac

    address_n, address, slip44 = obj
    _check_path(session, address_n)
    keychain = await _address_mac_keychain()
    return get_address_mac(address, slip44, address_n, keychain)


async def _check_address_mac(session: Session, obj: Any) -> bool:
    from apps.common.address_mac import check_address_mac

    address_n, mac, address, slip44 = obj
    keychain = await _address_mac_keychain()
    # raises on a wrong MAC; the path may belong to another app, e.g. in a memo
    check_address_mac(address, mac, slip44, address_n, keychain)
    return True


_HANDLERS: dict[int, CryptoHandler] = {
    _GET_XPUB: _get_xpub,
    _GET_PUBLIC_KEY: _get_public_key,
    _ECDSA_SIGN_DIGEST: _ecdsa_sign_digest,
    _ED25519_SIGN: _ed25519_sign,
    _GET_ADDRESS_MAC: _get_address_mac,
    _CHECK_ADDRESS_MAC: _check_address_mac,
}
