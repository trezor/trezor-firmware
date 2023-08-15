from typing import TYPE_CHECKING

from apps.common.keychain import auto_keychain
from apps.monero import layout, misc

if TYPE_CHECKING:
    from trezor.messages import (
        MoneroLiveRefreshFinalAck,
        MoneroLiveRefreshStartAck,
        MoneroLiveRefreshStartRequest,
        MoneroLiveRefreshStepAck,
        MoneroLiveRefreshStepRequest,
    )
    from trezor.ui.layouts.common import ProgressLayout

    from apps.common.keychain import Keychain

    from .xmr.credentials import AccountCreds


@auto_keychain(__name__)
async def live_refresh(
    msg: MoneroLiveRefreshStartRequest, keychain: Keychain
) -> MoneroLiveRefreshFinalAck:
    import gc

    from trezor.enums import MessageType
    from trezor.messages import MoneroLiveRefreshFinalAck, MoneroLiveRefreshStepRequest
    from trezor.wire.context import call_any

    state = LiveRefreshState()

    res = await _init_step(state, msg, keychain)
    progress = layout.monero_live_refresh_progress()
    while True:
        step = await call_any(
            res,
            MessageType.MoneroLiveRefreshStepRequest,
            MessageType.MoneroLiveRefreshFinalRequest,
        )
        del res
        if MoneroLiveRefreshStepRequest.is_type_of(step):
            res = _refresh_step(state, step, progress)
        else:
            return MoneroLiveRefreshFinalAck()
        gc.collect()


class LiveRefreshState:
    def __init__(self) -> None:
        self.current_output = 0
        self.creds: AccountCreds | None = None


async def _init_step(
    s: LiveRefreshState,
    msg: MoneroLiveRefreshStartRequest,
    keychain: Keychain,
) -> MoneroLiveRefreshStartAck:
    import storage.cache as storage_cache
    from trezor.messages import MoneroLiveRefreshStartAck

    from apps.common import paths

    await paths.validate_path(keychain, msg.address_n)

    if not storage_cache.get(storage_cache.APP_MONERO_LIVE_REFRESH):
        await layout.require_confirm_live_refresh()
        storage_cache.set(storage_cache.APP_MONERO_LIVE_REFRESH, b"\x01")

    s.creds = misc.get_creds(keychain, msg.address_n, msg.network_type)

    return MoneroLiveRefreshStartAck()


def _refresh_step(
    s: LiveRefreshState,
    msg: MoneroLiveRefreshStepRequest,
    progress: ProgressLayout,
) -> MoneroLiveRefreshStepAck:
    from trezor import log
    from trezor.messages import MoneroLiveRefreshStepAck

    from apps.monero.xmr import chacha_poly, crypto, crypto_helpers, key_image, monero

    assert s.creds is not None

    buff = bytearray(32 * 3)
    buff_mv = memoryview(buff)

    progress.report((1000 * s.current_output // 8) % 1000, str(s.current_output))
    s.current_output += 1

    if __debug__:
        log.debug(__name__, "refresh, step i: %d", s.current_output)

    # Compute spending secret key and the key image
    # spend_priv = Hs(recv_deriv || real_out_idx) + spend_key_private
    # If subaddr:
    #   spend_priv += Hs("SubAddr" || view_key_private || major || minor)
    # out_key = spend_priv * G, KI: spend_priv * Hp(out_key)
    out_key = crypto_helpers.decodepoint(msg.out_key)
    recv_deriv = crypto_helpers.decodepoint(msg.recv_deriv)
    received_index = msg.sub_addr_major, msg.sub_addr_minor
    spend_priv, ki = monero.generate_tx_spend_and_key_image(
        s.creds, out_key, recv_deriv, msg.real_out_idx, received_index
    )

    ki_enc = crypto_helpers.encodepoint(ki)
    sig = key_image.generate_ring_signature(ki_enc, ki, [out_key], spend_priv, 0, False)
    del spend_priv  # spend_priv never leaves the device

    # Serialize into buff
    buff[0:32] = ki_enc
    crypto.encodeint_into(buff_mv[32:64], sig[0][0])
    crypto.encodeint_into(buff_mv[64:], sig[0][1])

    # Encrypt with view key private based key - so host can decrypt and verify HMAC
    enc_key, salt = misc.compute_enc_key_host(s.creds.view_key_private, msg.out_key)
    resp = chacha_poly.encrypt_pack(enc_key, buff)

    return MoneroLiveRefreshStepAck(salt=salt, key_image=resp)
