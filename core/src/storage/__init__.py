from storage import common, device


def wipe() -> None:
    from storage import cache
    from trezor import config

    config.wipe()
    cache.clear_all()


def reset() -> None:
    """
    Wipes storage but keeps the device id unchanged.
    """
    device_id = device.get_device_id()
    wipe()
    common.set(common.APP_DEVICE, device.DEVICE_ID, device_id.encode(), public=True)
