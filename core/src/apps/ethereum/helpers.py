from ubinascii import hexlify, unhexlify

from trezor import wire
from trezor.enums import EthereumDataType
from trezor.messages import EthereumFieldType

if False:
    from .networks import NetworkInfo


def address_from_bytes(address_bytes: bytes, network: NetworkInfo | None = None) -> str:
    """
    Converts address in bytes to a checksummed string as defined
    in https://github.com/ethereum/EIPs/blob/master/EIPS/eip-55.md
    """
    from trezor.crypto.hashlib import sha3_256

    if network is not None and network.rskip60:
        prefix = str(network.chain_id) + "0x"
    else:
        prefix = ""

    address_hex = hexlify(address_bytes).decode()
    digest = sha3_256((prefix + address_hex).encode(), keccak=True).digest()

    def maybe_upper(i: int) -> str:
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

    return "0x" + "".join(maybe_upper(i) for i in range(len(address_hex)))


def bytes_from_address(address: str) -> bytes:
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
        return str(from_bytes_bigendian_signed(data))

    raise ValueError  # Unsupported data type for direct field decoding


def from_bytes_bigendian_signed(b: bytes) -> int:
    negative = b[0] & 0x80
    if negative:
        neg_b = bytearray(b)
        for i in range(len(neg_b)):
            neg_b[i] = ~neg_b[i] & 0xFF
        result = int.from_bytes(neg_b, "big")
        return -result - 1
    else:
        return int.from_bytes(b, "big")
