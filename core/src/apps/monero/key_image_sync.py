import gc

from trezor import log, wire
from trezor.messages import (
    MoneroExportedKeyImage,
    MoneroKeyImageExportInitAck,
    MoneroKeyImageSyncFinalAck,
    MoneroKeyImageSyncFinalRequest,
    MoneroKeyImageSyncStepAck,
    MoneroKeyImageSyncStepRequest,
)

from apps.common import paths
from apps.common.keychain import auto_keychain
from apps.monero import misc
from apps.monero.layout import confirms
from apps.monero.xmr import crypto, key_image, monero
from apps.monero.xmr.crypto import chacha_poly


@auto_keychain(__name__)
async def key_image_sync(ctx, msg, keychain):
    state = KeyImageSync()

    res = await _init_step(state, ctx, msg, keychain)
    while state.current_output + 1 < state.num_outputs:
        msg = await ctx.call(res, MoneroKeyImageSyncStepRequest)
        res = await _sync_step(state, ctx, msg)
        gc.collect()
    msg = await ctx.call(res, MoneroKeyImageSyncFinalRequest)
    res = await _final_step(state, ctx)

    return res


class KeyImageSync:
    def __init__(self):
        self.current_output = -1
        self.num_outputs = 0
        self.expected_hash = None
        self.enc_key = None
        self.creds = None
        self.subaddresses = {}
        self.hasher = crypto.get_keccak()


async def _init_step(s, ctx, msg, keychain):
    await paths.validate_path(ctx, keychain, msg.address_n)

    s.creds = misc.get_creds(keychain, msg.address_n, msg.network_type)

    await confirms.require_confirm_keyimage_sync(ctx)

    s.num_outputs = msg.num
    s.expected_hash = msg.hash
    s.enc_key = crypto.random_bytes(32)

    for sub in msg.subs:
        monero.compute_subaddresses(
            s.creds, sub.account, sub.minor_indices, s.subaddresses
        )

    return MoneroKeyImageExportInitAck()


async def _sync_step(s, ctx, tds):
    if not tds.tdis:
        raise wire.DataError("Empty")

    kis = []
    buff = bytearray(32 * 3)
    buff_mv = memoryview(buff)

    await confirms.keyimage_sync_step(ctx, s.current_output, s.num_outputs)

    for td in tds.tdis:
        s.current_output += 1
        if s.current_output >= s.num_outputs:
            raise wire.DataError("Too many outputs")

        if __debug__:
            log.debug(__name__, "ki_sync, step i: %d", s.current_output)

        # Update the control hash
        s.hasher.update(key_image.compute_hash(td))

        # Compute keyimage + signature
        ki, sig = key_image.export_key_image(s.creds, s.subaddresses, td)

        # Serialize into buff
        crypto.encodepoint_into(buff_mv[0:32], ki)
        crypto.encodeint_into(buff_mv[32:64], sig[0][0])
        crypto.encodeint_into(buff_mv[64:], sig[0][1])

        # Encrypt with enc_key
        nonce, ciph, _ = chacha_poly.encrypt(s.enc_key, buff)

        kis.append(MoneroExportedKeyImage(iv=nonce, blob=ciph))

    return MoneroKeyImageSyncStepAck(kis=kis)


async def _final_step(s, ctx):
    if s.current_output + 1 != s.num_outputs:
        raise wire.DataError("Invalid number of outputs")

    final_hash = s.hasher.digest()
    if final_hash != s.expected_hash:
        raise wire.DataError("Invalid number of outputs")

    return MoneroKeyImageSyncFinalAck(enc_key=s.enc_key)
