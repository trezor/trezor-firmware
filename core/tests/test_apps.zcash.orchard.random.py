from common import *
from apps.zcash.orchard.random import BundleShieldingRng


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestZcashRedPallas(unittest.TestCase):
    def test_zcash_shielding_rng(self):
        print()
        print()
        seed = bytes(list(range(32)))
        brng = BundleShieldingRng(seed)
        f = lambda x: list(x)
        print("seed", f(seed))

        inps = list(range(100))
        brng.shuffle_inputs(inps)
        print("shuffled_inputs", inps)

        outs = list(range(100))
        brng.shuffle_outputs(outs)
        print("shuffled_outputs", outs)

        for i in [0]:
            print()
            rng = brng.for_action(i)
            print("sub rng", i, f(rng.seed))
            for attr in ["alpha", "rcv", "recipient", "ock", "op", "rseed_old", "rseed_new", "rho"]:
                value = getattr(rng, attr)()
                if hasattr(value, "to_bytes"):
                    value = value.to_bytes()
                print(attr, f(value))

        print()


if __name__ == "__main__":
    unittest.main()
