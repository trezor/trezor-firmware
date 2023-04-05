# This file is part of the Trezor project.
#
# Copyright (C) 2012-2019 SatoshiLabs and contributors
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

from hashlib import sha256

import pytest

from trezorlib import cosi
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import H_, Address, parse_path

DIGEST = sha256(b"this is not a pipe").digest()


def test_cosi_pubkey(client: Client):
    c0 = cosi.commit(client, parse_path("m/10018h/0h"))
    c1 = cosi.commit(client, parse_path("m/10018h/1h"))
    c2 = cosi.commit(client, parse_path("m/10018h/2h"))

    assert c0.pubkey != c1.pubkey
    assert c0.pubkey != c2.pubkey
    assert c1.pubkey != c2.pubkey


def test_cosi_nonce(client: Client):
    # The nonce/commitment must change after each signing.
    c0 = cosi.commit(client, parse_path("m/10018h/0h"))
    cosi.sign(client, parse_path("m/10018h/0h"), DIGEST, c0.commitment, c0.pubkey)
    c1 = cosi.commit(client, parse_path("m/10018h/0h"))
    assert c0.commitment != c1.commitment


def test_cosi_sign1(client: Client):
    # Single party signature.
    commit = cosi.commit(client, parse_path("m/10018h/0h"))
    sig = cosi.sign(
        client, parse_path("m/10018h/0h"), DIGEST, commit.commitment, commit.pubkey
    )
    signature = cosi.combine_sig(commit.commitment, [sig.signature])
    cosi.verify_combined(signature, DIGEST, commit.pubkey)


def test_cosi_sign2(client: Client):
    # Two party signature.
    remote_commit = cosi.commit(client, parse_path("m/10018h/1h"))

    local_privkey = sha256(b"private key").digest()[:32]
    local_pubkey = cosi.pubkey_from_privkey(local_privkey)
    local_nonce, local_commitment = cosi.get_nonce(local_privkey, DIGEST, 42)

    global_pk = cosi.combine_keys([remote_commit.pubkey, local_pubkey])
    global_R = cosi.combine_keys([remote_commit.commitment, local_commitment])

    remote_sig = cosi.sign(
        client, parse_path("m/10018h/1h"), DIGEST, global_R, global_pk
    )
    local_sig = cosi.sign_with_privkey(
        DIGEST, local_privkey, global_pk, local_nonce, global_R
    )
    signature = cosi.combine_sig(global_R, [remote_sig.signature, local_sig])

    cosi.verify_combined(signature, DIGEST, global_pk)


def test_cosi_sign3(client: Client):
    # Three party signature.
    remote_commit = cosi.commit(client, parse_path("m/10018h/2h"))

    local_privkey1 = sha256(b"private key").digest()[:32]
    local_pubkey1 = cosi.pubkey_from_privkey(local_privkey1)
    local_nonce1, local_commitment1 = cosi.get_nonce(local_privkey1, DIGEST, 42)

    local_privkey2 = sha256(b"private key").digest()[:32]
    local_pubkey2 = cosi.pubkey_from_privkey(local_privkey2)
    local_nonce2, local_commitment2 = cosi.get_nonce(local_privkey2, DIGEST, 42)

    global_pk = cosi.combine_keys([remote_commit.pubkey, local_pubkey1, local_pubkey2])
    global_R = cosi.combine_keys(
        [remote_commit.commitment, local_commitment1, local_commitment2]
    )

    remote_sig = cosi.sign(
        client, parse_path("m/10018h/2h"), DIGEST, global_R, global_pk
    )
    local_sig1 = cosi.sign_with_privkey(
        DIGEST, local_privkey1, global_pk, local_nonce1, global_R
    )
    local_sig2 = cosi.sign_with_privkey(
        DIGEST, local_privkey2, global_pk, local_nonce2, global_R
    )
    signature = cosi.combine_sig(
        global_R, [remote_sig.signature, local_sig1, local_sig2]
    )

    cosi.verify_combined(signature, DIGEST, global_pk)


@pytest.mark.skip_t1
def test_cosi_different_key(client: Client):
    with pytest.raises(TrezorFailure):
        commit = cosi.commit(client, parse_path("m/10018h/0h"))
        cosi.sign(
            client, parse_path("m/10018h/1h"), DIGEST, commit.commitment, commit.pubkey
        )


@pytest.mark.parametrize(
    "model, image_type",
    (
        (b"T1B1", 0),
        (b"T2T1", 0),
        (b"T2B1", 0),
        (b"T3W1", 0),
        (b"\xfe\xfe\xfe\xfe", 0),
        (b"\x00", 0),
        (b"\x00", 3),
        (b"dog", 0),
        (b"42", 0),
        (b"T2B1", 1),
        (b"T2B1", 2),
        (b"T2B1", 3),
    ),
)
@pytest.mark.skip_t1
def test_slip26_paths(client: Client, model: bytes, image_type: int):
    slip26_model = int.from_bytes(model, "little")
    path = Address([H_(10026), H_(slip26_model), H_(image_type), H_(0)])
    commit = cosi.commit(client, path)
    cosi.sign(client, path, DIGEST, commit.commitment, commit.pubkey)


@pytest.mark.parametrize(
    "path",
    (
        "m/44h/0h/0h/0/0",
        "m/44h/60h/0h/0/0",
        "m/44h/60h/1h",
        "m/84h/60h/1h/0",
        "m/1",
        "m/10018/0",
    ),
)
def test_invalid_path(client: Client, path: str) -> None:
    with pytest.raises(TrezorFailure, match="DataError"):
        cosi.commit(client, parse_path(path))
