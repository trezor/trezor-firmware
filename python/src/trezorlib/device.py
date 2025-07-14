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

import hashlib
import hmac
import random
import secrets
import time
import warnings
from typing import TYPE_CHECKING, Callable, Iterable, Optional, Tuple

from slip10 import SLIP10

from . import messages
from .exceptions import Cancelled, TrezorException
from .tools import Address, _deprecation_retval_helper, _return_success, parse_path

if TYPE_CHECKING:
    from .transport.session import Session


RECOVERY_BACK = "\x08"  # backspace character, sent literally

SLIP39_EXTENDABLE_MIN_VERSION = (2, 7, 1)
ENTROPY_CHECK_MIN_VERSION = (2, 8, 7)
HOMESCREEN_STREAMING_MIN_VERSION = (2, 8, 11)


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
) -> str | None:
    if language is not None:
        warnings.warn(
            "language ignored. Use change_language() to set device language.",
            DeprecationWarning,
        )
    settings = messages.ApplySettings(
        label=label,
        use_passphrase=use_passphrase,
        passphrase_always_on_device=passphrase_always_on_device,
        auto_lock_delay_ms=auto_lock_delay_ms,
        display_rotation=display_rotation,
        safety_checks=safety_checks,
        experimental_features=experimental_features,
        hide_passphrase_from_host=hide_passphrase_from_host,
        haptic_feedback=haptic_feedback,
    )

    if homescreen and session.version >= HOMESCREEN_STREAMING_MIN_VERSION:
        settings.homescreen_length = len(homescreen)
        response = session.call(settings, expect=messages.DataChunkRequest)
        _send_chunked_data(session, response, homescreen)
        out = messages.Success()
    else:
        settings.homescreen = homescreen
        out = session.call(settings, expect=messages.Success)
    session.refresh_features()
    return _return_success(out)


def _send_chunked_data(
    session: "Session",
    request: "messages.DataChunkRequest",
    language_data: bytes,
) -> None:
    response = request
    while not isinstance(response, messages.Success):
        response = messages.DataChunkRequest.ensure_isinstance(response)
        data_length = response.data_length
        data_offset = response.data_offset
        chunk = language_data[data_offset : data_offset + data_length]
        response = session.call(messages.DataChunkAck(data_chunk=chunk))


def change_language(
    session: "Session",
    language_data: bytes,
    show_display: bool | None = None,
) -> str | None:
    data_length = len(language_data)
    msg = messages.ChangeLanguage(data_length=data_length, show_display=show_display)

    response = session.call(msg)
    if data_length > 0:
        response = messages.DataChunkRequest.ensure_isinstance(response)
        _send_chunked_data(session, response, language_data)
    else:
        messages.Success.ensure_isinstance(response)
    session.refresh_features()  # changing the language in features
    return _return_success(messages.Success(message="Language changed."))


def apply_flags(session: "Session", flags: int) -> str | None:
    out = session.call(messages.ApplyFlags(flags=flags), expect=messages.Success)
    session.refresh_features()
    return _return_success(out)


def change_pin(session: "Session", remove: bool = False) -> str | None:
    ret = session.call(messages.ChangePin(remove=remove), expect=messages.Success)
    session.refresh_features()
    return _return_success(ret)


def change_wipe_code(session: "Session", remove: bool = False) -> str | None:
    ret = session.call(messages.ChangeWipeCode(remove=remove), expect=messages.Success)
    session.refresh_features()
    return _return_success(ret)


def sd_protect(
    session: "Session", operation: messages.SdProtectOperationType
) -> str | None:
    ret = session.call(messages.SdProtect(operation=operation), expect=messages.Success)
    session.refresh_features()
    return _return_success(ret)


def wipe(session: "Session") -> str | None:
    ret = session.call(messages.WipeDevice(), expect=messages.Success)
    session.invalidate()
    return _return_success(ret)


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
) -> messages.Success | None:
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

    # check that the result is a Success
    res = messages.Success.ensure_isinstance(res)
    # reinitialize the device
    session.refresh_features()

    return _deprecation_retval_helper(res)


def is_slip39_backup_type(backup_type: messages.BackupType):
    return backup_type in (
        messages.BackupType.Slip39_Basic,
        messages.BackupType.Slip39_Advanced,
        messages.BackupType.Slip39_Single_Extendable,
        messages.BackupType.Slip39_Basic_Extendable,
        messages.BackupType.Slip39_Advanced_Extendable,
    )


def _seed_from_entropy(
    internal_entropy: bytes,
    external_entropy: bytes,
    strength: int,
    backup_type: messages.BackupType,
) -> bytes:
    entropy = hashlib.sha256(internal_entropy + external_entropy).digest()
    secret = entropy[: strength // 8]

    if len(secret) * 8 != strength:
        raise ValueError("Entropy length mismatch")

    if backup_type == messages.BackupType.Bip39:
        import mnemonic

        bip39 = mnemonic.Mnemonic("english")
        words = bip39.to_mnemonic(secret)
        seed = bip39.to_seed(words, passphrase="")
    elif is_slip39_backup_type(backup_type):
        import shamir_mnemonic

        seed = shamir_mnemonic.cipher.decrypt(
            secret, b"", iteration_exponent=1, identifier=0, extendable=True
        )
    else:
        raise ValueError("Unknown backup type.")

    return seed


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
) -> str | None:
    warnings.warn(
        "reset() is deprecated. Use setup() instead.",
        DeprecationWarning,
        stacklevel=2,
    )

    if display_random:
        warnings.warn(
            "display_random ignored. The feature is deprecated.",
            DeprecationWarning,
            stacklevel=2,
        )

    if language is not None:
        warnings.warn(
            "language ignored. Use change_language() to set device language.",
            DeprecationWarning,
            stacklevel=2,
        )

    setup(
        session,
        strength=strength,
        passphrase_protection=passphrase_protection,
        pin_protection=pin_protection,
        label=label,
        u2f_counter=u2f_counter,
        skip_backup=skip_backup,
        no_backup=no_backup,
        backup_type=backup_type,
    )

    return _return_success(messages.Success(message="Initialized"))


def _get_external_entropy() -> bytes:
    return secrets.token_bytes(32)


def setup(
    session: "Session",
    *,
    strength: Optional[int] = None,
    passphrase_protection: bool = True,
    pin_protection: bool = False,
    label: Optional[str] = None,
    u2f_counter: int = 0,
    skip_backup: bool = False,
    no_backup: bool = False,
    backup_type: Optional[messages.BackupType] = None,
    entropy_check_count: Optional[int] = None,
    paths: Iterable[Address] = [],
    _get_entropy: Callable[[], bytes] = _get_external_entropy,
) -> Iterable[Tuple[Address, str]]:
    """Create a new wallet on device.

    On supporting devices, automatically performs the entropy check: for N rounds, ask
    the device to generate a new seed and provide XPUBs derived from that seed. In the
    next round, the previous round's seed is revealed and verified that it was generated
    with the appropriate entropy and that it matches the provided XPUBs.

    On round N+1, instead of revealing, the final seed is stored on device.

    This function returns the XPUBs from the last round. Caller SHOULD store these XPUBs
    and periodically check that the device still generates the same ones, to ensure that
    the device has not maliciously switched to a pre-generated seed.

    The caller can provide a list of interesting derivation paths to be used in the
    entropy check. If an empty list is provided, the function will use the first BTC
    SegWit v0 account and the first ETH account.

    Returned XPUBs are in the form of tuples (derivation path, xpub).

    Specifying an entropy check count other than 0 on devices that don't support it,
    such as Trezor Model One, will result in an error. If not specified, a random value
    between 2 and 8 is chosen on supporting devices.

    Args:
     * client: TrezorClient instance.
     * strength: Entropy strength in bits. Default is 128 for the core family, and 256
       for Trezor Model One.
     * passphrase_protection: Enable passphrase feature. Defaults to True.
     * pin_protection: Enable and set up device PIN as part of the setup flow. Defaults
       to False.
     * label: Device label.
     * u2f_counter: U2F counter value.
     * skip_backup: Skip the backup step. Defaults to False.
     * no_backup: Do not create backup (seedless mode). Defaults to False.
     * entropy_check_count: Number of rounds for the entropy check.

    Returns:
        Sequence of tuples (derivation path, xpub) from the last round of the entropy
        check.
    """

    if session.features.initialized:
        raise RuntimeError(
            "Device is initialized already. Call wipe_device() and try again."
        )

    if strength is None:
        if session.features.model == "1":
            strength = 256
        else:
            strength = 128

    if backup_type is None:
        if session.version < SLIP39_EXTENDABLE_MIN_VERSION:
            # includes Trezor One 1.x.x
            backup_type = messages.BackupType.Bip39
        else:
            backup_type = messages.BackupType.Slip39_Single_Extendable

    if not paths:
        # Get XPUBs for the first BTC SegWit v0 account and first ETH account.
        paths = [parse_path("m/84h/0h/0h"), parse_path("m/44h/60h/0h")]

    if entropy_check_count is None:
        if session.version < ENTROPY_CHECK_MIN_VERSION:
            # includes Trezor One 1.x.x
            entropy_check_count = 0
        else:
            entropy_check_count = random.randint(2, 8)

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
        entropy_check=entropy_check_count > 0,
    )
    if entropy_check_count > 0:
        xpubs = _reset_with_entropycheck(
            session, msg, entropy_check_count, paths, _get_entropy
        )
    else:
        _reset_no_entropycheck(session, msg, _get_entropy)
        xpubs = []

    session.refresh_features()
    return xpubs


def _reset_no_entropycheck(
    session: "Session",
    msg: messages.ResetDevice,
    get_entropy: Callable[[], bytes],
) -> None:
    """Simple reset workflow without entropy checks:

    >> ResetDevice
    << EntropyRequest
    >> EntropyAck(entropy=...)
    << Success
    """
    assert msg.entropy_check is False
    session.call(msg, expect=messages.EntropyRequest)
    session.call(messages.EntropyAck(entropy=get_entropy()), expect=messages.Success)


def _reset_with_entropycheck(
    session: "Session",
    reset_msg: messages.ResetDevice,
    entropy_check_count: int,
    paths: Iterable[Address],
    get_entropy: Callable[[], bytes],
) -> list[tuple[Address, str]]:
    """Reset workflow with entropy checks:

    >> ResetDevice
    repeat n times:
    << EntropyRequest(entropy_commitment=..., prev_entropy=...)
    >> EntropyAck(entropy=...)
    << EntropyCheckReady
    >> GetPublicKey(...)
    << PublicKey(...)
    >> EntropyCheckContinue(finish=False)
    last round:
    >> EntropyCheckContinue(finish=True)
    << Success

    After each round, the device reveals its internal entropy via the prev_entropy
    field. This function verifies that the entropy matches the respective commitment,
    then recalculate the seed for the previous round, and verifies that the public keys
    generated by the device match that seed.

    Returns the list of XPUBs from the last round. Caller is responsible for storing
    those XPUBs and later verifying that these are still valid.
    """
    assert reset_msg.strength is not None
    assert reset_msg.backup_type is not None
    strength = reset_msg.strength
    backup_type = reset_msg.backup_type

    def get_xpubs() -> list[tuple[Address, str]]:
        xpubs = []
        for path in paths:
            resp = session.call(
                messages.GetPublicKey(address_n=path), expect=messages.PublicKey
            )
            xpubs.append((path, resp.xpub))
        return xpubs

    def verify_entropy_commitment(
        internal_entropy: bytes | None,
        external_entropy: bytes,
        entropy_commitment: bytes | None,
        xpubs: list[tuple[Address, str]],
    ) -> None:
        if internal_entropy is None or entropy_commitment is None:
            raise TrezorException("Invalid entropy check response.")
        calculated_commitment = hmac.HMAC(
            key=internal_entropy, msg=b"", digestmod=hashlib.sha256
        ).digest()
        if calculated_commitment != entropy_commitment:
            raise TrezorException("Invalid entropy commitment.")

        seed = _seed_from_entropy(
            internal_entropy, external_entropy, strength, backup_type
        )
        slip10 = SLIP10.from_seed(seed)
        for path, xpub in xpubs:
            if slip10.get_xpub_from_path(path) != xpub:
                raise TrezorException("Invalid XPUB in entropy check")

    xpubs = []
    resp = session.call(reset_msg, expect=messages.EntropyRequest)
    entropy_commitment = resp.entropy_commitment

    while True:
        # provide external entropy for this round
        external_entropy = get_entropy()
        session.call(
            messages.EntropyAck(entropy=external_entropy),
            expect=messages.EntropyCheckReady,
        )

        # fetch xpubs for the current round
        xpubs = get_xpubs()

        if entropy_check_count <= 0:
            # last round, wait for a Success and exit the loop
            session.call(
                messages.EntropyCheckContinue(finish=True),
                expect=messages.Success,
            )
            break

        entropy_check_count -= 1

        # Next round starts.
        resp = session.call(
            messages.EntropyCheckContinue(finish=False),
            expect=messages.EntropyRequest,
        )

        # Check the entropy commitment from the previous round.
        verify_entropy_commitment(
            resp.prev_entropy, external_entropy, entropy_commitment, xpubs
        )
        # Update the entropy commitment for the next round.
        entropy_commitment = resp.entropy_commitment

    # TODO when we grow an API for auto-opening an empty passphrase session,
    # we should run the following piece:
    # xpubs_verify = get_xpubs()
    # if xpubs != xpubs_verify:
    #     raise TrezorException("Invalid XPUBs after entropy check phase")

    return xpubs


def backup(
    session: "Session",
    group_threshold: Optional[int] = None,
    groups: Iterable[tuple[int, int]] = (),
) -> str | None:
    ret = session.call(
        messages.BackupDevice(
            group_threshold=group_threshold,
            groups=[
                messages.Slip39Group(member_threshold=t, member_count=c)
                for t, c in groups
            ],
        ),
        expect=messages.Success,
    )
    session.refresh_features()
    return _return_success(ret)


def cancel_authorization(session: "Session") -> str | None:
    ret = session.call(messages.CancelAuthorization(), expect=messages.Success)
    return _return_success(ret)


def unlock_path(session: "Session", n: "Address") -> bytes:
    resp = session.call(
        messages.UnlockPath(address_n=n), expect=messages.UnlockedPathRequest
    )

    # Cancel the UnlockPath workflow now that we have the authentication code.
    try:
        session.call(messages.Cancel())
    except Cancelled:
        return resp.mac
    else:
        raise TrezorException("Unexpected response in UnlockPath flow")


def reboot_to_bootloader(
    session: "Session",
    boot_command: messages.BootCommand = messages.BootCommand.STOP_AND_WAIT,
    firmware_header: Optional[bytes] = None,
    language_data: bytes = b"",
) -> str | None:
    response = session.call(
        messages.RebootToBootloader(
            boot_command=boot_command,
            firmware_header=firmware_header,
            language_data_length=len(language_data),
        )
    )
    if isinstance(response, messages.DataChunkRequest):
        response = _send_chunked_data(session, response, language_data)
    return _return_success(messages.Success(message=""))


def show_device_tutorial(session: "Session") -> str | None:
    ret = session.call(messages.ShowDeviceTutorial(), expect=messages.Success)
    return _return_success(ret)


def unlock_bootloader(session: "Session") -> str | None:
    ret = session.call(messages.UnlockBootloader(), expect=messages.Success)
    return _return_success(ret)


def set_busy(session: "Session", expiry_ms: Optional[int]) -> str | None:
    """Sets or clears the busy state of the device.

    In the busy state the device shows a "Do not disconnect" message instead of the homescreen.
    Setting `expiry_ms=None` clears the busy state.
    """
    ret = session.call(messages.SetBusy(expiry_ms=expiry_ms), expect=messages.Success)
    session.refresh_features()
    return _return_success(ret)


def authenticate(session: "Session", challenge: bytes) -> messages.AuthenticityProof:
    return session.call(
        messages.AuthenticateDevice(challenge=challenge),
        expect=messages.AuthenticityProof,
    )


def set_brightness(session: "Session", value: Optional[int] = None) -> str | None:
    ret = session.call(messages.SetBrightness(value=value), expect=messages.Success)
    return _return_success(ret)
