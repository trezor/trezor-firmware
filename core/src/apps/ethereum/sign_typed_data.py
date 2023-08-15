from typing import TYPE_CHECKING

from trezor.enums import EthereumDataType
from trezor.wire import DataError
from trezor.wire.context import call

from .helpers import get_type_name
from .keychain import PATTERNS_ADDRESS, with_keychain_from_path
from .layout import should_show_struct

if TYPE_CHECKING:
    from trezor.messages import (
        EthereumFieldType,
        EthereumSignTypedData,
        EthereumTypedDataSignature,
        EthereumTypedDataStructAck,
    )
    from trezor.utils import HashWriter

    from apps.common.keychain import Keychain

    from .definitions import Definitions


@with_keychain_from_path(*PATTERNS_ADDRESS)
async def sign_typed_data(
    msg: EthereumSignTypedData,
    keychain: Keychain,
    defs: Definitions,
) -> EthereumTypedDataSignature:
    from trezor.crypto.curve import secp256k1
    from trezor.messages import EthereumTypedDataSignature

    from apps.common import paths

    from .helpers import address_from_bytes
    from .layout import require_confirm_address

    await paths.validate_path(keychain, msg.address_n)

    node = keychain.derive(msg.address_n)
    address_bytes: bytes = node.ethereum_pubkeyhash()

    # Display address so user can validate it
    await require_confirm_address(address_bytes)

    data_hash = await _generate_typed_data_hash(
        msg.primary_type, msg.metamask_v4_compat
    )

    signature = secp256k1.sign(
        node.private_key(), data_hash, False, secp256k1.CANONICAL_SIG_ETHEREUM
    )

    return EthereumTypedDataSignature(
        address=address_from_bytes(address_bytes, defs.network),
        signature=signature[1:] + signature[0:1],
    )


async def _generate_typed_data_hash(
    primary_type: str, metamask_v4_compat: bool = True
) -> bytes:
    """
    Generate typed data hash according to EIP-712 specification
    https://eips.ethereum.org/EIPS/eip-712#specification

    metamask_v4_compat - a flag that enables compatibility with MetaMask's signTypedData_v4 method
    """
    from .layout import (
        confirm_empty_typed_message,
        confirm_typed_data_final,
        should_show_domain,
    )

    typed_data_envelope = TypedDataEnvelope(
        primary_type,
        metamask_v4_compat,
    )
    await typed_data_envelope.collect_types()

    name, version = await _get_name_and_version_for_domain(typed_data_envelope)
    show_domain = await should_show_domain(name, version)
    domain_separator = await typed_data_envelope.hash_struct(
        "EIP712Domain",
        [0],
        show_domain,
        ["EIP712Domain"],
    )

    # Setting the primary_type to "EIP712Domain" is technically in spec
    # In this case, we ignore the "message" part and only use the "domain" part
    # https://ethereum-magicians.org/t/eip-712-standards-clarification-primarytype-as-domaintype/3286
    if primary_type == "EIP712Domain":
        await confirm_empty_typed_message()
        message_hash = b""
    else:
        show_message = await should_show_struct(
            primary_type,
            typed_data_envelope.types[primary_type].members,
            "Confirm message",
            "Show full message",
        )
        message_hash = await typed_data_envelope.hash_struct(
            primary_type,
            [1],
            show_message,
            [primary_type],
        )

    await confirm_typed_data_final()

    return keccak256(b"\x19\x01" + domain_separator + message_hash)


def get_hash_writer() -> HashWriter:
    from trezor.crypto.hashlib import sha3_256
    from trezor.utils import HashWriter

    return HashWriter(sha3_256(keccak=True))


def keccak256(message: bytes) -> bytes:
    h = get_hash_writer()
    h.extend(message)
    return h.get_digest()


class TypedDataEnvelope:
    """Encapsulates the type information for the message being hashed and signed."""

    def __init__(
        self,
        primary_type: str,
        metamask_v4_compat: bool,
    ) -> None:
        self.primary_type = primary_type
        self.metamask_v4_compat = metamask_v4_compat
        self.types: dict[str, EthereumTypedDataStructAck] = {}

    async def collect_types(self) -> None:
        """Aggregate type collection process for both domain and message data."""
        await self._collect_types("EIP712Domain")
        await self._collect_types(self.primary_type)

    async def _collect_types(self, type_name: str) -> None:
        """Recursively collect types from the client."""
        from trezor.messages import (
            EthereumTypedDataStructAck,
            EthereumTypedDataStructRequest,
        )

        req = EthereumTypedDataStructRequest(name=type_name)
        current_type = await call(req, EthereumTypedDataStructAck)
        self.types[type_name] = current_type
        for member in current_type.members:
            member_type = member.type
            validate_field_type(member_type)
            while member_type.data_type == EthereumDataType.ARRAY:
                assert member_type.entry_type is not None  # validate_field_type
                member_type = member_type.entry_type
            if (
                member_type.data_type == EthereumDataType.STRUCT
                and member_type.struct_name not in self.types
            ):
                assert member_type.struct_name is not None  # validate_field_type
                await self._collect_types(member_type.struct_name)

    async def hash_struct(
        self,
        primary_type: str,
        member_path: list[int],
        show_data: bool,
        parent_objects: list[str],
    ) -> bytes:
        """Generate a hash representation of the whole struct."""
        w = get_hash_writer()
        self.hash_type(w, primary_type)
        await self.get_and_encode_data(
            w,
            primary_type,
            member_path,
            show_data,
            parent_objects,
        )
        return w.get_digest()

    def hash_type(self, w: HashWriter, primary_type: str) -> None:
        """Create a representation of a type."""
        result = keccak256(self.encode_type(primary_type))
        w.extend(result)

    def encode_type(self, primary_type: str) -> bytes:
        """
        SPEC:
        The type of a struct is encoded as name ‖ "(" ‖ member₁ ‖ "," ‖ member₂ ‖ "," ‖ … ‖ memberₙ ")"
        where each member is written as type ‖ " " ‖ name
        If the struct type references other struct types (and these in turn reference even more struct types),
        then the set of referenced struct types is collected, sorted by name and appended to the encoding.
        """
        result: list[str] = []

        deps: set[str] = set()
        self.find_typed_dependencies(primary_type, deps)
        deps.remove(primary_type)

        for type_name in [primary_type] + sorted(deps):
            members = self.types[type_name].members
            fields = ",".join(f"{get_type_name(m.type)} {m.name}" for m in members)
            result.append(f"{type_name}({fields})")

        return "".join(result).encode()

    def find_typed_dependencies(
        self,
        primary_type: str,
        results: set[str],
    ) -> None:
        """Find all types within a type definition object."""
        # We already have this type or it is not even a defined type
        if (primary_type in results) or (primary_type not in self.types):
            return

        results.add(primary_type)

        # Recursively adding all the children struct types,
        # also looking into (even nested) arrays for them
        for member in self.types[primary_type].members:
            member_type = member.type
            while member_type.data_type == EthereumDataType.ARRAY:
                assert member_type.entry_type is not None  # validate_field_type
                member_type = member_type.entry_type
            if member_type.data_type == EthereumDataType.STRUCT:
                assert member_type.struct_name is not None  # validate_field_type
                self.find_typed_dependencies(member_type.struct_name, results)

    async def get_and_encode_data(
        self,
        w: HashWriter,
        primary_type: str,
        member_path: list[int],
        show_data: bool,
        parent_objects: list[str],
    ) -> None:
        """
        Gradually fetch data from client and encode the whole struct.

        SPEC:
        The encoding of a struct instance is enc(value₁) ‖ enc(value₂) ‖ … ‖ enc(valueₙ),
        i.e. the concatenation of the encoded member values in the order that they appear in the type.
        Each encoded member value is exactly 32-byte long.
        """
        from .layout import confirm_typed_value, should_show_array

        type_members = self.types[primary_type].members
        member_value_path = member_path + [0]
        current_parent_objects = parent_objects + [""]
        for member_index, member in enumerate(type_members):
            member_value_path[-1] = member_index
            field_name = member.name
            field_type = member.type

            # Arrays and structs need special recursive handling
            if field_type.data_type == EthereumDataType.STRUCT:
                assert field_type.struct_name is not None  # validate_field_type
                struct_name = field_type.struct_name
                current_parent_objects[-1] = field_name

                if show_data:
                    show_struct = await should_show_struct(
                        struct_name,  # description
                        self.types[struct_name].members,  # data_members
                        ".".join(current_parent_objects),  # title
                    )
                else:
                    show_struct = False

                res = await self.hash_struct(
                    struct_name,
                    member_value_path,
                    show_struct,
                    current_parent_objects,
                )
                w.extend(res)
            elif field_type.data_type == EthereumDataType.ARRAY:
                # Getting the length of the array first, if not fixed
                if field_type.size is None:
                    array_size = await _get_array_size(member_value_path)
                else:
                    array_size = field_type.size

                assert field_type.entry_type is not None  # validate_field_type
                entry_type = field_type.entry_type
                current_parent_objects[-1] = field_name

                if show_data:
                    show_array = await should_show_array(
                        current_parent_objects,
                        get_type_name(entry_type),
                        array_size,
                    )
                else:
                    show_array = False

                arr_w = get_hash_writer()
                el_member_path = member_value_path + [0]
                for i in range(array_size):
                    el_member_path[-1] = i
                    # TODO: we do not support arrays of arrays, check if we should
                    if entry_type.data_type == EthereumDataType.STRUCT:
                        assert entry_type.struct_name is not None  # validate_field_type
                        struct_name = entry_type.struct_name
                        # Metamask V4 implementation has a bug, that causes the
                        # behavior of structs in array be different from SPEC
                        # Explanation at https://github.com/MetaMask/eth-sig-util/pull/107
                        # encode_data() is the way to process structs in arrays, but
                        # Metamask V4 is using hash_struct() even in this case
                        if self.metamask_v4_compat:
                            res = await self.hash_struct(
                                struct_name,
                                el_member_path,
                                show_array,
                                current_parent_objects,
                            )
                            arr_w.extend(res)
                        else:
                            await self.get_and_encode_data(
                                arr_w,
                                struct_name,
                                el_member_path,
                                show_array,
                                current_parent_objects,
                            )
                    else:
                        value = await get_value(entry_type, el_member_path)
                        encode_field(arr_w, entry_type, value)
                        if show_array:
                            await confirm_typed_value(
                                field_name,
                                value,
                                parent_objects,
                                entry_type,
                                i,
                            )
                w.extend(arr_w.get_digest())
            else:
                value = await get_value(field_type, member_value_path)
                encode_field(w, field_type, value)
                if show_data:
                    await confirm_typed_value(
                        field_name,
                        value,
                        parent_objects,
                        field_type,
                    )


def encode_field(
    w: HashWriter,
    field: EthereumFieldType,
    value: bytes,
) -> None:
    """
    SPEC:
    Atomic types:
    - Boolean false and true are encoded as uint256 values 0 and 1 respectively
    - Addresses are encoded as uint160
    - Integer values are sign-extended to 256-bit and encoded in big endian order
    - Bytes1 to bytes31 are arrays with a beginning (index 0)
      and an end (index length - 1), they are zero-padded at the end to bytes32 and encoded
      in beginning to end order
    Dynamic types:
    - Bytes and string are encoded as a keccak256 hash of their contents
    Reference types:
    - Array values are encoded as the keccak256 hash of the concatenated
      encodeData of their contents
    - Struct values are encoded recursively as hashStruct(value)
    """
    EDT = EthereumDataType  # local_cache_global

    data_type = field.data_type

    if data_type == EDT.BYTES:
        if field.size is None:
            w.extend(keccak256(value))
        else:
            # write_rightpad32
            assert len(value) <= 32
            w.extend(value)
            for _ in range(32 - len(value)):
                w.append(0x00)
    elif data_type == EDT.STRING:
        w.extend(keccak256(value))
    elif data_type == EDT.INT:
        write_leftpad32(w, value, signed=True)
    elif data_type in (
        EDT.UINT,
        EDT.BOOL,
        EDT.ADDRESS,
    ):
        write_leftpad32(w, value)
    else:
        raise ValueError  # Unsupported data type for field encoding


def write_leftpad32(w: HashWriter, value: bytes, signed: bool = False) -> None:
    assert len(value) <= 32

    # Values need to be sign-extended, so accounting for negative ints
    if signed and value[0] & 0x80:
        pad_value = 0xFF
    else:
        pad_value = 0x00

    for _ in range(32 - len(value)):
        w.append(pad_value)
    w.extend(value)


def _validate_value(field: EthereumFieldType, value: bytes) -> None:
    """
    Make sure the byte data we receive are not corrupted or incorrect.

    Raise DataError if encountering a problem, so clients are notified.
    """
    # Checking if the size corresponds to what is defined in types.
    # Not having any maximum field size - it is a responsibility of the client
    # (and message creator) to make sure the data is not too large to cause problems
    # on the Trezor side.
    if field.size is not None and len(value) != field.size:
        raise DataError("Invalid length")

    # Specific tests for some data types
    if field.data_type == EthereumDataType.BOOL:
        if value not in (b"\x00", b"\x01"):
            raise DataError("Invalid boolean value")
    elif field.data_type == EthereumDataType.ADDRESS:
        if len(value) != 20:
            raise DataError("Invalid address")
    elif field.data_type == EthereumDataType.STRING:
        try:
            value.decode()
        except UnicodeError:
            raise DataError("Invalid UTF-8")


def validate_field_type(field: EthereumFieldType) -> None:
    """
    Make sure the field type is consistent with our expectation.

    Raise DataError if encountering a problem, so clients are notified.
    """
    EDT = EthereumDataType  # local_cache_global

    data_type = field.data_type

    # entry_type is only for arrays
    if data_type == EDT.ARRAY:
        if field.entry_type is None:
            raise DataError("Missing entry_type in array")
        # We also need to validate it recursively
        validate_field_type(field.entry_type)
    else:
        if field.entry_type is not None:
            raise DataError("Unexpected entry_type in nonarray")

    # struct_name is only for structs
    if data_type == EDT.STRUCT:
        if field.struct_name is None:
            raise DataError("Missing struct_name in struct")
    else:
        if field.struct_name is not None:
            raise DataError("Unexpected struct_name in nonstruct")
    size = field.size  # local_cache_attribute

    # size is special for each type
    if data_type == EDT.STRUCT:
        if size is None:
            raise DataError("Missing size in struct")
    elif data_type == EDT.BYTES:
        if size is not None and not 1 <= size <= 32:
            raise DataError("Invalid size in bytes")
    elif data_type in (
        EDT.UINT,
        EDT.INT,
    ):
        if size is None or not 1 <= size <= 32:
            raise DataError("Invalid size in int/uint")
    elif data_type in (
        EDT.STRING,
        EDT.BOOL,
        EDT.ADDRESS,
    ):
        if size is not None:
            raise DataError("Unexpected size in str/bool/addr")


async def _get_array_size(member_path: list[int]) -> int:
    """Get the length of an array at specific `member_path` from the client."""
    from trezor.messages import EthereumFieldType

    # Field type for getting the array length from client, so we can check the return value
    ARRAY_LENGTH_TYPE = EthereumFieldType(data_type=EthereumDataType.UINT, size=2)
    length_value = await get_value(ARRAY_LENGTH_TYPE, member_path)
    return int.from_bytes(length_value, "big")


async def get_value(
    field: EthereumFieldType,
    member_value_path: list[int],
) -> bytes:
    """Get a single value from the client and perform its validation."""
    from trezor.messages import EthereumTypedDataValueAck, EthereumTypedDataValueRequest

    req = EthereumTypedDataValueRequest(
        member_path=member_value_path,
    )
    res = await call(req, EthereumTypedDataValueAck)
    value = res.value

    _validate_value(field=field, value=value)

    return value


async def _get_name_and_version_for_domain(
    typed_data_envelope: TypedDataEnvelope,
) -> tuple[bytes, bytes]:
    domain_name = b"unknown"
    domain_version = b"unknown"

    domain_members = typed_data_envelope.types["EIP712Domain"].members
    member_value_path = [0, 0]
    for member_index, member in enumerate(domain_members):
        member_value_path[-1] = member_index
        if member.name == "name":
            domain_name = await get_value(member.type, member_value_path)
        elif member.name == "version":
            domain_version = await get_value(member.type, member_value_path)

    return domain_name, domain_version
