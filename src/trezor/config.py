import sys
if sys.platform in ['trezor', 'pyboard']:  # stmhal
    from config_mock import Config
    _config = Config('/sd/trezor.config')
else:
    from TrezorConfig import Config
    _config = Config()

def get(app, key, default=None):
    v = _config.get(app, key)
    return v if v else default

def set(app, key, value):
    return _config.set(app, key, value)

def wipe():
    return _config.wipe()
