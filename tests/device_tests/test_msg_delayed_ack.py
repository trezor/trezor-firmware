# This file is part of the Trezor project.
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

import time
import typing as t

import pytest

from trezorlib import device, messages
from trezorlib.debuglink import DebugSession as Session
from trezorlib.debuglink import LayoutType

from ..common import MNEMONIC12, MOCK_GET_ENTROPY, click_through, generate_entropy

if t.TYPE_CHECKING:
    from trezorlib.debuglink import InputFlowType


def ping_without_ack(session: Session):
    br = session.call_raw(messages.Ping(message="delayed", button_protection=True))
    assert isinstance(br, messages.ButtonRequest)
    assert br.code == messages.ButtonRequestType.ProtectCall
    # confirm layout before ButtonAck is sent
    session.debug.press_yes()
    # "waiting" screen should be shown after 2 seconds on Core models
    # (following https://github.com/trezor/trezor-firmware/issues/5884)
    time.sleep(2.5)


def test_delayed_ack(session: Session):
    ping_without_ack(session)

    res = session.call_raw(messages.ButtonAck())
    res = messages.Success.ensure_isinstance(res)
    assert res.message == "delayed"


@pytest.mark.models("core")
def test_abort(session: Session):
    ping_without_ack(session)

    session.debug.press_yes()
    assert session.read() == messages.Failure(
        code=messages.FailureType.ActionCancelled, message="Cancelled"
    )
    assert session.client.ping("again") == "again"


@pytest.mark.setup_client(needs_backup=True, mnemonic=MNEMONIC12)
@pytest.mark.models("core")
def test_backup_no_acks(session: Session):
    assert session.features.backup_availability == messages.BackupAvailability.Required

    words = []
    with session.test_ctx as client:

        def flow() -> "InputFlowType":
            nonlocal words
            words = yield from _perform_backup(session)

        client.set_input_flow(flow())
        client.set_expected_responses(
            [
                messages.ButtonRequest,  # backup_intro
                messages.ButtonRequest,  # backup_warning
                messages.Success,
                messages.Features,
            ]
        )
        device.backup(session)

    assert words == MNEMONIC12
    session.refresh_features()
    assert session.features.initialized is True
    assert (
        session.features.backup_availability == messages.BackupAvailability.NotAvailable
    )
    assert session.features.unfinished_backup is False
    assert session.features.no_backup is False
    assert session.features.backup_type is messages.BackupType.Bip39


@pytest.mark.setup_client(uninitialized=True)
@pytest.mark.models("core")
def test_setup_no_acks(session: Session):
    from tests.click_tests import reset

    assert session.features.initialized is False

    debug = session.debug

    words = ""
    with session.test_ctx as client:

        setup_success: int = {
            LayoutType.Bolt: False,
            LayoutType.Caesar: False,
            LayoutType.Delizia: True,
            LayoutType.Eckhart: True,
        }[session.layout_type]

        def flow() -> "InputFlowType":
            # confirm new wallet & first backup-related ButtonRequest
            yield from click_through(
                debug,
                screens=(1 + int(setup_success)),
                code=messages.ButtonRequestType.ResetDevice,
            )

            assert (yield).name == "backup_device"
            debug.press_yes()

            nonlocal words
            words = yield from _perform_backup(session)

        client.set_input_flow(flow())
        client.set_expected_responses(
            [
                (client.is_protocol_v1(), messages.Features),
                messages.ButtonRequest,
                messages.EntropyRequest,
                (setup_success, messages.ButtonRequest),
                messages.ButtonRequest,  # backup_device
                messages.ButtonRequest,  # backup_intro
                messages.ButtonRequest,  # backup_warning
                messages.Success,
                messages.Features,
            ]
        )
        device.setup(
            session,
            entropy_check_count=0,
            _get_entropy=MOCK_GET_ENTROPY,
        )

    # generate secret locally
    internal_entropy = debug.state().reset_entropy
    assert internal_entropy is not None
    secret = generate_entropy(128, internal_entropy, MOCK_GET_ENTROPY())

    # validate that all combinations will result in the correct master secret
    reset.validate_mnemonics([words], secret)

    session.refresh_features()
    assert session.features.initialized is True
    assert (
        session.features.backup_availability == messages.BackupAvailability.NotAvailable
    )
    assert session.features.unfinished_backup is False
    assert session.features.no_backup is False
    assert session.features.backup_type is messages.BackupType.Slip39_Single_Extendable


def _perform_backup(
    session: Session,
) -> t.Generator[t.Any, messages.ButtonRequest, str]:
    from tests.click_tests import reset

    debug = session.debug

    # Wait until the first backup-related ButtonRequest is sent
    assert (yield).name == "backup_intro"
    reset.confirm_read(debug)

    # Don't next ACK backup-related ButtonRequest messages
    with session.client._interact(force_flush=True):
        # - read ButtonRequest, without sending ButtonAck back to the device
        # - send THP-level ACK (to avoid retransmissions and assertion when sending `Success`)
        messages.ButtonRequest.ensure_isinstance(session.read())

    # proceed with backup (even if no ButtonAck)
    reset.confirm_read(debug, middle_r=True)

    # confirm warning
    reset.confirm_read(debug, middle_r=True)

    # read words
    words = reset.read_words(debug)

    # confirm words
    reset.confirm_words(debug, words)

    # confirm backup done
    reset.confirm_read(debug)

    # Your backup is done
    if debug.layout_type is not LayoutType.Eckhart:
        reset.confirm_read(debug)

    return " ".join(words)
