from typing import TYPE_CHECKING
from ubinascii import hexlify

from trezor import utils, wire, log
from trezor.crypto.hashlib import blake256, sha256

from apps.common.writers import write_compact_size

if TYPE_CHECKING:
    from apps.common.coininfo import CoinInfo


def message_digest(coin: CoinInfo, message: bytes) -> bytes:
    if not utils.BITCOIN_ONLY and coin.decred:
        log.error(__name__, "hashwriter is blacke256")
        h = utils.HashWriter(blake256())
    else:
        log.error(__name__, "hashwriter is sha256")
        h = utils.HashWriter(sha256())
    if not coin.signed_message_header:
        raise wire.DataError("Empty message header not allowed.")
    write_compact_size(h, len(coin.signed_message_header))
    log.error(__name__, "Message start signed adding length: 0x%x", len(coin.signed_message_header))
    h.extend(coin.signed_message_header.encode())
    log.error(__name__, "Message signed part 1: %s", repr(coin.signed_message_header.encode()))
    write_compact_size(h, len(message))
    log.error(__name__, "Message signed adding length: 0x%x", len(message))
    h.extend(message)
    log.error(__name__, "Message signed part 2: %s", repr(message))
    ret = h.get_digest()
    log.error(__name__, "First digest: %s", hexlify(ret))
    if coin.sign_hash_double:
        log.error(__name__, "KUUUUUUUUUUURVA doubling SHA256!!!!!!!!!!!!!!!!")
        ret = sha256(ret).digest()
        log.error(__name__, "Second digest: %s", hexlify(ret))
    log.error(__name__, "Final digest: %s", hexlify(ret))
    return ret


def decode_message(message: bytes) -> str:
    try:
        return bytes(message).decode()
    except UnicodeError:
        return f"hex({hexlify(message).decode()})"
