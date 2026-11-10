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

import hashlib
import io
from functools import partial

import pytest

from trezorlib import exceptions, messages, protobuf
from trezorlib.debuglink import DebugSession as Session
from trezorlib.tools import parse_path

from . import testapp_ext
from .generated import messages as m
from .testapp_ext import DEFAULT_BIP32_PATH, SdkError, assert_fails


def hash_request(instance_id: int, message_id: int) -> messages.ExtAppMessage:
    """A valid `Hash` request, addressed to `instance_id` as `message_id`."""
    buf = io.BytesIO()
    protobuf.dump_message(
        buf, m.Hash(algorithm=m.HashAlgorithm.Sha256, chunks=[b"abc"])
    )
    return messages.ExtAppMessage(
        instance_id=instance_id, message_id=message_id, data=buf.getvalue()
    )


def test_crashed_app_reports_app_error(session: Session, instance_id: int):
    """A crashed app reaches the host as a detail-less `AppError`."""
    with pytest.raises(exceptions.TrezorFailure) as e:
        testapp_ext.crash(session, instance_id)
    assert e.value.code == messages.FailureType.AppError
    # the app's own error text stays in the log
    assert e.value.message == "Application error"


def test_restarted_after_crash(session: Session, instance_id: int):
    """Core starts the app anew for every request, also after a crash."""
    with pytest.raises(exceptions.TrezorFailure):
        testapp_ext.crash(session, instance_id)
    digest = testapp_ext.hash(session, instance_id, m.HashAlgorithm.Sha256, [b"abc"])
    assert digest == hashlib.sha256(b"abc").digest()


def test_wrong_instance_id(session: Session, instance_id: int):
    request = hash_request(instance_id ^ 1, testapp_ext.message_id(m.Hash))
    with pytest.raises(exceptions.TrezorFailure) as e:
        session.call(request, expect=messages.ExtAppResponse)
    assert e.value.code == messages.FailureType.DataError
    assert e.value.message == "Invalid instance ID"


def test_message_id_out_of_range(session: Session, instance_id: int):
    """App message ids are 16 bits."""
    request = hash_request(instance_id, 0x10000 | testapp_ext.message_id(m.Hash))
    with pytest.raises(exceptions.TrezorFailure) as e:
        session.call(request, expect=messages.ExtAppResponse)
    assert e.value.code == messages.FailureType.DataError
    assert e.value.message == "Invalid message ID"


def test_unrepresentable_argument(session: Session, instance_id: int):
    """The testapp refuses a parameter the SDK function's types can't hold,
    before calling the function: this checks the testapp, not the SDK."""
    calls = {
        "digest of 31 bytes": partial(
            testapp_ext.ecdsa_sign_digest,
            session,
            instance_id,
            parse_path(DEFAULT_BIP32_PATH),
            b"\x01" * 31,
            True,
        ),
        "CoSi key of 33 bytes": partial(
            testapp_ext.cosi_combine_publickeys, session, instance_id, [b"\x01" * 33]
        ),
        "CoSi threshold over 255": partial(
            testapp_ext.cosi_verify,
            session,
            instance_id,
            256,
            b"message",
            [b"\x01" * 32],
            0b1,
            b"\x00" * 64,
        ),
    }
    for what, call in calls.items():
        assert_fails(what, call, SdkError.InvalidArgument)
