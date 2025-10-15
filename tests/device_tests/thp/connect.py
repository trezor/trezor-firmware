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
from trezorlib.thp.channel import Channel
from trezorlib.thp.client import TrezorClientThp
from trezorlib.thp.exceptions import ThpError
from trezorlib.thp.credentials import Credential, TrezorPublicKeys
from trezorlib.thp.pairing import PairingController
from trezorlib.debuglink import TrezorTestContext


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
