from ubinascii import hexlify, unhexlify

from trezor.crypto.curve import secp256k1
from trezor.crypto.hashlib import sha3_256
from trezor.messages.EthereumTypedDataAck import EthereumTypedDataAck
from trezor.messages.EthereumTypedDataRequest import EthereumTypedDataRequest

from trezor.ui.components.tt.text import Text
from trezor.utils import HashWriter

from apps.common import paths
from apps.common.confirm import confirm, require_confirm, require_hold_to_confirm

from . import address
from .keychain import PATTERNS_ADDRESS, with_keychain_from_path
from .layout import (
    confirm_typed_domain_brief,
    confirm_typed_data_brief,
    require_confirm_typed_domain,
    require_confirm_typed_data,
    require_confirm_typed_data_hash,
)

from .abi import abi_encode, is_array, typeof_array


def keccak256(message):
    h = HashWriter(sha3_256(keccak=True))
    h.extend(message)
    return h.get_digest()


@with_keychain_from_path(*PATTERNS_ADDRESS)
async def sign_typed_data(ctx, msg, keychain):
    data_hash = await generate_typed_data_hash(ctx, msg.use_v4)

    await paths.validate_path(ctx, keychain, msg.address_n)

    node = keychain.derive(msg.address_n)
    signature = secp256k1.sign(
        node.private_key(), data_hash, False, secp256k1.CANONICAL_SIG_ETHEREUM
    )

    sig = EthereumTypedDataRequest()
    sig.address = address.address_from_bytes(node.ethereum_pubkeyhash())
    sig.signature = signature[1:] + bytearray([signature[0]])
    return sig


async def generate_typed_data_hash(ctx, use_v4: bool = True) -> bytes:
    """
    Generates typed data hash according to EIP-712 specification
    https://eips.ethereum.org/EIPS/eip-712#specification

    use_v4 - a flag that enables compatibility with MetaMask's signTypedData_v4 method
    """
    domain_types = await collect_domain_types(ctx)
    domain_values = await collect_values(ctx, "EIP712Domain", domain_types, [0])
    primary_type, message_types = await collect_types(ctx)
    message_values = await collect_values(ctx, primary_type, message_types)

    show_domain = await confirm_typed_domain_brief(ctx, domain_values)
    if show_domain:
        await require_confirm_typed_domain(ctx, domain_types["EIP712Domain"], domain_values)

    show_message = await confirm_typed_data_brief(ctx, primary_type, message_types[primary_type])
    if show_message:
        await require_confirm_typed_data(ctx, primary_type, message_types, message_values)

    domain_separator = hash_struct("EIP712Domain", domain_values, domain_types, use_v4)
    message_hash = hash_struct(primary_type, message_values, message_types, use_v4)

    if not show_message:
        await require_confirm_typed_data_hash(ctx, primary_type, message_hash)

    return keccak256(b"\x19" + b"\x01" + domain_separator + message_hash)


async def collect_domain_types(ctx) -> dict:
    """
    Collects domain types from the client
    """
    root_type = await request_member_type(ctx, [0, 0])
    if root_type.member_type != "EIP712Domain":
        raise ValueError("EIP712 domain not provided")

    children = []
    if root_type.member_children:
        for i in range(0, root_type.member_children):
            dep = await request_member_type(ctx, [0, 0, i])
            children.append({
                "type": dep.member_type,
                "name": dep.member_name,
                "children_num": dep.member_children,
                "member_array_n": dep.member_array_n,
            })

    types = {
        "EIP712Domain": children,
    }
    return types


async def collect_types(ctx, types: dict = None, member_path: list = None) -> (str, dict):
    """
    Collects type definitions from the client
    """
    if types is None:
        types = {}
    if member_path is None:
        member_path = [1]

    primary_type = None
    member_type_offset = 0
    while member_type_offset < 65536:
        member_type_path = member_path + [member_type_offset]
        member = await request_member_type(ctx, member_type_path)
        type_name = member.member_type
        if type_name is None:
            break
        elif member_type_offset is 0:
            primary_type = type_name

        if not (type_name in types):
            types[type_name] = []
            if member.member_children:
                for i in range(0, member.member_children):
                    dep = await request_member_type(ctx, member_type_path + [i])
                    types[type_name].append({
                        "type": dep.member_type,
                        "name": dep.member_name,
                        "children_num": dep.member_children,
                        "member_array_n": dep.member_array_n,
                    })

        member_type_offset += 1

    return primary_type, types


def hash_struct(primary_type: str, data: dict, types: dict = None, use_v4: bool = True) -> bytes:
    """
    Encodes and hashes an object using Keccak256
    """
    return keccak256(encode_data(primary_type, data, types, use_v4))


def encode_data(primary_type: str, data: dict, types: dict = None, use_v4: bool = True) -> bytes:
    """
    Encodes an object by encoding and concatenating each of its members

    primary_type - Root type
    data - Object to encode
    types - Type definitions
    """
    encoded_types = ["bytes32"]
    encoded_values = [hash_type(primary_type, types)]

    for field in types[primary_type]:
        enc_type, enc_value = encode_field(
            use_v4=use_v4,
            in_array=False,
            types=types,
            name=field["name"],
            type_name=field["type"],
            value=data.get(field["name"]),
        )
        encoded_types.append(enc_type)
        encoded_values.append(enc_value)

    return abi_encode(encoded_types, encoded_values)


def encode_field(use_v4: bool, in_array: bool, types: dict, name: str, type_name: str, value) -> (str, bytes):
    if type_name in types:
        if value is None:
            return "bytes32", bytes(32)

        if in_array and not use_v4:
            return "bytes", encode_data(type_name, value, types)

        return "bytes32", hash_struct(type_name, value, types, use_v4)

    if value is None:
        raise ValueError("missing value for field %s of type %s" % (name, type_name))

    if type_name is "bytes32":
        if not (isinstance(value, bytes) or isinstance(value, bytearray)):
            raise ValueError("value for field %s (type %s) expected to be bytes or bytearray" % (name, type_name))

        return "bytes32", keccak256(value)

    if type_name is "string":
        if isinstance(value, str):
            value = bytes(value, encoding="utf8")
            return "bytes32", keccak256(value)
        elif not (isinstance(value, bytes) or isinstance(value, bytearray)):
            raise ValueError("value for field %s (type %s) expected to be bytes, bytearray or str" % (name, type_name))

        return "bytes32", keccak256(value)

    if is_array(type_name):
        parsed_type = typeof_array(type_name)
        while is_array(parsed_type):
            parsed_type = typeof_array(parsed_type)

        if parsed_type in types:
            if not isinstance(value, list):
                raise ValueError("value for field %s (type %s) expected to be a list" % (name, type_name))

            type_value_pairs = map(lambda x: encode_field(
               use_v4=use_v4,
               in_array=True,
               types=types,
               name=name,
               type_name=typeof_array(type_name),
               value=x,
            ), value)

            encoded_value = bytearray(0)
            for [_, value] in type_value_pairs:
                encoded_value.extend(value)

            return "bytes32", keccak256(encoded_value)

        return "bytes32", keccak256(value)

    # value is already abi-encoded
    return "bytes32", value


async def collect_values(ctx, primary_type: str, types: dict = None, member_path: list = None) -> dict:
    """
    Collects data values from the client
    """
    if types is None:
        types = {}
    if member_path is None:
        member_path = [1]

    values = {}
    struct = types.get(primary_type)

    for fieldIdx in range(0, len(struct)):
        field = struct[fieldIdx]
        field_name = field["name"]
        field_type = field["type"]
        type_children = field["children_num"]
        type_array = field["member_array_n"]
        member_value_path = member_path + [fieldIdx]

        res = await request_member_value(ctx, member_value_path)
        if res.member_type is None:
            raise ValueError("value of %s in %s is not set in data" % (field_name, primary_type))

        if not (res.member_value is None):
            values[field_name] = res.member_value
        elif type_children and type_children > 0:
            values[field_name] = await collect_values(ctx, field_type, types, member_value_path)
        elif not (type_array is None):
            if type_array is 0:
                # override with dynamic size we've just got from values
                type_array = res.member_array_n

            values[field_name] = []
            for elemIdx in range(0, type_array):
                elem = await collect_values(ctx, res.member_type, types, member_value_path + [elemIdx])
                values[field_name].append(elem)
        else:
            values[field_name] = None

    return values


def hash_type(primary_type, types) -> bytes:
    """
    Encodes and hashes a type using Keccak256
    """
    return keccak256(encode_type(primary_type, types))


def encode_type(primary_type: str, types: dict):
    """
    Encodes the type of an object by encoding a comma delimited list of its members

    primary_type - Root type to encode
    types - Type definitions
    """
    result = b""

    deps = find_typed_dependencies(primary_type, types)
    deps = list(filter(lambda dep: dep != primary_type, deps))
    deps = [primary_type] + sorted(deps)

    for type_name in deps:
        children = types.get(type_name)
        if children is None:
            raise ValueError("no type definition specified: %s" % type_name)
        fields = ",".join(map(lambda field: "%s %s" % (field["type"], field["name"]), children))
        result += b"%s(%s)" % (type_name, fields)

    return result


def find_typed_dependencies(primary_type: str, types=None, results=None):
    """
    Finds all types within a type definition object

    primary_type - Root type
    types - Type definitions
    results - Current set of accumulated types
    """
    if results is None:
        results = []
    if types is None:
        types = {}

    if primary_type[len(primary_type)-1] == ']':
        primary_type = primary_type[:primary_type.rindex('[')]

    if (primary_type in results) or (types.get(primary_type) is None):
        return results

    results = results + [primary_type]
    for field in types[primary_type]:
        deps = find_typed_dependencies(field["type"], types, results)
        for dep in deps:
            if not (dep in results):
                results = results + [dep]

    return results


async def request_member_type(ctx, member_path):
    """
    Requests a type of member at `member_path` from the client
    """
    req = EthereumTypedDataRequest()
    req.member_path = member_path
    req.expect_type = True
    return await ctx.call(req, EthereumTypedDataAck)


async def request_member_value(ctx, member_path):
    """
    Requests a value of member at `member_path` from the client
    """
    req = EthereumTypedDataRequest()
    req.member_path = member_path
    req.expect_type = False
    return await ctx.call(req, EthereumTypedDataAck)
