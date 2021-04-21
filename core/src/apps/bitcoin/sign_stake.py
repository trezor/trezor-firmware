from trezor import wire
from trezor.crypto.curve import secp256k1
from trezor.crypto.hashlib import sha256
from trezor.messages.StakeSignature import StakeSignature
from trezor.utils import HashWriter

from apps.bitcoin.keychain import with_keychain
from apps.bitcoin.layout import require_confirm_sign_stake
from apps.bitcoin.writers import write_stake
from apps.common.paths import validate_path

if False:
    from trezor.messages.SignStake import SignStake

    from apps.common.coininfo import CoinInfo
    from apps.common.keychain import Keychain


@with_keychain
async def sign_stake(
    ctx: wire.Context, msg: SignStake, keychain: Keychain, coin: CoinInfo
) -> StakeSignature:
    address_n = msg.address_n

    await validate_path(ctx, keychain, address_n)
    await require_confirm_sign_stake(ctx, coin, msg)

    node = keychain.derive(address_n)
    pubkey = node.public_key()

    w = HashWriter(sha256())
    write_stake(w, msg, pubkey)
    digest = sha256(w.get_digest()).digest()

    signature = secp256k1.sign_schnorr(node.private_key(), digest)

    return StakeSignature(pubkey=pubkey, signature=signature)
