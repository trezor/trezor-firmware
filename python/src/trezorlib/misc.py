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

from typing import TYPE_CHECKING, Optional

from . import messages
from .tools import workflow

if TYPE_CHECKING:
    from .client import Session
    from .tools import Address


@workflow(capability=messages.Capability.Crypto)
def get_entropy(session: "Session", size: int) -> bytes:
    return session.call(messages.GetEntropy(size=size), expect=messages.Entropy).entropy


@workflow(capability=messages.Capability.Crypto)
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


@workflow(capability=messages.Capability.Crypto)
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


@workflow(capability=messages.Capability.Crypto)
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


@workflow(capability=messages.Capability.Crypto)
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


@workflow(capability=messages.Capability.Crypto)
def get_bip85_entropy(
    session: "Session",
    n: "Address",
    show_display: bool = False,
    on_device_only: bool = False,
) -> messages.Bip85Entropy:
    """Derive deterministic entropy according to BIP-85.

    `n` is the full BIP-85 derivation path, e.g. m/83696968'/39'/0'/12'/0' for a
    12-word English BIP-39 mnemonic. If `on_device_only` is set, the derived secret
    is only shown on the device and the returned message is empty.
    """
    return session.call(
        messages.GetBip85Entropy(
            address_n=n,
            show_display=show_display,
            on_device_only=on_device_only,
        ),
        expect=messages.Bip85Entropy,
    )


@workflow(capability=messages.Capability.Crypto)
def get_nonce(session: "Session") -> bytes:
    return session.call(messages.GetNonce(), expect=messages.Nonce).nonce


@workflow()
def payment_notification(
    session: "Session", payment_req: messages.PaymentRequest
) -> None:
    session.call(
        messages.PaymentNotification(payment_req=payment_req), expect=messages.Success
    )
