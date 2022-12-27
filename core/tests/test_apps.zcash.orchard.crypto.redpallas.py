from common import *

from trezor.crypto.hashlib import blake2b
from trezor.crypto.pallas import to_scalar, Point, Scalar

from apps.zcash.orchard.crypto.generators import SPENDING_KEY_BASE as G
from apps.zcash.orchard.random import ActionShieldingRng

if not utils.BITCOIN_ONLY:
    from apps.zcash.orchard.crypto.redpallas import sign_spend_auth


def H_star(x: bytes) -> Scalar:
    digest = blake2b(personal=b"Zcash_RedPallasH", data=x).digest()
    return to_scalar(digest)


def verify(signature, message, vk_):
    R_, S_ = signature[:32], signature[32:]
    R = Point(R_)
    S = Scalar(S_)
    vk = Point(vk_)
    c = H_star(R_ + vk_ + message)
    if R.to_bytes() != R_:
        return False
    if S.to_bytes() != S_:
        return False
    return ((-S) * G + R + c * vk).is_identity()


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestZcashRedPallas(unittest.TestCase):
    def test_redpallas(self):
        message = b"hello"
        sk = Scalar(32 * b"\x01")
        vk = sk * G
        rng = ActionShieldingRng(32 * b"\x00")
        sig = sign_spend_auth(sk, message, rng)
        self.assertEqual(verify(sig, message, vk.to_bytes()), True)
        print()
        print("vk:", list(vk.to_bytes()))
        print("message:", list(message))
        print("sig:", list(sig))
        print("===")
        print(list(vk.to_bytes()), ",", list(sig), ", &", list(message))
        print("===")


if __name__ == "__main__":
    unittest.main()
