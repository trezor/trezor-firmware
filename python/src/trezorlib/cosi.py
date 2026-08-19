# This file is part of the Trezor project.
#
# Copyright (C) SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

from __future__ import annotations

import os
import typing as t
from functools import reduce

from . import _ed25519

# XXX, these could be NewType's, but that would infect users of the cosi module with these types as well.
# Unsure if we want that.
Ed25519PrivateKey = bytes
Ed25519PublicPoint = bytes
Ed25519Signature = bytes


def combine_keys(pks: t.Iterable[Ed25519PublicPoint]) -> Ed25519PublicPoint:
    """Combine a list of Ed25519 points into a "global" CoSi key."""
    P = [_ed25519.decodepoint(pk) for pk in pks]
    combine = reduce(_ed25519.edwards_add, P)
    return Ed25519PublicPoint(_ed25519.encodepoint(combine))


def combine_sig(
    global_R: Ed25519PublicPoint, sigs: t.Iterable[Ed25519Signature]
) -> Ed25519Signature:
    """Combine a list of signatures into a single CoSi signature."""
    S = [_ed25519.decodeint(si) for si in sigs]
    s = sum(S) % _ed25519.l
    sig = global_R + _ed25519.encodeint(s)
    return Ed25519Signature(sig)


def get_nonce() -> tuple[int, Ed25519PublicPoint]:
    """Generate a random CoSi nonce.

    Returns both the private point `r` and the partial signature `R`.
    `r` is returned for performance reasons: :func:`sign_with_privkey`
    takes it as its `nonce` argument so that it doesn't repeat the `get_nonce` call.

    `R` should be combined with other partial signatures through :func:`combine_keys`
    to obtain a "global commitment".
    """
    # r = random512 mod l
    # R = rB
    # Same construction as ed25519_cosi_commit() in crypto/ed25519-donna/ed25519.c
    r = _ed25519.decodeint(os.urandom(64)) % _ed25519.l
    R = _ed25519.scalarmult(_ed25519.B, r)
    return r, Ed25519PublicPoint(_ed25519.encodepoint(R))


def _get_deterministic_nonce(
    sk: Ed25519PrivateKey, data: bytes, ctr: int = 0
) -> tuple[int, Ed25519PublicPoint]:
    """Calculate a deterministic CoSi nonce for given data.
    This differs from Ed25519 deterministic nonces in that there is a counter appended
    at end.

    DANGER: only use this with private keys that are public knowledge, i.e. the
    development keys. The nonce depends solely on (sk, data, ctr), but the CoSi
    challenge depends on the global commitment, which is not known at the time the
    nonce is generated and which is chosen by the coordinator. If the same key ever
    signs the same data in two sessions whose global commitments differ, the two
    partial signatures reveal the private scalar.

    Use :func:`get_nonce` for anything else. See also :func:`sign_with_privkeys`.

    Returns the same pair as :func:`get_nonce`.
    """
    # r = hash(hash(sk)[b .. 2b] + M + ctr)
    # R = rB
    h = _ed25519.H(sk)
    bytesize = _ed25519.b // 8
    assert len(h) == bytesize * 2
    r = _ed25519.Hint(h[bytesize:] + data + ctr.to_bytes(4, "big"))
    R = _ed25519.scalarmult(_ed25519.B, r)
    return r, Ed25519PublicPoint(_ed25519.encodepoint(R))


def verify_combined(
    signature: Ed25519Signature, digest: bytes, pub_key: Ed25519PublicPoint
) -> None:
    """Verify Ed25519 signature. Raise exception if the signature is invalid.

    A CoSi combined signature is equivalent to a plain Ed25519 signature with a public
    key that is a combination of the cosigners' public keys. This function takes the
    combined public key and performs simple Ed25519 verification.
    """
    # XXX this *might* change to bool function
    _ed25519.checkvalid(signature, digest, pub_key)


def verify(
    signature: Ed25519Signature,
    digest: bytes,
    sigs_required: int,
    keys: t.Sequence[Ed25519PublicPoint],
    mask: int,
) -> None:
    """Verify a CoSi multi-signature. Raise exception if the signature is invalid.

    This function verifies a M-of-N signature scheme. The arguments are:
    - the minimum number M of signatures required
    - public keys of all N possible cosigners
    - a bitmask specifying which of the N cosigners have produced the signature.

    The verification checks that the mask specifies at least M cosigners, then combines
    the selected public keys and verifies the signature against the combined key.
    """
    if sigs_required < 1:
        raise ValueError("At least one signer must be specified.")
    if mask.bit_length() > len(keys):
        raise ValueError("Sigmask specifies more public keys than provided.")
    selected_keys = [key for i, key in enumerate(keys) if mask & (1 << i)]
    if len(selected_keys) < sigs_required:
        raise _ed25519.SignatureMismatch("Insufficient number of signatures.")
    global_pk = combine_keys(selected_keys)
    verify_combined(signature, digest, global_pk)


def pubkey_from_privkey(privkey: Ed25519PrivateKey) -> Ed25519PublicPoint:
    """Interpret 32 bytes of data as an Ed25519 private key.
    Calculate and return the corresponding public key.
    """
    return Ed25519PublicPoint(_ed25519.publickey_unsafe(privkey))


def sign_with_privkey(
    digest: bytes,
    privkey: Ed25519PrivateKey,
    global_pubkey: Ed25519PublicPoint,
    nonce: int,
    global_commit: Ed25519PublicPoint,
) -> Ed25519Signature:
    """Create a CoSi signature of `digest` with the supplied private key.
    This function needs to know the global public key and global commitment.
    """
    h = _ed25519.H(privkey)
    a = _ed25519.decodecoord(h)

    S = (nonce + _ed25519.Hint(global_commit + global_pubkey + digest) * a) % _ed25519.l
    return Ed25519Signature(_ed25519.encodeint(S))


def sign_with_privkeys(
    digest: bytes, privkeys: t.Sequence[bytes], *, deterministic: bool = False
) -> bytes:
    """Locally produce a CoSi signature from a list of private keys.

    Nonces are random by default. With `deterministic=True` the resulting signature
    is a pure function of `(digest, privkeys)`, which is required where the signature
    bytes are committed to a repository or compared across builds. It is only
    safe for keys that are public knowledge, such as the development keys.
    See :func:`_get_deterministic_nonce`.
    """
    pubkeys = [pubkey_from_privkey(sk) for sk in privkeys]
    if deterministic:
        nonces = [
            _get_deterministic_nonce(sk, digest, i) for i, sk in enumerate(privkeys)
        ]
    else:
        nonces = [get_nonce() for _ in privkeys]

    global_pk = combine_keys(pubkeys)
    global_R = combine_keys(R for _, R in nonces)

    sigs = [
        sign_with_privkey(digest, sk, global_pk, r, global_R)
        for sk, (r, _) in zip(privkeys, nonces)
    ]

    return combine_sig(global_R, sigs)
