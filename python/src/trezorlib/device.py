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

from __future__ import annotations

import os
import time
import warnings
from typing import TYPE_CHECKING, Callable, Iterable, Optional

from . import messages
from .exceptions import Cancelled, TrezorException
from .tools import Address, expect

if TYPE_CHECKING:
    from .protobuf import MessageType
    from .transport.session import Session


RECOVERY_BACK = "\x08"  # backspace character, sent literally


@expect(messages.Success, field="message", ret_type=str)
def apply_settings(
    session: "Session",
    label: Optional[str] = None,
    language: Optional[str] = None,
    use_passphrase: Optional[bool] = None,
    homescreen: Optional[bytes] = None,
    passphrase_always_on_device: Optional[bool] = None,
    auto_lock_delay_ms: Optional[int] = None,
    display_rotation: Optional[messages.DisplayRotation] = None,
    safety_checks: Optional[messages.SafetyCheckLevel] = None,
    experimental_features: Optional[bool] = None,
    hide_passphrase_from_host: Optional[bool] = None,
    haptic_feedback: Optional[bool] = None,
) -> "MessageType":
    if language is not None:
        warnings.warn(
            "language ignored. Use change_language() to set device language.",
            DeprecationWarning,
        )
    settings = messages.ApplySettings(
        label=label,
        use_passphrase=use_passphrase,
        homescreen=homescreen,
        passphrase_always_on_device=passphrase_always_on_device,
        auto_lock_delay_ms=auto_lock_delay_ms,
        display_rotation=display_rotation,
        safety_checks=safety_checks,
        experimental_features=experimental_features,
        hide_passphrase_from_host=hide_passphrase_from_host,
        haptic_feedback=haptic_feedback,
    )

    out = session.call(settings)
    session.refresh_features()
    return out


def _send_language_data(
    session: "Session",
    request: "messages.TranslationDataRequest",
    language_data: bytes,
) -> "MessageType":
    response: MessageType = request
    while not isinstance(response, messages.Success):
        assert isinstance(response, messages.TranslationDataRequest)
        data_length = response.data_length
        data_offset = response.data_offset
        chunk = language_data[data_offset : data_offset + data_length]
        response = session.call(messages.TranslationDataAck(data_chunk=chunk))

    return response


@expect(messages.Success, field="message", ret_type=str)
def change_language(
    session: "Session",
    language_data: bytes,
    show_display: bool | None = None,
) -> "MessageType":
    data_length = len(language_data)
    msg = messages.ChangeLanguage(data_length=data_length, show_display=show_display)

    response = session.call(msg)
    if data_length > 0:
        assert isinstance(response, messages.TranslationDataRequest)
        response = _send_language_data(session, response, language_data)
    assert isinstance(response, messages.Success)
    session.refresh_features()  # changing the language in features
    return response


@expect(messages.Success, field="message", ret_type=str)
def apply_flags(session: "Session", flags: int) -> "MessageType":
    out = session.call(messages.ApplyFlags(flags=flags))
    session.refresh_features()
    return out


@expect(messages.Success, field="message", ret_type=str)
def change_pin(session: "Session", remove: bool = False) -> "MessageType":
    ret = session.call(messages.ChangePin(remove=remove))
    session.refresh_features()
    return ret


@expect(messages.Success, field="message", ret_type=str)
def change_wipe_code(session: "Session", remove: bool = False) -> "MessageType":
    ret = session.call(messages.ChangeWipeCode(remove=remove))
    session.refresh_features()
    return ret


@expect(messages.Success, field="message", ret_type=str)
def sd_protect(
    session: "Session", operation: messages.SdProtectOperationType
) -> "MessageType":
    ret = session.call(messages.SdProtect(operation=operation))
    session.refresh_features()
    return ret


@expect(messages.Success, field="message", ret_type=str)
def wipe(session: "Session") -> "MessageType":

    ret = session.call(messages.WipeDevice())
    # if not session.features.bootloader_mode:
    #     session.refresh_features()
    return ret


def recover(
    session: "Session",
    word_count: int = 24,
    passphrase_protection: bool = False,
    pin_protection: bool = True,
    label: Optional[str] = None,
    language: Optional[str] = None,
    input_callback: Optional[Callable] = None,
    input_method: messages.RecoveryDeviceInputMethod = messages.RecoveryDeviceInputMethod.ScrambledWords,
    dry_run: Optional[bool] = None,
    u2f_counter: Optional[int] = None,
    *,
    type: Optional[messages.RecoveryType] = None,
) -> "MessageType":
    if language is not None:
        warnings.warn(
            "language ignored. Use change_language() to set device language.",
            DeprecationWarning,
        )

    if dry_run is not None:
        warnings.warn(
            "Use type=RecoveryType.DryRun instead!",
            DeprecationWarning,
            stacklevel=3,
        )

        if type is not None:
            raise ValueError("Cannot use both dry_run and type simultaneously.")
        elif dry_run:
            type = messages.RecoveryType.DryRun
        else:
            type = messages.RecoveryType.NormalRecovery

    if type is None:
        type = messages.RecoveryType.NormalRecovery

    if session.features.model == "1" and input_callback is None:
        raise RuntimeError("Input callback required for Trezor One")

    if word_count not in (12, 18, 24):
        raise ValueError("Invalid word count. Use 12/18/24")

    if session.features.initialized and type == messages.RecoveryType.NormalRecovery:
        raise RuntimeError(
            "Device already initialized. Call device.wipe() and try again."
        )

    if u2f_counter is None:
        u2f_counter = int(time.time())

    msg = messages.RecoveryDevice(
        word_count=word_count,
        enforce_wordlist=True,
        input_method=input_method,
        type=type,
    )

    if type == messages.RecoveryType.NormalRecovery:
        # set additional parameters
        msg.passphrase_protection = passphrase_protection
        msg.pin_protection = pin_protection
        msg.label = label
        msg.u2f_counter = u2f_counter

    res = session.call(msg)

    while isinstance(res, messages.WordRequest):
        try:
            assert input_callback is not None
            inp = input_callback(res.type)
            res = session.call(messages.WordAck(word=inp))
        except Cancelled:
            res = session.call(messages.Cancel())

    session.refresh_features()
    return res


@expect(messages.Success, field="message", ret_type=str)
def reset(
    session: "Session",
    display_random: bool = False,
    strength: Optional[int] = None,
    passphrase_protection: bool = False,
    pin_protection: bool = True,
    label: Optional[str] = None,
    language: Optional[str] = None,
    u2f_counter: int = 0,
    skip_backup: bool = False,
    no_backup: bool = False,
    backup_type: messages.BackupType = messages.BackupType.Bip39,
) -> "MessageType":
    if display_random:
        warnings.warn(
            "display_random ignored. The feature is deprecated.",
            DeprecationWarning,
        )

    if language is not None:
        warnings.warn(
            "language ignored. Use change_language() to set device language.",
            DeprecationWarning,
        )

    if session.features.initialized:
        raise RuntimeError(
            "Device is initialized already. Call wipe_device() and try again."
        )

    if strength is None:
        if session.features.model == "1":
            strength = 256
        else:
            strength = 128

    # Begin with device reset workflow
    msg = messages.ResetDevice(
        strength=strength,
        passphrase_protection=bool(passphrase_protection),
        pin_protection=bool(pin_protection),
        label=label,
        u2f_counter=u2f_counter,
        skip_backup=bool(skip_backup),
        no_backup=bool(no_backup),
        backup_type=backup_type,
    )

    resp = session.call(msg)
    if not isinstance(resp, messages.EntropyRequest):
        raise RuntimeError("Invalid response, expected EntropyRequest")

    external_entropy = os.urandom(32)
    # LOG.debug("Computer generated entropy: " + external_entropy.hex())
    ret = session.call(messages.EntropyAck(entropy=external_entropy))
    session.refresh_features()  # TODO is necessary?
    return ret


@expect(messages.Success, field="message", ret_type=str)
def backup(
    session: "Session",
    group_threshold: Optional[int] = None,
    groups: Iterable[tuple[int, int]] = (),
) -> "MessageType":
    ret = session.call(
        messages.BackupDevice(
            group_threshold=group_threshold,
            groups=[
                messages.Slip39Group(member_threshold=t, member_count=c)
                for t, c in groups
            ],
        )
    )
    session.refresh_features()
    return ret


@expect(messages.Success, field="message", ret_type=str)
def cancel_authorization(session: "Session") -> "MessageType":
    return session.call(messages.CancelAuthorization())


@expect(messages.UnlockedPathRequest, field="mac", ret_type=bytes)
def unlock_path(session: "Session", n: "Address") -> "MessageType":
    resp = session.call(messages.UnlockPath(address_n=n))

    # Cancel the UnlockPath workflow now that we have the authentication code.
    try:
        session.call(messages.Cancel())
    except Cancelled:
        return resp
    else:
        raise TrezorException("Unexpected response in UnlockPath flow")


@expect(messages.Success, field="message", ret_type=str)
def reboot_to_bootloader(
    session: "Session",
    boot_command: messages.BootCommand = messages.BootCommand.STOP_AND_WAIT,
    firmware_header: Optional[bytes] = None,
    language_data: bytes = b"",
) -> "MessageType":
    response = session.call(
        messages.RebootToBootloader(
            boot_command=boot_command,
            firmware_header=firmware_header,
            language_data_length=len(language_data),
        )
    )
    if isinstance(response, messages.TranslationDataRequest):
        response = _send_language_data(session, response, language_data)
    return response


@expect(messages.Success, field="message", ret_type=str)
def show_device_tutorial(session: "Session") -> "MessageType":
    return session.call(messages.ShowDeviceTutorial())


@expect(messages.Success, field="message", ret_type=str)
def unlock_bootloader(session: "Session") -> "MessageType":
    return session.call(messages.UnlockBootloader())


@expect(messages.Success, field="message", ret_type=str)
def set_busy(session: "Session", expiry_ms: Optional[int]) -> "MessageType":
    """Sets or clears the busy state of the device.

    In the busy state the device shows a "Do not disconnect" message instead of the homescreen.
    Setting `expiry_ms=None` clears the busy state.
    """
    ret = session.call(messages.SetBusy(expiry_ms=expiry_ms))
    session.refresh_features()
    return ret


@expect(messages.AuthenticityProof)
def authenticate(session: "Session", challenge: bytes):
    return session.call(messages.AuthenticateDevice(challenge=challenge))


@expect(messages.Success, field="message", ret_type=str)
def set_brightness(session: "Session", value: Optional[int] = None) -> "MessageType":
    return session.call(messages.SetBrightness(value=value))
