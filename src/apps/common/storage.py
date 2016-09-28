from trezor import config


APP_MANAGEMENT = const(1)
CFG_STORAGE = const(1)


def get_storage(session_id):
    return config.get(session_id, APP_MANAGEMENT, CFG_STORAGE)


def set_storage(session_id, buf):
    config.set(session_id, APP_MANAGEMENT, CFG_STORAGE, buf)


def clear_storage(session_id):
    set_storage(session_id, '')
