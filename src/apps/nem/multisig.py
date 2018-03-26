
from .helpers import *
from .writers import *
from trezor.crypto import hashlib


def nem_transaction_create_multisig(network: int, timestamp: int, signer_public_key: bytes,
                                    fee: int, deadline: int, inner: bytes):

    w = nem_transaction_write_common(NEM_TRANSACTION_TYPE_MULTISIG,
                                     nem_get_version(network),
                                     timestamp,
                                     signer_public_key,
                                     fee,
                                     deadline)

    write_bytes_with_length(w, bytearray(inner))

    return w


def nem_transaction_create_multisig_signature(network: int, timestamp: int, signer_public_key: bytes,
                                              fee: int, deadline: int, inner: bytes, address: str):

    w = nem_transaction_write_common(NEM_TRANSACTION_TYPE_MULTISIG_SIGNATURE,
                                     nem_get_version(network),
                                     timestamp,
                                     signer_public_key,
                                     fee,
                                     deadline)

    hash = hashlib.sha3_256(inner).digest(True)

    write_uint32(w, 4 + len(hash))
    write_bytes_with_length(w, hash)
    write_bytes_with_length(w, address)

    return w
