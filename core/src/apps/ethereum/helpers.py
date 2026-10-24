from typing import TYPE_CHECKING

from trezor import TR

from . import networks

if TYPE_CHECKING:
    from buffer_types import AnyBytes
    from collections.abc import Awaitable, Callable, Sequence

    from trezor.messages import (
        EthereumDisplayFormatInfo,
        EthereumFieldType,
        EthereumTokenInfo,
    )
    from trezor.ui.layouts import StrPropertyType
    from trezor.utils import HashWriter

    from .definitions import Definitions
    from .keychain import MsgInSignTx
    from .networks import EthereumNetworkInfo

    # Fetch the next calldata chunk from host.
    # `data_left: int` argument is provided.
    DataChunkLoader = Callable[[int], Awaitable[AnyBytes]]


RSKIP60_NETWORKS = (30, 31)


def address_from_bytes(
    address_bytes: AnyBytes, network: EthereumNetworkInfo = networks.UNKNOWN_NETWORK
) -> str:
    """
    Converts address in bytes to a checksummed string as defined
    in https://github.com/ethereum/EIPs/blob/master/EIPS/eip-55.md
    """
    if network.chain_id in RSKIP60_NETWORKS:
        # rskip60 is a different way to calculate checksum
        prefix = str(network.chain_id) + "0x"
    else:
        prefix = ""

    address_hex = address_bytes.hex().encode()
    writer = keccak256(prefix.encode())
    writer.extend(address_hex)
    digest = writer.get_digest()

    def _maybe_upper(i: int) -> str:
        """Uppercase i-th letter only if the corresponding nibble has high bit set."""
        digest_byte = digest[i // 2]
        hex_letter = chr(address_hex[i])
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
    from trezor import wire

    if len(address) == 40:
        return bytes.fromhex(address)

    elif len(address) == 42:
        if address[0:2] not in ("0x", "0X"):
            raise wire.ProcessError("Ethereum: invalid beginning of an address")
        return bytes.fromhex(address[2:])

    elif len(address) == 0:
        return bytes()

    raise wire.ProcessError("Ethereum: Invalid address length")


async def request_definitions(
    chain_id: int, token_address: bytes, func_sig: bytes | None
) -> tuple[Definitions | None, EthereumDisplayFormatInfo | None]:
    """Ask the host for definitions of the network and the token at the address,
    or for the display format of `func_sig` called on the address."""
    from trezor.messages import EthereumDefinitionAck, EthereumDefinitionRequest
    from trezor.wire.context import call

    from apps.common.definitions import decode_definition

    from .definitions import Definitions

    req = EthereumDefinitionRequest(
        chain_id=chain_id,
        token_address=token_address,
        func_sig=func_sig,
    )
    res = await call(req, EthereumDefinitionAck)

    if res.definitions is None:
        return None, None

    definitions = Definitions.from_encoded(
        res.definitions.encoded_network, res.definitions.encoded_token, chain_id
    )

    display_format = (
        decode_definition(
            res.definitions.encoded_display_format, EthereumDisplayFormatInfo
        )
        if res.definitions.encoded_display_format is not None
        else None
    )

    return definitions, display_format


async def lookup_known_address(
    chain_id: int, address: bytes, msg: MsgInSignTx | None = None
) -> str | None:
    """Return a human-readable name of a well-known smart contract,
    or `None` if the address is not known.

    Built-in names and known vaults are tried first. If `msg` is given, the host is then asked
    about the address: the provider name of a returned display format, or the
    name of a returned token, is used.
    """
    from .sc_constants import known_address_iterator
    from .yielding_vaults import UNKNOWN_VAULT, lookup_vault

    for known_chain_id, known_address, name in known_address_iterator():
        if chain_id == known_chain_id and address == known_address:
            return name

    vault = lookup_vault(chain_id, address)
    if vault is not UNKNOWN_VAULT:
        return vault.name

    if msg is not None and msg.supports_definition_request:
        from .tokens import UNKNOWN_TOKEN

        # Host can send any displa formatter, we just care about the provider name.
        # TODO: definitions should have a simple 000.. display formatter for each contract we clear sign, potentially even unsupported providers.
        # TODO: Host (Connect, trezor-connect) should lookup ERC-20 tokens when contracts are not available.
        definitions, display_format = await request_definitions(
            chain_id, address, b"\x00\x00\x00\x00"
        )

        if (
            display_format is not None
            and display_format.chain_id == chain_id
            and bytes(display_format.address) == address
            and display_format.provider_name is not None
        ):
            return display_format.provider_name

        # Address was for an ERC-20 token.
        if definitions is not None:
            token = definitions.get_token(address)
            if token is not UNKNOWN_TOKEN:
                return token.name

    return None


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


def decode_typed_data(data: AnyBytes, type_name: str) -> str:
    """Used by sign_typed_data module to show data to user."""
    if type_name.startswith("bytes"):
        return data.hex()
    elif type_name == "string":
        return bytes(data).decode()
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
) -> Sequence[StrPropertyType]:
    # regular
    gas_limit_str = TR.ethereum__units_template.format(gas_limit)
    gas_price_str = format_ethereum_amount(
        gas_price, None, network, force_unit_gwei=True
    )

    return (
        (TR.ethereum__gas_limit, gas_limit_str, False),
        (TR.ethereum__gas_price, gas_price_str, False),
    )


def get_fee_items_eip1559(
    max_gas_fee: int,
    max_priority_fee: int,
    gas_limit: int,
    network: EthereumNetworkInfo,
) -> Sequence[StrPropertyType]:
    # EIP-1559
    gas_limit_str = TR.ethereum__units_template.format(gas_limit)
    max_gas_fee_str = format_ethereum_amount(
        max_gas_fee, None, network, force_unit_gwei=True
    )
    max_priority_fee_str = format_ethereum_amount(
        max_priority_fee, None, network, force_unit_gwei=True
    )

    return (
        (TR.ethereum__gas_limit, gas_limit_str, False),
        (TR.ethereum__max_gas_price, max_gas_fee_str, False),
        (TR.ethereum__priority_fee, max_priority_fee_str, False),
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


def get_account_and_path(address_n: list[int]) -> tuple[str | None, str | None]:
    from apps.common import paths

    from .keychain import PATTERNS_ADDRESS

    if not address_n or len(address_n) < 2:
        return (None, None)

    slip44_id = address_n[1]  # it depends on the network (ETH vs ETC...)

    account = paths.get_account_name("ETH", address_n, PATTERNS_ADDRESS, slip44_id)
    account_path = paths.address_n_to_str(address_n)

    return (account, account_path)


def _from_bytes_bigendian_signed(b: AnyBytes) -> int:
    negative = b[0] & 0x80
    if negative:
        neg_b = bytearray(b)
        for i in range(len(neg_b)):
            neg_b[i] = ~neg_b[i] & 0xFF
        result = int.from_bytes(neg_b, "big")
        return -result - 1
    else:
        return int.from_bytes(b, "big")


class DataChunkConfirmer:
    def __init__(self, total_len: int) -> None:
        self.total_len = total_len
        self.confirmed_len = 0
        self.progress_bar = None
        self.first: bool = True
        self.hasher: HashWriter | None = None

    async def confirm(self, chunk: AnyBytes) -> None:
        from trezor.enums import ButtonRequestType
        from trezor.ui.layouts import confirm_blob_intro, confirm_blob_prefix

        if self.first:
            self.first = False
            # show intro layout
            skip = await confirm_blob_intro(
                title=TR.ethereum__title_input_data,
                value=chunk,
                subtitle=TR.ethereum__data_size_template.format(self.total_len),
                verb=TR.buttons__confirm,
                verb_cancel=TR.buttons__cancel_sign,
                verb_view_all=TR.ethereum__view_data_and_hash,
                br_name="confirm_data",
                br_code=ButtonRequestType.SignTx,
            )
            if skip:
                # skip following chunks confirmation - use a progress bar instead
                self.progress_bar = self._get_progress_indicator()
            else:
                # ERC-8213 calldata digest will be confirmed after all calldata is hashed
                # https://ethereum-magicians.org/t/erc-8213-wallet-signature-and-calldata-digest-display/24295#calldata-digest
                self.hasher = keccak256(self.total_len.to_bytes(32, "big"))

        if self.hasher is not None:
            self.hasher.extend(chunk)

        if self.progress_bar is not None:
            return self.progress_bar(chunk)

        # for efficient chunk slicing (see below)
        chunk = memoryview(chunk)
        while True:
            assert 0 <= self.confirmed_len <= self.total_len
            prefix_len = await confirm_blob_prefix(
                data=chunk,
                total_len=self.total_len,
                confirmed_len=self.confirmed_len,
                br_name="confirm_data",
                br_code=ButtonRequestType.SignTx,
            )
            if prefix_len is None:
                # skip this and following chunks confirmation - use a progress bar instead
                assert self.progress_bar is None
                self.progress_bar = self._get_progress_indicator()
                return self.progress_bar(chunk)
            else:
                self.confirmed_len += prefix_len
                chunk = chunk[prefix_len:]
                if not chunk:
                    return

    def _get_progress_indicator(self) -> Callable[[AnyBytes], None]:
        from trezor.ui.layouts.progress import progress

        def _progress_value() -> int:
            assert 0 <= self.confirmed_len <= self.total_len
            if self.total_len == 0:
                return 1000
            return (1000 * self.confirmed_len) // self.total_len

        layout = progress(title=TR.progress__loading_transaction)
        layout.value = _progress_value()

        def confirm_fn(chunk: AnyBytes) -> None:
            self.confirmed_len += len(chunk)
            layout.report(_progress_value())

        return confirm_fn

    async def confirm_digest(self) -> None:
        if self.hasher is None:
            return

        if self.confirmed_len != self.total_len:
            from trezor.wire import ProcessError

            raise ProcessError("Missing calldata")

        from trezor.ui.layouts import confirm_calldata_digest

        # TODO: missing on Bolt & Caesar
        return await confirm_calldata_digest(self.hasher.get_digest(), self.total_len)


def keccak256(data: AnyBytes | None = None) -> HashWriter:
    from trezor.crypto.hashlib import sha3_256
    from trezor.utils import HashWriter

    return HashWriter(sha3_256(data=data, keccak=True))
