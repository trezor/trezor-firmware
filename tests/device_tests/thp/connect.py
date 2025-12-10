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

import pytest

from trezorlib import messages
from trezorlib.debuglink import TrezorTestContext
from trezorlib.thp.channel import Channel
from trezorlib.thp.client import TrezorClientThp
from trezorlib.thp.credentials import Credential, TrezorPublicKeys
from trezorlib.thp.exceptions import ThpError
from trezorlib.thp.pairing import Nfc, PairingController


class StaticCredential(Credential):
    def matches(self, trezor_public_keys: TrezorPublicKeys) -> bool:
        return True


def prepare_channel_for_handshake(test_ctx: TrezorTestContext) -> None:
    """Create a fresh channel instance before the handshake phase."""
    assert isinstance(test_ctx.client, TrezorClientThp)
    test_ctx.channel = Channel.allocate(test_ctx.transport)
    test_ctx.channel._init_noise()


def prepare_channel_for_pairing(
    test_ctx: TrezorTestContext,
    host_static_privkey: bytes | None = None,
    credential: Credential | None = None,
) -> None:
    """Create a fresh channel, perform the handshake using the provided fixed entropy
    and credentials, and leave it in the pairing phase.
    """
    # set up a fresh channel
    prepare_channel_for_handshake(test_ctx)
    if host_static_privkey is not None:
        test_ctx.channel._init_noise(static_privkey=host_static_privkey)
    credentials = []
    if credential is not None:
        credentials.append(credential)

    # run the handshake
    test_ctx.channel.open(credentials)
    assert isinstance(test_ctx.client, TrezorClientThp)
    test_ctx.client.pairing = test_ctx.pairing = PairingController(test_ctx.client)


def get_encrypted_transport_protocol(test_ctx: TrezorTestContext) -> None:
    prepare_channel_for_pairing(test_ctx)
    test_ctx.pairing.skip()


def break_channel(test_ctx: TrezorTestContext) -> None:
    cse = test_ctx.channel._noise.noise_protocol.cipher_state_encrypt
    cse.n = cse.n + 1

    session = test_ctx.client._get_any_session()
    session.write(messages.ButtonAck())
    with pytest.raises(ThpError):
        session.read(1)


def nfc_pairing(test_ctx: TrezorTestContext) -> None:
    assert isinstance(test_ctx.client, TrezorClientThp)
    method = Nfc(test_ctx.client.pairing)

    # NFC screen shown

    # Read `nfc_secret` and `handshake_hash` from Trezor using debuglink
    pairing_info = test_ctx.debug.pairing_info(
        thp_channel_id=test_ctx.channel.channel_id.to_bytes(2, "big"),
        handshake_hash=test_ctx.channel.handshake_hash,
        nfc_secret_host=method.nfc_host_secret,
    )
    assert pairing_info.handshake_hash is not None
    assert pairing_info.nfc_secret_trezor is not None
    assert pairing_info.handshake_hash[:16] == test_ctx.channel.handshake_hash[:16]

    method.send_nfc_tag(pairing_info.nfc_secret_trezor)
