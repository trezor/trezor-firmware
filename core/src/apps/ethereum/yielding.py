from typing import TYPE_CHECKING

from trezor.utils import BufferReader
from trezor.wire import DataError

from .yielding_vaults import lookup_vault

if TYPE_CHECKING:
    from buffer_types import AnyBytes
    from typing import Any, Coroutine, Iterable

    from trezor.messages import EthereumNetworkInfo, EthereumTokenInfo
    from trezor.ui.layouts import StrPropertyType

    from .helpers import ConfirmDataFn
    from .keychain import MsgInSignTx

# https://ethereum.org/developers/docs/standards/tokens/erc-4626
FUNC_SIG_DEPOSIT = b"\x6e\x55\x3f\x65"
FUNC_SIG_WITHDRAW = b"\xb4\x60\xaf\x94"
FUNC_SIG_REDEEM = b"\xba\x08\x76\x52"

if __debug__:
    from trezor.crypto.hashlib import sha3_256

    assert (
        FUNC_SIG_DEPOSIT
        == sha3_256(b"deposit(uint256,address)", keccak=True).digest()[:4]
    )
    assert (
        FUNC_SIG_WITHDRAW
        == sha3_256(b"withdraw(uint256,address,address)", keccak=True).digest()[:4]
    )
    assert (
        FUNC_SIG_REDEEM
        == sha3_256(b"redeem(uint256,address,address)", keccak=True).digest()[:4]
    )


def get_approver(
    msg: MsgInSignTx,
    network: EthereumNetworkInfo,
    address_bytes: AnyBytes,
    maximum_fee: str,
    fee_items: Iterable[StrPropertyType],
    sender_bytes: AnyBytes,
) -> tuple[ConfirmDataFn, Coroutine[Any, Any, None]] | None:

    from .clear_signing import SC_FUNC_SIG_BYTES
    from .helpers import get_progress_indicator

    if msg.data_length > len(msg.data_initial_chunk):
        return None

    data_reader = BufferReader(msg.data_initial_chunk)
    if data_reader.remaining_count() < SC_FUNC_SIG_BYTES:
        return None

    is_known_vault, vault_str, asset_token, vault_token = lookup_vault(
        network, address_bytes
    )

    handler = None
    func_sig = data_reader.read_memoryview(SC_FUNC_SIG_BYTES)
    if func_sig in (FUNC_SIG_DEPOSIT, FUNC_SIG_WITHDRAW, FUNC_SIG_REDEEM):
        token = vault_token if func_sig == FUNC_SIG_REDEEM else asset_token
        handler = _prepare_vault_tx(
            data_reader=data_reader,
            msg=msg,
            network=network,
            maximum_fee=maximum_fee,
            fee_items=fee_items,
            sender_bytes=sender_bytes,
            is_known_vault=is_known_vault,
            vault_str=vault_str,
            token=token,
            func_sig=func_sig,
        )

    if handler is not None:
        progress_indicator = get_progress_indicator(msg.data_length)
        return progress_indicator, handler
    return None


def _prepare_vault_tx(
    data_reader: BufferReader,
    msg: MsgInSignTx,
    network: EthereumNetworkInfo,
    maximum_fee: str,
    fee_items: Iterable[StrPropertyType],
    sender_bytes: AnyBytes,
    is_known_vault: bool,
    vault_str: str,
    token: EthereumTokenInfo,
    func_sig: "AnyBytes",
) -> "Coroutine[Any, Any, None] | None":

    from .clear_signing import InvalidFunctionCall, parse_address, parse_uint256
    from .layout import require_confirm_vault_tx

    # deposit(uint256 assets, address receiver)
    # withdraw(uint256 assets, address receiver, address owner)
    # redeem(uint256 shares, address receiver, address owner)
    is_deposit = func_sig == FUNC_SIG_DEPOSIT
    try:
        amount = parse_uint256(data_reader.read_memoryview(32))
        receiver_bytes = parse_address(data_reader.read_memoryview(32))
        owner_bytes = (
            None if is_deposit else parse_address(data_reader.read_memoryview(32))
        )
        if (
            data_reader.remaining_count() != 0
            or not isinstance(amount, int)
            or not isinstance(receiver_bytes, bytes)
            or (owner_bytes is not None and not isinstance(owner_bytes, bytes))
            or int.from_bytes(msg.value, "big") != 0
            or amount == 0
        ):
            raise ValueError
    except (ValueError, EOFError, InvalidFunctionCall):
        raise DataError("Invalid data for ERC-4626 vault transaction")

    if not _is_vault_tx_safe(is_known_vault, sender_bytes, receiver_bytes, owner_bytes):
        return None
    return require_confirm_vault_tx(
        value=amount,
        address_n=msg.address_n,
        maximum_fee=maximum_fee,
        fee_info_items=fee_items,
        network=network,
        vault_str=vault_str,
        token=token,
        func_sig=func_sig,
    )


def _is_vault_tx_safe(
    is_known_vault: bool,
    sender_bytes: AnyBytes,
    receiver_bytes: AnyBytes,
    owner_bytes: AnyBytes | None = None,
) -> bool:

    is_calldata_safe = receiver_bytes == sender_bytes
    if owner_bytes is not None:
        # Withdraw/redeem transaction
        is_calldata_safe = is_calldata_safe and owner_bytes == sender_bytes

    if is_calldata_safe:
        return True
    else:
        # Hard fail for known (Trezor) vaults, blind sign for unknown vaults
        if is_known_vault:
            raise DataError("Vault tx: Signer receiver mismatch")
        return False
