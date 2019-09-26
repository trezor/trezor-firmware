from trezor import config
from trezor.crypto import beam

from apps.beam.helpers import beam_app_id, get_master_nonce_idx


def create_master_nonce(seed):
    master_nonce = bytearray(32)
    beam.create_master_nonce(master_nonce, seed)
    config.set(beam_app_id(), get_master_nonce_idx(), master_nonce)
    for idx in range(1, 255):
        consume_nonce(idx)


def is_master_nonce_created():
    master_nonce = config.get(beam_app_id(), get_master_nonce_idx())
    return master_nonce is not None


def create_nonce(idx):
    if idx != get_master_nonce_idx():
        old_nonce = config.get(beam_app_id(), idx)
        new_nonce = bytearray(32)
        if old_nonce:
            new_nonce = bytearray(old_nonce)
        master_nonce = config.get(beam_app_id(), get_master_nonce_idx())
        beam.create_derived_nonce(master_nonce, idx, new_nonce)
        config.set(beam_app_id(), idx, new_nonce)
        return old_nonce, new_nonce


def calc_nonce_pub(nonce):
    out_nonce_pub_x = bytearray(32)
    out_nonce_pub_y = bytearray(1)
    beam.get_nonce_public_key(nonce, out_nonce_pub_x, out_nonce_pub_y)
    return (out_nonce_pub_x, out_nonce_pub_y)


def consume_nonce(idx):
    old_nonce, _ = create_nonce(idx)
    return old_nonce


def get_nonce_pub(idx):
    if idx != get_master_nonce_idx():
        nonce = config.get(beam_app_id(), idx)
        return calc_nonce_pub(nonce)
