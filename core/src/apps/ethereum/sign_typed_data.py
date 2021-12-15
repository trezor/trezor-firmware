from trezor import wire
from trezor.crypto.curve import secp256k1
from trezor.crypto.hashlib import sha3_256
from trezor.enums import EthereumDataType
from trezor.messages import (
    EthereumFieldType,
    EthereumSignTypedData,
    EthereumTypedDataSignature,
    EthereumTypedDataStructAck,
    EthereumTypedDataStructRequest,
    EthereumTypedDataValueAck,
    EthereumTypedDataValueRequest,
)
from trezor.utils import HashWriter

from apps.common import paths

from .helpers import address_from_bytes, get_type_name
from .keychain import PATTERNS_ADDRESS, with_keychain_from_path
from .layout import (
    confirm_hash,
    confirm_typed_value,
    should_show_array,
    should_show_domain,
    should_show_struct,
)

if False:
    from apps.common.keychain import Keychain
    from trezor.wire import Context


# Maximum data size we support
MAX_VALUE_BYTE_SIZE = 1024


@with_keychain_from_path(*PATTERNS_ADDRESS)
async def sign_typed_data(
    ctx: Context, msg: EthereumSignTypedData, keychain: Keychain
) -> EthereumTypedDataSignature:
    await paths.validate_path(ctx, keychain, msg.address_n)

    data_hash = await generate_typed_data_hash(
        ctx, msg.primary_type, msg.metamask_v4_compat
    )

    node = keychain.derive(msg.address_n)
    signature = secp256k1.sign(
        node.private_key(), data_hash, False, secp256k1.CANONICAL_SIG_ETHEREUM
    )

    return EthereumTypedDataSignature(
        address=address_from_bytes(node.ethereum_pubkeyhash()),
        signature=signature[1:] + signature[0:1],
    )


async def generate_typed_data_hash(
    ctx: Context, primary_type: str, metamask_v4_compat: bool = True
) -> bytes:
    """
    Generate typed data hash according to EIP-712 specification
    https://eips.ethereum.org/EIPS/eip-712#specification

    metamask_v4_compat - a flag that enables compatibility with MetaMask's signTypedData_v4 method
    """
    typed_data_envelope = TypedDataEnvelope(
        ctx=ctx,
        primary_type=primary_type,
        metamask_v4_compat=metamask_v4_compat,
    )
    await typed_data_envelope.collect_types()

    name, version = await get_name_and_version_for_domain(ctx, typed_data_envelope)
    show_domain = await should_show_domain(ctx, name, version)
    domain_separator = await typed_data_envelope.hash_struct(
        primary_type="EIP712Domain",
        member_path=[0],
        show_data=show_domain,
        parent_objects=["EIP712Domain"],
    )

    show_message = await should_show_struct(
        ctx,
        description=primary_type,
        data_members=typed_data_envelope.types[primary_type].members,
        title="Confirm message",
        button_text="Show full message",
    )
    message_hash = await typed_data_envelope.hash_struct(
        primary_type=primary_type,
        member_path=[1],
        show_data=show_message,
        parent_objects=[primary_type],
    )

    await confirm_hash(ctx, message_hash)

    return keccak256(b"\x19" + b"\x01" + domain_separator + message_hash)


def get_hash_writer() -> HashWriter:
    return HashWriter(sha3_256(keccak=True))


def keccak256(message: bytes) -> bytes:
    h = get_hash_writer()
    h.extend(message)
    return h.get_digest()


class TypedDataEnvelope:
    """Encapsulates the type information for the message being hashed and signed."""

    def __init__(
        self,
        ctx: Context,
        primary_type: str,
        metamask_v4_compat: bool,
    ) -> None:
        self.ctx = ctx
        self.primary_type = primary_type
        self.metamask_v4_compat = metamask_v4_compat
        self.types: dict[str, EthereumTypedDataStructAck] = {}

    async def collect_types(self) -> None:
        """Aggregate type collection process for both domain and message data."""
        await self._collect_types("EIP712Domain")
        await self._collect_types(self.primary_type)

    async def _collect_types(self, type_name: str) -> None:
        """Recursively collect types from the client."""
        req = EthereumTypedDataStructRequest(name=type_name)
        current_type = await self.ctx.call(req, EthereumTypedDataStructAck)
        self.types[type_name] = current_type
        for member in current_type.members:
            validate_field_type(member.type)
            if (
                member.type.data_type == EthereumDataType.STRUCT
                and member.type.struct_name not in self.types
            ):
                assert member.type.struct_name is not None  # validate_field_type
                await self._collect_types(member.type.struct_name)

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
            w=w,
            primary_type=primary_type,
            member_path=member_path,
            show_data=show_data,
            parent_objects=parent_objects,
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
                        ctx=self.ctx,
                        description=struct_name,
                        data_members=self.types[struct_name].members,
                        title=".".join(current_parent_objects),
                    )
                else:
                    show_struct = False

                res = await self.hash_struct(
                    primary_type=struct_name,
                    member_path=member_value_path,
                    show_data=show_struct,
                    parent_objects=current_parent_objects,
                )
                w.extend(res)
            elif field_type.data_type == EthereumDataType.ARRAY:
                # Getting the length of the array first, if not fixed
                if field_type.size is None:
                    array_size = await get_array_size(self.ctx, member_value_path)
                else:
                    array_size = field_type.size

                assert field_type.entry_type is not None  # validate_field_type
                entry_type = field_type.entry_type
                current_parent_objects[-1] = field_name

                if show_data:
                    show_array = await should_show_array(
                        ctx=self.ctx,
                        parent_objects=current_parent_objects,
                        data_type=get_type_name(entry_type),
                        size=array_size,
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
                                primary_type=struct_name,
                                member_path=el_member_path,
                                show_data=show_array,
                                parent_objects=current_parent_objects,
                            )
                            arr_w.extend(res)
                        else:
                            await self.get_and_encode_data(
                                w=arr_w,
                                primary_type=struct_name,
                                member_path=el_member_path,
                                show_data=show_array,
                                parent_objects=current_parent_objects,
                            )
                    else:
                        value = await get_value(self.ctx, entry_type, el_member_path)
                        encode_field(arr_w, entry_type, value)
                        if show_array:
                            await confirm_typed_value(
                                ctx=self.ctx,
                                name=field_name,
                                value=value,
                                parent_objects=parent_objects,
                                field=entry_type,
                                array_index=i,
                            )
                w.extend(arr_w.get_digest())
            else:
                value = await get_value(self.ctx, field_type, member_value_path)
                encode_field(w, field_type, value)
                if show_data:
                    await confirm_typed_value(
                        ctx=self.ctx,
                        name=field_name,
                        value=value,
                        parent_objects=parent_objects,
                        field=field_type,
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
    data_type = field.data_type

    if data_type == EthereumDataType.BYTES:
        if field.size is None:
            w.extend(keccak256(value))
        else:
            write_rightpad32(w, value)
    elif data_type == EthereumDataType.STRING:
        w.extend(keccak256(value))
    elif data_type == EthereumDataType.INT:
        write_leftpad32(w, value, signed=True)
    elif data_type in (
        EthereumDataType.UINT,
        EthereumDataType.BOOL,
        EthereumDataType.ADDRESS,
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


def write_rightpad32(w: HashWriter, value: bytes) -> None:
    assert len(value) <= 32

    w.extend(value)
    for _ in range(32 - len(value)):
        w.append(0x00)


def validate_value(field: EthereumFieldType, value: bytes) -> None:
    """
    Make sure the byte data we receive are not corrupted or incorrect.

    Raise wire.DataError if encountering a problem, so clients are notified.
    """
    # Checking if the size corresponds to what is defined in types,
    # and also setting our maximum supported size in bytes
    if field.size is not None:
        if len(value) != field.size:
            raise wire.DataError("Invalid length")
    else:
        if len(value) > MAX_VALUE_BYTE_SIZE:
            raise wire.DataError(f"Invalid length, bigger than {MAX_VALUE_BYTE_SIZE}")

    # Specific tests for some data types
    if field.data_type == EthereumDataType.BOOL:
        if value not in (b"\x00", b"\x01"):
            raise wire.DataError("Invalid boolean value")
    elif field.data_type == EthereumDataType.ADDRESS:
        if len(value) != 20:
            raise wire.DataError("Invalid address")
    elif field.data_type == EthereumDataType.STRING:
        try:
            value.decode()
        except UnicodeError:
            raise wire.DataError("Invalid UTF-8")


def validate_field_type(field: EthereumFieldType) -> None:
    """
    Make sure the field type is consistent with our expectation.

    Raise wire.DataError if encountering a problem, so clients are notified.
    """
    data_type = field.data_type

    # entry_type is only for arrays
    if data_type == EthereumDataType.ARRAY:
        if field.entry_type is None:
            raise wire.DataError("Missing entry_type in array")
        # We also need to validate it recursively
        validate_field_type(field.entry_type)
    else:
        if field.entry_type is not None:
            raise wire.DataError("Unexpected entry_type in nonarray")

    # struct_name is only for structs
    if data_type == EthereumDataType.STRUCT:
        if field.struct_name is None:
            raise wire.DataError("Missing struct_name in struct")
    else:
        if field.struct_name is not None:
            raise wire.DataError("Unexpected struct_name in nonstruct")

    # size is special for each type
    if data_type == EthereumDataType.STRUCT:
        if field.size is None:
            raise wire.DataError("Missing size in struct")
    elif data_type == EthereumDataType.BYTES:
        if field.size is not None and not 1 <= field.size <= 32:
            raise wire.DataError("Invalid size in bytes")
    elif data_type in (
        EthereumDataType.UINT,
        EthereumDataType.INT,
    ):
        if field.size is None or not 1 <= field.size <= 32:
            raise wire.DataError("Invalid size in int/uint")
    elif data_type in (
        EthereumDataType.STRING,
        EthereumDataType.BOOL,
        EthereumDataType.ADDRESS,
    ):
        if field.size is not None:
            raise wire.DataError("Unexpected size in str/bool/addr")


async def get_array_size(ctx: Context, member_path: list[int]) -> int:
    """Get the length of an array at specific `member_path` from the client."""
    # Field type for getting the array length from client, so we can check the return value
    ARRAY_LENGTH_TYPE = EthereumFieldType(data_type=EthereumDataType.UINT, size=2)
    length_value = await get_value(ctx, ARRAY_LENGTH_TYPE, member_path)
    return int.from_bytes(length_value, "big")


async def get_value(
    ctx: Context,
    field: EthereumFieldType,
    member_value_path: list[int],
) -> bytes:
    """Get a single value from the client and perform its validation."""
    req = EthereumTypedDataValueRequest(
        member_path=member_value_path,
    )
    res = await ctx.call(req, EthereumTypedDataValueAck)
    value = res.value

    validate_value(field=field, value=value)

    return value


async def get_name_and_version_for_domain(
    ctx: Context, typed_data_envelope: TypedDataEnvelope
) -> tuple[bytes, bytes]:
    domain_name = b"unknown"
    domain_version = b"unknown"

    domain_members = typed_data_envelope.types["EIP712Domain"].members
    member_value_path = [0, 0]
    for member_index, member in enumerate(domain_members):
        member_value_path[-1] = member_index
        if member.name == "name":
            domain_name = await get_value(ctx, member.type, member_value_path)
        elif member.name == "version":
            domain_version = await get_value(ctx, member.type, member_value_path)

    return domain_name, domain_version
