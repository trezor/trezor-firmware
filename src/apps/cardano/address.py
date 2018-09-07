from micropython import const

from trezor import wire
from trezor.crypto import base58, crc, hashlib

from . import cbor

from apps.common import HARDENED, seed


def validate_derivation_path(path: list):
    if len(path) < 2 or len(path) > 5:
        raise wire.ProcessError("Derivation path must be composed from 2-5 indices")

    if path[0] != HARDENED | 44 or path[1] != HARDENED | 1815:
        raise wire.ProcessError("This is not cardano derivation path")

    return path


def _address_hash(data) -> bytes:
    data = cbor.encode(data)
    data = hashlib.sha3_256(data).digest()
    res = hashlib.blake2b(data=data, outlen=28).digest()
    return res


def _get_address_root(node, payload):
    extpubkey = seed.remove_ed25519_prefix(node.public_key()) + node.chain_code()
    if payload:
        payload = {1: cbor.encode(payload)}
    else:
        payload = {}
    return _address_hash([0, [0, extpubkey], payload])


def derive_address_and_node(root_node, path: list):
    validate_derivation_path(path)

    derived_node = root_node.clone()

    address_payload = None
    address_attributes = {}

    for indice in path:
        derived_node.derive_cardano(indice)

    address_root = _get_address_root(derived_node, address_payload)
    address_type = 0
    address_data = [address_root, address_attributes, address_type]
    address_data_encoded = cbor.encode(address_data)

    address = base58.encode(
        cbor.encode(
            [cbor.Tagged(24, address_data_encoded), crc.crc32(address_data_encoded)]
        )
    )
    return (address, derived_node)


def _break_address_n_to_lines(address_n: list) -> list:
    def path_item(i: int):
        if i & HARDENED:
            return str(i ^ HARDENED) + "'"
        else:
            return str(i)

    lines = []
    path_str = "m/" + "/".join([path_item(i) for i in address_n])

    per_line = const(17)
    while len(path_str) > per_line:
        i = path_str[:per_line].rfind("/")
        lines.append(path_str[:i])
        path_str = path_str[i:]
    lines.append(path_str)

    return lines
