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
from .tools import Address, expect, session

if TYPE_CHECKING:
    from .client import TrezorClient
    from .protobuf import MessageType


RECOVERY_BACK = "\x08"  # backspace character, sent literally


@expect(messages.Success, field="message", ret_type=str)
@session
def apply_settings(
    client: "TrezorClient",
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

    out = client.call(settings)
    client.refresh_features()
    return out


def _send_language_data(
    client: "TrezorClient",
    request: "messages.TranslationDataRequest",
    language_data: bytes,
) -> "MessageType":
    response: MessageType = request
    while not isinstance(response, messages.Success):
        assert isinstance(response, messages.TranslationDataRequest)
        data_length = response.data_length
        data_offset = response.data_offset
        chunk = language_data[data_offset : data_offset + data_length]
        response = client.call(messages.TranslationDataAck(data_chunk=chunk))

    return response


@expect(messages.Success, field="message", ret_type=str)
@session
def change_language(
    client: "TrezorClient",
    language_data: bytes,
    show_display: bool | None = None,
) -> "MessageType":
    data_length = len(language_data)
    msg = messages.ChangeLanguage(data_length=data_length, show_display=show_display)

    response = client.call(msg)
    if data_length > 0:
        assert isinstance(response, messages.TranslationDataRequest)
        response = _send_language_data(client, response, language_data)
    assert isinstance(response, messages.Success)
    client.refresh_features()  # changing the language in features
    return response


@expect(messages.Success, field="message", ret_type=str)
@session
def apply_flags(client: "TrezorClient", flags: int) -> "MessageType":
    out = client.call(messages.ApplyFlags(flags=flags))
    client.refresh_features()
    return out


@expect(messages.Success, field="message", ret_type=str)
@session
def change_pin(client: "TrezorClient", remove: bool = False) -> "MessageType":
    ret = client.call(messages.ChangePin(remove=remove))
    client.refresh_features()
    return ret


@expect(messages.Success, field="message", ret_type=str)
@session
def change_wipe_code(client: "TrezorClient", remove: bool = False) -> "MessageType":
    ret = client.call(messages.ChangeWipeCode(remove=remove))
    client.refresh_features()
    return ret


@expect(messages.Success, field="message", ret_type=str)
@session
def sd_protect(
    client: "TrezorClient", operation: messages.SdProtectOperationType
) -> "MessageType":
    ret = client.call(messages.SdProtect(operation=operation))
    client.refresh_features()
    return ret


@expect(messages.Success, field="message", ret_type=str)
@session
def wipe(client: "TrezorClient") -> "MessageType":
    ret = client.call(messages.WipeDevice())
    if not client.features.bootloader_mode:
        client.init_device()
    return ret


@session
def recover(
    client: "TrezorClient",
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

    if client.features.model == "1" and input_callback is None:
        raise RuntimeError("Input callback required for Trezor One")

    if word_count not in (12, 18, 24):
        raise ValueError("Invalid word count. Use 12/18/24")

    if client.features.initialized and type == messages.RecoveryType.NormalRecovery:
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

    res = client.call(msg)

    while isinstance(res, messages.WordRequest):
        try:
            assert input_callback is not None
            inp = input_callback(res.type)
            res = client.call(messages.WordAck(word=inp))
        except Cancelled:
            res = client.call(messages.Cancel())

    client.init_device()
    return res


@expect(messages.Success, field="message", ret_type=str)
@session
def reset(
    client: "TrezorClient",
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

    if client.features.initialized:
        raise RuntimeError(
            "Device is initialized already. Call wipe_device() and try again."
        )

    if strength is None:
        if client.features.model == "1":
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

    resp = client.call(msg)
    if not isinstance(resp, messages.EntropyRequest):
        raise RuntimeError("Invalid response, expected EntropyRequest")

    external_entropy = os.urandom(32)
    # LOG.debug("Computer generated entropy: " + external_entropy.hex())
    ret = client.call(messages.EntropyAck(entropy=external_entropy))
    client.init_device()
    return ret


@expect(messages.Success, field="message", ret_type=str)
@session
def backup(
    client: "TrezorClient",
    group_threshold: Optional[int] = None,
    groups: Iterable[tuple[int, int]] = (),
) -> "MessageType":
    ret = client.call(
        messages.BackupDevice(
            group_threshold=group_threshold,
            groups=[
                messages.Slip39Group(member_threshold=t, member_count=c)
                for t, c in groups
            ],
        )
    )
    client.refresh_features()
    return ret


@expect(messages.Success, field="message", ret_type=str)
def cancel_authorization(client: "TrezorClient") -> "MessageType":
    return client.call(messages.CancelAuthorization())


@expect(messages.UnlockedPathRequest, field="mac", ret_type=bytes)
def unlock_path(client: "TrezorClient", n: "Address") -> "MessageType":
    resp = client.call(messages.UnlockPath(address_n=n))

    # Cancel the UnlockPath workflow now that we have the authentication code.
    try:
        client.call(messages.Cancel())
    except Cancelled:
        return resp
    else:
        raise TrezorException("Unexpected response in UnlockPath flow")


@session
@expect(messages.Success, field="message", ret_type=str)
def reboot_to_bootloader(
    client: "TrezorClient",
    boot_command: messages.BootCommand = messages.BootCommand.STOP_AND_WAIT,
    firmware_header: Optional[bytes] = None,
    language_data: bytes = b"",
) -> "MessageType":
    response = client.call(
        messages.RebootToBootloader(
            boot_command=boot_command,
            firmware_header=firmware_header,
            language_data_length=len(language_data),
        )
    )
    if isinstance(response, messages.TranslationDataRequest):
        response = _send_language_data(client, response, language_data)
    return response


@session
@expect(messages.Success, field="message", ret_type=str)
def show_device_tutorial(client: "TrezorClient") -> "MessageType":
    return client.call(messages.ShowDeviceTutorial())


@session
@expect(messages.Success, field="message", ret_type=str)
def unlock_bootloader(client: "TrezorClient") -> "MessageType":
    return client.call(messages.UnlockBootloader())


@expect(messages.Success, field="message", ret_type=str)
@session
def set_busy(client: "TrezorClient", expiry_ms: Optional[int]) -> "MessageType":
    """Sets or clears the busy state of the device.

    In the busy state the device shows a "Do not disconnect" message instead of the homescreen.
    Setting `expiry_ms=None` clears the busy state.
    """
    ret = client.call(messages.SetBusy(expiry_ms=expiry_ms))
    client.refresh_features()
    return ret


@expect(messages.AuthenticityProof)
def authenticate(client: "TrezorClient", challenge: bytes):
    return client.call(messages.AuthenticateDevice(challenge=challenge))


@expect(messages.Success, field="message", ret_type=str)
def set_brightness(
    client: "TrezorClient", value: Optional[int] = None
) -> "MessageType":
    return client.call(messages.SetBrightness(value=value))
