# mock implementation using binary file

import ustruct

def Config():

    def __init__(self, filename):
        self._data = {}
        self._file = filename
        try:
            with open(self._file, 'rb') as f:
                while True:
                    d = f.read(4)
                    if len(d) != 4:
                        break
                    k, l = ustruct.unpack('<HH', d)
                    v = f.read(l)
                    self._data[k] = v
        except OSError:
            pass

    def _save(self):
        with open(self._file, 'wb') as f:
            for k, v in self._data.items():
                f.write(ustruct.pack('<HH', k, len(v)))
                f.write(v)

    def get(self, app_id, key, default=None):
        return self._data.get((app_id << 8) | key, default)

    def set(self, app_id, key, value):
        self._data[(app_id << 8) | key] = value
        self._save()

    def wipe(self):
        self._data = {}
        self._save()
