from typing import TYPE_CHECKING

from trezor.wire import DataError

from .clear_signing import Atomic, DisplayFormat, parse_address, parse_uint256
from .yielding_vaults import UNKNOWN_VAULT, lookup_vault

if TYPE_CHECKING:
    from buffer_types import AnyBytes
    from typing import Any, Coroutine, Iterable

    from trezor.messages import EthereumNetworkInfo, EthereumTokenInfo
    from trezor.ui.layouts import StrPropertyType

    from .helpers import ConfirmDataFn
    from .keychain import MsgInSignTx
    from .yielding_vaults import EthereumVaultInfo

# https://ethereum.org/developers/docs/standards/tokens/erc-4626
FUNC_SIG_DEPOSIT = b"\x6e\x55\x3f\x65"
FUNC_SIG_WITHDRAW = b"\xb4\x60\xaf\x94"
FUNC_SIG_REDEEM = b"\xba\x08\x76\x52"
FUNC_SIG_CLAIM = b"\x71\xee\x95\xc0"

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
    assert (
        FUNC_SIG_CLAIM
        == sha3_256(
            b"claim(address[],address[],uint256[],bytes32[][])", keccak=True
        ).digest()[:4]
    )

# deposit(uint256 assets, address receiver)
DEPOSIT_DISPLAY_FORMAT = DisplayFormat(
    binding_context=None,
    func_sig=FUNC_SIG_DEPOSIT,
    intent="Deposit",
    parameter_definitions=[
        Atomic(parse_uint256),  # assets
        Atomic(parse_address),  # receiver
    ],
    field_definitions=[],
)

# withdraw(uint256 assets, address receiver, address owner)
WITHDRAW_DISPLAY_FORMAT = DisplayFormat(
    binding_context=None,
    func_sig=FUNC_SIG_WITHDRAW,
    intent="Withdraw",
    parameter_definitions=[
        Atomic(parse_uint256),  # assets
        Atomic(parse_address),  # receiver
        Atomic(parse_address),  # owner
    ],
    field_definitions=[],
)

# redeem(uint256 shares, address receiver, address owner)
REDEEM_DISPLAY_FORMAT = DisplayFormat(
    binding_context=None,
    func_sig=FUNC_SIG_REDEEM,
    intent="Redeem",
    parameter_definitions=[
        Atomic(parse_uint256),  # shares
        Atomic(parse_address),  # receiver
        Atomic(parse_address),  # owner
    ],
    field_definitions=[],
)


async def get_approver(
    msg: MsgInSignTx,
    initial_data: AnyBytes,
    network: EthereumNetworkInfo,
    address_bytes: AnyBytes,
    maximum_fee: str,
    fee_items: Iterable[StrPropertyType],
    sender_bytes: AnyBytes,
) -> tuple[ConfirmDataFn, Coroutine[Any, Any, None]] | None:

    from .clear_signing import SC_FUNC_SIG_BYTES
    from .helpers import get_progress_indicator

    if msg.data_length > len(initial_data):
        return None

    if len(initial_data) < SC_FUNC_SIG_BYTES:
        return None

    vault = lookup_vault(network, address_bytes)

    func_sig = bytes(initial_data[:SC_FUNC_SIG_BYTES])
    calldata = memoryview(initial_data)[SC_FUNC_SIG_BYTES:]

    handler = None
    if func_sig == FUNC_SIG_DEPOSIT:
        handler = await _prepare_vault_tx(
            calldata=calldata,
            display_format=DEPOSIT_DISPLAY_FORMAT,
            msg=msg,
            network=network,
            maximum_fee=maximum_fee,
            fee_items=fee_items,
            sender_bytes=sender_bytes,
            vault=vault,
            token=vault.asset_token,
        )
    elif func_sig == FUNC_SIG_WITHDRAW:
        handler = await _prepare_vault_tx(
            calldata=calldata,
            display_format=WITHDRAW_DISPLAY_FORMAT,
            msg=msg,
            network=network,
            maximum_fee=maximum_fee,
            fee_items=fee_items,
            sender_bytes=sender_bytes,
            vault=vault,
            token=vault.asset_token,
        )
    elif func_sig == FUNC_SIG_REDEEM:
        handler = await _prepare_vault_tx(
            calldata=calldata,
            display_format=REDEEM_DISPLAY_FORMAT,
            msg=msg,
            network=network,
            maximum_fee=maximum_fee,
            fee_items=fee_items,
            sender_bytes=sender_bytes,
            vault=vault,
            token=vault.vault_token,
        )
    elif func_sig == FUNC_SIG_CLAIM:
        handler = _prepare_claim_rewards(
            calldata=calldata,
            msg=msg,
            network=network,
            maximum_fee=maximum_fee,
            fee_items=fee_items,
            sender_bytes=sender_bytes,
        )

    if handler is not None:
        progress_indicator = get_progress_indicator(msg.data_length)
        return progress_indicator, handler
    return None


async def _prepare_vault_tx(
    calldata: memoryview,
    display_format: DisplayFormat,
    msg: MsgInSignTx,
    network: EthereumNetworkInfo,
    maximum_fee: str,
    fee_items: Iterable[StrPropertyType],
    sender_bytes: AnyBytes,
    vault: EthereumVaultInfo,
    token: EthereumTokenInfo,
) -> Coroutine[Any, Any, None] | None:

    from .clear_signing import InvalidFunctionCall
    from .definitions import Definitions
    from .layout import require_confirm_vault_tx

    defs = Definitions(network, {})

    try:
        parameters, _ = await display_format.parse_calldata(calldata, msg, defs)
        amount = parameters[0]
        receiver_bytes = parameters[1]
        owner_bytes = parameters[2] if len(parameters) > 2 else None
        if (
            not isinstance(amount, int)
            or not isinstance(receiver_bytes, bytes)
            or (owner_bytes is not None and not isinstance(owner_bytes, bytes))
            or int.from_bytes(msg.value, "big") != 0
            or amount == 0
        ):
            raise ValueError
    except (ValueError, InvalidFunctionCall):
        raise DataError("Invalid data for ERC-4626 vault transaction.")

    if not _is_vault_tx_safe(vault, sender_bytes, receiver_bytes, owner_bytes):
        return None

    params_size = len(display_format.parameter_definitions) * 32
    extra_data = calldata[params_size:] if len(calldata) > params_size else None

    return require_confirm_vault_tx(
        value=amount,
        address_n=msg.address_n,
        maximum_fee=maximum_fee,
        fee_info_items=fee_items,
        network=network,
        vault_str=(vault.name if vault is not UNKNOWN_VAULT else msg.to),
        token=token,
        func_sig=display_format.func_sig,
        extra_data=extra_data,
    )


def _prepare_claim_rewards(
    calldata: memoryview,
    msg: MsgInSignTx,
    network: EthereumNetworkInfo,
    maximum_fee: str,
    fee_items: Iterable[StrPropertyType],
    sender_bytes: AnyBytes,
) -> Coroutine[Any, Any, None] | None:

    return None
    # TODO: Finalize the UI in the next iteration.

    from .clear_signing import InvalidFunctionCall, parse_address
    from .layout import require_confirm_claim_rewards
    from .yielding_vaults import get_token_label

    _MERKL_XYZ_CLAIM_DISTRIBUTOR_ADDR = "0x3ef3d8ba38ebe18db133cec108f4d14ce00dd9ae"

    if int.from_bytes(msg.value, "big") != 0:
        raise DataError(
            "Non-zero ETH transfer with ERC-4626 vault transaction not allowed"
        )

    # claim(address[] users, address[] tokens, uint256[] amounts, bytes32[][] proofs)
    # All 4 params are dynamic; first 128 bytes are their ABI offsets (relative to abi_base).
    try:
        from trezor.utils import BufferReader

        data_reader = BufferReader(bytes(calldata))
        param_base = data_reader.offset

        receivers_param_offset = int.from_bytes(data_reader.read_memoryview(32), "big")
        tokens_param_offset = int.from_bytes(data_reader.read_memoryview(32), "big")
        amounts_param_offset = int.from_bytes(data_reader.read_memoryview(32), "big")
        proofs_param_offset = int.from_bytes(data_reader.read_memoryview(32), "big")

        def _read_array_length(param_offset: int) -> int:
            data_reader.seek(param_base + param_offset)
            return int.from_bytes(data_reader.read_memoryview(32), "big")

        receivers_array_length = _read_array_length(receivers_param_offset)
        tokens_array_length = _read_array_length(tokens_param_offset)
        amounts_array_length = _read_array_length(amounts_param_offset)
        proofs_array_length = _read_array_length(proofs_param_offset)

        if (
            receivers_array_length != tokens_array_length
            or tokens_array_length != amounts_array_length
            or amounts_array_length != proofs_array_length
        ):
            raise ValueError

        data_reader.seek(param_base + receivers_param_offset + 32)
        first_receiver_address = parse_address(data_reader.read_memoryview(32))
        if not isinstance(first_receiver_address, bytes):
            raise InvalidFunctionCall

        # Check if all users are the same. We validate if it's the sender in _is_vault_tx_safe()
        # If either of these conditions are unmet, we revert to blind signing (return None).
        for i in range(1, receivers_array_length):
            data_reader.seek(param_base + receivers_param_offset + 32 + i * 32)
            other = parse_address(data_reader.read_memoryview(32))
            if other != first_receiver_address:
                return None

        token_labels: list[str] = []
        for i in range(tokens_array_length):
            data_reader.seek(param_base + tokens_param_offset + 32 + i * 32)
            addr = parse_address(data_reader.read_memoryview(32))
            if not isinstance(addr, bytes):
                raise InvalidFunctionCall
            label = get_token_label(addr, network)
            token_labels.append(label)

    except (ValueError, EOFError, InvalidFunctionCall):
        raise DataError("Invalid data for claim rewards transaction")

    # We don't show claim flows for any unknown distributor for now.
    if (
        msg.to != _MERKL_XYZ_CLAIM_DISTRIBUTOR_ADDR
        or sender_bytes != first_receiver_address
    ):
        return None

    return require_confirm_claim_rewards(
        address_n=msg.address_n,
        maximum_fee=maximum_fee,
        fee_info_items=fee_items,
        token_labels=token_labels,
    )


def _is_vault_tx_safe(
    vault: EthereumVaultInfo,
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
        if vault is not UNKNOWN_VAULT:
            raise DataError("Vault tx: Signer receiver mismatch")
        return False
