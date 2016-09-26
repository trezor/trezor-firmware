import sys
import ustruct

# mock implementation using binary file

_mock = {}

if sys.platform in ['trezor', 'pyboard']:  # stmhal
    _file = '/flash/trezor.config'
else:
    _file = '/var/tmp/trezor.config'


def _load():
    try:
        with open(_file, 'rb') as f:
            while True:
                d = f.read(4)
                if len(d) != 4:
                    break
                k, l = ustruct.unpack('<HH', d)
                v = f.read(l)
                _mock[k] = v
    except OSError:
        pass


def _save():
    with open(_file, 'wb') as f:
        for k, v in _mock.items():
            f.write(ustruct.pack('<HH', k, len(v)))
            f.write(v)

_load()


def get(session_id, app_id, key, default=None):
    # TODO: session_id
    return _mock.get((app_id << 8) | key, default)


def set(session_id, app_id, key, value):
    # TODO: session_id
    _mock[(app_id << 8) | key] = value
    _save()
    return True


def commit(session_id):
    pass
