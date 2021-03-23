import gc

import storage.cache
from trezor import log
from trezor.enums import MessageType
from trezor.messages import (
    MoneroLiveRefreshFinalAck,
    MoneroLiveRefreshStartAck,
    MoneroLiveRefreshStartRequest,
    MoneroLiveRefreshStepAck,
    MoneroLiveRefreshStepRequest,
)

from apps.common import paths
from apps.common.keychain import auto_keychain
from apps.monero import misc
from apps.monero.layout import confirms
from apps.monero.xmr import crypto, key_image, monero
from apps.monero.xmr.crypto import chacha_poly


@auto_keychain(__name__)
async def live_refresh(ctx, msg: MoneroLiveRefreshStartRequest, keychain):
    state = LiveRefreshState()

    res = await _init_step(state, ctx, msg, keychain)
    while True:
        msg = await ctx.call_any(
            res,
            MessageType.MoneroLiveRefreshStepRequest,
            MessageType.MoneroLiveRefreshFinalRequest,
        )
        del res
        if msg.MESSAGE_WIRE_TYPE == MessageType.MoneroLiveRefreshStepRequest:
            res = await _refresh_step(state, ctx, msg)
        else:
            return MoneroLiveRefreshFinalAck()
        gc.collect()

    return res


class LiveRefreshState:
    def __init__(self):
        self.current_output = 0
        self.creds = None


async def _init_step(
    s: LiveRefreshState, ctx, msg: MoneroLiveRefreshStartRequest, keychain
):
    await paths.validate_path(ctx, keychain, msg.address_n)

    if not storage.cache.get(storage.cache.APP_MONERO_LIVE_REFRESH):
        await confirms.require_confirm_live_refresh(ctx)
        storage.cache.set(storage.cache.APP_MONERO_LIVE_REFRESH, b"\x01")

    s.creds = misc.get_creds(keychain, msg.address_n, msg.network_type)

    return MoneroLiveRefreshStartAck()


async def _refresh_step(s: LiveRefreshState, ctx, msg: MoneroLiveRefreshStepRequest):
    buff = bytearray(32 * 3)
    buff_mv = memoryview(buff)

    await confirms.live_refresh_step(ctx, s.current_output)
    s.current_output += 1

    if __debug__:
        log.debug(__name__, "refresh, step i: %d", s.current_output)

    # Compute spending secret key and the key image
    # spend_priv = Hs(recv_deriv || real_out_idx) + spend_key_private
    # If subaddr:
    #   spend_priv += Hs("SubAddr" || view_key_private || major || minor)
    # out_key = spend_priv * G, KI: spend_priv * Hp(out_key)
    out_key = crypto.decodepoint(msg.out_key)
    recv_deriv = crypto.decodepoint(msg.recv_deriv)
    received_index = msg.sub_addr_major, msg.sub_addr_minor
    spend_priv, ki = monero.generate_tx_spend_and_key_image(
        s.creds, out_key, recv_deriv, msg.real_out_idx, received_index
    )

    ki_enc = crypto.encodepoint(ki)
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
