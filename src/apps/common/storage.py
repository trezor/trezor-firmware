from micropython import const
from trezor import config
from trezor.messages.Storage import Storage


APP_COMMON = const(1)
CFG_STORAGE = const(1)


def has(session_id):
    buf = config.get(session_id, APP_COMMON, CFG_STORAGE)
    return bool(buf)


def get(session_id):
    buf = config.get(session_id, APP_COMMON, CFG_STORAGE)
    if not buf:
        raise KeyError('Storage is not initialized')
    return Storage.loads(buf)


def set(session_id, st):
    config.set(session_id, APP_COMMON, CFG_STORAGE, st.dumps())


def clear(session_id):
    config.set(session_id, APP_COMMON, CFG_STORAGE, b'')
