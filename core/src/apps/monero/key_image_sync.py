from typing import TYPE_CHECKING

from trezor.wire import DataError

from apps.common.keychain import auto_keychain
from apps.monero import layout

if TYPE_CHECKING:
    from trezor.messages import (
        MoneroKeyImageExportInitAck,
        MoneroKeyImageExportInitRequest,
        MoneroKeyImageSyncFinalAck,
        MoneroKeyImageSyncStepAck,
        MoneroKeyImageSyncStepRequest,
    )
    from trezor.ui.layouts.common import ProgressLayout

    from apps.common.keychain import Keychain

    from .xmr.credentials import AccountCreds


@auto_keychain(__name__)
async def key_image_sync(
    msg: MoneroKeyImageExportInitRequest, keychain: Keychain
) -> MoneroKeyImageSyncFinalAck:
    import gc

    from trezor.messages import (
        MoneroKeyImageSyncFinalAck,
        MoneroKeyImageSyncFinalRequest,
        MoneroKeyImageSyncStepRequest,
    )
    from trezor.wire.context import call

    state = KeyImageSync()

    res = await _init_step(state, msg, keychain)
    progress = layout.monero_keyimage_sync_progress()
    while state.current_output + 1 < state.num_outputs:
        step = await call(res, MoneroKeyImageSyncStepRequest)
        res = _sync_step(state, step, progress)
        gc.collect()
    await call(res, MoneroKeyImageSyncFinalRequest)

    # _final_step
    if state.current_output + 1 != state.num_outputs:
        raise DataError("Invalid number of outputs")
    final_hash = state.hasher.digest()
    if final_hash != state.expected_hash:
        raise DataError("Invalid number of outputs")
    return MoneroKeyImageSyncFinalAck(enc_key=state.enc_key)


class KeyImageSync:
    def __init__(self):
        from apps.monero.xmr import crypto_helpers

        self.current_output = -1
        self.num_outputs = 0
        self.expected_hash = b""
        self.enc_key = b""
        self.creds: AccountCreds | None = None
        self.subaddresses = {}
        self.hasher = crypto_helpers.get_keccak()


async def _init_step(
    s: KeyImageSync,
    msg: MoneroKeyImageExportInitRequest,
    keychain: Keychain,
) -> MoneroKeyImageExportInitAck:
    from trezor.crypto import random
    from trezor.messages import MoneroKeyImageExportInitAck

    from apps.common import paths
    from apps.monero import misc
    from apps.monero.xmr import monero

    await paths.validate_path(keychain, msg.address_n)

    s.creds = misc.get_creds(keychain, msg.address_n, msg.network_type)

    await layout.require_confirm_keyimage_sync()

    s.num_outputs = msg.num
    s.expected_hash = msg.hash
    s.enc_key = random.bytes(32)

    for sub in msg.subs:
        monero.compute_subaddresses(
            s.creds, sub.account, sub.minor_indices, s.subaddresses
        )

    return MoneroKeyImageExportInitAck()


def _sync_step(
    s: KeyImageSync,
    tds: MoneroKeyImageSyncStepRequest,
    progress: ProgressLayout,
) -> MoneroKeyImageSyncStepAck:
    from trezor import log
    from trezor.messages import MoneroExportedKeyImage, MoneroKeyImageSyncStepAck

    from apps.monero.xmr import chacha_poly, crypto, key_image

    assert s.creds is not None

    if not tds.tdis:
        raise DataError("Empty")

    kis = []
    buff = bytearray(32 * 3)
    buff_mv = memoryview(buff)

    if s.current_output is not None and s.num_outputs > 0:
        progress.report(1000 * (s.current_output + 1) // s.num_outputs)

    for td in tds.tdis:
        s.current_output += 1
        if s.current_output >= s.num_outputs:
            raise DataError("Too many outputs")

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
