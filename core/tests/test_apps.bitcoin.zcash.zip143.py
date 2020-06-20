from common import *
from trezor.messages import InputScriptType
from trezor.messages.SignTx import SignTx
from trezor.messages.TxInputType import TxInputType
from trezor.messages.TxOutputBinType import TxOutputBinType

from apps.common import coins
from apps.bitcoin.writers import get_tx_hash

if not utils.BITCOIN_ONLY:
    from apps.bitcoin.sign_tx.zcash import Overwintered


# test vectors inspired from https://github.com/zcash-hackworks/zcash-test-vectors/blob/master/zip_0143.py
@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestZcashZip143(unittest.TestCase):

    VECTORS = [
        {
            "expiry": 71895707,
            "inputs": [
                {
                    "amount": 35268204,
                    "prevout": [
                        "702c35a67cd7364d3fab552fb349e35c15c50250453fd18f7b855992632e2c76",
                        4025613248,
                    ],
                    "pubkey": "03c6d9cc725bb7e19c026df03bf693ee1171371a8eaf25f04b7a58f6befabcd38c",
                    "script_type": InputScriptType.SPENDADDRESS,
                    "sequence": 1999822371,
                }
            ],
            "lock_time": 452079490,
            "outputs": [
                {"script_pubkey": "06535251635252", "amount": 1246336469307855}
            ],
            "version": 3,
            "version_group_id": 0x3C48270,
            "hash_type": 1,
            "prevouts_hash": b"bd4318eecf841a0cf01c2be532cf4bc3303e881e2aface159f1882f153152688",
            "sequence_hash": b"9ac6a31952ff626bf5a0a30d3d8ac63a0d4298d33d7bc38854bfa5860695e30a",
            "outputs_hash": b"d0cadf116b4441f5e1e17814908dee509ec262a79f3c88f7f3389e8200658992",
            "preimage_hash": b"fed855ea5fcec81928fa35d39b8582c6e026a0bf52cebeed4445a7fc7d730280",
        },
        {
            "expiry": 231041495,
            "inputs": [
                {
                    "amount": 39263472,
                    "prevout": [
                        "76647d2be4c2cd6b3d17d6870971d7a098baf72c6f6f1214cf1faae488bd7de2",
                        1547817817,
                    ],
                    "pubkey": "03c6d9cc725bb7e19c026df03bf693ee1171371a8eaf25f04b7a58f6befabcd38c",
                    "script_type": InputScriptType.SPENDADDRESS,
                    "sequence": 3973122135,
                },
                {
                    "amount": 57533728,
                    "prevout": [
                        "cccc0df65a04943ad5cbc13f295f000fe056c40b2d88f27dc34cfeb803be3483",
                        3053054889,
                    ],
                    "pubkey": "02c651a011009e2c7e7b3ed2068857ca0a47cba35b73e06c32e3c06ef3aa67621d",
                    "script_type": InputScriptType.SPENDADDRESS,
                    "sequence": 3932380530,
                },
            ],
            "lock_time": 3087412294,
            "outputs": [
                {"script_pubkey": "03ac6552", "amount": 546412698509744},
                {"script_pubkey": "00", "amount": 166856241017532},
            ],
            "version": 3,
            "version_group_id": 0x3C48270,
            "hash_type": 1,
            "prevouts_hash": b"8e286c6c0dde3119271c9c1398ef46614b0253c502b00a3691cec2e9047da35b",
            "sequence_hash": b"58477fd9ecd5faf3e08159e0ab5fdaab66cab364d081498ddcef41de0af3624e",
            "outputs_hash": b"c518797fc6f2c08fc22aa3f66122047b360e1db4df5c3feb28573c00cdf45fa1",
            "preimage_hash": b"1c6f563d2f16002f4c59bec5e7d56ed298315630c1d7e9a431b89e6f81026a02",
        },
        {
            "expiry": 186996458,
            "inputs": [
                {
                    "amount": 14267260,
                    "prevout": [
                        "6c6fae359f645c276891c0dcab3faf187700c082dc477740fb3f2cd7bb59fb35",
                        1290359941,
                    ],
                    "script_type": InputScriptType.SPENDADDRESS,
                    "pubkey": "03c6d9cc725bb7e19c026df03bf693ee1171371a8eaf25f04b7a58f6befabcd38c",
                    "sequence": 1230917966,
                }
            ],
            "lock_time": 1520002857,
            "outputs": [],
            "version": 3,
            "version_group_id": 0x3C48270,
            "hash_type": 1,
            "prevouts_hash": b"445bc6328cd33b3c86259953dd674bded341ff1e1104dc21856919e9761036dd",
            "sequence_hash": b"42e1d5c2636f165afaa954afa6d7a50779eb145e947bf668f1a40dd771c711fc",
            "outputs_hash": b"869eda84eecf7257f9979a4848bbf52f4969a5736594ab7ba41452e7bb906824",
            "preimage_hash": b"7159247daa16cc7e683f03ebf968314ce03324028ac138468a7b76c77e551fe8",
        },
        {
            "expiry": 254788522,
            "inputs": [
                {
                    "amount": 36100600,
                    "prevout": [
                        "e818f9057c5abaaa2e5c15b94945cd424c28a5fa385dadfe4907b274d842707d",
                        1517971891,
                    ],
                    "script_type": InputScriptType.SPENDADDRESS,
                    "pubkey": "03c6d9cc725bb7e19c026df03bf693ee1171371a8eaf25f04b7a58f6befabcd38c",
                    "sequence": 3833577708,
                },
                {
                    "amount": 71238918,
                    "prevout": [
                        "7350d1014670212efe81fb7c73e8450df814ef6232f7490f63ccf07480f884a6",
                        687648622,
                    ],
                    "script_type": InputScriptType.SPENDADDRESS,
                    "pubkey": "02c651a011009e2c7e7b3ed2068857ca0a47cba35b73e06c32e3c06ef3aa67621d",
                    "sequence": 4190617831,
                },
            ],
            "lock_time": 1557067344,
            "outputs": [
                {"script_pubkey": "076a53655151516a", "amount": 470086065540185}
            ],
            "version": 3,
            "version_group_id": 0x3C48270,
            "hash_type": 1,
            "prevouts_hash": b"509abdfafcc75265037f1ce6a4658ac9ecadd7b82378c3fbaeb48ab437ff6898",
            "sequence_hash": b"2b13f671cd1a9aa04c1e250eef74a316d7d2b049360d20604514ddc2dfacfd23",
            "outputs_hash": b"4f01b8785e80779290aa86c16b24952f9b7f8bc09da44e68f760ab1920ab8f2a",
            "preimage_hash": b"16b24c5d599107efb41cbc6cb0127094878bab1e0d33d734cfccce58e07b3386",
        },
    ]

    def test_zip143(self):
        coin = coins.by_name("Zcash")

        for v in self.VECTORS:
            tx = SignTx(
                coin_name="Zcash",
                inputs_count=len(v["inputs"]),
                outputs_count=len(v["outputs"]),
                version=v["version"],
                lock_time=v["lock_time"],
                expiry=v["expiry"],
                version_group_id=v["version_group_id"],
            )

            zip143 = Overwintered(tx, None, coin)

            for i in v["inputs"]:
                txi = TxInputType()
                txi.amount = i["amount"]
                txi.prev_hash = unhexlify(i["prevout"][0])
                txi.prev_index = i["prevout"][1]
                txi.script_type = i["script_type"]
                txi.sequence = i["sequence"]
                zip143.hash143_add_input(txi)
            for o in v["outputs"]:
                txo = TxOutputBinType()
                txo.amount = o["amount"]
                txo.script_pubkey = unhexlify(o["script_pubkey"])
                zip143.hash143_add_output(txo, txo.script_pubkey)

            self.assertEqual(hexlify(get_tx_hash(zip143.h_prevouts)), v["prevouts_hash"])
            self.assertEqual(hexlify(get_tx_hash(zip143.h_sequence)), v["sequence_hash"])
            self.assertEqual(hexlify(get_tx_hash(zip143.h_outputs)), v["outputs_hash"])
            self.assertEqual(
                hexlify(zip143.hash143_preimage_hash(txi, [unhexlify(i["pubkey"])], 1)),
                v["preimage_hash"],
            )


if __name__ == "__main__":
    unittest.main()
