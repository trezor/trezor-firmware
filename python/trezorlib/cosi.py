# This file is part of the Trezor project.
#
# Copyright (C) 2012-2018 SatoshiLabs and contributors
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

from functools import reduce
from typing import Iterable, List, Tuple

from . import _ed25519, messages
from .tools import expect

# XXX, these could be NewType's, but that would infect users of the cosi module with these types as well.
# Unsure if we want that.
Ed25519PrivateKey = bytes
Ed25519PublicPoint = bytes
Ed25519Signature = bytes


def combine_keys(pks: Iterable[Ed25519PublicPoint]) -> Ed25519PublicPoint:
    """Combine a list of Ed25519 points into a "global" CoSi key."""
    P = [_ed25519.decodepoint(pk) for pk in pks]
    combine = reduce(_ed25519.edwards_add, P)
    return Ed25519PublicPoint(_ed25519.encodepoint(combine))


def combine_sig(
    global_R: Ed25519PublicPoint, sigs: Iterable[Ed25519Signature]
) -> Ed25519Signature:
    """Combine a list of signatures into a single CoSi signature."""
    S = [_ed25519.decodeint(si) for si in sigs]
    s = sum(S) % _ed25519.l
    sig = global_R + _ed25519.encodeint(s)
    return Ed25519Signature(sig)


def get_nonce(
    sk: Ed25519PrivateKey, data: bytes, ctr: int = 0
) -> Tuple[int, Ed25519PublicPoint]:
    """Calculate CoSi nonces for given data.
    These differ from Ed25519 deterministic nonces in that there is a counter appended at end.

    Returns both the private point `r` and the partial signature `R`.
    `r` is returned for performance reasons: :func:`sign_with_privkey`
    takes it as its `nonce` argument so that it doesn't repeat the `get_nonce` call.

    `R` should be combined with other partial signatures through :func:`combine_keys`
    to obtain a "global commitment".
    """
    # r = hash(hash(sk)[b .. 2b] + M + ctr)
    # R = rB
    h = _ed25519.H(sk)
    bytesize = _ed25519.b // 8
    assert len(h) == bytesize * 2
    r = _ed25519.Hint(h[bytesize:] + data + ctr.to_bytes(4, "big"))
    R = _ed25519.scalarmult(_ed25519.B, r)
    return r, Ed25519PublicPoint(_ed25519.encodepoint(R))


def verify(
    signature: Ed25519Signature, digest: bytes, pub_key: Ed25519PublicPoint
) -> None:
    """Verify Ed25519 signature. Raise exception if the signature is invalid."""
    # XXX this *might* change to bool function
    _ed25519.checkvalid(signature, digest, pub_key)


def verify_m_of_n(
    signature: Ed25519Signature,
    digest: bytes,
    m: int,
    n: int,
    mask: int,
    keys: List[Ed25519PublicPoint],
) -> None:
    if m < 1:
        raise ValueError("At least 1 signer must be specified")
    selected_keys = [keys[i] for i in range(n) if mask & (1 << i)]
    if len(selected_keys) < m:
        raise ValueError(
            "Not enough signers ({} required, {} found)".format(m, len(selected_keys))
        )
    global_pk = combine_keys(selected_keys)
    return verify(signature, digest, global_pk)


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


# ====== Client functions ====== #


@expect(messages.CosiCommitment)
def commit(client, n, data):
    return client.call(messages.CosiCommit(address_n=n, data=data))


@expect(messages.CosiSignature)
def sign(client, n, data, global_commitment, global_pubkey):
    return client.call(
        messages.CosiSign(
            address_n=n,
            data=data,
            global_commitment=global_commitment,
            global_pubkey=global_pubkey,
        )
    )
