from micropython import const

from trezor import wire
from trezor.crypto import base58, chacha20poly1305, crc, hashlib, pbkdf2

from . import cbor

from apps.common import HARDENED, seed


def validate_derivation_path(path: list):
    if len(path) < 2 or len(path) > 5:
        raise wire.ProcessError("Derivation path must be composed from 2-5 indices")

    if path[0] != HARDENED | 44 or path[1] != HARDENED | 1815:
        raise wire.ProcessError("This is not cardano derivation path")

    return path


def _derive_hd_passphrase(node) -> bytes:
    iterations = const(500)
    length = const(32)
    passwd = seed.remove_ed25519_prefix(node.public_key()) + node.chain_code()
    x = pbkdf2("hmac-sha512", passwd, b"address-hashing", iterations)
    return x.key()[:length]


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


def _encrypt_derivation_path(path: list, hd_passphrase: bytes) -> bytes:
    serialized = cbor.encode(cbor.IndefiniteLengthArray(path))
    ctx = chacha20poly1305(hd_passphrase, b"serokellfore")
    data = ctx.encrypt(serialized)
    tag = ctx.finish()
    return data + tag


def derive_address_and_node(root_node, path: list):
    validate_derivation_path(path)

    derived_node = root_node.clone()

    # this means empty derivation path m/44'/1815'
    if len(path) == 2:
        address_payload = None
        address_attributes = {}
    else:
        if len(path) == 5:
            p = [path[2], path[4]]
        else:
            p = [path[2]]
        for indice in p:
            derived_node.derive_cardano(indice)

        hd_passphrase = _derive_hd_passphrase(root_node)
        address_payload = _encrypt_derivation_path(p, hd_passphrase)
        address_attributes = {1: cbor.encode(address_payload)}

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
