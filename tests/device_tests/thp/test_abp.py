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

import functools
import time
import typing as t
from unittest.mock import Mock

import pytest

from trezorlib import device, messages
from trezorlib.debuglink import DebugSession
from trezorlib.thp.client import TrezorClientThp

from ..test_msg_applysettings import homescreen_jpeg_path

pytestmark = [pytest.mark.protocol("thp")]


def test_abp(session: DebugSession) -> None:
    assert isinstance(session.client, TrezorClientThp)
    channel = session.client.channel

    nonce_enc = channel._noise.noise_protocol.cipher_state_encrypt.n

    # patch out channel._read_ack to do nothing, so that its auto-acking
    # logic is not triggered, so that Trezor doesn't think we read its messages.
    channel._read_ack = Mock()
    session.write(messages.Ping(message="ping"))

    # revert channel to earlier state
    channel._noise.noise_protocol.cipher_state_encrypt.n = nonce_enc
    channel.sync_bit_send = not channel.sync_bit_send

    # retransmit the original message
    time.sleep(0.1)
    session.write(messages.Ping(message="ping"))
    time.sleep(2)

    # we should now successfully read the response
    resp = session.read()
    messages.Success.ensure_isinstance(resp)


def delay_call(func: t.Callable, seconds: float) -> t.Callable:

    @functools.wraps(func)
    def wrapper(*args, **kw):
        time.sleep(seconds)
        return func(*args, **kw)

    return wrapper


def test_delay_acks_from_host(session: DebugSession) -> None:
    assert isinstance(session.client, TrezorClientThp)
    channel = session.client.channel

    # delay THP ACK sending, to trigger retransmits
    channel._send_ack = delay_call(channel._send_ack, seconds=0.6)
    session.client.ping("Should succeed after some retransmits")
    session.client.ping("ButtonRequest should be retransmitted", button_protection=True)

    with open(homescreen_jpeg_path(session.debug.layout_type), "rb") as f:
        # Multiple requests and responses
        device.apply_settings(session, homescreen=f.read())
