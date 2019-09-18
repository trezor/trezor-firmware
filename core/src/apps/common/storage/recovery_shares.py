from trezor.crypto import slip39

from apps.common.storage import common, recovery

if False:
    from typing import List, Optional

# Mnemonics stored during SLIP-39 recovery process.
# Each mnemonic is stored under key = index.


def set(index: int, mnemonic: str) -> None:
    common.set(common.APP_RECOVERY_SHARES, index, mnemonic.encode())


def get(index: int) -> Optional[str]:
    m = common.get(common.APP_RECOVERY_SHARES, index)
    if m:
        return m.decode()
    return None


def fetch() -> List[List[str]]:
    mnemonics = []
    if not recovery.get_slip39_group_count():
        return mnemonics
    for i in range(recovery.get_slip39_group_count()):
        mnemonics.append(fetch_group(i))

    return mnemonics


def fetch_group(group_index: int) -> List[str]:
    mnemonics = []
    starting_index = group_index * slip39.MAX_SHARE_COUNT
    for index in range(starting_index, starting_index + slip39.MAX_SHARE_COUNT):
        m = get(index)
        if m:
            mnemonics.append(m)

    return mnemonics


def delete() -> None:
    for index in range(slip39.MAX_SHARE_COUNT * slip39.MAX_GROUP_COUNT):
        common.delete(common.APP_RECOVERY_SHARES, index)
