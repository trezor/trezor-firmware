from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import EthereumGetPublicKey, EthereumPublicKey


async def get_public_key(msg: EthereumGetPublicKey) -> EthereumPublicKey | None:
    from ubinascii import hexlify

    from trezor.messages import EthereumPublicKey, GetPublicKey
    from trezor.ui.layouts import show_continue_in_app, show_pubkey
    from trezor.wire import context

    from apps.bitcoin import get_public_key as bitcoin_get_public_key

    # we use the Bitcoin format for Ethereum xpubs
    btc_pubkey_msg = GetPublicKey(address_n=msg.address_n, show_display=False)
    btc_resp = await bitcoin_get_public_key.get_public_key(btc_pubkey_msg)
    assert btc_resp is not None

    response = EthereumPublicKey(node=btc_resp.node, xpub=btc_resp.xpub)
    if msg.show_display:
        from trezor import TR

        await show_pubkey(hexlify(response.node.public_key).decode())
        await context.write(response)
        await show_continue_in_app(TR.address__public_key_confirmed)
        return None

    return response
