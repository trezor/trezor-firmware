# This file is part of the Trezor project.
#
# Copyright (C) 2012-2022 SatoshiLabs and contributors
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

from typing import TYPE_CHECKING, Optional

from . import messages

if TYPE_CHECKING:
    from .tools import Address
    from .transport.session import Session


def get_entropy(session: "Session", size: int) -> bytes:
    return session.call(messages.GetEntropy(size=size), expect=messages.Entropy).entropy


def sign_identity(
    session: "Session",
    identity: messages.IdentityType,
    challenge_hidden: bytes,
    challenge_visual: str,
    ecdsa_curve_name: Optional[str] = None,
) -> messages.SignedIdentity:
    return session.call(
        messages.SignIdentity(
            identity=identity,
            challenge_hidden=challenge_hidden,
            challenge_visual=challenge_visual,
            ecdsa_curve_name=ecdsa_curve_name,
        ),
        expect=messages.SignedIdentity,
    )


def get_ecdh_session_key(
    session: "Session",
    identity: messages.IdentityType,
    peer_public_key: bytes,
    ecdsa_curve_name: Optional[str] = None,
) -> messages.ECDHSessionKey:
    return session.call(
        messages.GetECDHSessionKey(
            identity=identity,
            peer_public_key=peer_public_key,
            ecdsa_curve_name=ecdsa_curve_name,
        ),
        expect=messages.ECDHSessionKey,
    )


def encrypt_keyvalue(
    session: "Session",
    n: "Address",
    key: str,
    value: bytes,
    ask_on_encrypt: bool = True,
    ask_on_decrypt: bool = True,
    iv: bytes = b"",
) -> bytes:
    return session.call(
        messages.CipherKeyValue(
            address_n=n,
            key=key,
            value=value,
            encrypt=True,
            ask_on_encrypt=ask_on_encrypt,
            ask_on_decrypt=ask_on_decrypt,
            iv=iv,
        ),
        expect=messages.CipheredKeyValue,
    ).value


def decrypt_keyvalue(
    session: "Session",
    n: "Address",
    key: str,
    value: bytes,
    ask_on_encrypt: bool = True,
    ask_on_decrypt: bool = True,
    iv: bytes = b"",
) -> bytes:
    return session.call(
        messages.CipherKeyValue(
            address_n=n,
            key=key,
            value=value,
            encrypt=False,
            ask_on_encrypt=ask_on_encrypt,
            ask_on_decrypt=ask_on_decrypt,
            iv=iv,
        ),
        expect=messages.CipheredKeyValue,
    ).value


def get_nonce(session: "Session") -> bytes:
    return session.call(messages.GetNonce(), expect=messages.Nonce).nonce
