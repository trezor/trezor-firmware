from common import *
from trezor.utils import BufferReader
from trezor.messages import TxInput, TxOutput, SignTx, PrevOutput
from trezor.enums import InputScriptType
from apps.common.readers import read_compact_size, read_uint64_le
from apps.zcash.sig_hasher import ZcashSigHasher, get_txin_sig_digest
from apps.zcash.signer import ZcashExtendedSigHasher
from apps.bitcoin.common import SigHashType
from apps.bitcoin.verification import SignatureVerifier, decode_der_signature
from trezor.crypto.curve import secp256k1

from apps.common.coininfo import by_name

COIN = by_name("Zcash")

@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestZcashSigHasher(unittest.TestCase):
    def test_zcash_extended_sig_hasher(self):
        # TEST VECTOR
        tx = SignTx(
            version=5,
            version_group_id=0x26a7270a,
            branch_id=0x37519621,
            lock_time=1785621,
            expiry=1785672,
            inputs_count=1,
            outputs_count=2,
        )
        vin1 = TxInput(
            amount=80399712075,
            #prev_hash=unhexlify("baabf185d65b480a860b02b1dd96030f66b23c1eb834c39ed0c7cec3674a0da6"),
            prev_hash=unhexlify("a60d4a67c3cec7d09ec334b81e3cb2660f0396ddb1020b860a485bd685f1abba"),  # reversed
            prev_index=0,
            script_pubkey=unhexlify("76a914896ed2bb906d29fed843f27fa770e6c2803ed02588ac"),
            script_type=InputScriptType.SPENDADDRESS,
            sequence=0xfffffffe,
        )
        signature_script = unhexlify("483045022100d98dab6845dca34249f794feab82af6b59f353546e13a8177620e1ee897a17b302201d2c57c05f4d0dc5b4ad59751abe4d182c89b772a3902c4045e2de9376a738dc012102dd9c73972e1af17b443fb5983728dfdf2a8386809508dfa19f4846b878c2f0b7")
        vout1 = PrevOutput(
            amount=100000000,
            script_pubkey=unhexlify("76a91484c451ce0fb26f530d392546706ad2269f2b3bd188ac"),
        )
        vout2 = PrevOutput(
            amount=80299711834,
            script_pubkey=unhexlify("76a914db95ed732fa88fd632bac8d75a9192723db98fef88ac"),
        )
        expected_sighash = unhexlify("a23204084760ae673d08209aab4a026afcb06c324d433e862d6392edd3a9f7f3")
        expected_txid = unhexlify("a56650ec3dcc388c010b62d8303fcdb7c35e60d9709783acf806a912ab9a4d64")

        hasher = ZcashExtendedSigHasher()
        hasher.initialize(tx)
        for txi in [vin1]:
            hasher.add_input(txi, txi.script_pubkey)

        for txo in [vout1, vout2]:
            hasher.add_output(txo, txo.script_pubkey)

        computed_txid = hasher.txid_digest()
        computed_txid = bytes(reversed(computed_txid))
        self.assertEqual(computed_txid, expected_txid)

        computed_sighash = hasher.hash143(
            vin1,
            [signature_script[-33:]],
            1,  # threshold
            tx,
            COIN,
            SigHashType.SIGHASH_ALL,
        )

        self.assertEqual(computed_sighash, expected_sighash)

        """
        v = SignatureVerifier(
            script_pubkey=vin1.script_pubkey,
            script_sig=signature_script,
            witness=None,
            coin=COIN,
        )

        v.verify(computed_sighash)
        """

if __name__ == "__main__":
    unittest.main()