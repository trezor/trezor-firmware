# bolt11: https://github.com/lightning/bolts/blob/master/11-payment-encoding.md
# inspired by https://github.com/lnbits/bolt11/blob/master/bolt11/core.py

from trezor.crypto.curve import secp256k1
from trezor.crypto.hashlib import sha256

from .bech32 import Encoding, bech32_decode, convertbits


# decodes bolt11 amount into millisatoshi
def _decode_amount(amount: str) -> int | None:
    if not amount:
        return None
    mult = amount[-1]
    if mult == "p":
        assert amount[-2] == "0"
        return int(amount[:-1]) // 10
    elif mult == "n":
        return int(amount[:-1]) * 100
    elif mult == "u":
        return int(amount[:-1]) * 100_000
    elif mult == "m":
        return int(amount[:-1]) * 100_000_000
    else:
        return int(amount) * 100_000_000_000


class Bolt11Invoice:
    def __init__(
        self,
        network: str,
        timestamp: int,
        payee: bytes,
        amount: int | None = None,
        payment_hash: bytes | None = None,
        payment_secret: bytes | None = None,
        description: str | None = None,
    ):
        self.network = network
        self.amount = amount
        self.timestamp = timestamp
        self.payee = payee
        self.payment_hash = payment_hash
        self.payment_secret = payment_secret
        self.description = description


def bolt11_decode(bolt: str) -> Bolt11Invoice:
    # 1024 below is arbitrary limit
    hrp, data, enc = bech32_decode(bolt.lower(), 1024)
    assert hrp is not None
    assert data is not None
    assert enc == Encoding.BECH32
    assert hrp[:4] in ["lnbc", "lntb"]
    assert len(data) > 104
    sig = convertbits(data[-104:], 5, 8, False)
    sig = bytes([sig[-1] + 31] + sig[:-1])  # convert recover byte
    data = data[:-104]
    digest = sha256(hrp.encode() + bytes(convertbits(data, 5, 8, True))).digest()
    pubkey = secp256k1.verify_recover(sig, digest)
    assert pubkey is not None

    t = convertbits(data[:7], 5, 8, True)
    timestamp = (t[0] << 27) + (t[1] << 19) + (t[2] << 11) + (t[3] << 3) + (t[4] >> 5)
    invoice = Bolt11Invoice(
        network=hrp[2:4],
        timestamp=timestamp,
        payee=pubkey,
        amount=_decode_amount(hrp[4:]),
    )
    pos = 7
    while pos < len(data):
        t = data[pos]
        l = data[pos + 1] * 32 + data[pos + 2]
        if t == 1 and l == 52:  # p
            v = convertbits(data[pos + 3 : pos + 3 + l], 5, 8, True)
            invoice.payment_hash = bytes(v[:32])
        elif t == 13:  # d
            v = convertbits(data[pos + 3 : pos + 3 + l], 5, 8, True)
            if v[-1] == 0:
                invoice.description = bytes(v[:-1]).decode()
            else:
                invoice.description = bytes(v).decode()
        elif t == 16 and l == 52:  # s
            v = convertbits(data[pos + 3 : pos + 3 + l], 5, 8, True)
            invoice.payment_secret = bytes(v[:32])
        elif t == 19 and l == 53:  # n
            v = convertbits(data[pos + 3 : pos + 3 + l], 5, 8, True)
            assert invoice.payee == bytes(v[:33])
        pos += 3 + l
    return invoice
