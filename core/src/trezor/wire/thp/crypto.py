import trezorthp
from storage import device


def get_trezor_static_public_key() -> bytes:
    return trezorthp.static_public_key(device.get_device_secret())
