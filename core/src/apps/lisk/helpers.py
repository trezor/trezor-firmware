from trezor import log
from trezor.crypto.hashlib import sha256
from .lisk32 import encode_lisk32

def get_address_from_public_key(pubkey):
    string_ints0 = [hex(int) for int in pubkey]
    log.debug(__name__,
        "lisk get_address_from_public_key pubkey > %d, %s",
        len(pubkey), "".join(string_ints0))
    pubkeyHash = sha256(pubkey).digest()
    string_ints = [hex(int) for int in pubkeyHash]
    log.debug(__name__,
        "lisk get_address_from_public_key pubkeyhash > %d, %s",
        len(pubkeyHash), "".join(string_ints))
    addressHash = pubkeyHash[:20]
    string_ints2 = [hex(int) for int in addressHash]
    log.debug(__name__,
        "lisk get_address_from_public_key addressHash > %d, %s",
        len(addressHash), "". join(string_ints2))
    address = encode_lisk32(addressHash)
    log.debug(__name__,
        "lisk get_address_from_public_key address > %s",
        address)
    return address


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
