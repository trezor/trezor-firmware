from typing import TYPE_CHECKING
from ubinascii import hexlify

from trezor import TR

from . import networks

if TYPE_CHECKING:
    from typing import Iterable

    from trezor.messages import EthereumFieldType, EthereumTokenInfo

    from .networks import EthereumNetworkInfo

RSKIP60_NETWORKS = (30, 31)


def address_from_bytes(
    address_bytes: bytes, network: EthereumNetworkInfo = networks.UNKNOWN_NETWORK
) -> str:
    """
    Converts address in bytes to a checksummed string as defined
    in https://github.com/ethereum/EIPs/blob/master/EIPS/eip-55.md
    """
    from trezor.crypto.hashlib import sha3_256

    if network.chain_id in RSKIP60_NETWORKS:
        # rskip60 is a different way to calculate checksum
        prefix = str(network.chain_id) + "0x"
    else:
        prefix = ""

    address_hex = hexlify(address_bytes).decode()
    digest = sha3_256((prefix + address_hex).encode(), keccak=True).digest()

    def _maybe_upper(i: int) -> str:
        """Uppercase i-th letter only if the corresponding nibble has high bit set."""
        digest_byte = digest[i // 2]
        hex_letter = address_hex[i]
        if i % 2 == 0:
            # even letter -> high nibble
            bit = 0x80
        else:
            # odd letter -> low nibble
            bit = 0x08
        if digest_byte & bit:
            return hex_letter.upper()
        else:
            return hex_letter

    return "0x" + "".join(_maybe_upper(i) for i in range(len(address_hex)))


def bytes_from_address(address: str) -> bytes:
    from ubinascii import unhexlify

    from trezor import wire

    if len(address) == 40:
        return unhexlify(address)

    elif len(address) == 42:
        if address[0:2] not in ("0x", "0X"):
            raise wire.ProcessError("Ethereum: invalid beginning of an address")
        return unhexlify(address[2:])

    elif len(address) == 0:
        return bytes()

    raise wire.ProcessError("Ethereum: Invalid address length")


def get_type_name(field: EthereumFieldType) -> str:
    """Create a string from type definition (like uint256 or bytes16)."""
    from trezor.enums import EthereumDataType

    data_type = field.data_type
    size = field.size

    TYPE_TRANSLATION_DICT = {
        EthereumDataType.UINT: "uint",
        EthereumDataType.INT: "int",
        EthereumDataType.BYTES: "bytes",
        EthereumDataType.STRING: "string",
        EthereumDataType.BOOL: "bool",
        EthereumDataType.ADDRESS: "address",
    }

    if data_type == EthereumDataType.STRUCT:
        assert field.struct_name is not None  # validate_field_type
        return field.struct_name
    elif data_type == EthereumDataType.ARRAY:
        assert field.entry_type is not None  # validate_field_type
        type_name = get_type_name(field.entry_type)
        if size is None:
            return f"{type_name}[]"
        else:
            return f"{type_name}[{size}]"
    elif data_type in (EthereumDataType.UINT, EthereumDataType.INT):
        assert size is not None  # validate_field_type
        return TYPE_TRANSLATION_DICT[data_type] + str(size * 8)
    elif data_type == EthereumDataType.BYTES:
        if size:
            return TYPE_TRANSLATION_DICT[data_type] + str(size)
        else:
            return TYPE_TRANSLATION_DICT[data_type]
    else:
        # all remaining types can use the name directly
        # if the data_type is left out, this will raise KeyError
        return TYPE_TRANSLATION_DICT[data_type]


def decode_typed_data(data: bytes, type_name: str) -> str:
    """Used by sign_typed_data module to show data to user."""
    if type_name.startswith("bytes"):
        return hexlify(data).decode()
    elif type_name == "string":
        return data.decode()
    elif type_name == "address":
        return address_from_bytes(data)
    elif type_name == "bool":
        return "true" if data == b"\x01" else "false"
    elif type_name.startswith("uint"):
        return str(int.from_bytes(data, "big"))
    elif type_name.startswith("int"):
        # Micropython does not implement "signed" arg in int.from_bytes()
        return str(_from_bytes_bigendian_signed(data))

    raise ValueError  # Unsupported data type for direct field decoding


def get_fee_items_regular(
    gas_price: int, gas_limit: int, network: EthereumNetworkInfo
) -> Iterable[tuple[str, str]]:
    # regular
    gas_limit_str = TR.ethereum__units_template.format(gas_limit)
    gas_price_str = format_ethereum_amount(
        gas_price, None, network, force_unit_gwei=True
    )

    return (
        (TR.ethereum__gas_limit, gas_limit_str),
        (TR.ethereum__gas_price, gas_price_str),
    )


def get_fee_items_eip1559(
    max_gas_fee: int,
    max_priority_fee: int,
    gas_limit: int,
    network: EthereumNetworkInfo,
) -> Iterable[tuple[str, str]]:
    # EIP-1559
    gas_limit_str = TR.ethereum__units_template.format(gas_limit)
    max_gas_fee_str = format_ethereum_amount(
        max_gas_fee, None, network, force_unit_gwei=True
    )
    max_priority_fee_str = format_ethereum_amount(
        max_priority_fee, None, network, force_unit_gwei=True
    )

    return (
        (TR.ethereum__gas_limit, gas_limit_str),
        (TR.ethereum__max_gas_price, max_gas_fee_str),
        (TR.ethereum__priority_fee, max_priority_fee_str),
    )


def format_ethereum_amount(
    value: int,
    token: EthereumTokenInfo | None,
    network: EthereumNetworkInfo,
    force_unit_gwei: bool = False,
) -> str:
    from trezor.strings import format_amount

    if token:
        suffix = token.symbol
        decimals = token.decimals
    else:
        suffix = network.symbol
        decimals = 18

    if force_unit_gwei:
        assert token is None
        assert decimals >= 9
        decimals = decimals - 9
        suffix = "Gwei"
    elif decimals > 9 and value < 10 ** (decimals - 9):
        # Don't want to display wei values for tokens with small decimal numbers
        suffix = "Wei " + suffix
        decimals = 0

    amount = format_amount(value, decimals)
    return f"{amount} {suffix}"


def _from_bytes_bigendian_signed(b: bytes) -> int:
    negative = b[0] & 0x80
    if negative:
        neg_b = bytearray(b)
        for i in range(len(neg_b)):
            neg_b[i] = ~neg_b[i] & 0xFF
        result = int.from_bytes(neg_b, "big")
        return -result - 1
    else:
        return int.from_bytes(b, "big")
