from micropython import const

from trezor import wire
from trezor.crypto.curve import secp256k1
from trezor.messages import EthereumSignTypedHash, EthereumTypedDataSignature

from apps.common import paths, safety_checks

from .helpers import address_from_bytes
from .keychain import PATTERNS_ADDRESS, with_keychain_from_path
from .layout import confirm_hash
from .sign_typed_data import finalize_hash

if False:
    from apps.common.keychain import Keychain
    from trezor.wire import Context

_HASH_LEN = const(32)


@with_keychain_from_path(*PATTERNS_ADDRESS)
async def sign_typed_data_hash(
    ctx: Context, msg: EthereumSignTypedHash, keychain: Keychain
) -> EthereumTypedDataSignature:
    if safety_checks.is_strict():
        raise wire.ProcessError("Blind signing forbidden in strict setting")

    if (
        len(msg.domain_separator_hash) != _HASH_LEN
        or len(msg.message_hash) != _HASH_LEN
    ):
        raise wire.DataError("Invalid hash length")

    await paths.validate_path(ctx, keychain, msg.address_n)

    await confirm_hash(ctx, msg.domain_separator_hash, description="Domain hash:")
    await confirm_hash(ctx, msg.message_hash, description="Message hash:")
    data_hash = finalize_hash(msg.domain_separator_hash, msg.message_hash)

    node = keychain.derive(msg.address_n)
    signature = secp256k1.sign(
        node.private_key(), data_hash, False, secp256k1.CANONICAL_SIG_ETHEREUM
    )

    return EthereumTypedDataSignature(
        address=address_from_bytes(node.ethereum_pubkeyhash()),
        signature=signature[1:] + signature[0:1],
    )
