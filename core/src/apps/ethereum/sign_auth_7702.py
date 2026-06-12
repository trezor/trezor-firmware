from micropython import const
from typing import TYPE_CHECKING

from trezor import TR
from trezor.wire import ActionCancelled, DataError, ProcessError

from .keychain import PATTERNS_ADDRESS, with_keychain_from_path

if TYPE_CHECKING:
    from trezor.messages import EthereumAuth7702Signature, EthereumSignAuth7702

    from apps.common.keychain import Keychain

    from .definitions import Definitions

_MAGIC_7702 = const(5)

_ZERO_7702_DELEGATE = b"\x00" * 20

_AMBIRE_7702_DELEGATE = (
    b"\x5a\x7f\xc1\x13\x97\xe9\xa8\xad\x41\xbf\x10\xbf\x13\xf2\x2b\x0a\x63\xf9\x6f\x6d"
)

_METAMASK_7702_DELEGATE = (
    b"\x63\xc0\xc1\x9a\x28\x2a\x1b\x52\xb0\x7d\xd5\xa6\x5b\x58\x94\x8a\x07\xda\xe3\x2b"
)
if __debug__:
    from ubinascii import unhexlify

    # https://etherscan.io/address/0x5a7fc11397e9a8ad41bf10bf13f22b0a63f96f6d
    assert _AMBIRE_7702_DELEGATE == unhexlify(
        "5a7fc11397e9a8ad41bf10bf13f22b0a63f96f6d"
    )
    # https://etherscan.io/address/0x63c0c19a282a1b52b07dd5a65b58948a07dae32b
    assert _METAMASK_7702_DELEGATE == unhexlify(
        "63c0c19a282a1b52b07dd5a65b58948a07dae32b"
    )

KNOWN_EIP_7702_ADDRESS: dict[bytes, str] = {
    _AMBIRE_7702_DELEGATE: "Ambire",
    _METAMASK_7702_DELEGATE: "Metamask",
}


@with_keychain_from_path(*PATTERNS_ADDRESS)
async def sign_auth_7702(
    msg: EthereumSignAuth7702,
    keychain: Keychain,
    defs: Definitions,
) -> EthereumAuth7702Signature:

    from trezor import utils

    from apps.common import paths, safety_checks

    if utils.INTERNAL_MODEL == "T2T1":
        raise ActionCancelled("EIP-7702 authorisation not supported in T2T1")

    from trezor.crypto import rlp  # local_cache_global
    from trezor.crypto.hashlib import sha3_256
    from trezor.ui.layouts import (
        confirm_ethereum_auth_7702,
        confirm_ethereum_revocation_7702,
        show_continue_in_app,
    )
    from trezor.utils import HashWriter

    from .helpers import bytes_from_address, get_account_and_path
    from .networks import by_chain_id

    await paths.validate_path(keychain, msg.address_n)

    delegate_bytes = bytes_from_address(msg.delegate)
    is_revocation = delegate_bytes == _ZERO_7702_DELEGATE

    if not is_revocation and safety_checks.is_strict():
        raise ProcessError(
            "EIP-7702 authorisation not allowed with strict safety checks"
        )

    delegate_name: str | None = None
    if not is_revocation:
        delegate_name = KNOWN_EIP_7702_ADDRESS.get(delegate_bytes)
        if not delegate_name:
            raise DataError("Unknown EIP-7702 delegate address")

    network_name = (
        TR.ethereum__all_evms if msg.chain_id == 0 else by_chain_id(msg.chain_id).name
    )
    account, account_path = get_account_and_path(msg.address_n)
    assert account is not None and account_path is not None

    if is_revocation:
        await confirm_ethereum_revocation_7702(msg, account, account_path, network_name)
    else:
        assert delegate_name is not None
        await confirm_ethereum_auth_7702(
            msg, account, account_path, delegate_name, network_name
        )

    fields: tuple[rlp.RLPItem, ...] = (
        msg.chain_id,
        delegate_bytes,
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

    if is_revocation:
        show_continue_in_app(TR.ethereum__eip_7702_revocation_transaction_completion)
    else:
        show_continue_in_app(TR.ethereum__eip_7702_authorization_signed)
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
