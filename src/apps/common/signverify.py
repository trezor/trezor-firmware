from trezor.crypto.hashlib import sha256

from apps.wallet.sign_tx.signing import HashWriter, write_varint


def message_digest(coin, message):

    h = HashWriter(sha256)
    write_varint(h, len(coin.signed_message_header))
    h.extend(coin.signed_message_header)
    write_varint(h, len(message))
    h.extend(message)

    return sha256(h.getvalue()).digest()
