import storage
import storage.device
import storage.recovery
import storage.sd_salt
from storage import cache
from trezor import config, io, utils, wire
from trezor.messages import Capability, MessageType
from trezor.messages.Features import Features
from trezor.messages.Success import Success
from trezor.wire import register

from apps.common import mnemonic

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
    f.language = "en-US"
    f.major_version = utils.VERSION_MAJOR
    f.minor_version = utils.VERSION_MINOR
    f.patch_version = utils.VERSION_PATCH
    f.revision = utils.GITREV.encode()
    f.model = utils.MODEL
    f.device_id = storage.device.get_device_id()
    f.label = storage.device.get_label()
    f.initialized = storage.is_initialized()
    f.pin_protection = config.has_pin()
    f.pin_cached = config.has_pin()
    f.passphrase_protection = storage.device.is_passphrase_enabled()
    # f.passphrase_cached = cache.has_passphrase()  # TODO
    f.needs_backup = storage.device.needs_backup()
    f.unfinished_backup = storage.device.unfinished_backup()
    f.no_backup = storage.device.no_backup()
    f.flags = storage.device.get_flags()
    f.recovery_mode = storage.recovery.is_in_progress()
    f.backup_type = mnemonic.get_type()
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
    f.sd_card_present = io.SDCard().present()
    f.sd_protection = storage.sd_salt.is_enabled()
    f.wipe_code_protection = config.has_wipe_code()
    f.session_id = cache.get_session_id()
    f.passphrase_always_on_device = storage.device.get_passphrase_always_on_device()
    return f


async def handle_Initialize(ctx: wire.Context, msg: Initialize) -> Features:
    if msg.session_id is None or msg.session_id != cache.get_session_id():
        cache.clear()
    return get_features()


async def handle_GetFeatures(ctx: wire.Context, msg: GetFeatures) -> Features:
    return get_features()


async def handle_Cancel(ctx: wire.Context, msg: Cancel) -> NoReturn:
    raise wire.ActionCancelled("Cancelled")


async def handle_ClearSession(ctx: wire.Context, msg: ClearSession) -> Success:
    cache.clear()
    return Success(message="Session cleared")


async def handle_Ping(ctx: wire.Context, msg: Ping) -> Success:
    if msg.button_protection:
        from apps.common.confirm import require_confirm
        from trezor.messages.ButtonRequestType import ProtectCall
        from trezor.ui.text import Text

        await require_confirm(ctx, Text("Confirm"), ProtectCall)
    if msg.passphrase_protection:  # TODO
        from apps.common import passphrase

        await passphrase.get(ctx)
    return Success(message=msg.message)


def boot() -> None:
    register(MessageType.Initialize, handle_Initialize)
    register(MessageType.GetFeatures, handle_GetFeatures)
    register(MessageType.Cancel, handle_Cancel)
    register(MessageType.ClearSession, handle_ClearSession)
    register(MessageType.Ping, handle_Ping)
