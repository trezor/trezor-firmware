# flake8: noqa: F403,F405
from common import *

if utils.USE_THP:
    from trezor.crypto import elligator2


@unittest.skipUnless(utils.USE_THP, "only needed for THP")
class TestCryptoElligator2(unittest.TestCase):
    def test_map_to_curve25519(self):

        # https://elligator.org/vectors/curve25519_direct.vec
        vectors = [
            (
                "0000000000000000000000000000000000000000000000000000000000000000",
                "0000000000000000000000000000000000000000000000000000000000000000",
            ),
            (
                "66665895c5bc6e44ba8d65fd9307092e3244bf2c18877832bd568cb3a2d38a12",
                "04d44290d13100b2c25290c9343d70c12ed4813487a07ac1176daa5925e7975e",
            ),
            (
                "673a505e107189ee54ca93310ac42e4545e9e59050aaac6f8b5f64295c8ec02f",
                "242ae39ef158ed60f20b89396d7d7eef5374aba15dc312a6aea6d1e57cacf85e",
            ),
            (
                "990b30e04e1c3620b4162b91a33429bddb9f1b70f1da6e5f76385ed3f98ab131",
                "998e98021eb4ee653effaa992f3fae4b834de777a953271baaa1fa3fef6b776e",
            ),
            (
                "341a60725b482dd0de2e25a585b208433044bc0a1ba762442df3a0e888ca063c",
                "683a71d7fca4fc6ad3d4690108be808c2e50a5af3174486741d0a83af52aeb01",
            ),
            (
                "922688fa428d42bc1fa8806998fbc5959ae801817e85a42a45e8ec25a0d7541a",
                "696f341266c64bcfa7afa834f8c34b2730be11c932e08474d1a22f26ed82410b",
            ),
            (
                "0d3b0eb88b74ed13d5f6a130e03c4ad607817057dc227152827c0506a538bb3a",
                "0b00df174d9fb0b6ee584d2cf05613130bad18875268c38b377e86dfefef177f",
            ),
            (
                "01a3ea5658f4e00622eeacf724e0bd82068992fae66ed2b04a8599be16662e35",
                "7ae4c58bc647b5646c9f5ae4c2554ccbf7c6e428e7b242a574a5a9c293c21f7e",
            ),
            (
                "1d991dff82a84afe97874c0f03a60a56616a15212fbe10d6c099aa3afcfabe35",
                "f81f235696f81df90ac2fc861ceee517bff611a394b5be5faaee45584642fb0a",
            ),
            (
                "185435d2b005a3b63f3187e64a1ef3582533e1958d30e4e4747b4d1d3376c728",
                "f938b1b320abb0635930bd5d7ced45ae97fa8b5f71cc21d87b4c60905c125d34",
            ),
        ]

        for input, output in vectors:
            self.assertEqual(
                hexlify(elligator2.map_to_curve25519(unhexlify(input))).decode("ascii"),
                output,
            )


if __name__ == "__main__":
    unittest.main()
