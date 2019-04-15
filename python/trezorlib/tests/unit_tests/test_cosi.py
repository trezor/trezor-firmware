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

import hashlib

import pytest

from trezorlib import _ed25519, cosi

RFC8032_VECTORS = (
    (  # test 1
        # privkey
        bytes.fromhex(
            "9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60"
        ),
        # pubkey
        bytes.fromhex(
            "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"
        ),
        # message
        bytes.fromhex(""),
        # signature
        bytes.fromhex(
            "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e06522490155"
            "5fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b"
        ),
    ),
    (  # test 2
        # privkey
        bytes.fromhex(
            "4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb"
        ),
        # pubkey
        bytes.fromhex(
            "3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c"
        ),
        # message
        bytes.fromhex("72"),
        # signature
        bytes.fromhex(
            "92a009a9f0d4cab8720e820b5f642540a2b27b5416503f8fb3762223ebdb69da"
            "085ac1e43e15996e458f3613d0f11d8c387b2eaeb4302aeeb00d291612bb0c00"
        ),
    ),
    (  # test 3
        # privkey
        bytes.fromhex(
            "c5aa8df43f9f837bedb7442f31dcb7b166d38535076f094b85ce3a2e0b4458f7"
        ),
        # pubkey
        bytes.fromhex(
            "fc51cd8e6218a1a38da47ed00230f0580816ed13ba3303ac5deb911548908025"
        ),
        # message
        bytes.fromhex("af82"),
        # signature
        bytes.fromhex(
            "6291d657deec24024827e69c3abe01a30ce548a284743a445e3680d7db5ac3ac"
            "18ff9b538d16f290ae67f760984dc6594a7c15e9716ed28dc027beceea1ec40a"
        ),
    ),
    (  # test SHA(abc)
        # privkey
        bytes.fromhex(
            "833fe62409237b9d62ec77587520911e9a759cec1d19755b7da901b96dca3d42"
        ),
        # pubkey
        bytes.fromhex(
            "ec172b93ad5e563bf4932c70e1245034c35467ef2efd4d64ebf819683467e2bf"
        ),
        # message
        hashlib.sha512(b"abc").digest(),
        # signature
        bytes.fromhex(
            "dc2a4459e7369633a52b1bf277839a00201009a3efbf3ecb69bea2186c26b589"
            "09351fc9ac90b3ecfdfbc7c66431e0303dca179c138ac17ad9bef1177331a704"
        ),
    ),
)

COMBINED_KEY = bytes.fromhex(
    "283967b1c19ff93d2924cdcba95e586547cafef509ea402963ceefe96ccb44f2"
)
GLOBAL_COMMIT = bytes.fromhex(
    "75bd5806c6366e0374a1c6e020c53feb0791d6cc07560d27d8c158f886ecf389"
)


@pytest.mark.parametrize("privkey, pubkey, message, signature", RFC8032_VECTORS)
def test_single_eddsa_vector(privkey, pubkey, message, signature):
    my_pubkey = cosi.pubkey_from_privkey(privkey)
    assert my_pubkey == pubkey
    try:
        cosi.verify(signature, message, pubkey)
    except ValueError:
        pytest.fail("Signature does not verify.")

    fake_signature = signature[:37] + b"\xf0" + signature[38:]
    with pytest.raises(_ed25519.SignatureMismatch):
        cosi.verify(fake_signature, message, pubkey)


def test_combine_keys():
    pubkeys = [pubkey for _, pubkey, _, _ in RFC8032_VECTORS]
    assert cosi.combine_keys(pubkeys) == COMBINED_KEY

    Rs = [
        cosi.get_nonce(privkey, message)[1]
        for privkey, _, message, _ in RFC8032_VECTORS
    ]
    assert cosi.combine_keys(Rs) == GLOBAL_COMMIT


@pytest.mark.parametrize("keyset", [(0,), (0, 1), (0, 1, 2), (0, 1, 2, 3), (1, 3)])
def test_cosi_combination(keyset):
    message = hashlib.sha512(b"You all have to sign this.").digest()
    selection = [RFC8032_VECTORS[i] for i in keyset]

    # zip(*iterable) turns a list of tuples to a tuple of lists
    privkeys, pubkeys, _, _ = zip(*selection)
    nonce_pairs = [cosi.get_nonce(pk, message) for pk in privkeys]
    nonces, commits = zip(*nonce_pairs)

    # calculate global pubkey and commitment
    global_pk = cosi.combine_keys(pubkeys)
    global_commit = cosi.combine_keys(commits)

    # generate individual signatures
    signatures = [
        cosi.sign_with_privkey(message, privkey, global_pk, nonce, global_commit)
        for privkey, nonce in zip(privkeys, nonces)
    ]

    # combine signatures
    global_sig = cosi.combine_sig(global_commit, signatures)

    try:
        cosi.verify(global_sig, message, global_pk)
    except Exception:
        pytest.fail("Failed to validate global signature")


def test_m_of_n():
    privkeys, pubkeys, _, _ = zip(*RFC8032_VECTORS)
    message = hashlib.sha512(b"My hovercraft is full of eels!").digest()

    signer_ids = 0, 2, 3
    signers = [privkeys[i] for i in signer_ids]
    signer_pubkeys = [pubkeys[i] for i in signer_ids]
    sigmask = sum(1 << i for i in signer_ids)

    # generate multisignature
    nonce_pairs = [cosi.get_nonce(pk, message) for pk in signers]
    nonces, commits = zip(*nonce_pairs)
    global_pk = cosi.combine_keys(signer_pubkeys)
    global_commit = cosi.combine_keys(commits)
    signatures = [
        cosi.sign_with_privkey(message, privkey, global_pk, nonce, global_commit)
        for privkey, nonce in zip(signers, nonces)
    ]
    global_sig = cosi.combine_sig(global_commit, signatures)

    try:
        # this is what we are actually doing
        cosi.verify_m_of_n(global_sig, message, 3, 4, sigmask, pubkeys)
        # we can require less signers too
        cosi.verify_m_of_n(global_sig, message, 1, 4, sigmask, pubkeys)
    except Exception:
        pytest.fail("Failed to validate by sigmask")

    # and now for various ways that should fail
    with pytest.raises(ValueError) as e:
        cosi.verify_m_of_n(global_sig, message, 4, 4, sigmask, pubkeys)
    assert "Not enough signers" in e.value.args[0]

    with pytest.raises(_ed25519.SignatureMismatch):
        # when N < number of possible signers, the topmost signers will be ignored
        cosi.verify_m_of_n(global_sig, message, 2, 3, sigmask, pubkeys)

    with pytest.raises(_ed25519.SignatureMismatch):
        # wrong sigmask
        cosi.verify_m_of_n(global_sig, message, 1, 4, 5, pubkeys)

    with pytest.raises(ValueError):
        # can't use "0 of N" scheme
        cosi.verify_m_of_n(global_sig, message, 0, 4, sigmask, pubkeys)
