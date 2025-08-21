from micropython import const
from typing import TYPE_CHECKING

from trezor.wire import ProcessError
from trezor.wire.context import call as ctx_call

from apps.cardano.helpers.credential import Credential
from apps.cardano.helpers.paths import SCHEMA_MINT, SCHEMA_PUBKEY
from apps.cardano.helpers.utils import derive_public_key, is_printable_ascii
from apps.common import cbor

from . import addresses, seed

if TYPE_CHECKING:
    from typing import Any

    from trezor.messages import CardanoMessageSignature, CardanoSignMessageInit

    from apps.common.cbor import CborSequence

    Headers = dict[str | int, Any]
    from apps.common.keychain import Keychain as Slip21Keychain

_COSE_HEADER_ADDRESS_KEY = "address"
_COSE_HEADER_ALGORITHM_KEY = const(1)
_COSE_EDDSA_ALGORITHM_ID = const(-8)


async def _validate_message_signing_path(
    path: list[int], keychain: seed.Keychain
) -> None:
    from apps.common import paths

    await paths.validate_path(keychain, path)

    if not SCHEMA_PUBKEY.match(path) and not SCHEMA_MINT.match(path):
        raise ProcessError("Invalid signing path")


async def _validate_message_init(
    msg: CardanoSignMessageInit, keychain: seed.Keychain
) -> None:
    if msg.address_parameters:
        if msg.network_id is None or msg.protocol_magic is None:
            raise ProcessError(
                "Must specify network_id and protocol_magic if using address_parameters"
            )
        addresses.validate_message_address_parameters(msg.address_parameters)

    await _validate_message_signing_path(msg.signing_path, keychain)


async def _get_confirmed_header_address(
    msg: CardanoSignMessageInit, keychain: seed.Keychain
) -> bytes:
    from . import layout

    if msg.address_parameters:
        assert (
            msg.protocol_magic is not None and msg.network_id is not None
        )  # _validate_message_init

        await layout.show_message_header_credentials(
            [
                Credential.payment_credential(msg.address_parameters),
                Credential.stake_credential(msg.address_parameters),
            ]
        )

        return addresses.derive_bytes(
            keychain, msg.address_parameters, msg.protocol_magic, msg.network_id
        )
    else:
        return addresses.get_public_key_hash(keychain, msg.signing_path)


async def _get_payload_data(
    payload_size: int,
    chunk_length: int,
    chunk_offset: int,
) -> bytes:
    """Returns payload data using length+offset pattern."""
    from trezor.messages import CardanoMessageDataRequest, CardanoMessageDataResponse

    if chunk_offset + chunk_length > payload_size:
        raise ProcessError("Requested data exceeds payload size")

    request = CardanoMessageDataRequest(length=chunk_length, offset=chunk_offset)
    response = await ctx_call(request, CardanoMessageDataResponse)

    if len(response.data) != chunk_length:
        raise ProcessError("Data length mismatch")

    return response.data


async def _get_confirmed_payload(size: int, prefer_hex_display: bool) -> bytes:
    from . import layout

    # Request the entire payload at once for now, regardless of RAM constraints.
    payload = (
        await _get_payload_data(payload_size=size, chunk_length=size, chunk_offset=0)
        if size > 0
        else b""
    )

    if size == 28 and not is_printable_ascii(payload):
        # We do not support hashed signing yet, this is a heuristic to reject them.
        # The length of a Blake2b224 hash is 28 bytes (224 bits).
        # The chance of a valid hash composed of only printable ASCII is very low.
        raise ProcessError("The payload is interpreted as a hash and cannot be signed")

    await layout.confirm_message_payload(
        payload,
        size,
        prefer_hex_display,
    )

    return payload


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
    msg: CardanoSignMessageInit,
    keychain: seed.Keychain,
    slip21_keychain: "Slip21Keychain",
) -> CardanoMessageSignature:
    from trezor.messages import CardanoMessageSignature

    from . import layout

    await _validate_message_init(msg, keychain)

    payload = await _get_confirmed_payload(
        size=msg.payload_size,
        prefer_hex_display=msg.prefer_hex_display,
    )

    address = await _get_confirmed_header_address(msg, keychain)

    headers: Headers = {
        _COSE_HEADER_ALGORITHM_KEY: _COSE_EDDSA_ALGORITHM_ID,
        _COSE_HEADER_ADDRESS_KEY: address,
    }

    await layout.confirm_message_path(path=msg.signing_path)

    signature = _sign_sig_structure(
        msg.signing_path,
        keychain,
        _cborize_sig_structure(payload=payload, protected_headers=headers),
    )

    return CardanoMessageSignature(
        signature=signature,
        address=address,
        pub_key=derive_public_key(keychain, msg.signing_path),
    )
