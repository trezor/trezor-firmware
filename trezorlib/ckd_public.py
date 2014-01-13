import struct
import hmac
import hashlib
from ecdsa.util import string_to_number
from ecdsa.curves import SECP256k1

import messages_pb2 as proto

# FIXME, this isn't finished yet

PRIME_DERIVATION_FLAG = 0x80000000

def is_prime(n):
    return (bool)(n & PRIME_DERIVATION_FLAG)

def hash_160(public_key):
    md = hashlib.new('ripemd160')
    md.update(hashlib.sha256(public_key).digest())
    return md.digest()

def fingerprint(pubkey):
    return string_to_number(hash_160(pubkey)[:4])

def get_subnode(node, i):
    # Public Child key derivation (CKD) algorithm of BIP32
    i_as_bytes = struct.pack(">L", i)

    if is_prime(i):
        raise Exception("Prime derivation not supported")

    # Public derivation
    data = node.public_key + i_as_bytes

    I64 = hmac.HMAC(key=node.chain_code, msg=data, digestmod=hashlib.sha512).digest()
    I_left_as_exponent = string_to_number(I64[:32])

    node_out = proto.HDNodeType()
    node_out.version = node.version
    node_out.depth = node.depth + 1
    node_out.child_num = i
    node_out.chain_code = I64[32:]
    node_out.fingerprint = fingerprint(node.public_key)

    # FIXME
    # node_out.public_key = cls._get_pubkey(node_out.private_key)
    # x, y = self.public_pair
    # the_point = I_left_as_exponent * ecdsa.generator_secp256k1 + ecdsa.Point(ecdsa.generator_secp256k1.curve(), x, y, SECP256k1.generator.order())

    return node_out
