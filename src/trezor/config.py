# mock in-memory implementation

_mock = {}

def get(app, key, default=None):
    return _mock.get((app << 8) | key, default)

def set(app, key, value):
    _mock[(app << 8) | key] = value
    return True

# real implementation commented below

'''
from TrezorConfig import Config

_config = Config()

def get(app, key, default=None):
    v = _config.get(app, key)
    return v if v else default

def set(app, key, value):
    return _config.set(app, key, value)
'''
