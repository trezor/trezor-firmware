from micropython import const
from typing import TYPE_CHECKING

from trezor import TR
from trezor.crypto.curve import secp256k1
from trezor.messages import EthereumAuth7702Tuple
from trezor.wire import DataError, ProcessError

from .networks import UNKNOWN_NETWORK
from .sc_constants import lookup_eip7702_address

if TYPE_CHECKING:
    from trezor.messages import EthereumSignAuth7702

    from apps.common.keychain import Keychain

    from .definitions import Definitions

_MAGIC = const(5)

_REVOKE_ADDRESS = b"\x00" * 20


async def sign_auth_eip7702(
    msg: EthereumSignAuth7702, keychain: Keychain, defs: Definitions
) -> EthereumAuth7702Tuple:
    """
    Confirm and sign a single EIP-7702 authorization/revocation tuple.
    """

    from trezor.crypto import rlp
    from trezor.ui.layouts import (
        confirm_ethereum_eip7702_auth,
        confirm_ethereum_eip7702_revoke,
    )

    from apps.common import paths, safety_checks

    from .helpers import bytes_from_address, get_account_and_path, keccak256

    await paths.validate_path(keychain, msg.address_n)

    chain_id = msg.chain_id
    if chain_id == 0:
        raise DataError("chain_id 0 not supported")

    if defs.network is UNKNOWN_NETWORK:
        raise DataError("Unknown network")

    network_item = (TR.ethereum__network, defs.network.name, None)

    account, account_path = get_account_and_path(msg.address_n)
    if account is None or account_path is None:
        raise DataError("Unknown account")

    nonce = msg.nonce
    if nonce >= 0xFFFFFFFFFFFFFFFF:
        raise DataError("Invalid nonce")

    delegate_bytes = bytes_from_address(msg.delegate)
    if delegate_bytes == _REVOKE_ADDRESS:
        # revocation can be done with strict safety checks
        await confirm_ethereum_eip7702_revoke(
            network_item=network_item,
            account=account,
            account_path=account_path,
            nonce=nonce,
        )
    else:
        if safety_checks.is_strict():
            raise ProcessError(
                "EIP-7702 authorisation not allowed with strict safety checks"
            )

        delegate_name = lookup_eip7702_address(chain_id, delegate_bytes)
        if delegate_name is None:
            raise DataError("Unknown EIP-7702 delegate address")

        await confirm_ethereum_eip7702_auth(
            delegate_name=delegate_name,
            delegate_addr=msg.delegate,
            network_item=network_item,
            account=account,
            account_path=account_path,
            nonce=nonce,
        )

    sha = keccak256()
    sha.append(_MAGIC)

    fields: rlp.RLPList = [chain_id, delegate_bytes, nonce]
    rlp.write(sha, fields)

    digest = sha.get_digest()
    node = keychain.derive(msg.address_n)
    signature = secp256k1.sign(
        node.private_key(), digest, False, secp256k1.CANONICAL_SIG_ETHEREUM
    )
    # EIP-7702 authorization tuple: [chain_id, delegate, nonce, y_parity, r, s]
    return EthereumAuth7702Tuple(
        items=[
            rlp.int_to_bytes(chain_id),
            delegate_bytes,
            rlp.int_to_bytes(nonce),
            rlp.int_to_bytes(signature[0] - 27),
            signature[1:33],
            signature[33:],
        ]
    )
