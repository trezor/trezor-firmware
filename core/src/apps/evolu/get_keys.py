from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import EvoluGetKeys, EvoluKeys

_EVOLU_KEY_PATH_PREFIX = [b"TREZOR", b"Evolu"]


async def get_keys(_msg: EvoluGetKeys) -> EvoluKeys:
    from storage.device import is_initialized
    from trezor.messages import EvoluKeys
    from trezor.ui.layouts import confirm_action
    from trezor.wire import NotInitialized

    from apps.common.seed import Slip21Node, get_seed

    if not is_initialized():
        raise NotInitialized("Device is not initialized")

    # TODO: use translated strings when exposing this to production
    await confirm_action(
        "get_evolu_keys",
        "Evolu keys",
        action="Derive keys for Evolu?",
        prompt_screen=True,
    )
    seed = await get_seed()
    node1 = Slip21Node(seed)
    node2 = node1.clone()
    node3 = node1.clone()

    node1.derive_path(_EVOLU_KEY_PATH_PREFIX + [b"Owner Id"])
    owner_id = node1.key()

    node2.derive_path(_EVOLU_KEY_PATH_PREFIX + [b"Write Key"])
    write_key = node2.key()

    node3.derive_path(_EVOLU_KEY_PATH_PREFIX + [b"Encryption Key"])
    encryption_key = node3.key()

    return EvoluKeys(
        owner_id=owner_id, write_key=write_key, encryption_key=encryption_key
    )
