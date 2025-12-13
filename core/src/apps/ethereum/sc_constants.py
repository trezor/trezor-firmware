from micropython import const
from typing import TYPE_CHECKING, Any, Callable, Iterable
from ubinascii import unhexlify

from trezor.crypto import base58

from .helpers import address_from_bytes

if TYPE_CHECKING:
    from trezor.messages import EthereumNetworkInfo
    from trezor.ui.layouts import PropertyType

# smart contract 'data' field lengths in bytes
SC_FUNC_SIG_BYTES = const(4)
SC_ARGUMENT_BYTES = const(32)
SC_ARGUMENT_ADDRESS_BYTES = const(20)
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


# custom formatters: https://eips.ethereum.org/EIPS/eip-7730#field-formats


def token_amount(amount: Any, network: EthereumNetworkInfo) -> str | None:
    return str(amount)


def address_name(address: Any, network: EthereumNetworkInfo) -> str | None:
    return address_from_bytes(address, network) if address else None


# https://eips.ethereum.org/EIPS/eip-7730#display-section
# "Keys MUST use canonical Solidity type names"
# TODO: extract all types used throughout the registry
class SolidityType:
    ADDRESS = 1
    UINT256 = 2


# https://eips.ethereum.org/EIPS/eip-7730#context-section
# The Binding Context specifies which ChainId / Address pairs certain rules apply to (contract.deployments)
class BindingContext:  # TODO: optimize: no need to store the same address multiple times
    def __init__(self, deployments: Iterable[tuple[int, bytes]], metadata: dict):
        self.deployments = deployments

        # https://eips.ethereum.org/EIPS/eip-7730#metadata-section
        # The metadata section, which we use to extract the owner's name
        # is actually a separate section that sits *besides* the Context section.
        self.metadata = metadata

    def get_name(self):
        return self.metadata["owner"]

    def matches(self, chain_id: int, address: bytes) -> bool:
        for d_chain_id, d_address in self.deployments:
            if d_chain_id == chain_id and d_address == address:
                return True
        return False


# https://eips.ethereum.org/EIPS/eip-7730#structured-data-format-specification
class FieldFormat:
    def __init__(
        self,
        path: str,  # absolute or relative location of the field in the structured data
        label: str,  # displayable string shown before the formatted field value
        format: Callable[[Any, EthereumNetworkInfo], str | None],  # custom formatter
        threshold: int | None = None,
    ):
        self.path = path
        self.label = label
        self.format = format
        self.threshold = threshold


class InvalidFunctionCall(Exception):
    pass


class DisplayFormat:
    def __init__(
        self,
        binding_contexts: Iterable[BindingContext] | None,
        func_sig: bytes,
        intent: str,
        interpolated_intent: str | None,
        field_types: list[int],
        required_fields: list[str],
        field_formats: list[FieldFormat],
    ):
        self.binding_contexts = binding_contexts

        self.func_sig = func_sig

        self.intent = intent
        self.interpolated_intent = interpolated_intent

        self.field_types = field_types
        self.required_fields = required_fields
        self.field_formats = field_formats

    def parse_fields(
        self, data_reader, network
    ) -> Iterable[tuple[int | bytes | None, PropertyType]]:
        for field_type, field_format in zip(self.field_types, self.field_formats):
            if data_reader.remaining_count() < SC_ARGUMENT_BYTES:
                raise InvalidFunctionCall()
            arg = data_reader.read_memoryview(SC_ARGUMENT_BYTES)
            if field_type == SolidityType.ADDRESS:
                assert all(
                    byte == 0
                    for byte in arg[: SC_ARGUMENT_BYTES - SC_ARGUMENT_ADDRESS_BYTES]
                )
                value = bytes(arg[SC_ARGUMENT_BYTES - SC_ARGUMENT_ADDRESS_BYTES :])
            elif field_type == SolidityType.UINT256:
                value = int.from_bytes(arg, "big")
                if field_format.threshold is not None and value is not None:
                    if value > field_format.threshold:
                        value = None
            else:
                raise InvalidFunctionCall()
            yield (
                value,
                (
                    field_format.label,
                    field_format.format(value, network),
                    None,
                ),
            )


# https://github.com/LedgerHQ/clear-signing-erc7730-registry/blob/master/registry/1inch/calldata-AggregationRouterV6.json#L9
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
ONEINCH_METADATA = {"owner": "1inch"}

# https://github.com/LedgerHQ/clear-signing-erc7730-registry/blob/master/registry/lifi/calldata-LIFIDiamond.json#L6
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
LIFI_METADATA = {"owner": "LI.FI Service GmbH"}

# https://etherscan.io/address/0xe592427a0aece92de3edee1f18e0157c05861564
UNISWAP_V3_ROUTER_ADDRESS = unhexlify("e592427a0aece92de3edee1f18e0157c05861564")
# https://github.com/LedgerHQ/clear-signing-erc7730-registry/blob/master/registry/uniswap/calldata-UniswapV3Router02.json#L6
UNISWAP_V3_ROUTER_02_ADDRESS = unhexlify("68b3465833fb72A70ecDF485E0e4C7bD8665Fc45")
UNISWAP_V3_ROUTER_CHAINS = [1]
UNISWAP_METADATA = {"owner": "Uniswap"}

ALL_BINDING_CONTEXTS = (
    BindingContext(
        [(chain, ONEINCH_ADDRESS) for chain in ONEINCH_CHAINS], ONEINCH_METADATA
    ),
    BindingContext([(chain, LIFI_ADDRESS) for chain in LIFI_CHAINS], LIFI_METADATA),
    BindingContext(
        [(chain, UNISWAP_V3_ROUTER_02_ADDRESS) for chain in UNISWAP_V3_ROUTER_CHAINS],
        UNISWAP_METADATA,
    ),
    BindingContext(
        [(chain, UNISWAP_V3_ROUTER_ADDRESS) for chain in UNISWAP_V3_ROUTER_CHAINS],
        UNISWAP_METADATA,
    ),
)


# "approve" and "transfer" functions, defined here https://github.com/LedgerHQ/clear-signing-erc7730-registry/blob/master/ercs/calldata-erc20-tokens.json#L27
# should apply to *any* binding context, but we currently only allow them on the ALL_BINDING_CONTEXTS
APPROVE_DISPLAY_FORMAT = DisplayFormat(
    ALL_BINDING_CONTEXTS,
    base58.keccak_32(b"approve(address,uint256)"),
    intent="Approve",
    interpolated_intent=None,
    field_types=[SolidityType.ADDRESS, SolidityType.UINT256],
    required_fields=["_spender", "_value"],
    field_formats=[
        FieldFormat("_spender", "Spender", address_name),
        FieldFormat(
            "_value",
            "Amount",
            token_amount,
            threshold=0x8000000000000000000000000000000000000000000000000000000000000000,
        ),
    ],
)
SC_FUNC_APPROVE_REVOKE_AMOUNT = const(0)

TRANSFER_DISPLAY_FORMAT = DisplayFormat(
    ALL_BINDING_CONTEXTS,
    base58.keccak_32(b"transfer(address,uint256)"),
    intent="Send",
    interpolated_intent=None,
    field_types=[SolidityType.ADDRESS, SolidityType.UINT256],
    required_fields=["_to", "_value"],
    field_formats=[
        FieldFormat("_to", "To", address_name),
        FieldFormat("_value", "Amount", token_amount),
    ],
)

ALL_DISPLAY_FORMATS = [APPROVE_DISPLAY_FORMAT, TRANSFER_DISPLAY_FORMAT]
