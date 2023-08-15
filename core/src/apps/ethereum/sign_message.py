from typing import TYPE_CHECKING

from .keychain import PATTERNS_ADDRESS, with_keychain_from_path

if TYPE_CHECKING:
    from trezor.messages import EthereumMessageSignature, EthereumSignMessage

    from apps.common.keychain import Keychain

    from .definitions import Definitions


def message_digest(message: bytes) -> bytes:
    from trezor.crypto.hashlib import sha3_256
    from trezor.utils import HashWriter

    h = HashWriter(sha3_256(keccak=True))
    signed_message_header = b"\x19Ethereum Signed Message:\n"
    h.extend(signed_message_header)
    h.extend(str(len(message)).encode())
    h.extend(message)
    return h.get_digest()


@with_keychain_from_path(*PATTERNS_ADDRESS)
async def sign_message(
    msg: EthereumSignMessage,
    keychain: Keychain,
    defs: Definitions,
) -> EthereumMessageSignature:
    from trezor.crypto.curve import secp256k1
    from trezor.messages import EthereumMessageSignature
    from trezor.ui.layouts import confirm_signverify

    from apps.common import paths
    from apps.common.signverify import decode_message

    from .helpers import address_from_bytes

    await paths.validate_path(keychain, msg.address_n)

    node = keychain.derive(msg.address_n)
    address = address_from_bytes(node.ethereum_pubkeyhash(), defs.network)
    await confirm_signverify("ETH", decode_message(msg.message), address, verify=False)

    signature = secp256k1.sign(
        node.private_key(),
        message_digest(msg.message),
        False,
        secp256k1.CANONICAL_SIG_ETHEREUM,
    )

    return EthereumMessageSignature(
        address=address,
        signature=signature[1:] + bytearray([signature[0]]),
    )
