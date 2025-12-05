from micropython import const
from typing import Any, Callable
from ubinascii import unhexlify

# smart contract 'data' field lengths in bytes
SC_FUNC_SIG_BYTES = const(4)
SC_ARGUMENT_BYTES = const(32)
SC_ARGUMENT_ADDRESS_BYTES = const(20)
SC_FUNC_APPROVE_REVOKE_AMOUNT = const(0)

assert SC_ARGUMENT_ADDRESS_BYTES <= SC_ARGUMENT_BYTES

SC_FUNC_SIG_STAKE = unhexlify("3a29dbae")
SC_FUNC_SIG_UNSTAKE = unhexlify("76ec871c")
SC_FUNC_SIG_CLAIM = unhexlify("33986ffa")

# Everstake staking

# addresses for pool (stake/unstake) and accounting (claim) operations
ADDRESSES_POOL = (
    unhexlify("AFA848357154a6a624686b348303EF9a13F63264"),  # Hoodi testnet
    unhexlify("D523794C879D9eC028960a231F866758e405bE34"),  # mainnet
)
ADDRESSES_ACCOUNTING = (
    unhexlify("624087DD1904ab122A32878Ce9e933C7071F53B9"),  # Hoodi testnet
    unhexlify("7a7f0b3c23C23a31cFcb0c44709be70d4D545c6e"),  # mainnet
)


def token_amount(amount: Any) -> str:
    return str(amount)  # TODO


def address_name(address: Any) -> str:
    return str(address)  # TODO


class BindingContext:  # TODO: optimize: no need to store the same address multiple times
    def __init__(deployments: list[tuple[int, str]]):
        self.deployments = deployments


class FieldFormat:
    def __init__(path: str, label: str, format: Callable[[Any], str]):
        self.path = path
        self.label = label
        self.format = format


class DisplayFormat:
    def __init__(
        binding_context: BindingContext | None,
        format: str,
        intent: str,
        interpolated_intent: str | None,
        required_fields: list[str],
        field_formats: list[FieldFormat],
    ):
        self.format = format
        self.intent = intent
        self.interpolated_intent = interpolated_intent
        self.required_fields = required_fields
        self.field_formats = field_formats


ONEINCH_ADDRESS = unhexlify("111111125421cA6dc452d289314280a0f8842A65")
ONEINCH_CHAINS = [
    1,
    10,
    56,
    100,
    137,
    146,
    250,
    8217,
    8453,
    42161,
    43114,
    59144,
    1313161554,
]
LIFI_ADDRESS = unhexlify("1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE")
LIFI_CHAINS = [
    1,
    10,
    25,
    56,
    100,
    106,
    122,
    137,
    204,
    250,
    252,
    288,
    324,
    1088,
    1284,
    1285,
    5000,
    8453,
    9001,
    34443,
    42161,
    42170,
    42220,
    43114,
    59144,
    81457,
    167004,
    534352,
    1313161554,
    1666600000,
]
UNISWAP_V3_ROUTER_ADDRESS = unhexlify("e592427a0aece92de3edee1f18e0157c05861564")
UNISWAP_V3_ROUTER_02_ADDRESS = unhexlify("68b3465833fb72A70ecDF485E0e4C7bD8665Fc45")
UNISWAP_V3_ROUTER_CHAINS = [1]

GENERIC_BINDING_CONTEXT = BindingContext(
    [(chain, ONEINCH_ADDRESS) for chain in ONEINCH_CHAINS]
    + [(chain, LIFI_ADDRESS) for chain in LIFI_CHAINS]
    + [(chain, UNISWAP_V3_ROUTER_02_ADDRESS) for chain in UNISWAP_V3_ROUTER_CHAINS]
    + [(chain, UNISWAP_V3_ROUTER_ADDRESS) for chain in UNISWAP_V3_ROUTER_CHAINS]
)

APPROVE_DISPLAY_FORMAT = DisplayFormat(
    GENERIC_BINDING_CONTEXT,
    "approve(address,uint256)",
    "Approve",
    None,
    ["_spender", "_value"],
    [
        FieldFormat("_spender", "Spender", address_name),
        FieldFormat("_value", "Amount", token_amount),  # TODO: deal with threshold
    ],
)

TRANSFER_DISPLAY_FORMAT = DisplayFormat(
    GENERIC_BINDING_CONTEXT,
    "transfer(address,uint256)",
    "Send",
    None,
    ["_to", "_value"],
    [
        FieldFormat("_value", "Amount", token_amount),
        FieldFormat("_to", "To", address_name),
    ],
)
