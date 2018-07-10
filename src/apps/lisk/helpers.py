from trezor.crypto.hashlib import sha256

LISK_CURVE = "ed25519"


def get_address_from_public_key(pubkey):
    pubkeyhash = sha256(pubkey).digest()
    address = int.from_bytes(pubkeyhash[:8], "little")
    return str(address) + "L"


def get_votes_count(votes):
    plus, minus = 0, 0
    for vote in votes:
        if vote.startswith("+"):
            plus += 1
        else:
            minus += 1
    return plus, minus


def get_vote_tx_text(votes):
    plus, minus = get_votes_count(votes)
    text = []
    if plus > 0:
        text.append(_text_with_plural("Add", plus))
    if minus > 0:
        text.append(_text_with_plural("Remove", minus))
    return text


def _text_with_plural(txt, value):
    return "%s %s %s" % (txt, value, ("votes" if value != 1 else "vote"))
