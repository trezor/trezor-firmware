from common import *
from trezor.crypto.pallas import group_hash, Point
from apps.zcash.orchard.crypto import generators as gen


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestOrchardGenerators(unittest.TestCase):
    def test_zcash_recompute_orchard_generators(self):
        self.assertEqual(gen.SPENDING_KEY_BASE, group_hash('z.cash:Orchard', b'G'))
        self.assertEqual(gen.NULLIFIER_K_BASE, group_hash('z.cash:Orchard', b'K'))
        self.assertEqual(gen.VALUE_COMMITMENT_VALUE_BASE, group_hash('z.cash:Orchard-cv', b'v'))
        self.assertEqual(gen.VALUE_COMMITMENT_RANDOMNESS_BASE, group_hash('z.cash:Orchard-cv', b'r'))
        self.assertEqual(gen.NOTE_COMMITMENT_BASE, group_hash('z.cash:Orchard-NoteCommit-r', b''))
        self.assertEqual(gen.NOTE_COMMITMENT_Q, group_hash('z.cash:SinsemillaQ', b'z.cash:Orchard-NoteCommit-M'))
        self.assertEqual(gen.IVK_COMMITMENT_BASE, group_hash('z.cash:Orchard-CommitIvk-r', b''))
        self.assertEqual(gen.IVK_COMMITMENT_Q, group_hash('z.cash:SinsemillaQ', b'z.cash:Orchard-CommitIvk-M'))

    def test_zcash_orchard_generators(self):
        ZCASH_TEST_VECTORS = zcash_parse([
            ["From https://github.com/zcash-hackworks/zcash-test-vectors/blob/master/orchard_generators.py"],
            ["skb, nkb, vcvb, vcrb, cmb, cmq, ivkb, ivkq, mcq"],
            ["63c975b884721a8d0ca1707be30c7f0c5f445f3e7c188d3b06d6f128b32355b7", "75ca47e4a76a6fd39bdbb5cc92b17e5ecfc9f4fa7155372e8d19a89c16aae725", "6743f93a6ebda72a8c7c5a2b7fa304fe32b29b4f706aa8f7420f3d8e7a59702f", "915a3c8868c6c30e2f8090ee45d76e4048208dea5b23664fbb09a40f5544f407", "136efc0f482c022c7ca414fc5cc59e23f23d6f93ab9f23cd3345a928c306b2a6", "5d74a84009ba0e322add46fd5a0f96c55dedb079b4f29ff70dcdfb56a0078097", "18a1f85f6e482398c7ed1ad3e27f9502488980400a2934164e137050cd2ca2a5", "f2820f79922fcb6b32a2285124cc1b42fa41a25ab881cc7d11c8a94af10cbc05", "a0c6297ff9c7b9f870108dc055b9bec9990e89ef5a360fa0b918a86396d21616"]
        ])
        tv = list(ZCASH_TEST_VECTORS)[0]
        self.assertEqual(gen.SPENDING_KEY_BASE, Point(tv.skb))
        self.assertEqual(gen.NULLIFIER_K_BASE, Point(tv.nkb))
        self.assertEqual(gen.VALUE_COMMITMENT_VALUE_BASE, Point(tv.vcvb))
        self.assertEqual(gen.VALUE_COMMITMENT_RANDOMNESS_BASE, Point(tv.vcrb))
        self.assertEqual(gen.NOTE_COMMITMENT_BASE, Point(tv.cmb))
        self.assertEqual(gen.NOTE_COMMITMENT_Q, Point(tv.cmq))
        self.assertEqual(gen.IVK_COMMITMENT_BASE, Point(tv.ivkb))
        self.assertEqual(gen.IVK_COMMITMENT_Q, Point(tv.ivkq))
        # tv.mcq not tested
        # tv.mcq = merkle tree commitment Q personalization
        # which is not needed in Trezor


if __name__ == "__main__":
    unittest.main()
