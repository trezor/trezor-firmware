from typing import TYPE_CHECKING

from .keychain import PATTERNS_ADDRESS, with_keychain_from_path

if TYPE_CHECKING:
    from trezor.messages import EthereumAddress, EthereumGetAddress
    from trezor.wire import MaybeEarlyResponse

    from apps.common.keychain import Keychain

    from .definitions import Definitions


@with_keychain_from_path(*PATTERNS_ADDRESS)
async def get_address(
    msg: EthereumGetAddress,
    keychain: Keychain,
    defs: Definitions,
) -> MaybeEarlyResponse[EthereumAddress]:
    from trezor.messages import EthereumAddress
    from trezor.ui.layouts import show_address, show_continue_in_app
    from trezor.wire import early_response

    from apps.common import paths

    from .helpers import address_from_bytes

    address_n = msg.address_n  # local_cache_attribute

    await paths.validate_path(keychain, address_n)

    node = keychain.derive(address_n)

    address = address_from_bytes(node.ethereum_pubkeyhash(), defs.network)
    response = EthereumAddress(address=address)

    if msg.show_display:
        from trezor import TR

        slip44_id = address_n[1]  # it depends on the network (ETH vs ETC...)
        await show_address(
            address,
            path=paths.address_n_to_str(address_n),
            account=paths.get_account_name(
                "ETH", address_n, PATTERNS_ADDRESS, slip44_id
            ),
            chunkify=bool(msg.chunkify),
        )
        return await early_response(
            response, show_continue_in_app(TR.address__confirmed)
        )

    return response
