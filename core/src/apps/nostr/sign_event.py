from typing import TYPE_CHECKING

from ..bitcoin.common import encode_bech32_address

if TYPE_CHECKING:
    from trezor.messages import NostrMessageSignature, NostrSignEvent
    from apps.common.keychain import Keychain


async def sign_message(
    msg: NostrSignEvent, keychain: Keychain
) -> NostrMessageSignature:
    from trezor.crypto.curve import bip340

    address_n = msg.address_n

    node = keychain.derive(address_n)

    seckey = node.private_key()

    digest = "1234"
    signature = bip340.sign(seckey, digest)

    address = encode_bech32_address(coin.bech32_prefix, 1, output_pubkey)

    return NostrMessageSignature(address=address, signature=signature)
