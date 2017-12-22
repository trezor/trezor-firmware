from trezor.crypto.hashlib import sha256

from apps.wallet.sign_tx.signing import write_varint
from apps.common.hash_writer import HashWriter


def message_digest(coin, message):

    h = HashWriter(sha256)
    write_varint(h, len(coin.signed_message_header))
    h.extend(coin.signed_message_header)
    write_varint(h, len(message))
    h.extend(message)

    return sha256(h.get_digest()).digest()
