from trezor import utils, wire
from trezor.crypto import hashlib, hmac

from .writers import write_bitcoin_varint, write_bytes_unchecked, write_uint32_le

if False:
    from trezor.messages.PaymentRequestMemo import PaymentRequestMemo
    from apps.common.coininfo import CoinInfo
    from apps.common.keychain import Keychain

_ADDRESS_MAC_KEY_PATH = [b"SLIP-0019", b"Address MAC key"]


def check_address_mac(
    memo: PaymentRequestMemo, coin: CoinInfo, keychain: Keychain
) -> None:
    assert memo.mac is not None
    mac = get_address_mac(memo.data, coin, keychain)
    if len(memo.mac) != hashlib.sha256.digest_size or not utils.consteq(mac, memo.mac):
        raise wire.DataError("Invalid address MAC.")


def get_address_mac(address: bytes, coin: CoinInfo, keychain: Keychain) -> bytes:
    # k = Key(m/""/"Address MAC key")
    node = keychain.derive_slip21(_ADDRESS_MAC_KEY_PATH)

    # mac = HMAC-SHA256(key = k, msg = slip44 || address)
    mac = utils.HashWriter(hmac(hmac.SHA256, node.key()))
    write_uint32_le(mac, coin.slip44)
    write_bitcoin_varint(mac, len(address))
    write_bytes_unchecked(mac, address)
    return mac.get_digest()
