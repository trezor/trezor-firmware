from ubinascii import hexlify

from trezor import utils
from trezor.crypto.hashlib import blake256, sha256

from apps.wallet.sign_tx.writers import write_varint

if False:
    from typing import List
    from apps.common.coininfo import CoinType


def message_digest(coin: CoinType, message: bytes) -> bytes:
    if not utils.BITCOIN_ONLY and coin.decred:
        h = utils.HashWriter(blake256())
    else:
        h = utils.HashWriter(sha256())
    write_varint(h, len(coin.signed_message_header))
    h.extend(coin.signed_message_header)
    write_varint(h, len(message))
    h.extend(message)
    ret = h.get_digest()
    if coin.sign_hash_double:
        ret = sha256(ret).digest()
    return ret


def split_message(message: bytes) -> List[str]:
    try:
        m = bytes(message).decode()
        words = m.split(" ")
    except UnicodeError:
        m = "hex(%s)" % hexlify(message).decode()
        words = [m]
    return words


# hashes the serialized bytes
# required for Stakenet TPOS contracts
def tpos_digest(coin, tpos):
    if coin.decred:
        h = utils.HashWriter(blake256())
    else:
        h = utils.HashWriter(sha256())
    h.extend(tpos)
    ret = h.get_digest()
    if coin.sign_hash_double:
        ret = sha256(ret).digest()

    return ret
