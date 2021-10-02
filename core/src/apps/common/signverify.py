from ubinascii import hexlify

from trezor import utils, wire
from trezor.crypto.hashlib import blake256, sha256

from apps.common.writers import write_bitcoin_varint

if False:
    from apps.common.coininfo import CoinInfo


def message_digest(coin: CoinInfo, message: bytes) -> bytes:
    if not utils.BITCOIN_ONLY and coin.decred:
        h = utils.HashWriter(blake256())
    else:
        h = utils.HashWriter(sha256())
    if not coin.signed_message_header:
        raise wire.DataError("Empty message header not allowed.")
    write_bitcoin_varint(h, len(coin.signed_message_header))
    h.extend(coin.signed_message_header.encode())
    write_bitcoin_varint(h, len(message))
    h.extend(message)
    ret = h.get_digest()
    if coin.sign_hash_double:
        ret = sha256(ret).digest()
    return ret


def decode_message(message: bytes) -> str:
    try:
        return bytes(message).decode()
    except UnicodeError:
        return f"hex({hexlify(message).decode()})"
