from common import *

from apps.zcash.orchard.signer import (
    shuffle, OrchardSigner,
    _sanitize_input, _sanitize_output,
)
from trezor.utils import empty_bytearray
from apps.zcash.signer import ZcashApprover, ZcashExtendedSigHasher
from apps.zcash.orchard.keychain import OrchardKeychain
from apps.common.coininfo import by_name
from trezor.messages import *
from trezor.messages import (
    SignTx, ZcashOrchardData, TxRequest,
    ZcashOrchardInput, ZcashOrchardOutput,
    TxRequestSerializedType, TxRequestDetailsType,
)

from apps.bitcoin.sign_tx.helpers import sanitize_sign_tx
from apps.bitcoin.sign_tx.tx_info import TxInfo

ZCASH_COININFO = by_name("Zcash Testnet")


def evaluate_awaitable(task):
    while True:
        try:
            task.send(None)
        except StopIteration:
            break

class BoxedOrchardSigner(OrchardSigner):
    def __init__(self, tx, key_seed, shielding_seed, inputs, outputs):
        super().__init__(
            TxInfo(self, sanitize_sign_tx(tx, ZCASH_COININFO)),
            OrchardKeychain(key_seed, ZCASH_COININFO),
            ZcashApprover(tx, ZCASH_COININFO),
            ZCASH_COININFO,
            TxRequest(
                details = TxRequestDetailsType(),
                serialized = TxRequestSerializedType(
                    serialized_tx = empty_bytearray(2048),
                ),
            )
        )
        self.tx_info.sig_hasher.initialize(self.tx_info.tx)
        self.inputs = inputs
        self.outputs = outputs
        self.shielding_seed = shielding_seed
        self.serialized = b""

    def create_sig_hasher(self):
        return ZcashExtendedSigHasher()

    def gen_shielding_seed(self):
        return self.shielding_seed

    async def get_input(self, i):
        return _sanitize_input(self.inputs[i])

    async def get_output(self, i):
        return _sanitize_output(self.outputs[i])

    def verify_hmac(self, msg, hmac_type, index):
        pass

@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestZcashShielding(unittest.TestCase):
    def test_orchard_actions_shuffle(self):
        seed = unhexlify("2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b")
        expected_states = [
            [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19],
            [8, 2, 15, 14, 12, 5, 9, 18, 16, 17, 19, 6, 13, 3, 1, 0, 4, 10, 7, 11],
            [8, 5, 16, 6, 17, 4, 14, 10, 1, 7, 13, 0, 2, 18, 3, 9, 19, 11, 12, 15],
            [13, 7, 15, 5, 18, 6, 16, 11, 9, 0, 8, 10, 3, 12, 4, 14, 17, 19, 1, 2],
            [12, 6, 10, 0, 8, 19, 5, 7, 9, 13, 15, 3, 17, 11, 14, 4, 18, 2, 16, 1],
            [2, 19, 17, 12, 10, 5, 8, 3, 13, 15, 11, 4, 1, 7, 0, 6, 9, 16, 14, 18],
            [14, 16, 9, 2, 18, 12, 1, 11, 10, 13, 17, 4, 0, 3, 8, 7, 5, 15, 6, 19],
            [12, 10, 9, 0, 13, 5, 14, 4, 19, 3, 7, 2, 16, 11, 17, 6, 15, 1, 8, 18],
            [8, 11, 2, 9, 7, 18, 15, 1, 16, 5, 10, 13, 4, 17, 14, 0, 12, 3, 19, 6],
            [2, 6, 11, 10, 8, 16, 5, 12, 19, 14, 17, 9, 1, 0, 7, 18, 4, 3, 13, 15],
            [1, 10, 4, 18, 6, 14, 5, 7, 17, 9, 19, 3, 0, 15, 11, 12, 16, 8, 13, 2],
            [16, 5, 0, 14, 6, 9, 18, 10, 12, 3, 17, 1, 8, 4, 11, 7, 15, 19, 2, 13],
            [16, 8, 17, 15, 2, 14, 13, 3, 7, 12, 0, 18, 4, 6, 19, 9, 5, 10, 11, 1],
            [5, 10, 6, 19, 4, 12, 0, 9, 16, 14, 11, 3, 15, 18, 7, 17, 1, 2, 8, 13],
            [2, 3, 5, 4, 12, 1, 17, 13, 6, 7, 15, 11, 0, 19, 16, 10, 8, 14, 9, 18],
            [8, 12, 1, 0, 2, 4, 16, 13, 7, 15, 19, 10, 18, 6, 17, 9, 14, 11, 3, 5],
        ]

        rng_state = {
            "seed": seed,
            "pos": 0,
        }

        actual_state = expected_states[0]
        for expected_state in expected_states:
            self.assertEqual(actual_state, expected_state)
            shuffle(actual_state, rng_state)

    def test_orchard_bundle_shielding(self):
        tx = SignTx(
            inputs_count = 0,
            outputs_count = 0,
            coin_name = "Zcash Testnet",
            version = 5,
            version_group_id = 0x26A7270A,
            branch_id = 0x37519621,
            expiry = 0,
            orchard = ZcashOrchardData(
                outputs_count = 1,
                inputs_count = 1,
                anchor = unhexlify("cde081516549d2485ce26b62e9d81fae4c32398a410a61f82008f6e75e3d930e"),
                enable_spends = True,
                enable_outputs = True,
                account = 0,
            ),
        )
        key_seed = unhexlify("c76c4ac4f4e4a00d6b274d5c39c700bb4a7ddc04fbc6f78e85ca75007b5b495f74a9043eeb77bdd53aa6fc3a0e31462270316fa04b8c19114c8798706cd02ac9")
        shielding_seed = unhexlify("0505050505050505050505050505050505050505050505050505050505050505")
        inputs = [
            ZcashOrchardInput(
                note = unhexlify("000000000000000000000079f06d3a6d132b27c08f6bb7fb950a2224f2bb8830c364c1cb845477d04b6419881300000000000000000000000000000000000000000000000000000000000000000000000000009bf49a6a0755f953811fce125f2683d50429c3bb49e074147e0089a52eae155f"),
                amount = 5000,
                internal = False,
            ),
        ]
        outputs = [
            ZcashOrchardOutput(
                amount = 5000,
                address = "utest1p75982zvpjqre6l7wx8jurclud46py70yxdvhsx35xs9n64lkl2alrmk9a4l5dpul7ac7h8zzrkafswgpx923p034ff4ppgt7uxt2237"
            ),
        ]
        serialized = unhexlify("a3eab9de8c6ced2082040b8e6994303875f1dc7f646579a7269e39c8d5fde8954d0399bce9535a2b5c4fb6ea8366e120f0589fc89bd94d0ecd932ff10f83340a4f18e5d02b7a51fb4f6f411e554f5fce48aaca43c78d72e7746870ed7eb463bc37f6c0527c1c28bf530424dbf870d5688c355e7d26b1cc724eec20933e94c20f9156975f5fc132a3e3f5c67dae620401cad5531143b99b471d15cf5e806e472cedadce82c1aa3d617b466ecd246096046fabd311f45e89032fde8a95db4194b12ca2c7ec4b8079ee6d771ec858ea23bfd2d9a6b63402de8027e04f7103729606a430103b25a00a6a8cac7a81f7d5cca04559b83b978bf5a0723677b639bd2d219fe82a2a598f07747e80cffa1ce94ee1d43aed3c58d9d5f9b4f40abbda5de76c0e0ff40c585deb39fe12d71b92280bdf056cdfa6a17b934238899d7ab14765c12df4da50b7e03d8d5096f876dfc7dbb5304ec28c8f8d940d38a10a51527b88601ab41a3c1eb35298feb0e23b1f426225bd5e65988e27dc5126cd8c198dc3e04479ea5ee225181b6e48f28736e0570747e09bf52e64c95623d836b4736979205a5223a8f287898ddf24e2673fbb82923b42b2c191a73d9484a185d65e63eddc9a1b772ac2a6570d56bca958cbd2545918cbf174701aefd0838881a562c4c336b3bf9d5cb41e2524327560e8effe5b7f7a69213782a5efd95343417205d861d44d4fa3a261125575d22f3606ae3ef6963685834094240caf50b2fb33280dad8aafc3398520f59d6d80735b4e2e3eb387c384d591332ec76132a2dae775b1eaeac97822b9df00eef73083487488e684a38e1a738c5bb0e9166384f44187f92d19397a36808900be88538de5f7fc5b4f127215e57a3dc1a4a11fc8ececae9b7fd0c4b215b3b4bcc8ba2d3ae43e1924bcf2c0c686d2e3b10bdec1d7e5aa917d01ec813c08951b5e27a4f208fc27cab0037b9714b23153b2b685087a762194666d7710d08872c1cf1977845d60e255b232ed76f081b3fc8a1711fd61bd7338303d52f09aaa6a2037ba0e8d2a2af4247d99be7518941ef8a13fad319ab6e80eb84ee56fc5aec116bcb60f664eca4d3f43483a2ce8d7d79f468d5afcb65a9c266503494cefc5b120ffa9fb226c2255554fc5796d3dc54dd4030000000000000000cde081516549d2485ce26b62e9d81fae4c32398a410a61f82008f6e75e3d930e")
        digest = unhexlify("c1e811d9e6c13b34bb902378cab6261bdee5f5859a4ada1b734b186d4c495595")

        signer = BoxedOrchardSigner(
            tx,
            key_seed,
            shielding_seed,
            inputs,
            outputs,
        )

        evaluate_awaitable(signer.process_flags())
        evaluate_awaitable(signer.compute_digest())
        computed_digest = signer.tx_info.sig_hasher.orchard.digest()
        self.assertEqual(computed_digest, digest)

if __name__ == '__main__':
    unittest.main()
