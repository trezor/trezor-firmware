
LISK_CURVE = 'ed25519'

def get_address_from_public_key(public_key):
    from trezor.crypto.hashlib import sha256

    # logic from lisk-js library
    # https://github.com/LiskHQ/lisk-js/blob/115e0e771e8456dc6c1d4acaabba93d975655cfe/lib/transactions/crypto/convert.js#L30
    publicKeyHash = list(sha256(public_key).digest())
    addressData = []
    for i in range(8):
        addressData.append(publicKeyHash[7 - i])

    address = int.from_bytes(bytes(addressData), 'big')
    return str(address) + "L"

def get_votes_count(votes):
    plus, minus = [], []
    for vote in votes:
        plus.append(vote) if vote.startswith('+') else minus.append(vote)
    return len(plus), len(minus)

def get_vote_tx_text(votes):
    plus, minus = get_votes_count(votes)
    text = []
    if plus > 0:
        text.append(_text_with_plural('Add', plus))
    if minus > 0:
        text.append(_text_with_plural('Remove', minus))
    return text

def _text_with_plural(txt, value):
    return '%s %s %s' % (txt, value, ('votes' if value != 1 else 'vote'))
