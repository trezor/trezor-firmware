from ubinascii import unhexlify, hexlify

from trezor.crypto.curve import secp256k1
from trezor.crypto.hashlib import sha3_256
from trezor.messages.EthereumMessageSignature import EthereumMessageSignature
from trezor.messages.TypedData_DataType import Literal, Struct
from trezor.ui.text import Text
from trezor.utils import HashWriter

from apps.common import paths
from apps.common.confirm import require_confirm
from apps.common.signverify import split_message
from apps.ethereum import CURVE, address


def message_digest(message):
    h = HashWriter(sha3_256(keccak=True))
    h.extend(message)
    return h.get_digest()


async def sign_typed_data(ctx, msg, keychain):
    data_hash = None
    try:
        definitions = build_types_map(msg.typed_data_definitions)
        data_hash = parse_typed_data(msg.typed_data, definitions)
    except Exception as e:
        print("error", e)
    await paths.validate_path(
        ctx, address.validate_full_path, keychain, msg.address_n, CURVE
    )
    #await require_confirm_sign_message(ctx, msg.typed_data)

    node = keychain.derive(msg.address_n)
    signature = secp256k1.sign(
        node.private_key(),
        data_hash,
        False,
        secp256k1.CANONICAL_SIG_ETHEREUM,
    )

    sig = EthereumMessageSignature()
    sig.address = address.address_from_bytes(node.ethereum_pubkeyhash())
    sig.signature = signature[1:] + bytearray([signature[0]])
    return sig


def build_types_map(defs):
    defs_map = {}
    for definition in defs:
        if definition.name in defs_map:
            raise ValueError("Type defined multiple times")
        d = []
        for param in definition.parameters:
            if param.name in d:
                raise ValueError("Parameter defined multiple times")
            d += [{"name": param.name, "type": param.encoding}]
        defs_map[definition.name] = d
    return defs_map


def build_struct_map(struct):
    struct_map = {}
    for parameter in struct:
        if parameter.name in struct_map:
            raise ValueError("Parameter defined multiple times")

        if parameter.data_type == Literal:
            struct_map[parameter.name] = parameter.literal
        elif parameter.data_type == Struct:
            struct_map[parameter.name] = build_struct_map(parameter.struct)
        else:
            raise ValueError("Unknown data type")
    return struct_map


def encode_value(dataType, value, types):
    if (dataType == 'string'):
        return encode_solidity_static('bytes32', message_digest(value))
    elif (dataType == 'bytes'):
        return encode_solidity_static('bytes32', message_digest(bytes_from_hex(value)))
    elif (types.get(dataType)):
        return encode_solidity_static('bytes32', message_digest(encode_data(dataType, value, types)))
    elif (dataType.endswith("]")):
        raise ValueError("Arrays not supported yet")
    else:
        return encode_solidity_static(dataType, value)


def encode_data(name, data, definitions):
    return create_schema_hash(name, definitions) + b"".join([ encode_value(schemaType['type'], data[schemaType['name']], definitions) for schemaType in definitions[name] ])


def create_struct_hash(name, data, definitions):
    return message_digest(encode_data(name, data, definitions))


def typed_data_hash(primaryType, domain, message, definitions):
    domainHash = create_struct_hash("EIP712Domain", domain, definitions)
    messageHash = create_struct_hash(primaryType, message, definitions)
    return message_digest(b'\x19' + b'\x01' + domainHash + messageHash)


def parse_typed_data(data, definitions):
    if data.data_type != Struct or len(data.struct) != 3:
        raise ValueError("Invalid typed data")

    domain_struct = data.struct[0]
    if domain_struct.data_type != Struct or domain_struct.name != "domain":
        raise ValueError("Invalid domain object")

    message_struct = data.struct[1]
    if message_struct.data_type != Struct or message_struct.name != "message":
        raise ValueError("Invalid message object")

    primary_type = data.struct[2]
    if primary_type.data_type != Literal or primary_type.name != "primaryType":
        raise ValueError("Invalid primaryType")

    domain_map = build_struct_map(domain_struct.struct)
    message_map = build_struct_map(message_struct.struct)
    result = typed_data_hash(primary_type.literal, domain_map, message_map, definitions)
    print("EIP712 hash", hexlify(result))
    return result
    

async def require_confirm_sign_message(ctx, message):
    text = Text("Sign Typed Data", new_lines=False)
    text.normal(*message)
    await require_confirm(ctx, text)


def create_struct_definition(name, schema):
    schemaTypes = [ (schemaType['type'] + " " + schemaType['name']) for schemaType in schema ]
    return name + "(" + ",".join(schemaTypes) + ")"


def find_dependencies(name, definitions, dependencies):
    if name in dependencies:
        return
    schema = definitions.get(name)
    if not schema:
        return
    dependencies.add(name)
    for schemaType in schema:
        find_dependencies(schemaType['type'], definitions, dependencies)


def create_schema(name, definitions):
    arrayStart = name.find("[")
    cleanName = name if arrayStart < 0 else name[:arrayStart]
    dependencies = set()
    find_dependencies(cleanName, definitions, dependencies)
    dependencies.discard(cleanName)
    dependencyDefinitions = [ create_struct_definition(dependency, definitions[dependency]) for dependency in sorted(dependencies) if definitions.get(dependency) ]
    return create_struct_definition(cleanName, definitions[cleanName]) + "".join(dependencyDefinitions)


def create_schema_hash(name, definitions):
    return encode_solidity_static('bytes32', message_digest(create_schema(name, definitions)))


def bytes32_big(data):
    data_length = len(data)
    if data_length == 32:
        return data
    elif data_length > 32:
        return data[data_length-32:]
    else:
        return bytes(32 - data_length) + data


def bytes32_small(data):
    data_length = len(data)
    if data_length == 32:
        return data
    elif data_length > 32:
        return data[0:data_length-32]
    else:
        return data + bytes(32 - data_length)


def encode_solidity_static(solidity_type, value):
    if solidity_type == 'bool':
        return (1 if value == 'true' else 0).to_bytes(32, 'big')
    
    # Bytes are right padded to 32 bytes
    elif solidity_type.startswith('bytes') and solidity_type != 'bytes':
        if type(value) == bytes:
            return bytes32_small(value)
        return bytes32_small(bytes_from_hex(value))

    # All other values are hex or ints that are left padded to 32 bytes
    elif value[0:2] in ("0x", "0X"):
        return bytes32_big(bytes_from_hex(value))
    return int(value).to_bytes(32, 'big')


def bytes_from_hex(hex_str: str) -> bytes:
    if hex_str[0:2] in ("0x", "0X"):
        if (len(hex_str) == 2):
            return bytes()
        return unhexlify(hex_str[2:])

    elif len(hex_str) == 0:
        return bytes()
    
    else:
        return unhexlify(hex_str)
