import io
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from enum import IntEnum
from typing import TYPE_CHECKING, Any

import pytest

from trezorlib import exceptions, protobuf
from trezorlib.messages import ExtAppMessage, ExtAppResponse, Failure

from .generated import messages as m

if TYPE_CHECKING:
    from trezorlib.client import Session
    from trezorlib.tools import Address

# Testnet BIP-44 path, the one the testapp's manifest allows.
DEFAULT_BIP32_PATH = "m/44h/1h/0h/0/0"

# Version bytes of a testnet ("tpub") and a mainnet ("xpub") extended key.
TPUB_MAGIC = 0x043587CF
XPUB_MAGIC = 0x0488B21E


class SdkError(IntEnum):
    """`trezor_app_sdk::Error::code()`, which Core passes on as the Failure code."""

    ServiceError = 2
    DataError = 3
    Cancelled = 4
    InvalidFunction = 5
    InvalidMessage = 6
    InvalidArgument = 7
    ValueError = 8


# `DataError` messages: a `CryptoError` the SDK function returned, or an
# operation Core reported as failed.
INVALID_PUBLIC_KEY = "invalid public key"
INVALID_SIGNATURE = "invalid signature"
INVALID_ENCODING = "invalid encoding"
OPERATION_FAILED = "operation failed in Core"


@contextmanager
def raises(error: SdkError, message: str | None = None) -> Iterator[None]:
    """Expect the call to fail with the app error `error` (and `message`)."""
    with pytest.raises(exceptions.TrezorFailure) as e:
        yield
    assert e.value.code == error
    if message is not None:
        assert e.value.message == message


def message_id(msg: type[protobuf.MessageType] | protobuf.MessageType) -> int:
    """Return app-specific numeric message ID for a message class or instance."""
    if isinstance(msg, type):
        name = msg.__name__
    else:
        name = msg.__class__.__name__

    try:
        return int(m.MessageType[name])
    except KeyError as e:
        raise ValueError(f"Unknown message type: {name}") from e


def call_ext(
    session: "Session",
    instance_id: int,
    *,
    msg_data: protobuf.MessageType,
    expect: list[type[protobuf.MessageType]],
    timeout: float | None = None,
) -> Any:
    """Call a method on this session, process and return the response."""

    # Serialize to bytes
    buf = io.BytesIO()
    protobuf.dump_message(buf, msg_data)

    msg = ExtAppMessage(
        instance_id=instance_id,
        message_id=message_id(msg_data),
        data=buf.getvalue(),
    )
    if session.is_invalid:
        raise exceptions.InvalidSessionError(session.id)
    with session:
        resp = session.client._call(
            session, msg, expect=ExtAppResponse, timeout=timeout
        )
        buf = io.BytesIO(resp.data)

        assert isinstance(expect, list)
        assert len(expect) > 0

        expect_ids = [message_id(cls) for cls in expect]
        try:
            # Find the index of the matching message ID
            idx = expect_ids.index(resp.message_id)

            return protobuf.load_message(buf, expect[idx])
        except Exception:
            raise exceptions.TrezorFailure(
                failure=Failure(message="Unexpected response type")
            )


# ============================================================================
# Hashing
# ============================================================================


def hash(
    session: "Session",
    instance_id: int,
    algorithm: m.HashAlgorithm,
    chunks: Sequence[bytes],
) -> bytes:
    res = call_ext(
        session,
        instance_id,
        msg_data=m.Hash(algorithm=algorithm, chunks=list(chunks)),
        expect=[m.Digest],
    )
    return res.digest


def hmac(
    session: "Session",
    instance_id: int,
    algorithm: m.HmacAlgorithm,
    key: bytes,
    chunks: Sequence[bytes],
) -> bytes:
    res = call_ext(
        session,
        instance_id,
        msg_data=m.Hmac(algorithm=algorithm, key=key, chunks=list(chunks)),
        expect=[m.Digest],
    )
    return res.digest


# ============================================================================
# Keys and signatures (served by Core)
# ============================================================================


def get_xpub(
    session: "Session", instance_id: int, address_n: "Address", xpub_magic: int
) -> str:
    res = call_ext(
        session,
        instance_id,
        msg_data=m.GetXpub(address_n=list(address_n), xpub_magic=xpub_magic),
        expect=[m.Xpub],
    )
    return res.xpub


def get_public_key(
    session: "Session", instance_id: int, address_n: "Address", compressed: bool
) -> bytes:
    res = call_ext(
        session,
        instance_id,
        msg_data=m.GetPublicKey(address_n=list(address_n), compressed=compressed),
        expect=[m.PublicKey],
    )
    return res.public_key


def ecdsa_sign_digest(
    session: "Session",
    instance_id: int,
    address_n: "Address",
    digest: bytes,
    compressed: bool,
    canonical: m.CanonicalSig = m.CanonicalSig.Any,
) -> bytes:
    res = call_ext(
        session,
        instance_id,
        msg_data=m.EcdsaSignDigest(
            address_n=list(address_n),
            digest=digest,
            compressed=compressed,
            canonical=canonical,
        ),
        expect=[m.Signature],
    )
    return res.signature


def ed25519_sign(
    session: "Session", instance_id: int, address_n: "Address", message: bytes
) -> bytes:
    res = call_ext(
        session,
        instance_id,
        msg_data=m.Ed25519Sign(address_n=list(address_n), message=message),
        expect=[m.Signature],
    )
    return res.signature


def get_address_mac(
    session: "Session",
    instance_id: int,
    address_n: "Address",
    address: str,
    slip44: int,
) -> bytes:
    res = call_ext(
        session,
        instance_id,
        msg_data=m.GetAddressMac(
            address_n=list(address_n), address=address, slip44=slip44
        ),
        expect=[m.AddressMac],
    )
    return res.mac


def check_address_mac(
    session: "Session",
    instance_id: int,
    address_n: "Address",
    mac: bytes,
    address: str,
    slip44: int,
) -> None:
    call_ext(
        session,
        instance_id,
        msg_data=m.CheckAddressMac(
            address_n=list(address_n), mac=mac, address=address, slip44=slip44
        ),
        expect=[m.Success],
    )


def verify_nonce_cache(session: "Session", instance_id: int, nonce: bytes) -> bool:
    res = call_ext(
        session,
        instance_id,
        msg_data=m.VerifyNonceCache(nonce=nonce),
        expect=[m.Bool],
    )
    return res.value


# ============================================================================
# Signature verification and key recovery
# ============================================================================


def ecdsa_verify(
    session: "Session",
    instance_id: int,
    curve: m.EcdsaCurve,
    public_key: bytes,
    signature: bytes,
    message: bytes,
) -> None:
    call_ext(
        session,
        instance_id,
        msg_data=m.EcdsaVerify(
            curve=curve, public_key=public_key, signature=signature, message=message
        ),
        expect=[m.Success],
    )


def ecdsa_verify_digest(
    session: "Session",
    instance_id: int,
    curve: m.EcdsaCurve,
    public_key: bytes,
    signature: bytes,
    digest: bytes,
) -> None:
    call_ext(
        session,
        instance_id,
        msg_data=m.EcdsaVerifyDigest(
            curve=curve, public_key=public_key, signature=signature, digest=digest
        ),
        expect=[m.Success],
    )


def ecdsa_recover_pubkey(
    session: "Session",
    instance_id: int,
    curve: m.EcdsaCurve,
    signature: bytes,
    digest: bytes,
) -> bytes:
    res = call_ext(
        session,
        instance_id,
        msg_data=m.EcdsaRecoverPubkey(curve=curve, signature=signature, digest=digest),
        expect=[m.PublicKey],
    )
    return res.public_key


def ed25519_verify(
    session: "Session",
    instance_id: int,
    public_key: bytes,
    signature: bytes,
    message: bytes,
) -> None:
    call_ext(
        session,
        instance_id,
        msg_data=m.Ed25519Verify(
            public_key=public_key, signature=signature, message=message
        ),
        expect=[m.Success],
    )


# ============================================================================
# CoSi
# ============================================================================


def cosi_verify(
    session: "Session",
    instance_id: int,
    threshold: int,
    message: bytes,
    public_keys: Sequence[bytes],
    sigmask: int,
    signature: bytes,
) -> None:
    call_ext(
        session,
        instance_id,
        msg_data=m.CosiVerify(
            threshold=threshold,
            message=message,
            public_keys=list(public_keys),
            sigmask=sigmask,
            signature=signature,
        ),
        expect=[m.Success],
    )


def cosi_combine_publickeys(
    session: "Session", instance_id: int, public_keys: Sequence[bytes]
) -> bytes:
    res = call_ext(
        session,
        instance_id,
        msg_data=m.CosiCombinePublicKeys(public_keys=list(public_keys)),
        expect=[m.PublicKey],
    )
    return res.public_key


# ============================================================================
# Base58
# ============================================================================


def base58_encode(session: "Session", instance_id: int, data: bytes) -> str:
    res = call_ext(
        session,
        instance_id,
        msg_data=m.Base58Encode(data=data),
        expect=[m.Base58],
    )
    return res.encoded


def base58_decode(session: "Session", instance_id: int, encoded: str) -> bytes:
    res = call_ext(
        session,
        instance_id,
        msg_data=m.Base58Decode(encoded=encoded),
        expect=[m.Data],
    )
    return res.data


def base58check_encode(session: "Session", instance_id: int, data: bytes) -> str:
    res = call_ext(
        session,
        instance_id,
        msg_data=m.Base58CheckEncode(data=data),
        expect=[m.Base58],
    )
    return res.encoded


def base58check_decode(session: "Session", instance_id: int, encoded: str) -> bytes:
    res = call_ext(
        session,
        instance_id,
        msg_data=m.Base58CheckDecode(encoded=encoded),
        expect=[m.Data],
    )
    return res.data
