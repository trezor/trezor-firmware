from typing import TYPE_CHECKING

from trezor import TR
from trezor.crypto.curve import secp256k1
from trezor.messages import EthereumAuth7702Signature
from trezor.wire import DataError, ProcessError

from .keychain import with_keychain_from_chain_id
from .networks import UNKNOWN_NETWORK

if TYPE_CHECKING:
    from trezor.messages import EthereumSignAuth7702

    from apps.common.keychain import Keychain

    from .definitions import Definitions

_MAGIC = b"\x05"

_REVOKE_ADDRESS = b"\x00" * 20

_KNOWN_ADDRESSES: dict[bytes, str] = {
    # https://etherscan.io/address/0x5a7fc11397e9a8ad41bf10bf13f22b0a63f96f6d
    b"\x5a\x7f\xc1\x13\x97\xe9\xa8\xad\x41\xbf\x10\xbf\x13\xf2\x2b\x0a\x63\xf9\x6f\x6d": "Ambire",
    # https://etherscan.io/address/0x63c0c19a282a1b52b07dd5a65b58948a07dae32b
    b"\x63\xc0\xc1\x9a\x28\x2a\x1b\x52\xb0\x7d\xd5\xa6\x5b\x58\x94\x8a\x07\xda\xe3\x2b": "Metamask",
}


@with_keychain_from_chain_id
async def sign_auth_eip7702(
    msg: EthereumSignAuth7702,
    keychain: Keychain,
    defs: Definitions,
) -> EthereumAuth7702Signature:

    from trezor.crypto import rlp
    from trezor.ui.layouts import (
        confirm_ethereum_eip7702_auth,
        confirm_ethereum_eip7702_revoke,
        show_continue_in_app,
    )

    from apps.common import paths, safety_checks

    from .helpers import bytes_from_address, get_account_and_path, keccak256

    await paths.validate_path(keychain, msg.address_n)

    chain_id = msg.chain_id
    if chain_id == 0:
        # special marker making signature valid for all chains
        network_item = (TR.ethereum__network, TR.ethereum__all_evms, None)
    else:
        if defs.network is UNKNOWN_NETWORK:
            network_item = (
                TR.ethereum__approve_chain_id,
                f"{chain_id} (0x{chain_id:x})",
                None,
            )
        else:
            network_item = (TR.ethereum__network, defs.network.name, None)

    account, account_path = get_account_and_path(msg.address_n)
    if account is None or account_path is None:
        raise DataError("Unknown account")

    if msg.nonce >= 0xFFFFFFFFFFFFFFFF:
        raise DataError("Invalid nonce")

    delegate_bytes = bytes_from_address(msg.delegate)
    if delegate_bytes == _REVOKE_ADDRESS:
        # revocation can be done with strict safety checks
        await confirm_ethereum_eip7702_revoke(
            network_item=network_item,
            account=account,
            account_path=account_path,
            nonce=msg.nonce,
        )
        done_msg = TR.ethereum__revoke_done
    else:
        if safety_checks.is_strict():
            raise ProcessError(
                "EIP-7702 authorisation not allowed with strict safety checks"
            )

        delegate_name = _KNOWN_ADDRESSES.get(delegate_bytes)
        if delegate_name is None:
            raise DataError("Unknown EIP-7702 delegate address")

        await confirm_ethereum_eip7702_auth(
            delegate_name=delegate_name,
            delegate_addr=msg.delegate,
            network_item=network_item,
            account=account,
            account_path=account_path,
            nonce=msg.nonce,
        )
        done_msg = TR.ethereum__auth_done

    fields: tuple[rlp.RLPItem, ...] = (
        msg.chain_id,
        delegate_bytes,
        msg.nonce,
    )

    sha = keccak256(_MAGIC)

    data_length = sum(rlp.length(field) for field in fields)
    rlp.write_header(sha, data_length, rlp.LIST_HEADER_BYTE)
    for field in fields:
        rlp.write(sha, field)

    digest = sha.get_digest()
    node = keychain.derive(msg.address_n)
    signature = secp256k1.sign(
        node.private_key(), digest, False, secp256k1.CANONICAL_SIG_ETHEREUM
    )
    show_continue_in_app(done_msg)
    return EthereumAuth7702Signature(
        signature_v=signature[0] - 27,
        signature_r=signature[1:33],
        signature_s=signature[33:],
    )
