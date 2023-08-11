from pathlib import Path
from typing import Sequence

from . import cosi

# NOTE: the whole file taken from definitions repository

HERE = Path(__file__).parent

PRIVATE_KEYS_DEV = [byte * 32 for byte in (b"\xdd", b"\xde", b"\xdf")]


def sign_with_dev_keys(hash: bytes) -> bytes:
    """Sign the hash with the development private key."""
    return _sign_with_privkeys(hash, PRIVATE_KEYS_DEV)


def _sign_with_privkeys(digest: bytes, privkeys: Sequence[bytes]) -> bytes:
    """Locally produce a CoSi signature."""
    pubkeys = [cosi.pubkey_from_privkey(sk) for sk in privkeys]
    nonces = [cosi.get_nonce(sk, digest, i) for i, sk in enumerate(privkeys)]

    global_pk = cosi.combine_keys(pubkeys)
    global_R = cosi.combine_keys(R for _, R in nonces)

    sigs = [
        cosi.sign_with_privkey(digest, sk, global_pk, r, global_R)
        for sk, (r, _) in zip(privkeys, nonces)
    ]

    return cosi.combine_sig(global_R, sigs)
