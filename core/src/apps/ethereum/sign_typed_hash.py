from typing import TYPE_CHECKING

from .keychain import PATTERNS_ADDRESS, with_keychain_from_path

if TYPE_CHECKING:
    from trezor.messages import EthereumTypedDataSignature, EthereumSignTypedHash

    from apps.common.keychain import Keychain

    from .definitions import Definitions


def message_digest(domain_separator_hash: bytes, message_hash: "bytes | None") -> bytes:
    from trezor.crypto.hashlib import sha3_256
    from trezor.utils import HashWriter

    h = HashWriter(sha3_256(keccak=True))
    h.extend(b"\x19\x01")
    h.extend(domain_separator_hash)
    h.extend(message_hash)
    return h.get_digest()


@with_keychain_from_path(*PATTERNS_ADDRESS)
async def sign_typed_hash(
    msg: EthereumSignTypedHash,
    keychain: Keychain,
    defs: Definitions,
) -> EthereumTypedDataSignature:
    from trezor import TR
    from trezor.crypto.curve import secp256k1
    from trezor.messages import EthereumTypedDataSignature
    from trezor.ui.layouts import confirm_properties

    from apps.common import paths

    from .helpers import address_from_bytes
    from .layout import require_confirm_address, confirm_typed_data_final

    await paths.validate_path(keychain, msg.address_n)

    node = keychain.derive(msg.address_n)
    address_bytes: bytes = node.ethereum_pubkeyhash()

    # Display address so user can validate it
    await require_confirm_address(address_bytes)

    await confirm_properties(
        "confirm_typed_hash",
        TR.ethereum__title_confirm_typed_hashes,
        (
            (TR.ethereum__domain_hash, msg.domain_separator_hash, True),
            (TR.ethereum__message_hash, msg.message_hash, True),
        ),
    )

    await confirm_typed_data_final()

    signature = secp256k1.sign(
        node.private_key(),
        message_digest(msg.domain_separator_hash, msg.message_hash),
        False,
        secp256k1.CANONICAL_SIG_ETHEREUM,
    )

    return EthereumTypedDataSignature(
        address=address_from_bytes(address_bytes, defs.network),
        signature=signature[1:] + bytearray([signature[0]]),
    )
