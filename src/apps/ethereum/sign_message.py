from trezor.crypto.curve import secp256k1
from trezor.crypto.hashlib import sha3_256
from trezor.messages.EthereumMessageSignature import EthereumMessageSignature
from trezor.ui.text import Text
from trezor.utils import HashWriter

from .address import validate_full_path

from apps.common import paths, seed
from apps.common.confirm import require_confirm
from apps.common.signverify import split_message


def message_digest(message):
    h = HashWriter(sha3_256(keccak=True))
    signed_message_header = "\x19Ethereum Signed Message:\n"
    h.extend(signed_message_header)
    h.extend(str(len(message)))
    h.extend(message)
    return h.get_digest()


async def sign_message(ctx, msg):
    await paths.validate_path(ctx, validate_full_path, path=msg.address_n)
    await require_confirm_sign_message(ctx, msg.message)

    node = await seed.derive_node(ctx, msg.address_n)

    signature = secp256k1.sign(
        node.private_key(),
        message_digest(msg.message),
        False,
        secp256k1.CANONICAL_SIG_ETHEREUM,
    )

    sig = EthereumMessageSignature()
    sig.address = node.ethereum_pubkeyhash()
    sig.signature = signature[1:] + bytearray([signature[0]])
    return sig


async def require_confirm_sign_message(ctx, message):
    message = split_message(message)
    text = Text("Sign ETH message", new_lines=False)
    text.normal(*message)
    await require_confirm(ctx, text)
