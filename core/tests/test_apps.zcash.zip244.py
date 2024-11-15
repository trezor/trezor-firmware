# flake8: noqa: F403,F405
from common import *  # isort:skip

from trezor.enums import InputScriptType
from trezor.messages import PrevOutput, SignTx, TxInput
from trezor.utils import HashWriter

from apps.zcash.hasher import ZcashHasher, blake2b, write_hash


# NOTE: moved into tests not to occupy flash space
# in firmware binary, when it is not used in production
def txid_digest(hasher: "ZcashHasher") -> bytes:
    """
    Returns the transaction identifier.

    see: https://zips.z.cash/zip-0244#id4
    """
    h = HashWriter(blake2b(outlen=32, personal=hasher.tx_hash_person))

    write_hash(h, hasher.header.digest())  # T.1
    write_hash(h, hasher.transparent.digest())  # T.2
    write_hash(h, hasher.sapling.digest())  # T.3
    write_hash(h, hasher.orchard.digest())  # T.4

    return h.get_digest()


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestZcashSigHasher(unittest.TestCase):
    def test_zcash_hasher(self):
        # this test vector was generated using
        # https://github.com/zcash-hackworks/zcash-test-vectors
        tx = SignTx(
            coin_name="Zcash",
            version=5,
            version_group_id=648488714,
            branch_id=928093729,
            lock_time=2591264634,
            expiry=36466477,
            inputs_count=3,
            outputs_count=3,
        )
        inputs = [
            TxInput(
                prev_hash=unhexlify(
                    "4f61d91843ccb386dd1c482169eef62efaaf9d9364b1666e4d4c299e04a852e1"
                ),
                prev_index=1569726664,
                multisig=None,
                amount=1249971475008092,
                script_type=InputScriptType.SPENDADDRESS,
                sequence=0x8849F2A3,
                script_pubkey=unhexlify(
                    "76a9149466817faf329208fc3c3ef42ce4513d22fc1f9b88ac"
                ),
            ),
            TxInput(
                prev_hash=unhexlify(
                    "368e9c7e1fe01f6c54db9379a94c2941ef180c25b869bf8dcdb1cf014253b3c7"
                ),
                prev_index=2648876502,
                multisig=None,
                amount=1353789347081201,
                script_type=InputScriptType.SPENDADDRESS,
                sequence=0x8A37691C,
                script_pubkey=unhexlify(
                    "76a9142275979f97043edd9a6083ee27d136727ce5f42888ac"
                ),
            ),
            TxInput(
                prev_hash=unhexlify(
                    "f5621d6ad566c13dce81632a9168694bb6bcec2f7bfac2626f9425e1640fe4f1"
                ),
                prev_index=492165032,
                multisig=None,
                amount=1672802384749611,
                script_type=InputScriptType.SPENDADDRESS,
                sequence=0x6A993D20,
                script_pubkey=unhexlify(
                    "76a914682c89bfc3940621bd4a4bfc349a79b46ce707e388ac"
                ),
            ),
        ]
        outputs = [
            PrevOutput(
                amount=865034086766210,
                script_pubkey=unhexlify(
                    "76a9140d06a745f44ab023752cb5b406ed8985e18130ab88ac"
                ),
            ),
            PrevOutput(
                amount=2088955338922857,
                script_pubkey=unhexlify(
                    "76a91463ccb8f676495c222f7fba1e31defa3d5a57efc288ac"
                ),
            ),
            PrevOutput(
                amount=1760123755646275,
                script_pubkey=unhexlify(
                    "76a914fb1a38e01d94903d3c3e0ad3360c1d3710acd20b88ac"
                ),
            ),
        ]
        pubkeys = [
            unhexlify(
                "02ed9c769c787fda78a7da13764707d14217e74e26428b47a2a8fe6d5a0bc46196"
            ),
            unhexlify(
                "0219ac5de9a45f76e7efede5259acd94bb047ab8e7cc60fe844cb32317072ebbf3"
            ),
            unhexlify(
                "02829099a7cf1f617c956c0222e7b77ae331813d6a736eab3c5f6344d961843d39"
            ),
        ]
        expected_txid = unhexlify(
            "c91d34ecc44484b07ee573f385d80e57e4e57571bb86aa6ec6c44d654123e4e9"
        )
        expected_sighashes = [
            unhexlify(
                "4d82669c8c0e9b1f26d59bcb347212f2d044eeb839fce21e039d8bb082bbc343"
            ),
            unhexlify(
                "2e2a27d78d117e28760d3c972f9614547ec57688c970f06c19c515cded6b030c"
            ),
            unhexlify(
                "d0a92ffd4a4d262f5b84598bcfca741a42c17b8e9d26cf4fd87839df8f33e4ee"
            ),
        ]

        hasher = ZcashHasher(tx)
        for txi in inputs:
            hasher.add_input(txi, txi.script_pubkey)
        for txo in outputs:
            hasher.add_output(txo, txo.script_pubkey)

        # test ZcashSigHasher.txid_digest
        computed_txid = txid_digest(hasher)
        self.assertEqual(computed_txid, expected_txid)

        # test ZcashSigHasher.signature_digest
        for txi, expected_sighash, _ in zip(inputs, expected_sighashes, pubkeys):
            computed_sighash = hasher.signature_digest(txi, txi.script_pubkey)
            self.assertEqual(computed_sighash, expected_sighash)


if __name__ == "__main__":
    unittest.main()
