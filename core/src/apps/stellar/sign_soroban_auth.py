from typing import TYPE_CHECKING

from apps.common.keychain import auto_keychain

if TYPE_CHECKING:
    from trezor.messages import StellarSignedTx, StellarSignSorobanAuthorization

    from apps.common.keychain import Keychain


@auto_keychain(__name__)
async def sign_soroban_auth(
    msg: StellarSignSorobanAuthorization, keychain: Keychain
) -> StellarSignedTx:
    from trezor.crypto.curve import ed25519
    from trezor.crypto.hashlib import sha256
    from trezor.messages import StellarSignedTx

    from apps.common import paths, seed

    from . import helpers, layout, writers

    await paths.validate_path(keychain, msg.address_n)

    node = keychain.derive(msg.address_n)
    pubkey = seed.remove_ed25519_prefix(node.public_key())

    w = bytearray()

    # ---------------------------------
    # INIT
    # ---------------------------------
    address = helpers.address_from_public_key(pubkey)

    # confirm init
    await layout.require_confirm_init(address, msg.network_passphrase, True)

    # confirm auth info
    await layout.confirm_soroban_auth_info(
        msg.nonce, msg.signature_expiration_ledger, msg.invocation
    )

    writers.write_soroban_auth_info(
        w,
        network_passphrase=msg.network_passphrase,
        nonce=msg.nonce,
        signature_expiration_ledger=msg.signature_expiration_ledger,
        invocation=msg.invocation,
    )

    # ---------------------------------
    # FINAL
    # ---------------------------------
    # final confirm
    await layout.confirm_soroban_auth_final()

    # sign
    digest = sha256(w).digest()
    signature = ed25519.sign(node.private_key(), digest)

    # Add the public key for verification that the right account was used for signing
    return StellarSignedTx(public_key=pubkey, signature=signature)
