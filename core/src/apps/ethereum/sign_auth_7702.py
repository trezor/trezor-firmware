from micropython import const
from typing import TYPE_CHECKING

from .keychain import PATTERNS_ADDRESS, with_keychain_from_path

if TYPE_CHECKING:
    from trezor.messages import EthereumAuth7702Signature, EthereumSignAuth7702

    from apps.common.keychain import Keychain

    from .definitions import Definitions

_MAGIC_7702 = const(5)


@with_keychain_from_path(*PATTERNS_ADDRESS)
async def sign_auth_7702(
    msg: EthereumSignAuth7702,
    keychain: Keychain,
    defs: Definitions,
) -> EthereumAuth7702Signature:
    from trezor import TR
    from trezor.crypto import rlp  # local_cache_global
    from trezor.crypto.curve import secp256k1
    from trezor.crypto.hashlib import sha3_256
    from trezor.enums import ButtonRequestType
    from trezor.ui.layouts import confirm_properties
    from trezor.utils import HashWriter

    from apps.common import paths

    from .helpers import address_from_bytes, bytes_from_address

    await paths.validate_path(keychain, msg.address_n)

    node = keychain.derive(msg.address_n)
    address = address_from_bytes(node.ethereum_pubkeyhash(), defs.network)

    await confirm_properties(
        "confirm_7702",
        TR.ethereum__sign_auth7702,
        (
            (f"{TR.words__account}:", address),
            (TR.ethereum__auth7702_delegate, msg.delegate),
            (TR.ethereum__auth7702_nonce, str(msg.nonce)),
            (TR.ethereum__auth7702_chainid, str(msg.chain_id)),
        ),
        hold=True,
        br_code=ButtonRequestType.ConfirmOutput,
    )

    fields: tuple[rlp.RLPItem, ...] = (
        msg.chain_id,
        bytes_from_address(msg.delegate),
        msg.nonce,
    )

    sha = HashWriter(sha3_256(keccak=True))
    sha.append(_MAGIC_7702)
    length = 0
    for field in fields:
        length += rlp.length(field)
    rlp.write_header(sha, length, rlp.LIST_HEADER_BYTE)
    for field in fields:
        rlp.write(sha, field)

    digest = sha.get_digest()
    result = _sign_digest(msg, keychain, digest)

    return result


def _sign_digest(
    msg: EthereumSignAuth7702, keychain: Keychain, digest: bytes
) -> EthereumAuth7702Signature:
    from trezor.crypto.curve import secp256k1
    from trezor.messages import EthereumAuth7702Signature

    node = keychain.derive(msg.address_n)
    signature = secp256k1.sign(
        node.private_key(), digest, False, secp256k1.CANONICAL_SIG_ETHEREUM
    )

    req = EthereumAuth7702Signature(
        signature_v=signature[0] - 27,
        signature_r=signature[1:33],
        signature_s=signature[33:],
    )

    return req
