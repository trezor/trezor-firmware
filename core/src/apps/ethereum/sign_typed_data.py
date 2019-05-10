from ubinascii import unhexlify, hexlify

from trezor.crypto.curve import secp256k1
from trezor.crypto.hashlib import sha3_256
from trezor.messages import ButtonRequestType
from trezor.messages.EthereumTypedDataRequest import EthereumTypedDataRequest
from trezor.messages.MessageType import EthereumTypedDataAck
from trezor.ui.text import Text
from trezor.utils import HashWriter

from apps.common import paths
from apps.common.confirm import require_confirm, confirm
from apps.common.signverify import split_message
from apps.ethereum import CURVE, address
from apps.ethereum.layout import split_data


def message_digest(message):
    h = HashWriter(sha3_256(keccak=True))
    h.extend(message)
    return h.get_digest()


async def sign_typed_data(ctx, msg, keychain):
    data_hash = message_digest("debug") # TODO remove try except
    try:
        data_hash = await generate_typed_data_hash(ctx)
    except Exception as e:
        print("error", type(e), e)

    await paths.validate_path(
        ctx, address.validate_full_path, keychain, msg.address_n, CURVE
    )

    node = keychain.derive(msg.address_n)
    signature = secp256k1.sign(
        node.private_key(),
        data_hash,
        False,
        secp256k1.CANONICAL_SIG_ETHEREUM,
    )

    sig = EthereumTypedDataRequest()
    sig.address = address.address_from_bytes(node.ethereum_pubkeyhash())
    sig.signature = signature[1:] + bytearray([signature[0]])
    return sig


async def generate_typed_data_hash(ctx):
    domain = await request_member(ctx, [0])

    #await require_confirm(ctx, Text("Confirm domain"))

    if (domain.member_type != "EIP712Domain"):
        raise ValueError("EIP712 domain not provided")
    _, domainHash = await create_struct_hash(ctx, [0], domain, True)

    text = Text("Show details", new_lines=False)
    text.normal(ctx, "Show message details that are signed?")
    #show_message = await confirm(ctx, text)

    # TODO some checks here maybe
    message = await request_member(ctx, [1])
    _, messageHash = await create_struct_hash(ctx, [1], message, True)

    typed_data_hash = message_digest(b'\x19' + b'\x01' + domainHash + messageHash)
    return typed_data_hash


async def create_struct_hash(ctx, struct_path, struct, confirm_member):
    dependencies = {}
    encoded = []
    value_defs = []
    for member_index in range(struct.num_members):
        value_name, value_type, value_dep, encoded_value = await encode_value(ctx, struct_path + [member_index], confirm_member)
        if value_dep:
            dependencies.update(value_dep)
        encoded.append(encoded_value)
        value_defs.append(value_type + " " + value_name)
    struct_desc = struct.member_type + "(" + ",".join(value_defs) + ")"
    for dependency in sorted(dependencies):
        struct_desc += dependencies[dependency]
    dependencies[struct.member_type] = struct_desc
    schema_hash = encode_solidity_static('bytes32', message_digest(struct_desc))
    return dependencies, message_digest(schema_hash + b"".join(encoded))


async def encode_value(ctx, member_path, confirm_member):
    member = await request_member(ctx, member_path)

    text = Text(member.member_name, new_lines=False)
    text.normal(*member.member_type)
    text.br()

    dependencies = None
    encoded_value = None
    if (member.member_value is None):
        dependencies, encoded_value = await create_struct_hash(ctx, member_path, member, confirm_member)
    elif (member.member_type == 'string'):
        encoded_value = encode_solidity_static('bytes32', message_digest(member.member_value))
        text.mono(*member.member_value)
    elif (member.member_type == 'bytes'):
        rencoded_value = encode_solidity_static('bytes32', message_digest(bytes_from_hex(member.member_value)))
        text.mono(*member.member_value)
    elif (member.member_type.endswith("]")):
        raise ValueError("Arrays not supported yet")
    else:
        encoded_value = encode_solidity_static(member.member_type, member.member_value)
        text.mono(*member.member_value)

    #if confirm_member:
        #await require_confirm(ctx, text)
    return member.member_name, member.member_type, dependencies, encoded_value
    

async def request_member(ctx, member_path):
    req = EthereumTypedDataRequest()
    req.member_path = member_path
    return await ctx.call(req, EthereumTypedDataAck)


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
