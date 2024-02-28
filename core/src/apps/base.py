from typing import TYPE_CHECKING

import storage.cache as storage_cache
import storage.device as storage_device
from trezor import TR, config, utils, wire, workflow
from trezor.enums import HomescreenFormat, MessageType
from trezor.messages import Success, UnlockPath
from trezor.ui.layouts import confirm_action

from . import workflow_handlers

if TYPE_CHECKING:
    from trezor import protobuf
    from trezor.messages import (
        Cancel,
        CancelAuthorization,
        DoPreauthorized,
        EndSession,
        Features,
        GetFeatures,
        Initialize,
        LockDevice,
        Ping,
        SetBusy,
    )


_SCREENSAVER_IS_ON = False


def busy_expiry_ms() -> int:
    """
    Returns the time left until the busy state expires or 0 if the device is not in the busy state.
    """

    busy_deadline_ms = storage_cache.get_int(storage_cache.APP_COMMON_BUSY_DEADLINE_MS)
    if busy_deadline_ms is None:
        return 0

    import utime

    expiry_ms = utime.ticks_diff(busy_deadline_ms, utime.ticks_ms())
    return expiry_ms if expiry_ms > 0 else 0


def _language_version_matches() -> bool | None:
    """
    Whether translation blob version matches firmware version.
    Returns None if there is no blob.
    """
    from trezor import translations

    header = translations.TranslationsHeader.load_from_flash()
    if header is None:
        return True

    return header.version == utils.VERSION


def get_features() -> Features:
    import storage.recovery as storage_recovery
    from trezor import translations
    from trezor.enums import Capability
    from trezor.messages import Features
    from trezor.ui import HEIGHT, WIDTH

    from apps.common import mnemonic, safety_checks

    v_major, v_minor, v_patch, _v_build = utils.VERSION

    f = Features(
        vendor="trezor.io",
        fw_vendor=utils.firmware_vendor(),
        language=translations.get_language(),
        language_version_matches=_language_version_matches(),
        major_version=v_major,
        minor_version=v_minor,
        patch_version=v_patch,
        revision=utils.SCM_REVISION,
        model=utils.MODEL,
        internal_model=utils.INTERNAL_MODEL,
        device_id=storage_device.get_device_id(),
        label=storage_device.get_label(),
        pin_protection=config.has_pin(),
        unlocked=config.is_unlocked(),
        busy=busy_expiry_ms() > 0,
        homescreen_width=WIDTH,
        homescreen_height=HEIGHT,
        unit_color=utils.unit_color(),
        unit_btconly=utils.unit_btconly(),
        bootloader_locked=utils.bootloader_locked(),
    )

    if utils.INTERNAL_MODEL in ("T1B1", "T2B1"):
        f.homescreen_format = HomescreenFormat.ToiG
    else:
        f.homescreen_format = HomescreenFormat.Jpeg

    if utils.BITCOIN_ONLY:
        f.capabilities = [
            Capability.Bitcoin,
            Capability.Crypto,
            Capability.Shamir,
            Capability.ShamirGroups,
            Capability.PassphraseEntry,
            Capability.Translations,
        ]
    else:
        f.capabilities = [
            Capability.Bitcoin,
            Capability.Bitcoin_like,
            Capability.Binance,
            Capability.Cardano,
            Capability.Crypto,
            Capability.Ethereum,
            Capability.Monero,
            Capability.Ripple,
            Capability.Stellar,
            Capability.Tezos,
            Capability.U2F,
            Capability.Shamir,
            Capability.ShamirGroups,
            Capability.PassphraseEntry,
            Capability.Solana,
            Capability.Translations,
        ]

        # We do not support some currencies on T2B1
        if not utils.MODEL_IS_T2B1:
            f.capabilities.extend(
                [
                    Capability.NEM,
                    Capability.EOS,
                ]
            )

    # Only some models are capable of SD card
    if utils.USE_SD_CARD:
        from trezor import sdcard

        f.sd_card_present = sdcard.is_present()
    else:
        f.sd_card_present = False

    f.initialized = storage_device.is_initialized()

    # private fields:
    if config.is_unlocked():
        # passphrase_protection is private, see #1807
        f.passphrase_protection = storage_device.is_passphrase_enabled()
        f.needs_backup = storage_device.needs_backup()
        f.unfinished_backup = storage_device.unfinished_backup()
        f.no_backup = storage_device.no_backup()
        f.flags = storage_device.get_flags()
        f.recovery_mode = storage_recovery.is_in_progress()
        f.backup_type = mnemonic.get_type()

        # Only some models are capable of SD card
        if utils.USE_SD_CARD:
            import storage.sd_salt as storage_sd_salt

            f.sd_protection = storage_sd_salt.is_enabled()
        else:
            f.sd_protection = False

        f.wipe_code_protection = config.has_wipe_code()
        f.passphrase_always_on_device = storage_device.get_passphrase_always_on_device()
        f.safety_checks = safety_checks.read_setting()
        f.auto_lock_delay_ms = storage_device.get_autolock_delay_ms()
        f.display_rotation = storage_device.get_rotation()
        f.experimental_features = storage_device.get_experimental_features()
        f.hide_passphrase_from_host = storage_device.get_hide_passphrase_from_host()

    return f


async def handle_Initialize(msg: Initialize) -> Features:
    session_id = storage_cache.start_session(msg.session_id)

    if not utils.BITCOIN_ONLY:
        derive_cardano = storage_cache.get(storage_cache.APP_COMMON_DERIVE_CARDANO)
        have_seed = storage_cache.is_set(storage_cache.APP_COMMON_SEED)

        if (
            have_seed
            and msg.derive_cardano is not None
            and msg.derive_cardano != bool(derive_cardano)
        ):
            # seed is already derived, and host wants to change derive_cardano setting
            # => create a new session
            storage_cache.end_current_session()
            session_id = storage_cache.start_session()
            have_seed = False

        if not have_seed:
            storage_cache.set(
                storage_cache.APP_COMMON_DERIVE_CARDANO,
                b"\x01" if msg.derive_cardano else b"",
            )

    features = get_features()
    features.session_id = session_id
    return features


async def handle_GetFeatures(msg: GetFeatures) -> Features:
    return get_features()


async def handle_Cancel(msg: Cancel) -> Success:
    raise wire.ActionCancelled


async def handle_LockDevice(msg: LockDevice) -> Success:
    lock_device()
    return Success()


async def handle_SetBusy(msg: SetBusy) -> Success:
    if not storage_device.is_initialized():
        raise wire.NotInitialized("Device is not initialized")

    if msg.expiry_ms:
        import utime

        deadline = utime.ticks_add(utime.ticks_ms(), msg.expiry_ms)
        storage_cache.set_int(storage_cache.APP_COMMON_BUSY_DEADLINE_MS, deadline)
    else:
        storage_cache.delete(storage_cache.APP_COMMON_BUSY_DEADLINE_MS)
    set_homescreen()
    workflow.close_others()
    return Success()


async def handle_EndSession(msg: EndSession) -> Success:
    storage_cache.end_current_session()
    return Success()


async def handle_Ping(msg: Ping) -> Success:
    if msg.button_protection:
        from trezor.enums import ButtonRequestType as B
        from trezor.ui.layouts import confirm_action

        await confirm_action("ping", TR.words__confirm, "ping", br_code=B.ProtectCall)
    return Success(message=msg.message)


async def handle_DoPreauthorized(msg: DoPreauthorized) -> protobuf.MessageType:
    from trezor.messages import PreauthorizedRequest
    from trezor.wire.context import call_any, get_context

    from apps.common import authorization

    if not authorization.is_set():
        raise wire.ProcessError("No preauthorized operation")

    wire_types = authorization.get_wire_types()
    utils.ensure(bool(wire_types), "Unsupported preauthorization found")

    req = await call_any(PreauthorizedRequest(), *wire_types)

    assert req.MESSAGE_WIRE_TYPE is not None
    handler = workflow_handlers.find_registered_handler(
        get_context().iface, req.MESSAGE_WIRE_TYPE
    )
    if handler is None:
        return wire.unexpected_message()

    return await handler(req, authorization.get())  # type: ignore [Expected 1 positional argument]


async def handle_UnlockPath(msg: UnlockPath) -> protobuf.MessageType:
    from trezor.crypto import hmac
    from trezor.messages import UnlockedPathRequest
    from trezor.wire.context import call_any, get_context

    from apps.common.paths import SLIP25_PURPOSE
    from apps.common.seed import Slip21Node, get_seed
    from apps.common.writers import write_uint32_le

    _KEYCHAIN_MAC_KEY_PATH = [b"TREZOR", b"Keychain MAC key"]

    # UnlockPath is relevant only for SLIP-25 paths.
    # Note: Currently we only allow unlocking the entire SLIP-25 purpose subtree instead of
    # per-coin or per-account unlocking in order to avoid UI complexity.
    if msg.address_n != [SLIP25_PURPOSE]:
        raise wire.DataError("Invalid path")

    seed = await get_seed()
    node = Slip21Node(seed)
    node.derive_path(_KEYCHAIN_MAC_KEY_PATH)
    mac = utils.HashWriter(hmac(hmac.SHA256, node.key()))
    for i in msg.address_n:
        write_uint32_le(mac, i)
    expected_mac = mac.get_digest()

    # Require confirmation to access SLIP25 paths unless already authorized.
    if msg.mac:
        if len(msg.mac) != len(expected_mac) or not utils.consteq(
            expected_mac, msg.mac
        ):
            raise wire.DataError("Invalid MAC")
    else:
        await confirm_action(
            "confirm_coinjoin_access",
            title="Coinjoin",
            description=TR.coinjoin__access_account,
            verb=TR.buttons__access,
        )

    wire_types = (MessageType.GetAddress, MessageType.GetPublicKey, MessageType.SignTx)
    req = await call_any(UnlockedPathRequest(mac=expected_mac), *wire_types)

    assert req.MESSAGE_WIRE_TYPE in wire_types
    handler = workflow_handlers.find_registered_handler(
        get_context().iface, req.MESSAGE_WIRE_TYPE
    )
    assert handler is not None
    return await handler(req, msg)  # type: ignore [Expected 1 positional argument]


async def handle_CancelAuthorization(msg: CancelAuthorization) -> protobuf.MessageType:
    from apps.common import authorization

    authorization.clear()
    workflow.close_others()
    return Success(message="Authorization cancelled")


def set_homescreen() -> None:
    import storage.recovery as storage_recovery

    set_default = workflow.set_default  # local_cache_attribute

    if storage_cache.is_set(storage_cache.APP_COMMON_BUSY_DEADLINE_MS):
        from apps.homescreen import busyscreen

        set_default(busyscreen)

    elif not config.is_unlocked():
        from apps.homescreen import lockscreen

        set_default(lockscreen)

    elif _SCREENSAVER_IS_ON:
        from apps.homescreen import screensaver

        set_default(screensaver, restart=True)

    elif storage_recovery.is_in_progress():
        from apps.management.recovery_device.homescreen import recovery_homescreen

        set_default(recovery_homescreen)

    else:
        from apps.homescreen import homescreen

        set_default(homescreen)


def lock_device(interrupt_workflow: bool = True) -> None:
    if config.has_pin():
        config.lock()
        wire.find_handler = get_pinlocked_handler
        set_homescreen()
        if interrupt_workflow:
            workflow.close_others()


def lock_device_if_unlocked() -> None:
    from apps.common.request_pin import can_lock_device

    if not utils.USE_BACKLIGHT and not can_lock_device():
        # on OLED devices without PIN, trigger screensaver
        global _SCREENSAVER_IS_ON

        _SCREENSAVER_IS_ON = True
        set_homescreen()

    elif config.is_unlocked():
        lock_device(interrupt_workflow=workflow.autolock_interrupts_workflow)


async def unlock_device() -> None:
    """Ensure the device is in unlocked state.

    If the storage is locked, attempt to unlock it. Reset the homescreen and the wire
    handler.
    """
    from apps.common.request_pin import verify_user_pin

    global _SCREENSAVER_IS_ON

    if not config.is_unlocked():
        # verify_user_pin will raise if the PIN was invalid
        await verify_user_pin()

    _SCREENSAVER_IS_ON = False
    set_homescreen()
    wire.find_handler = workflow_handlers.find_registered_handler


def get_pinlocked_handler(
    iface: wire.WireInterface, msg_type: int
) -> wire.Handler[wire.Msg] | None:
    orig_handler = workflow_handlers.find_registered_handler(iface, msg_type)
    if orig_handler is None:
        return None

    if __debug__:
        import usb

        if iface is usb.iface_debug:
            return orig_handler

    if msg_type in workflow.ALLOW_WHILE_LOCKED:
        return orig_handler

    async def wrapper(msg: wire.Msg) -> protobuf.MessageType:
        await unlock_device()
        return await orig_handler(msg)

    return wrapper


# this function is also called when handling ApplySettings
def reload_settings_from_storage() -> None:
    from trezor import ui

    workflow.idle_timer.set(
        storage_device.get_autolock_delay_ms(), lock_device_if_unlocked
    )
    wire.EXPERIMENTAL_ENABLED = storage_device.get_experimental_features()
    if ui.display.orientation() != storage_device.get_rotation():
        ui.backlight_fade(ui.style.BACKLIGHT_DIM)
        ui.display.orientation(storage_device.get_rotation())


def boot() -> None:
    MT = MessageType  # local_cache_global

    # Register workflow handlers
    for msg_type, handler in (
        (MT.Initialize, handle_Initialize),
        (MT.GetFeatures, handle_GetFeatures),
        (MT.Cancel, handle_Cancel),
        (MT.LockDevice, handle_LockDevice),
        (MT.EndSession, handle_EndSession),
        (MT.Ping, handle_Ping),
        (MT.DoPreauthorized, handle_DoPreauthorized),
        (MT.UnlockPath, handle_UnlockPath),
        (MT.CancelAuthorization, handle_CancelAuthorization),
        (MT.SetBusy, handle_SetBusy),
    ):
        workflow_handlers.register(msg_type, handler)  # type: ignore [cannot be assigned to type]

    reload_settings_from_storage()
    if config.is_unlocked():
        wire.find_handler = workflow_handlers.find_registered_handler
    else:
        wire.find_handler = get_pinlocked_handler
