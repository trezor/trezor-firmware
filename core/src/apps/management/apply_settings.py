import storage.device
from trezor import ui, wire
from trezor.messages import ButtonRequestType, SafetyCheckLevel, Success
from trezor.strings import format_duration_ms
from trezor.ui.layouts import confirm_action

from apps.base import reload_settings_from_storage
from apps.common import safety_checks

if False:
    from trezor.messages import ApplySettings, EnumTypeSafetyCheckLevel


def validate_homescreen(homescreen: bytes) -> None:
    if homescreen == b"":
        return

    if len(homescreen) > storage.device.HOMESCREEN_MAXSIZE:
        raise wire.DataError(
            "Homescreen is too large, maximum size is {} bytes".format(
                storage.device.HOMESCREEN_MAXSIZE
            )
        )

    try:
        w, h, grayscale = ui.display.toif_info(homescreen)
    except ValueError:
        raise wire.DataError("Invalid homescreen")
    if w != 144 or h != 144:
        raise wire.DataError("Homescreen must be 144x144 pixel large")
    if grayscale:
        raise wire.DataError("Homescreen must be full-color TOIF image")


async def apply_settings(ctx: wire.Context, msg: ApplySettings):
    if not storage.device.is_initialized():
        raise wire.NotInitialized("Device is not initialized")
    if (
        msg.homescreen is None
        and msg.label is None
        and msg.use_passphrase is None
        and msg.passphrase_always_on_device is None
        and msg.display_rotation is None
        and msg.auto_lock_delay_ms is None
        and msg.safety_checks is None
        and msg.experimental_features is None
    ):
        raise wire.ProcessError("No setting provided")

    if msg.homescreen is not None:
        validate_homescreen(msg.homescreen)
        await require_confirm_change_homescreen(ctx)
        try:
            storage.device.set_homescreen(msg.homescreen)
        except ValueError:
            raise wire.DataError("Invalid homescreen")

    if msg.label is not None:
        if len(msg.label) > storage.device.LABEL_MAXLENGTH:
            raise wire.DataError("Label too long")
        await require_confirm_change_label(ctx, msg.label)
        storage.device.set_label(msg.label)

    if msg.use_passphrase is not None:
        await require_confirm_change_passphrase(ctx, msg.use_passphrase)
        storage.device.set_passphrase_enabled(msg.use_passphrase)

    if msg.passphrase_always_on_device is not None:
        if not storage.device.is_passphrase_enabled():
            raise wire.DataError("Passphrase is not enabled")
        await require_confirm_change_passphrase_source(
            ctx, msg.passphrase_always_on_device
        )
        storage.device.set_passphrase_always_on_device(msg.passphrase_always_on_device)

    if msg.auto_lock_delay_ms is not None:
        if msg.auto_lock_delay_ms < storage.device.AUTOLOCK_DELAY_MINIMUM:
            raise wire.ProcessError("Auto-lock delay too short")
        if msg.auto_lock_delay_ms > storage.device.AUTOLOCK_DELAY_MAXIMUM:
            raise wire.ProcessError("Auto-lock delay too long")
        await require_confirm_change_autolock_delay(ctx, msg.auto_lock_delay_ms)
        storage.device.set_autolock_delay_ms(msg.auto_lock_delay_ms)

    if msg.safety_checks is not None:
        await require_confirm_safety_checks(ctx, msg.safety_checks)
        safety_checks.apply_setting(msg.safety_checks)

    if msg.display_rotation is not None:
        await require_confirm_change_display_rotation(ctx, msg.display_rotation)
        storage.device.set_rotation(msg.display_rotation)

    if msg.experimental_features is not None:
        await require_confirm_experimental_features(ctx, msg.experimental_features)
        storage.device.set_experimental_features(msg.experimental_features)

    reload_settings_from_storage()

    return Success(message="Settings applied")


async def require_confirm_change_homescreen(ctx):
    await confirm_action(
        ctx,
        "set_homescreen",
        "Set homescreen",
        description="Do you really want to change the homescreen image?",
        br_code=ButtonRequestType.ProtectCall,
    )


async def require_confirm_change_label(ctx, label):
    await confirm_action(
        ctx,
        "set_label",
        "Change label",
        description="Do you really want to change the label to {}?",
        description_param=label,
        br_code=ButtonRequestType.ProtectCall,
    )


async def require_confirm_change_passphrase(ctx, use):
    if use:
        description = "Do you really want to enable passphrase encryption?"
    else:
        description = "Do you really want to disable passphrase encryption?"
    await confirm_action(
        ctx,
        "set_passphrase",
        "Enable passphrase" if use else "Disable passphrase",
        description=description,
        br_code=ButtonRequestType.ProtectCall,
    )


async def require_confirm_change_passphrase_source(
    ctx, passphrase_always_on_device: bool
):
    if passphrase_always_on_device:
        description = "Do you really want to enter passphrase always on the device?"
    else:
        description = "Do you want to revoke the passphrase on device setting?"
    await confirm_action(
        ctx,
        "set_passphrase_source",
        "Passphrase source",
        description=description,
        br_code=ButtonRequestType.ProtectCall,
    )


async def require_confirm_change_display_rotation(ctx, rotation):
    if rotation == 0:
        label = "north"
    elif rotation == 90:
        label = "east"
    elif rotation == 180:
        label = "south"
    elif rotation == 270:
        label = "west"
    else:
        raise wire.DataError("Unsupported display rotation")
    await confirm_action(
        ctx,
        "set_rotation",
        "Change rotation",
        description="Do you really want to change display rotation to {}?",
        description_param=label,
        br_code=ButtonRequestType.ProtectCall,
    )


async def require_confirm_change_autolock_delay(ctx, delay_ms):
    await confirm_action(
        ctx,
        "set_autolock_delay",
        "Auto-lock delay",
        description="Do you really want to auto-lock your device after {}?",
        description_param=format_duration_ms(delay_ms),
        br_code=ButtonRequestType.ProtectCall,
    )


async def require_confirm_safety_checks(ctx, level: EnumTypeSafetyCheckLevel) -> None:
    if level == SafetyCheckLevel.PromptAlways:
        await confirm_action(
            ctx,
            "set_safety_checks",
            "Safety override",
            hold=True,
            verb="Hold to confirm",
            description="Trezor will allow you to approve some actions which might be unsafe.",
            action="Are you sure?",
            reverse=True,
            larger_vspace=True,
            br_code=ButtonRequestType.ProtectCall,
        )
    elif level == SafetyCheckLevel.PromptTemporarily:
        await confirm_action(
            ctx,
            "set_safety_checks",
            "Safety override",
            hold=True,
            verb="Hold to confirm",
            description="Trezor will temporarily allow you to approve some actions which might be unsafe.",
            action="Are you sure?",
            reverse=True,
            br_code=ButtonRequestType.ProtectCall,
        )
    elif level == SafetyCheckLevel.Strict:
        await confirm_action(
            ctx,
            "set_safety_checks",
            "Safety checks",
            description="Do you really want to enforce strict safety checks (recommended)?",
            br_code=ButtonRequestType.ProtectCall,
        )
    else:
        raise ValueError  # enum value out of range


async def require_confirm_experimental_features(ctx, enable: bool) -> None:
    if enable:
        await confirm_action(
            ctx,
            "set_experimental_features",
            "Experimental mode",
            description="Enable experimental features?",
            action="Only for development and beta testing!",
            reverse=True,
            br_code=ButtonRequestType.ProtectCall,
        )
