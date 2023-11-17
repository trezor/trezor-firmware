from typing import TYPE_CHECKING

import trezorui2
from trezor.enums import ButtonRequestType
from trezor.ui.layouts import confirm_action
from trezor.wire import DataError

if TYPE_CHECKING:
    from trezor.enums import SafetyCheckLevel
    from trezor.messages import ApplySettings, Success


BRT_PROTECT_CALL = ButtonRequestType.ProtectCall  # CACHE


def _validate_homescreen(homescreen: bytes) -> None:
    import storage.device as storage_device

    if homescreen == b"":
        return

    if len(homescreen) > storage_device.HOMESCREEN_MAXSIZE:
        raise DataError(
            f"Homescreen is too large, maximum size is {storage_device.HOMESCREEN_MAXSIZE} bytes"
        )
    if not trezorui2.check_homescreen_format(homescreen):
        raise DataError("Wrong homescreen format")


async def apply_settings(msg: ApplySettings) -> Success:
    import storage.device as storage_device
    from trezor.messages import Success
    from trezor.wire import NotInitialized, ProcessError

    from apps.base import reload_settings_from_storage
    from apps.common import safety_checks

    if not storage_device.is_initialized():
        raise NotInitialized("Device is not initialized")
    homescreen = msg.homescreen  # local_cache_attribute
    label = msg.label  # local_cache_attribute
    auto_lock_delay_ms = msg.auto_lock_delay_ms  # local_cache_attribute
    use_passphrase = msg.use_passphrase  # local_cache_attribute
    passphrase_always_on_device = (
        msg.passphrase_always_on_device
    )  # local_cache_attribute
    display_rotation = msg.display_rotation  # local_cache_attribute
    msg_safety_checks = msg.safety_checks  # local_cache_attribute
    experimental_features = msg.experimental_features  # local_cache_attribute
    hide_passphrase_from_host = msg.hide_passphrase_from_host  # local_cache_attribute

    if (
        homescreen is None
        and label is None
        and use_passphrase is None
        and passphrase_always_on_device is None
        and display_rotation is None
        and auto_lock_delay_ms is None
        and msg_safety_checks is None
        and experimental_features is None
        and hide_passphrase_from_host is None
    ):
        raise ProcessError("No setting provided")

    if homescreen is not None:
        _validate_homescreen(homescreen)
        await _require_confirm_change_homescreen(homescreen)
        try:
            storage_device.set_homescreen(homescreen)
        except ValueError:
            raise DataError("Invalid homescreen")

    if label is not None:
        if len(label) > storage_device.LABEL_MAXLENGTH:
            raise DataError("Label too long")
        await _require_confirm_change_label(label)
        storage_device.set_label(label)

    if use_passphrase is not None:
        await _require_confirm_change_passphrase(use_passphrase)
        storage_device.set_passphrase_enabled(use_passphrase)

    if passphrase_always_on_device is not None:
        if not storage_device.is_passphrase_enabled():
            raise DataError("Passphrase is not enabled")
        await _require_confirm_change_passphrase_source(passphrase_always_on_device)
        storage_device.set_passphrase_always_on_device(passphrase_always_on_device)

    if auto_lock_delay_ms is not None:
        if auto_lock_delay_ms < storage_device.AUTOLOCK_DELAY_MINIMUM:
            raise ProcessError("Auto-lock delay too short")
        if auto_lock_delay_ms > storage_device.AUTOLOCK_DELAY_MAXIMUM:
            raise ProcessError("Auto-lock delay too long")
        await _require_confirm_change_autolock_delay(auto_lock_delay_ms)
        storage_device.set_autolock_delay_ms(auto_lock_delay_ms)

    if msg_safety_checks is not None:
        await _require_confirm_safety_checks(msg_safety_checks)
        safety_checks.apply_setting(msg_safety_checks)

    if display_rotation is not None:
        await _require_confirm_change_display_rotation(display_rotation)
        storage_device.set_rotation(display_rotation)

    if experimental_features is not None:
        await _require_confirm_experimental_features(experimental_features)
        storage_device.set_experimental_features(experimental_features)

    if hide_passphrase_from_host is not None:
        if safety_checks.is_strict():
            raise ProcessError("Safety checks are strict")
        await _require_confirm_hide_passphrase_from_host(hide_passphrase_from_host)
        storage_device.set_hide_passphrase_from_host(hide_passphrase_from_host)

    reload_settings_from_storage()

    return Success(message="Settings applied")


async def _require_confirm_change_homescreen(homescreen: bytes) -> None:
    from trezor.ui.layouts import confirm_homescreen

    await confirm_homescreen(homescreen)


async def _require_confirm_change_label(label: str) -> None:
    from trezor.ui.layouts import confirm_single

    await confirm_single(
        "set_label",
        "Device name",
        description="Change device name to {}?",
        description_param=label,
        verb="Change",
    )


async def _require_confirm_change_passphrase(use: bool) -> None:
    on_or_off = "on" if use else "off"
    description = f"Turn {on_or_off} passphrase protection?"
    verb = f"Turn {on_or_off}"
    await confirm_action(
        "set_passphrase",
        "Passphrase settings",
        description=description,
        verb=verb,
        br_code=BRT_PROTECT_CALL,
    )


async def _require_confirm_change_passphrase_source(
    passphrase_always_on_device: bool,
) -> None:
    description = (
        "Do you really want to enter passphrase always on the device?"
        if passphrase_always_on_device
        else "Do you want to revoke the passphrase on device setting?"
    )
    await confirm_action(
        "set_passphrase_source",
        "Passphrase source",
        description=description,
        br_code=BRT_PROTECT_CALL,
    )


async def _require_confirm_change_display_rotation(rotation: int) -> None:
    if rotation == 0:
        label = "north"
    elif rotation == 90:
        label = "east"
    elif rotation == 180:
        label = "south"
    elif rotation == 270:
        label = "west"
    else:
        raise DataError("Unsupported display rotation")

    await confirm_action(
        "set_rotation",
        "Change rotation",
        description="Do you want to change device rotation to {}?",
        description_param=label,
        br_code=BRT_PROTECT_CALL,
    )


async def _require_confirm_change_autolock_delay(delay_ms: int) -> None:
    from trezor.strings import format_duration_ms

    await confirm_action(
        "set_autolock_delay",
        "Auto-lock delay",
        description="Auto-lock your Trezor after {} of inactivity?",
        description_param=format_duration_ms(delay_ms),
        br_code=BRT_PROTECT_CALL,
    )


async def _require_confirm_safety_checks(level: SafetyCheckLevel) -> None:
    from trezor.enums import SafetyCheckLevel

    if level == SafetyCheckLevel.Strict:
        await confirm_action(
            "set_safety_checks",
            "Safety checks",
            description="Do you really want to enforce strict safety checks (recommended)?",
            br_code=BRT_PROTECT_CALL,
        )
    elif level in (SafetyCheckLevel.PromptAlways, SafetyCheckLevel.PromptTemporarily):
        # Reusing most stuff for both levels
        template = (
            "Trezor will{}allow you to approve some actions which might be unsafe."
        )
        description = template.format(
            " temporarily " if level == SafetyCheckLevel.PromptTemporarily else " "
        )

        await confirm_action(
            "set_safety_checks",
            "Safety override",
            "Are you sure?",
            description,
            hold=True,
            verb="Hold to confirm",
            reverse=True,
            br_code=BRT_PROTECT_CALL,
        )
    else:
        raise ValueError  # enum value out of range


async def _require_confirm_experimental_features(enable: bool) -> None:
    if enable:
        await confirm_action(
            "set_experimental_features",
            "Experimental mode",
            "Only for development and beta testing!",
            "Enable experimental features?",
            reverse=True,
            br_code=BRT_PROTECT_CALL,
        )


async def _require_confirm_hide_passphrase_from_host(enable: bool) -> None:
    if enable:
        await confirm_action(
            "set_hide_passphrase_from_host",
            "Hide passphrase",
            description="Hide passphrase coming from host?",
            br_code=BRT_PROTECT_CALL,
        )
