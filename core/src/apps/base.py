import storage
import storage.device
import storage.recovery
import storage.sd_salt
from storage import cache
from trezor import config, sdcard, utils, wire, workflow
from trezor.messages import Capability, MessageType
from trezor.messages.Features import Features
from trezor.messages.PreauthorizedRequest import PreauthorizedRequest
from trezor.messages.Success import Success

from apps.common import mnemonic, safety_checks
from apps.common.request_pin import verify_user_pin

if False:
    import protobuf
    from typing import Iterable, NoReturn, Optional, Protocol
    from trezor.messages.Initialize import Initialize
    from trezor.messages.EndSession import EndSession
    from trezor.messages.GetFeatures import GetFeatures
    from trezor.messages.Cancel import Cancel
    from trezor.messages.LockDevice import LockDevice
    from trezor.messages.Ping import Ping
    from trezor.messages.DoPreauthorized import DoPreauthorized
    from trezor.messages.CancelAuthorization import CancelAuthorization

if False:

    class Authorization(Protocol):
        def expected_wire_types(self) -> Iterable[int]:
            ...

        def __del__(self) -> None:
            ...


def get_features() -> Features:
    f = Features(
        vendor="trezor.io",
        language="en-US",
        major_version=utils.VERSION_MAJOR,
        minor_version=utils.VERSION_MINOR,
        patch_version=utils.VERSION_PATCH,
        revision=utils.GITREV.encode(),
        model=utils.MODEL,
        device_id=storage.device.get_device_id(),
        label=storage.device.get_label(),
        pin_protection=config.has_pin(),
        unlocked=config.is_unlocked(),
        passphrase_protection=storage.device.is_passphrase_enabled(),
    )

    if utils.BITCOIN_ONLY:
        f.capabilities = [
            Capability.Bitcoin,
            Capability.Crypto,
            Capability.Shamir,
            Capability.ShamirGroups,
            Capability.PassphraseEntry,
        ]
    else:
        f.capabilities = [
            Capability.Bitcoin,
            Capability.Bitcoin_like,
            Capability.Binance,
            Capability.Cardano,
            Capability.Crypto,
            Capability.EOS,
            Capability.Ethereum,
            Capability.Lisk,
            Capability.Monero,
            Capability.NEM,
            Capability.Ripple,
            Capability.Stellar,
            Capability.Tezos,
            Capability.U2F,
            Capability.Shamir,
            Capability.ShamirGroups,
            Capability.PassphraseEntry,
        ]
    f.sd_card_present = sdcard.is_present()
    f.initialized = storage.device.is_initialized()

    # private fields:
    if config.is_unlocked():

        f.needs_backup = storage.device.needs_backup()
        f.unfinished_backup = storage.device.unfinished_backup()
        f.no_backup = storage.device.no_backup()
        f.flags = storage.device.get_flags()
        f.recovery_mode = storage.recovery.is_in_progress()
        f.backup_type = mnemonic.get_type()
        f.sd_protection = storage.sd_salt.is_enabled()
        f.wipe_code_protection = config.has_wipe_code()
        f.passphrase_always_on_device = storage.device.get_passphrase_always_on_device()
        f.safety_checks = safety_checks.read_setting()
        f.auto_lock_delay_ms = storage.device.get_autolock_delay_ms()
        f.display_rotation = storage.device.get_rotation()
        f.experimental_features = storage.device.get_experimental_features()

    return f


async def handle_Initialize(ctx: wire.Context, msg: Initialize) -> Features:
    features = get_features()
    if msg.session_id:
        msg.session_id = bytes(msg.session_id)
    features.session_id = cache.start_session(msg.session_id)
    return features


async def handle_GetFeatures(ctx: wire.Context, msg: GetFeatures) -> Features:
    return get_features()


async def handle_Cancel(ctx: wire.Context, msg: Cancel) -> NoReturn:
    raise wire.ActionCancelled


async def handle_LockDevice(ctx: wire.Context, msg: LockDevice) -> Success:
    lock_device()
    return Success()


async def handle_EndSession(ctx: wire.Context, msg: EndSession) -> Success:
    cache.end_current_session()
    return Success()


async def handle_Ping(ctx: wire.Context, msg: Ping) -> Success:
    if msg.button_protection:
        from apps.common.confirm import require_confirm
        from trezor.messages.ButtonRequestType import ProtectCall
        from trezor.ui.text import Text

        await require_confirm(ctx, Text("Confirm"), ProtectCall)
    return Success(message=msg.message)


async def handle_DoPreauthorized(
    ctx: wire.Context, msg: DoPreauthorized
) -> protobuf.MessageType:
    authorization: Authorization = storage.cache.get(
        storage.cache.APP_BASE_AUTHORIZATION
    )
    if not authorization:
        raise wire.ProcessError("No preauthorized operation")

    req = await ctx.call_any(
        PreauthorizedRequest(), *authorization.expected_wire_types()
    )

    handler = wire.find_registered_workflow_handler(ctx.iface, req.MESSAGE_WIRE_TYPE)
    if handler is None:
        return wire.unexpected_message()

    return await handler(ctx, req, authorization)  # type: ignore


def set_authorization(authorization: Authorization) -> None:
    previous: Authorization = storage.cache.get(storage.cache.APP_BASE_AUTHORIZATION)
    if previous:
        previous.__del__()
    storage.cache.set(storage.cache.APP_BASE_AUTHORIZATION, authorization)


async def handle_CancelAuthorization(
    ctx: wire.Context, msg: CancelAuthorization
) -> protobuf.MessageType:
    authorization: Authorization = storage.cache.get(
        storage.cache.APP_BASE_AUTHORIZATION
    )
    if not authorization:
        raise wire.ProcessError("No preauthorized operation")

    authorization.__del__()
    storage.cache.delete(storage.cache.APP_BASE_AUTHORIZATION)

    return Success(message="Authorization cancelled")


ALLOW_WHILE_LOCKED = (
    MessageType.Initialize,
    MessageType.EndSession,
    MessageType.GetFeatures,
    MessageType.Cancel,
    MessageType.LockDevice,
    MessageType.DoPreauthorized,
    MessageType.WipeDevice,
)


def set_homescreen() -> None:
    if not config.is_unlocked():
        from apps.homescreen.lockscreen import lockscreen

        workflow.set_default(lockscreen)

    elif storage.recovery.is_in_progress():
        from apps.management.recovery_device.homescreen import recovery_homescreen

        workflow.set_default(recovery_homescreen)

    else:
        from apps.homescreen.homescreen import homescreen

        workflow.set_default(homescreen)


def lock_device() -> None:
    if config.has_pin():
        config.lock()
        wire.find_handler = get_pinlocked_handler
        set_homescreen()
        workflow.close_others()


async def unlock_device(ctx: wire.GenericContext = wire.DUMMY_CONTEXT) -> None:
    """Ensure the device is in unlocked state.

    If the storage is locked, attempt to unlock it. Reset the homescreen and the wire
    handler.
    """
    if not config.is_unlocked():
        # verify_user_pin will raise if the PIN was invalid
        await verify_user_pin(ctx)

    set_homescreen()
    wire.find_handler = wire.find_registered_workflow_handler


def get_pinlocked_handler(
    iface: wire.WireInterface, msg_type: int
) -> Optional[wire.Handler[wire.Msg]]:
    orig_handler = wire.find_registered_workflow_handler(iface, msg_type)
    if orig_handler is None:
        return None

    if __debug__:
        import usb

        if iface is usb.iface_debug:
            return orig_handler

    if msg_type in ALLOW_WHILE_LOCKED:
        return orig_handler

    async def wrapper(ctx: wire.Context, msg: wire.Msg) -> protobuf.MessageType:
        # mypy limitation: orig_handler is not recognized as non-None
        assert orig_handler is not None
        await unlock_device(ctx)
        return await orig_handler(ctx, msg)

    return wrapper


def boot() -> None:
    wire.register(MessageType.Initialize, handle_Initialize)
    wire.register(MessageType.GetFeatures, handle_GetFeatures)
    wire.register(MessageType.Cancel, handle_Cancel)
    wire.register(MessageType.LockDevice, handle_LockDevice)
    wire.register(MessageType.EndSession, handle_EndSession)
    wire.register(MessageType.Ping, handle_Ping)
    wire.register(MessageType.DoPreauthorized, handle_DoPreauthorized)
    wire.register(MessageType.CancelAuthorization, handle_CancelAuthorization)

    wire.experimental_enabled = storage.device.get_experimental_features()

    workflow.idle_timer.set(storage.device.get_autolock_delay_ms(), lock_device)
