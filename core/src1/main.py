import usb

usb.bus.open()

import trezorio as io
from trezorui import Display
import storage
import storage.resident_credentials
from trezor import config

config.init(False)
salt = None
config.unlock(1, salt)
storage.init_unlocked()
storage.cache.start_session()
print("is_initialized: ", storage.device.is_initialized())
print("version: ", storage.device.is_version_stored())
print("version: ", storage.device.get_version())
print("needs backup: ", storage.device.needs_backup())
storage.device.set_backed_up()
print("needs backup: ", storage.device.needs_backup())
flags = storage.device.get_flags()
print("flags", flags)
storage.device.set_flags(0x200)
print("flags", storage.device.get_flags())

secret = "0"*32
backup_type = 0
storage.device.store_mnemonic_secret(
    secret,
    backup_type,
    needs_backup=True,
    no_backup=True,
)


storage.device.set_unfinished_backup(False)
print("unfinished backup: ", storage.device.unfinished_backup())
storage.device.set_unfinished_backup(True)
print("unfinished backup: ", storage.device.unfinished_backup())

key54 = storage.common.get(0x1, 54, public=True)
print("App key 54:", key54)
storage.common.set(0x1, 54, b"asdZ", public=True)
key54 = storage.common.get(0x1, 54, public=True)
print("App key 54 (2):", key54)
key54 = storage.common.delete(0x1, 54, public=True)
key54 = storage.common.get(0x1, 54, public=True)
print("App key 54 (3):", key54)
delay = storage.device.get_autolock_delay_ms()
print("delay", delay)
storage.device.set_autolock_delay_ms(150000)
delay = storage.device.get_autolock_delay_ms()
print("delay", delay)

cache_seed = storage.cache.get(storage.cache.APP_COMMON_SEED)
print("cache seed", cache_seed)
storage.cache.set(storage.cache.APP_COMMON_SEED, 1234)
cache_seed = storage.cache.get(storage.cache.APP_COMMON_SEED)
print("cache seed", cache_seed)

res1 = storage.resident_credentials.get(1)
print("Res credential 1", res1)
res1 = storage.resident_credentials.set(1, b"0"*31 + b"F")
res1 = storage.resident_credentials.get(1)
print("Res credential 1", res1)

i = 0

d = Display()
d.clear()
d.backlight(255)

while True:
    d.clear()
    d.text(0, 20, "%d" % i, Display.FONT_NORMAL, 0xFFFF, 0x0000)
    d.text_right(128, 20, "%d" % i, Display.FONT_BOLD, 0xFFFF, 0x0000)
    d.text(0, 64, "%d" % i, Display.FONT_MONO, 0xFFFF, 0x0000)
    d.text_right(128, 64, "%d" % i, Display.FONT_MONO_BOLD, 0xFFFF, 0x0000)
    i += 1
    r = [0, 0]
    if io.poll([io.TOUCH], r, 1000000):
        print("TOUCH", r)
    else:
        print("NOTOUCH")
    d.refresh()
