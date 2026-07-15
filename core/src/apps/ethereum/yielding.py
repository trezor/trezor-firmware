from typing import TYPE_CHECKING

from trezor.wire import DataError

from .clear_signing import Array, Atomic, DisplayFormat, parse_address, parse_uint256
from .yielding_vaults import UNKNOWN_VAULT, lookup_vault

if TYPE_CHECKING:
    from buffer_types import AnyBytes
    from typing import Any, Coroutine, Iterable

    from trezor.messages import EthereumNetworkInfo, EthereumTokenInfo
    from trezor.ui.layouts import StrPropertyType

    from .keychain import MsgInSignTx
    from .yielding_vaults import EthereumVaultInfo

# https://ethereum.org/developers/docs/standards/tokens/erc-4626
FUNC_SIG_DEPOSIT = b"\x6e\x55\x3f\x65"
FUNC_SIG_WITHDRAW = b"\xb4\x60\xaf\x94"
FUNC_SIG_REDEEM = b"\xba\x08\x76\x52"
FUNC_SIG_CLAIM = b"\x71\xee\x95\xc0"

_MERKL_XYZ_CLAIM_DISTRIBUTOR_ADDR = (
    b"\x3e\xf3\xd8\xba\x38\xeb\xe1\x8d\xb1\x33\xce\xc1\x08\xf4\xd1\x4c\xe0\x0d\xd9\xae"
)

if __debug__:
    from ubinascii import unhexlify

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
    # https://etherscan.io/address/0x3ef3d8ba38ebe18db133cec108f4d14ce00dd9ae
    assert _MERKL_XYZ_CLAIM_DISTRIBUTOR_ADDR == unhexlify(
        "3ef3d8ba38ebe18db133cec108f4d14ce00dd9ae"
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

# claim(address[] users, address[] tokens, uint256[] amounts, bytes32[][] proofs)
# The proofs parameter is intentionally omitted from `parameter_definitions`:
# we don't display it, so we skip the per-element parsing/allocations and only
# manually validate the top-level array structure (see `_prepare_merkl_claim`).
CLAIM_DISPLAY_FORMAT = DisplayFormat(
    binding_context=None,
    func_sig=FUNC_SIG_CLAIM,
    intent="Claim",
    parameter_definitions=[
        Array(Atomic(parse_address)),  # users
        Array(Atomic(parse_address)),  # tokens
        Array(Atomic(parse_uint256)),  # amounts
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
) -> Coroutine[Any, Any, None] | None:

    from .clear_signing import SC_FUNC_SIG_BYTES

    if msg.data_length > len(initial_data):
        return None

    # No more data should be loaded from host:
    if len(initial_data) < SC_FUNC_SIG_BYTES:
        return None

    vault = lookup_vault(network, address_bytes)

    func_sig = bytes(initial_data[:SC_FUNC_SIG_BYTES])
    calldata = memoryview(initial_data)[SC_FUNC_SIG_BYTES:]

    handler = None
    if func_sig == FUNC_SIG_DEPOSIT:
        vault_tx_config = (DEPOSIT_DISPLAY_FORMAT, vault.asset_token)
    elif func_sig == FUNC_SIG_WITHDRAW:
        vault_tx_config = (WITHDRAW_DISPLAY_FORMAT, vault.asset_token)
    elif func_sig == FUNC_SIG_REDEEM:
        vault_tx_config = (REDEEM_DISPLAY_FORMAT, vault.vault_token)
    else:
        vault_tx_config = None

    if vault_tx_config is not None:
        display_format, token = vault_tx_config
        handler = await _prepare_vault_tx(
            calldata=calldata,
            display_format=display_format,
            msg=msg,
            network=network,
            maximum_fee=maximum_fee,
            fee_items=fee_items,
            sender_bytes=sender_bytes,
            vault=vault,
            token=token,
        )
    elif (
        func_sig == FUNC_SIG_CLAIM
        and address_bytes == _MERKL_XYZ_CLAIM_DISTRIBUTOR_ADDR
    ):
        handler = await _prepare_merkl_claim(
            calldata=calldata,
            msg=msg,
            network=network,
            maximum_fee=maximum_fee,
            fee_items=fee_items,
            sender_bytes=sender_bytes,
        )

    return handler


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

    # All atomic non-array fields for these 3 calls so this works.
    params_size = len(display_format.parameter_definitions) * 32
    calldata_suffix = calldata[params_size:] if len(calldata) > params_size else None

    return require_confirm_vault_tx(
        value=amount,
        address_n=msg.address_n,
        maximum_fee=maximum_fee,
        fee_info_items=fee_items,
        network=network,
        vault_str=(vault.name if vault is not UNKNOWN_VAULT else msg.to),
        token=token,
        func_sig=display_format.func_sig,
        extra_data=calldata_suffix,
    )


async def _prepare_merkl_claim(
    calldata: memoryview,
    msg: MsgInSignTx,
    network: EthereumNetworkInfo,
    maximum_fee: str,
    fee_items: Iterable[StrPropertyType],
    sender_bytes: AnyBytes,
) -> Coroutine[Any, Any, None] | None:

    from .clear_signing import InvalidFunctionCall
    from .definitions import Definitions
    from .layout import require_confirm_claim_rewards
    from .yielding_vaults import get_token_label

    if int.from_bytes(msg.value, "big") != 0:
        raise DataError(
            "Non-zero ETH transfer with claim rewards transaction not allowed"
        )

    defs = Definitions(network, {})

    try:
        parameters, _ = await CLAIM_DISPLAY_FORMAT.parse_calldata(calldata, msg, defs)
        users, tokens, amounts = parameters
        if (
            not isinstance(users, list)
            or not isinstance(tokens, list)
            or not isinstance(amounts, list)
        ):
            raise ValueError

        # The proofs head sits at offset 96, right after the three parsed array
        # heads. We only validate that proofs is a well-formed top-level array
        # whose length matches the others — we never read its elements.
        _PROOFS_HEAD_OFFSET = 3 * 32
        if _PROOFS_HEAD_OFFSET + 32 > len(calldata):
            raise ValueError
        proofs_body = int.from_bytes(
            calldata[_PROOFS_HEAD_OFFSET : _PROOFS_HEAD_OFFSET + 32], "big"
        )
        if proofs_body + 32 > len(calldata):
            raise ValueError
        proofs_length = int.from_bytes(calldata[proofs_body : proofs_body + 32], "big")

        if (
            len(users) != len(tokens)
            or len(tokens) != len(amounts)
            or len(amounts) != proofs_length
        ):
            raise ValueError

        if len(users) == 0:
            raise ValueError

        first_user = users[0]
        if not isinstance(first_user, bytes):
            raise ValueError

    except (ValueError, InvalidFunctionCall):
        raise DataError("Invalid data for claim rewards transaction")

    # All receivers must be the same; otherwise revert to blind signing.
    for other in users[1:]:
        if other != first_user:
            return None

    # We don't show claim flows for non-signer users.
    if sender_bytes != first_user:
        return None

    # Not sure about the UX if we fetch too many defintions so capping definition fetching to 4 for now.
    try_fetch_definitions = len(tokens) <= 4

    token_labels: list[str] = []
    for token in tokens:
        if not isinstance(token, bytes):
            raise DataError("Invalid data for claim rewards transaction")
        label = await get_token_label(token, network, msg, try_fetch_definitions)
        token_labels.append(label)

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
