from typing import TYPE_CHECKING

import storage.device as storage_device
import trezorui2
from trezor import TR, utils
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
    haptic_feedback = msg.haptic_feedback

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
        and (haptic_feedback is None or not utils.USE_HAPTIC)
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

    if haptic_feedback is not None and utils.USE_HAPTIC:
        from trezor import io

        await _require_confirm_haptic_feedback(haptic_feedback)
        io.haptic.haptic_set_enabled(haptic_feedback)
        storage_device.set_haptic_feedback(haptic_feedback)

    reload_settings_from_storage()

    return Success(message="Settings applied")


async def _require_confirm_change_homescreen(homescreen: bytes) -> None:
    from trezor.ui.layouts import confirm_homescreen

    await confirm_homescreen(homescreen)


async def _require_confirm_change_label(label: str) -> None:
    from trezor.ui.layouts import confirm_single

    await confirm_single(
        "set_label",
        TR.device_name__title,
        description=TR.device_name__change_template,
        description_param=label,
        verb=TR.buttons__change,
    )


async def _require_confirm_change_passphrase(use: bool) -> None:
    from trezor.ui.layouts import confirm_change_passphrase

    await confirm_change_passphrase(use)


async def _require_confirm_hide_passphrase_from_host(enable: bool) -> None:
    from trezor.ui.layouts import confirm_hide_passphrase_from_host

    if enable:
        await confirm_hide_passphrase_from_host()


async def _require_confirm_change_passphrase_source(
    passphrase_always_on_device: bool,
) -> None:
    from trezor.ui.layouts import confirm_change_passphrase_source

    await confirm_change_passphrase_source(passphrase_always_on_device)


async def _require_confirm_change_display_rotation(rotation: int) -> None:
    if rotation == 0:
        label = TR.rotation__north
    elif rotation == 90:
        label = TR.rotation__east
    elif rotation == 180:
        label = TR.rotation__south
    elif rotation == 270:
        label = TR.rotation__west
    else:
        raise DataError("Unsupported display rotation")

    await confirm_action(
        "set_rotation",
        TR.rotation__title_change,
        description=TR.rotation__change_template,
        description_param=label,
        br_code=BRT_PROTECT_CALL,
        prompt_screen=True,
    )


async def _require_confirm_change_autolock_delay(delay_ms: int) -> None:
    from trezor.strings import format_duration_ms

    unit_plurals = {
        "millisecond": TR.plurals__lock_after_x_milliseconds,
        "second": TR.plurals__lock_after_x_seconds,
        "minute": TR.plurals__lock_after_x_minutes,
        "hour": TR.plurals__lock_after_x_hours,
    }

    await confirm_action(
        "set_autolock_delay",
        TR.auto_lock__title,
        description=TR.auto_lock__change_template,
        description_param=format_duration_ms(delay_ms, unit_plurals),
        br_code=BRT_PROTECT_CALL,
        prompt_screen=True,
    )


async def _require_confirm_safety_checks(level: SafetyCheckLevel) -> None:
    from trezor.enums import SafetyCheckLevel

    if level == SafetyCheckLevel.Strict:
        await confirm_action(
            "set_safety_checks",
            TR.safety_checks__title,
            description=TR.safety_checks__enforce_strict,
            br_code=BRT_PROTECT_CALL,
            prompt_screen=True,
        )
    elif level in (SafetyCheckLevel.PromptAlways, SafetyCheckLevel.PromptTemporarily):
        description = (
            TR.safety_checks__approve_unsafe_temporary
            if level == SafetyCheckLevel.PromptTemporarily
            else TR.safety_checks__approve_unsafe_always
        )
        await confirm_action(
            "set_safety_checks",
            TR.safety_checks__title_safety_override,
            TR.words__are_you_sure,
            description,
            hold=True,
            verb=TR.buttons__hold_to_confirm,
            reverse=True,
            br_code=BRT_PROTECT_CALL,
            prompt_screen=True,
        )
    else:
        raise ValueError  # enum value out of range


async def _require_confirm_experimental_features(enable: bool) -> None:
    if enable:
        await confirm_action(
            "set_experimental_features",
            TR.experimental_mode__title,
            TR.experimental_mode__only_for_dev,
            TR.experimental_mode__enable,
            reverse=True,
            br_code=BRT_PROTECT_CALL,
            prompt_screen=True,
        )


if utils.USE_HAPTIC:

    async def _require_confirm_haptic_feedback(enable: bool) -> None:
        await confirm_action(
            "haptic_feedback__settings",
            TR.haptic_feedback__title,
            TR.haptic_feedback__enable if enable else TR.haptic_feedback__disable,
            subtitle=TR.haptic_feedback__subtitle,
            br_code=BRT_PROTECT_CALL,
            prompt_screen=True,
        )
