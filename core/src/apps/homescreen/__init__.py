from trezor import config, io, utils, wire
from trezor.messages import Capability, MessageType
from trezor.messages.Features import Features
from trezor.messages.Success import Success
from trezor.wire import register

from apps.common import cache, mnemonic, storage
from apps.common.storage import device as storage_device, recovery as storage_recovery

if False:
    from typing import NoReturn
    from trezor.messages.Initialize import Initialize
    from trezor.messages.GetFeatures import GetFeatures
    from trezor.messages.Cancel import Cancel
    from trezor.messages.ClearSession import ClearSession
    from trezor.messages.Ping import Ping


def get_features() -> Features:
    f = Features()
    f.vendor = "trezor.io"
    f.language = "english"
    f.major_version = utils.VERSION_MAJOR
    f.minor_version = utils.VERSION_MINOR
    f.patch_version = utils.VERSION_PATCH
    f.revision = utils.GITREV.encode()
    f.model = utils.MODEL
    f.device_id = storage_device.get_device_id()
    f.label = storage_device.get_label()
    f.initialized = storage.is_initialized()
    f.pin_protection = config.has_pin()
    f.pin_cached = config.has_pin()
    f.passphrase_protection = storage_device.has_passphrase()
    f.passphrase_cached = cache.has_passphrase()
    f.needs_backup = storage_device.needs_backup()
    f.unfinished_backup = storage_device.unfinished_backup()
    f.no_backup = storage_device.no_backup()
    f.flags = storage_device.get_flags()
    f.recovery_mode = storage_recovery.is_in_progress()
    f.backup_type = mnemonic.get_type()
    if utils.BITCOIN_ONLY:
        f.capabilities = [
            Capability.Bitcoin,
            Capability.Crypto,
            Capability.Shamir,
            Capability.ShamirGroups,
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
        ]
    f.sd_card_present = io.SDCard().present()
    f.sd_protection = storage.device.get_sd_salt_auth_key() is not None
    return f


async def handle_Initialize(ctx: wire.Context, msg: Initialize) -> Features:
    if msg.state is None or msg.state != cache.get_state(prev_state=bytes(msg.state)):
        cache.clear()
        if msg.skip_passphrase:
            cache.set_passphrase("")
    return get_features()


async def handle_GetFeatures(ctx: wire.Context, msg: GetFeatures) -> Features:
    return get_features()


async def handle_Cancel(ctx: wire.Context, msg: Cancel) -> NoReturn:
    raise wire.ActionCancelled("Cancelled")


async def handle_ClearSession(ctx: wire.Context, msg: ClearSession) -> Success:
    cache.clear(keep_passphrase=True)
    return Success(message="Session cleared")


async def handle_Ping(ctx: wire.Context, msg: Ping) -> Success:
    if msg.button_protection:
        from apps.common.confirm import require_confirm
        from trezor.messages.ButtonRequestType import ProtectCall
        from trezor.ui.text import Text

        await require_confirm(ctx, Text("Confirm"), ProtectCall)
    if msg.passphrase_protection:
        from apps.common.request_passphrase import protect_by_passphrase

        await protect_by_passphrase(ctx)
    return Success(message=msg.message)


def boot() -> None:
    register(MessageType.Initialize, handle_Initialize)
    register(MessageType.GetFeatures, handle_GetFeatures)
    register(MessageType.Cancel, handle_Cancel)
    register(MessageType.ClearSession, handle_ClearSession)
    register(MessageType.Ping, handle_Ping)
