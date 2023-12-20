from micropython import const
from typing import TYPE_CHECKING

from trezor.wire import ProcessError
from trezor.wire.context import call as ctx_call

from apps.cardano.helpers.chunks import MAX_CHUNK_SIZE, ChunkIterator
from apps.cardano.helpers.paths import SCHEMA_PUBKEY
from apps.common import cbor

from . import addresses, seed

if TYPE_CHECKING:
    from typing import Any

    from trezor.messages import CardanoSignMessageFinished, CardanoSignMessageInit

    from apps.common.cbor import CborSequence

    Headers = dict[str | int, Any]

_COSE_HEADER_ADDRESS_KEY = "address"
_COSE_HEADER_ALGORITHM_KEY = const(1)
_COSE_EDDSA_ALGORITHM_ID = const(-8)


def _validate_message_signing_path(path: list[int]) -> None:
    if not SCHEMA_PUBKEY.match(path):
        raise ProcessError("Invalid signing path")


def _validate_message_init(msg: CardanoSignMessageInit) -> None:
    if msg.address_parameters:
        if msg.network_id is None or msg.protocol_magic is None:
            raise ProcessError(
                "Must specify network_id and protocol_magic if using address_parameters"
            )
        addresses.validate_message_address_parameters(msg.address_parameters)

    if msg.payload_size > MAX_CHUNK_SIZE and not msg.hash_payload:
        raise ProcessError("Payload too long to sign without hashing")

    _validate_message_signing_path(msg.signing_path)


def _get_header_address(msg: CardanoSignMessageInit, keychain: seed.Keychain) -> bytes:
    if msg.address_parameters:
        assert (
            msg.protocol_magic is not None and msg.network_id is not None
        )  # _validate_message_init
        return addresses.derive_bytes(
            keychain, msg.address_parameters, msg.protocol_magic, msg.network_id
        )
    else:
        return addresses.get_public_key_hash(keychain, msg.signing_path)


async def _get_payload_hash_and_first_chunk(size: int) -> tuple[bytes, bytes]:
    """Returns the hash of the whole payload and the raw first chunk of the payload."""
    from trezor.crypto import hashlib
    from trezor.messages import (
        CardanoMessageItemAck,
        CardanoMessageItemHostAck,
        CardanoMessagePayloadChunk,
    )

    first_chunk = b""
    hash_fn = hashlib.blake2b(outlen=28)

    async for chunk_index, chunk in ChunkIterator(
        total_size=size,
        ack_msg=CardanoMessageItemAck(),
        chunk_type=CardanoMessagePayloadChunk,
    ):
        hash_fn.update(chunk.data)
        if chunk_index == 0:
            first_chunk = chunk.data

    await ctx_call(CardanoMessageItemAck(), CardanoMessageItemHostAck)
    return hash_fn.digest(), first_chunk


async def _get_confirmed_payload(
    size: int, is_signing_hash: bool, display_ascii: bool
) -> bytes:
    from . import layout

    hash, first_chunk = await _get_payload_hash_and_first_chunk(size)

    await layout.confirm_message_payload(
        payload_size=size,
        payload_first_chunk=first_chunk,
        payload_hash=hash,
        is_signing_hash=is_signing_hash,
        display_ascii=display_ascii,
    )

    return hash if is_signing_hash else first_chunk


def _cborize_sig_structure(
    payload: bytes,
    protected_headers: Headers,
    external_aad: bytes | None = None,
) -> CborSequence:
    serialized_headers = cbor.encode(protected_headers)
    # only "Signature1" context is supported
    return ["Signature1", serialized_headers, external_aad or b"", payload]


def _sign_sig_structure(
    path: list[int],
    keychain: seed.Keychain,
    cborized_sig_structure: CborSequence,
) -> bytes:
    from trezor.crypto.curve import ed25519

    serialized_sig_structure = cbor.encode(cborized_sig_structure)

    # Preventing ambiguity with tx body hashes
    if len(serialized_sig_structure) == 32:
        raise ProcessError("The structure to sign cannot be exactly 32 bytes long")

    node = keychain.derive(path)

    return ed25519.sign_ext(
        node.private_key(), node.private_key_ext(), serialized_sig_structure
    )


@seed.with_keychain
async def sign_message(
    msg: CardanoSignMessageInit, keychain: seed.Keychain
) -> CardanoSignMessageFinished:
    from trezor.messages import CardanoSignMessageFinished

    _validate_message_init(msg)

    address = _get_header_address(msg, keychain)

    headers: Headers = {
        _COSE_HEADER_ALGORITHM_KEY: _COSE_EDDSA_ALGORITHM_ID,
        _COSE_HEADER_ADDRESS_KEY: address,
    }

    payload = await _get_confirmed_payload(
        size=msg.payload_size,
        is_signing_hash=msg.hash_payload,
        display_ascii=msg.display_ascii,
    )

    signature = _sign_sig_structure(
        msg.signing_path,
        keychain,
        _cborize_sig_structure(payload=payload, protected_headers=headers),
    )

    return CardanoSignMessageFinished(signature=signature, address=address)
