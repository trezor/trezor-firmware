import sys

if sys.platform == 'trezor': # stmhal - use binary module (not working atm)

    from TrezorConfig import Config

    _config = Config()

    def get(app, key, default=None):
        v = _config.get(app, key)
        return v if v else default

    def set(app, key, value):
        return _config.set(app, key, value)

else: # emulator (mock implementation using binary file)

    import ustruct

    _mock = {}
    _file = 'trezor.config'

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

    def get(app, key, default=None):
        return _mock.get((app << 8) | key, default)

    def set(app, key, value):
        _mock[(app << 8) | key] = value
        _save()
        return True
