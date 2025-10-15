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

import typing as t
from dataclasses import dataclass
from hashlib import sha256

from cryptography.hazmat.primitives.asymmetric import x25519
from typing_extensions import Self

if t.TYPE_CHECKING:
    from noise.state import HandshakeState


class Credential(t.Protocol):
    @property
    def trezor_pubkey(self) -> bytes: ...
    @property
    def host_privkey(self) -> bytes: ...
    @property
    def credential(self) -> bytes: ...


class TrezorPublicKeys(t.NamedTuple):
    ephemeral: bytes
    static_masked: bytes

    @classmethod
    def from_noise(cls, handshake_state: HandshakeState) -> Self:
        return cls(
            ephemeral=handshake_state.re.public_bytes,
            static_masked=handshake_state.rs.public_bytes,
        )


@dataclass(frozen=True)
class StaticCredential:
    trezor_pubkey: bytes
    host_privkey: bytes
    credential: bytes


def matches(credential: Credential, trezor_public_keys: TrezorPublicKeys) -> bool:
    mask = sha256(credential.trezor_pubkey + trezor_public_keys.ephemeral).digest()
    mask_as_privkey = x25519.X25519PrivateKey.from_private_bytes(mask)
    pubkey = x25519.X25519PublicKey.from_public_bytes(credential.trezor_pubkey)
    shared_secret = mask_as_privkey.exchange(pubkey)
    return shared_secret == trezor_public_keys.static_masked


def find_credential(
    credentials: t.Iterable[Credential],
    trezor_public_keys: TrezorPublicKeys,
) -> Credential | None:
    for credential in credentials:
        if matches(credential, trezor_public_keys):
            return credential
    return None
