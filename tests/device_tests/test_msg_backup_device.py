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

import itertools

import pytest
import shamir_mnemonic as shamir

from trezorlib import device, messages, models
from trezorlib.debuglink import DebugSession as Session
from trezorlib.debuglink import LayoutType
from trezorlib.exceptions import Cancelled, TrezorFailure

from ..common import (
    MNEMONIC12,
    MNEMONIC_SLIP39_ADVANCED_20,
    MNEMONIC_SLIP39_CUSTOM_SECRET,
    MNEMONIC_SLIP39_SINGLE_EXT_20,
    MNEMONIC_SLIP39_BASIC_20_3of6,
    MNEMONIC_SLIP39_CUSTOM_1of1,
)
from ..input_flows import (
    FlowAdapter,
    InputFlowBip39Backup,
    InputFlowSlip39AdvancedBackup,
    InputFlowSlip39BasicBackup,
    InputFlowSlip39CustomBackup,
    normal,
    try_to_cancel,
)

FLOW_ADAPTERS = [normal, try_to_cancel()]


@pytest.mark.models("core")  # TODO we want this for t1 too
@pytest.mark.setup_client(needs_backup=True, mnemonic=MNEMONIC12)
@pytest.mark.parametrize("adapt_flow", FLOW_ADAPTERS, ids=lambda f: f.__name__)
def test_backup_bip39(session: Session, adapt_flow: "FlowAdapter"):
    assert session.features.backup_availability == messages.BackupAvailability.Required

    with session.test_ctx as client:
        IF = InputFlowBip39Backup(session)
        client.set_input_flow(adapt_flow(session, IF.get()))
        device.backup(session)

    assert IF.mnemonic == MNEMONIC12
    session.refresh_features()
    assert session.features.initialized is True
    assert (
        session.features.backup_availability == messages.BackupAvailability.NotAvailable
    )
    assert session.features.unfinished_backup is False
    assert session.features.no_backup is False
    assert session.features.backup_type is messages.BackupType.Bip39


SLIP39_BASIC_PARAMS = list(itertools.product([True, False], FLOW_ADAPTERS))
SLIP39_BASIC_IDS = [
    f"{['no_click_info', 'click_info'][click_info]}_{adapt_flow.__name__}"
    for click_info, adapt_flow in SLIP39_BASIC_PARAMS
]


@pytest.mark.models("core")
@pytest.mark.setup_client(needs_backup=True, mnemonic=MNEMONIC_SLIP39_BASIC_20_3of6)
@pytest.mark.parametrize(
    "click_info,adapt_flow",
    SLIP39_BASIC_PARAMS,
    ids=SLIP39_BASIC_IDS,
)
def test_backup_slip39_basic(
    session: Session, click_info: bool, adapt_flow: "FlowAdapter"
):
    if click_info and session.layout_type is LayoutType.Caesar:
        pytest.skip("click_info not implemented on T2B1")

    assert session.features.backup_availability == messages.BackupAvailability.Required

    with session.test_ctx as client:
        IF = InputFlowSlip39BasicBackup(session, click_info)
        client.set_input_flow(adapt_flow(session, IF.get()))
        device.backup(session)

    session.refresh_features()
    assert session.features.initialized is True
    assert (
        session.features.backup_availability == messages.BackupAvailability.NotAvailable
    )
    assert session.features.unfinished_backup is False
    assert session.features.no_backup is False
    assert session.features.backup_type is messages.BackupType.Slip39_Basic

    expected_ms = shamir.combine_mnemonics(MNEMONIC_SLIP39_BASIC_20_3of6)
    actual_ms = shamir.combine_mnemonics(IF.mnemonics[:3])
    assert expected_ms == actual_ms


@pytest.mark.models("core")
@pytest.mark.setup_client(needs_backup=True, mnemonic=MNEMONIC_SLIP39_SINGLE_EXT_20)
@pytest.mark.parametrize("adapt_flow", FLOW_ADAPTERS, ids=lambda f: f.__name__)
def test_backup_slip39_single(session: Session, adapt_flow: "FlowAdapter"):
    assert session.features.backup_availability == messages.BackupAvailability.Required

    with session.test_ctx as client:
        IF = InputFlowBip39Backup(
            session,
            confirm_success=(
                session.layout_type not in (LayoutType.Delizia, LayoutType.Eckhart)
            ),
        )
        client.set_input_flow(adapt_flow(session, IF.get()))
        device.backup(session)

    assert session.features.initialized is True
    assert (
        session.features.backup_availability == messages.BackupAvailability.NotAvailable
    )

    assert session.features.unfinished_backup is False
    assert session.features.no_backup is False
    assert session.features.backup_type is messages.BackupType.Slip39_Single_Extendable
    assert shamir.combine_mnemonics([IF.mnemonic]) == shamir.combine_mnemonics(
        MNEMONIC_SLIP39_SINGLE_EXT_20
    )


SLIP39_ADVANCED_PARAMS = list(itertools.product([True, False], FLOW_ADAPTERS))
SLIP39_ADVANCED_IDS = [
    f"{['no_click_info', 'click_info'][click_info]}_{adapt_flow.__name__}"
    for click_info, adapt_flow in SLIP39_ADVANCED_PARAMS
]


@pytest.mark.models("core")
@pytest.mark.setup_client(needs_backup=True, mnemonic=MNEMONIC_SLIP39_ADVANCED_20)
@pytest.mark.parametrize(
    "click_info,adapt_flow",
    SLIP39_ADVANCED_PARAMS,
    ids=SLIP39_ADVANCED_IDS,
)
def test_backup_slip39_advanced(
    session: Session, click_info: bool, adapt_flow: "FlowAdapter"
):
    if click_info and session.layout_type is LayoutType.Caesar:
        pytest.skip("click_info not implemented on T2B1")

    assert session.features.backup_availability == messages.BackupAvailability.Required

    with session.test_ctx as client:
        IF = InputFlowSlip39AdvancedBackup(session, click_info)
        client.set_input_flow(adapt_flow(session, IF.get()))
        device.backup(session)

    session.refresh_features()
    assert session.features.initialized is True
    assert (
        session.features.backup_availability == messages.BackupAvailability.NotAvailable
    )
    assert session.features.unfinished_backup is False
    assert session.features.no_backup is False
    assert session.features.backup_type is messages.BackupType.Slip39_Advanced

    expected_ms = shamir.combine_mnemonics(MNEMONIC_SLIP39_ADVANCED_20)
    actual_ms = shamir.combine_mnemonics(
        IF.mnemonics[:3] + IF.mnemonics[5:8] + IF.mnemonics[10:13]
    )
    assert expected_ms == actual_ms


SLIP39_CUSTOM_PARAMS = [
    (threshold, count, adapt_flow)
    for threshold, count in ((1, 1), (2, 2), (3, 5))
    for adapt_flow in FLOW_ADAPTERS
]
SLIP39_CUSTOM_IDS = [
    f"{threshold}_of_{count}_{adapt_flow.__name__}"
    for threshold, count, adapt_flow in SLIP39_CUSTOM_PARAMS
]


@pytest.mark.models("core")
@pytest.mark.setup_client(needs_backup=True, mnemonic=MNEMONIC_SLIP39_CUSTOM_1of1[0])
@pytest.mark.parametrize(
    "share_threshold,share_count,adapt_flow",
    SLIP39_CUSTOM_PARAMS,
    ids=SLIP39_CUSTOM_IDS,
)
def test_backup_slip39_custom(
    session: Session, share_threshold: int, share_count: int, adapt_flow: "FlowAdapter"
):
    assert session.features.backup_availability == messages.BackupAvailability.Required

    with session.test_ctx as client:
        IF = InputFlowSlip39CustomBackup(session, share_count)
        client.set_input_flow(adapt_flow(session, IF.get()))
        device.backup(
            session, group_threshold=1, groups=[(share_threshold, share_count)]
        )

    session.refresh_features()
    assert session.features.initialized is True
    assert (
        session.features.backup_availability == messages.BackupAvailability.NotAvailable
    )
    assert session.features.unfinished_backup is False
    assert session.features.no_backup is False

    assert len(IF.mnemonics) == share_count
    assert (
        shamir.combine_mnemonics(IF.mnemonics[-share_threshold:]).hex()
        == MNEMONIC_SLIP39_CUSTOM_SECRET
    )


# we only test this with bip39 because the code path is always the same
@pytest.mark.setup_client(no_backup=True)
def test_no_backup_fails(session: Session):
    session.ensure_unlocked()
    assert session.features.initialized is True
    assert session.features.no_backup is True
    assert (
        session.features.backup_availability == messages.BackupAvailability.NotAvailable
    )

    # backup attempt should fail because no_backup=True
    with pytest.raises(TrezorFailure, match=r".*Seed already backed up"):
        device.backup(session)


# we only test this with bip39 because the code path is always the same
@pytest.mark.setup_client(needs_backup=True)
def test_interrupt_backup_fails(session: Session):
    session.ensure_unlocked()
    assert session.features.initialized is True
    assert session.features.backup_availability == messages.BackupAvailability.Required
    assert session.features.unfinished_backup is False
    assert session.features.no_backup is False

    # start backup
    resp = session.call_raw(messages.BackupDevice())
    assert isinstance(resp, messages.ButtonRequest)

    # interrupt backup
    if session.model in models.LEGACY_MODELS:
        with pytest.raises(Cancelled):
            # backup can be cancelled on legacy
            session.call(messages.Cancel())
    else:
        # backup cancellation is ignored by Core models
        resp = session.call_raw(messages.Cancel())
        assert isinstance(resp, messages.Failure)
        assert resp.code == messages.FailureType.InProgress
        assert resp.message == "Backup in progress"

        # use debuglink to fail the backup
        session.test_ctx.restart_event_loop()

    # check that device state is as expected
    assert session.features.initialized is True
    session.refresh_features()
    assert (
        session.features.backup_availability == messages.BackupAvailability.NotAvailable
    )
    assert session.features.unfinished_backup is True
    assert session.features.no_backup is False

    # Second attempt at backup should fail
    with pytest.raises(TrezorFailure, match=r".*Seed already backed up"):
        device.backup(session)
