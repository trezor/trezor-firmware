from trezor.crypto import slip39

from apps.common.storage import common

# Mnemonics stored during SLIP-39 recovery process.
# Each mnemonic is stored under key = index.


def set(index: int, mnemonic: str):
    common._set(common._APP_SLIP39_MNEMONICS, index, mnemonic.encode())


def get(index: int) -> str:
    m = common._get(common._APP_SLIP39_MNEMONICS, index)
    if m:
        return m.decode()
    return False


def fetch() -> list:
    mnemonics = []
    for index in range(0, slip39.MAX_SHARE_COUNT):
        m = get(index)
        if m:
            mnemonics.append(m)
    return mnemonics


def delete():
    for index in range(0, slip39.MAX_SHARE_COUNT):
        common._delete(common._APP_SLIP39_MNEMONICS, index)
