from trezor.crypto.hashlib import sha256
from trezor.strings import format_amount

from .lisk32 import encode_lisk32


def get_lisk32_from_public_key(pubkey):
    pubkeyHash = sha256(pubkey).digest()
    addressHash = pubkeyHash[:20]
    return get_lisk32_from_address_hash(addressHash)


def get_lisk32_from_address_hash(address_hash):
    return encode_lisk32(address_hash)


def format_coin_amount(value):
    return "%s LSK" % format_amount(value, 8)


def get_votes_count(votes):
    plus, plusAmount, minus, minusAmount = 0, 0, 0, 0
    for vote in votes:
        if vote.amount > 0:
            plus += 1
            plusAmount += vote.amount
        else:
            minus += 1
            minusAmount += abs(vote.amount)
    return plus, plusAmount, minus, minusAmount


def get_vote_tx_text(votes):
    plus, plusAmount, minus, minusAmount = get_votes_count(votes)
    text = []
    if plus > 0:
        text.append(_text_vote_with_plural("Add", plus, plusAmount))
    if minus > 0:
        text.append(_text_vote_with_plural("Remove", minus, minusAmount))
    return text


def _text_vote_with_plural(txt, value, total):
    return "%s %s %s\nTotal: %s" % (
        txt,
        value,
        ("votes" if value != 1 else "vote"),
        format_coin_amount(total),
    )


def get_unlock_count(unlockObjects):
    count, total = 0, 0
    for unlock in unlockObjects:
        count += 1
        total += unlock.amount
    return count, total


def get_unlock_tx_text(unlockObjects):
    count, total = get_unlock_count(unlockObjects)
    text = _text_unlock(count, total)
    return text


def _text_unlock(value, total):
    return "Unlocks: %s \nTotal: %s" % (value, format_coin_amount(total))


def get_multisig_tx_text(asset):
    return "Total keys: %s\nMandatory: %s\nOptional: %s" % (
        asset.number_of_signatures,
        len(asset.mandatory_keys),
        len(asset.optional_keys),
    )
