from trezor.crypto.hashlib import sha256

from apps.common import HARDENED

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


def validate_full_path(path: list) -> bool:
    """
    Validates derivation path to equal 44'/134'/a',
    where `a` is an account index from 0 to 1 000 000.
    """
    if len(path) != 3:
        return False
    if path[0] != 44 | HARDENED:
        return False
    if path[1] != 134 | HARDENED:
        return False
    if path[2] < HARDENED or path[2] > 1000000 | HARDENED:
        return False
    return True
