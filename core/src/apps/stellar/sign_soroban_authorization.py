from typing import TYPE_CHECKING

from apps.common.keychain import with_slip44_keychain

from . import CURVE, PATTERN, SLIP44_ID

if TYPE_CHECKING:
    from trezor.messages import (
        StellarSignSorobanAuthorization,
        StellarSorobanAuthorizationSignature,
    )

    from apps.common.keychain import Keychain as Slip21Keychain


@with_slip44_keychain(*[PATTERN], slip44_id=SLIP44_ID, curve=CURVE)
async def sign_soroban_authorization(
    msg: StellarSignSorobanAuthorization, keychain: Slip21Keychain
) -> StellarSorobanAuthorizationSignature:
    from trezor.crypto.curve import ed25519
    from trezor.crypto.hashlib import sha256
    from trezor.enums import StellarSorobanAuthorizationEnvelopeType
    from trezor.messages import StellarSorobanAuthorizationSignature
    from trezor.wire import DataError, ProcessError

    from apps.common import paths, seed

    from . import helpers, layout, writers
    from .operations.layout import confirm_authorized_invocation

    await paths.validate_path(keychain, msg.address_n)

    node = keychain.derive(msg.address_n)
    pubkey = seed.remove_ed25519_prefix(node.public_key())
    signing_address = helpers.address_from_public_key(pubkey)

    # Only the address-bound preimage variant introduced in Protocol 27 is supported
    if (
        msg.envelope_type
        != StellarSorobanAuthorizationEnvelopeType.ENVELOPE_TYPE_SOROBAN_AUTHORIZATION_WITH_ADDRESS
    ):
        raise ProcessError("Stellar: unsupported authorization envelope type")
    auth = msg.soroban_authorization_with_address
    if auth is None:
        raise DataError("Stellar: missing soroban_authorization_with_address")

    # Serialize the ENVELOPE_TYPE_SOROBAN_AUTHORIZATION_WITH_ADDRESS preimage
    # (Protocol 27, CAP-46-11/CAP-71). It binds the signature to the
    # authorizing address.
    w = bytearray()
    writers.write_uint32(w, msg.envelope_type)
    writers.write_bytes_fixed(
        w, sha256(msg.network_passphrase.encode()).digest(), 32  # network id
    )
    writers.write_int64(w, auth.nonce)
    writers.write_uint32(w, auth.signature_expiration_ledger)
    writers.write_sc_address(w, auth.address)
    writers.write_soroban_authorized_invocation(w, auth.invocation)

    await layout.require_confirm_auth_signing_address(signing_address, msg.address_n)

    if auth.address != signing_address:
        # The credentials belong to another party, e.g. a contract account of
        # which the device account is a signer.
        await layout.require_confirm_auth_on_behalf_of(auth.address)

    await confirm_authorized_invocation(auth.invocation)
    await layout.require_confirm_signature_expiration_ledger(
        auth.signature_expiration_ledger
    )

    payload = sha256(w).digest()
    signature = ed25519.sign(node.private_key(), payload)

    return StellarSorobanAuthorizationSignature(public_key=pubkey, signature=signature)
