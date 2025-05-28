from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import EthereumGetPublicKey, EthereumPublicKey


async def get_public_key(msg: EthereumGetPublicKey) -> EthereumPublicKey:
    from ubinascii import hexlify

    from trezor.messages import EthereumPublicKey, GetPublicKey
    from trezor.ui.layouts import show_pubkey

    from apps.bitcoin import get_public_key as bitcoin_get_public_key

    # we use the Bitcoin format for Ethereum xpubs
    btc_pubkey_msg = GetPublicKey(address_n=msg.address_n)
    resp = await bitcoin_get_public_key.get_public_key(btc_pubkey_msg)

    if msg.show_display:
        await show_pubkey(hexlify(resp.node.public_key).decode())

    return EthereumPublicKey(node=resp.node, xpub=resp.xpub)
