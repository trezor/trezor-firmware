if not __debug__:
    from trezor import utils

    utils.halt("Disabled in production mode")
