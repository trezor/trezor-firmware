from trezor.crypto.curve import secp256k1
from trezor.crypto.hashlib import sha3_256
from trezor.messages.EthereumMessageSignature import EthereumMessageSignature
from trezor.utils import HashWriter

from apps.common import paths
from apps.common.signverify import require_confirm_sign_message

from . import address
from .keychain import PATTERNS_ADDRESS, with_keychain_from_path


def message_digest(message):
    h = HashWriter(sha3_256(keccak=True))
    signed_message_header = "\x19Ethereum Signed Message:\n"
    h.extend(signed_message_header)
    h.extend(str(len(message)))
    h.extend(message)
    return h.get_digest()


@with_keychain_from_path(*PATTERNS_ADDRESS)
async def sign_message(ctx, msg, keychain):
    await paths.validate_path(ctx, keychain, msg.address_n)
    await require_confirm_sign_message(ctx, "ETH", msg.message)

    node = keychain.derive(msg.address_n)
    signature = secp256k1.sign(
        node.private_key(),
        message_digest(msg.message),
        False,
        secp256k1.CANONICAL_SIG_ETHEREUM,
    )

    return EthereumMessageSignature(
        address=address.address_from_bytes(node.ethereum_pubkeyhash()),
        signature=signature[1:] + bytearray([signature[0]]),
    )
