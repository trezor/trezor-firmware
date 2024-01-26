from common import unhexlify, unittest  # isort:skip

from trezor.crypto import bip39
from trezor.enums import InputScriptType
from trezor.messages import HDNodeType, MultisigRedeemScriptType

from apps.bitcoin import ownership, scripts
from apps.bitcoin.addresses import (
    _address_multisig_p2sh,
    _address_multisig_p2wsh,
    _address_multisig_p2wsh_in_p2sh,
    _address_p2tr,
    address_p2wpkh,
    address_p2wpkh_in_p2sh,
)
from apps.bitcoin.multisig import multisig_get_pubkeys
from apps.common import coins
from apps.common.keychain import Keychain
from apps.common.paths import HARDENED, AlwaysMatchingSchema


class TestOwnershipProof(unittest.TestCase):
    def test_p2wpkh_gen_proof(self):
        # SLIP-0019 test vector 1
        coin = coins.by_name("Bitcoin")
        seed = bip39.seed(" ".join(["all"] * 12), "")
        keychain = Keychain(
            seed,
            coin.curve_name,
            [AlwaysMatchingSchema],
            slip21_namespaces=[[b"SLIP-0019"]],
        )
        commitment_data = b""

        node = keychain.derive([84 | HARDENED, 0 | HARDENED, 0 | HARDENED, 1, 0])
        address = address_p2wpkh(node.public_key(), coin)
        script_pubkey = scripts.output_derive_script(address, coin)
        ownership_id = ownership.get_identifier(script_pubkey, keychain)
        self.assertEqual(
            ownership_id,
            unhexlify(
                "a122407efc198211c81af4450f40b235d54775efd934d16b9e31c6ce9bad5707"
            ),
        )

        proof, signature = ownership.generate_proof(
            node=node,
            script_type=InputScriptType.SPENDWITNESS,
            multisig=None,
            coin=coin,
            user_confirmed=False,
            ownership_ids=[ownership_id],
            script_pubkey=script_pubkey,
            commitment_data=commitment_data,
        )
        self.assertEqual(
            signature,
            unhexlify(
                "3045022100c0dc28bb563fc5fea76cacff75dba9cb4122412faae01937cdebccfb065f9a7002202e980bfbd8a434a7fc4cd2ca49da476ce98ca097437f8159b1a386b41fcdfac5"
            ),
        )
        self.assertEqual(
            proof,
            unhexlify(
                "534c00190001a122407efc198211c81af4450f40b235d54775efd934d16b9e31c6ce9bad57070002483045022100c0dc28bb563fc5fea76cacff75dba9cb4122412faae01937cdebccfb065f9a7002202e980bfbd8a434a7fc4cd2ca49da476ce98ca097437f8159b1a386b41fcdfac50121032ef68318c8f6aaa0adec0199c69901f0db7d3485eb38d9ad235221dc3d61154b"
            ),
        )
        self.assertFalse(
            ownership.verify_nonownership(
                proof, script_pubkey, commitment_data, keychain, coin
            )
        )

    def test_p2wpkh_in_p2sh_gen_proof(self):
        # SLIP-0019 test vector 2
        coin = coins.by_name("Bitcoin")
        seed = bip39.seed(" ".join(["all"] * 12), "")
        keychain = Keychain(
            seed,
            coin.curve_name,
            [AlwaysMatchingSchema],
            slip21_namespaces=[[b"SLIP-0019"]],
        )
        commitment_data = b"TREZOR"

        node = keychain.derive([49 | HARDENED, 0 | HARDENED, 0 | HARDENED, 1, 0])
        address = address_p2wpkh_in_p2sh(node.public_key(), coin)
        script_pubkey = scripts.output_derive_script(address, coin)
        ownership_id = ownership.get_identifier(script_pubkey, keychain)

        self.assertEqual(
            ownership_id,
            unhexlify(
                "92caf0b8daf78f1d388dbbceaec34bd2dabc31b217e32343663667f6694a3f46"
            ),
        )

        proof, signature = ownership.generate_proof(
            node=node,
            script_type=InputScriptType.SPENDP2SHWITNESS,
            multisig=None,
            coin=coin,
            user_confirmed=True,
            ownership_ids=[ownership_id],
            script_pubkey=script_pubkey,
            commitment_data=commitment_data,
        )
        self.assertEqual(
            signature,
            unhexlify(
                "304402207f1003c59661ddf564af2e10d19ad8d6a1a47ad30e7052197d95fd65d186a67802205f0a804509980fec1b063554aadd8fb871d7c9fe934087cba2da09cbeff8531c"
            ),
        )
        self.assertEqual(
            proof,
            unhexlify(
                "534c0019010192caf0b8daf78f1d388dbbceaec34bd2dabc31b217e32343663667f6694a3f4617160014e0cffbee1925a411844f44c3b8d81365ab51d0360247304402207f1003c59661ddf564af2e10d19ad8d6a1a47ad30e7052197d95fd65d186a67802205f0a804509980fec1b063554aadd8fb871d7c9fe934087cba2da09cbeff8531c012103a961687895a78da9aef98eed8e1f2a3e91cfb69d2f3cf11cbd0bb1773d951928"
            ),
        )
        self.assertFalse(
            ownership.verify_nonownership(
                proof, script_pubkey, commitment_data, keychain, coin
            )
        )

    def test_p2tr_gen_proof(self):
        # SLIP-0019 test vector 5
        coin = coins.by_name("Bitcoin")
        seed = bip39.seed(" ".join(["all"] * 12), "")
        keychain = Keychain(
            seed,
            coin.curve_name,
            [AlwaysMatchingSchema],
            slip21_namespaces=[[b"SLIP-0019"]],
        )
        commitment_data = b""

        node = keychain.derive([86 | HARDENED, 0 | HARDENED, 0 | HARDENED, 1, 0])
        address = _address_p2tr(node.public_key(), coin)
        script_pubkey = scripts.output_derive_script(address, coin)
        ownership_id = ownership.get_identifier(script_pubkey, keychain)
        self.assertEqual(
            ownership_id,
            unhexlify(
                "dc18066224b9e30e306303436dc18ab881c7266c13790350a3fe415e438135ec"
            ),
        )

        proof, signature = ownership.generate_proof(
            node=node,
            script_type=InputScriptType.SPENDTAPROOT,
            multisig=None,
            coin=coin,
            user_confirmed=False,
            ownership_ids=[ownership_id],
            script_pubkey=script_pubkey,
            commitment_data=commitment_data,
        )
        self.assertEqual(
            signature,
            unhexlify(
                "647d6af883107a870417e808abe424882bd28ee04a28ba85a7e99400e1b9485075733695964c2a0fa02d4439ab80830e9566ccbd10f2597f5513eff9f03a0497"
            ),
        )
        self.assertEqual(
            proof,
            unhexlify(
                "534c00190001dc18066224b9e30e306303436dc18ab881c7266c13790350a3fe415e438135ec000140647d6af883107a870417e808abe424882bd28ee04a28ba85a7e99400e1b9485075733695964c2a0fa02d4439ab80830e9566ccbd10f2597f5513eff9f03a0497"
            ),
        )
        self.assertFalse(
            ownership.verify_nonownership(
                proof, script_pubkey, commitment_data, keychain, coin
            )
        )

    def test_p2pkh_gen_proof(self):
        # SLIP-0019 test vector 3
        coin = coins.by_name("Bitcoin")
        seed = bip39.seed(" ".join(["all"] * 12), "TREZOR")
        keychain = Keychain(
            seed,
            coin.curve_name,
            [AlwaysMatchingSchema],
            slip21_namespaces=[[b"SLIP-0019"]],
        )
        commitment_data = b""

        node = keychain.derive([44 | HARDENED, 0 | HARDENED, 0 | HARDENED, 1, 0])
        address = node.address(coin.address_type)
        script_pubkey = scripts.output_derive_script(address, coin)
        ownership_id = ownership.get_identifier(script_pubkey, keychain)
        self.assertEqual(
            ownership_id,
            unhexlify(
                "ccc49ac5fede0efc80725fbda8b763d4e62a221c51cc5425076cffa7722c0bda"
            ),
        )

        proof, signature = ownership.generate_proof(
            node=node,
            script_type=InputScriptType.SPENDADDRESS,
            multisig=None,
            coin=coin,
            user_confirmed=False,
            ownership_ids=[ownership_id],
            script_pubkey=script_pubkey,
            commitment_data=commitment_data,
        )
        self.assertEqual(
            signature,
            unhexlify(
                "3045022100e818002d0a85438a7f2140503a6aa0a6af6002fa956d0101fd3db24e776e546f0220430fd59dc1498bc96ab6e71a4829b60224828cf1fc35edc98e0973db203ca3f0"
            ),
        )
        self.assertEqual(
            proof,
            unhexlify(
                "534c00190001ccc49ac5fede0efc80725fbda8b763d4e62a221c51cc5425076cffa7722c0bda6b483045022100e818002d0a85438a7f2140503a6aa0a6af6002fa956d0101fd3db24e776e546f0220430fd59dc1498bc96ab6e71a4829b60224828cf1fc35edc98e0973db203ca3f0012102f63159e21fbcb54221ec993def967ad2183a9c243c8bff6e7d60f4d5ed3b386500"
            ),
        )
        self.assertFalse(
            ownership.verify_nonownership(
                proof, script_pubkey, commitment_data, keychain, coin
            )
        )

    def test_p2wpkh_verify_proof(self):
        # SLIP-0019 test vector 1
        coin = coins.by_name("Bitcoin")
        seed = bip39.seed(" ".join(["all"] * 12), "TREZOR")
        keychain = Keychain(
            seed,
            coin.curve_name,
            [AlwaysMatchingSchema],
            slip21_namespaces=[[b"SLIP-0019"]],
        )
        commitment_data = b""

        # Proof for "all all ... all" seed without passphrase.
        script_pubkey = unhexlify("0014b2f771c370ccf219cd3059cda92bdf7f00cf2103")
        proof = unhexlify(
            "534c00190001a122407efc198211c81af4450f40b235d54775efd934d16b9e31c6ce9bad57070002483045022100c0dc28bb563fc5fea76cacff75dba9cb4122412faae01937cdebccfb065f9a7002202e980bfbd8a434a7fc4cd2ca49da476ce98ca097437f8159b1a386b41fcdfac50121032ef68318c8f6aaa0adec0199c69901f0db7d3485eb38d9ad235221dc3d61154b"
        )
        self.assertTrue(
            ownership.verify_nonownership(
                proof, script_pubkey, commitment_data, keychain, coin
            )
        )

    def test_p2tr_verify_proof(self):
        # SLIP-0019 test vector 5
        coin = coins.by_name("Bitcoin")
        seed = bip39.seed(" ".join(["all"] * 12), "TREZOR")
        keychain = Keychain(
            seed,
            coin.curve_name,
            [AlwaysMatchingSchema],
            slip21_namespaces=[[b"SLIP-0019"]],
        )
        commitment_data = b""

        # Proof for "all all ... all" seed without passphrase.
        script_pubkey = unhexlify(
            "51204102897557de0cafea0a8401ea5b59668eccb753e4b100aebe6a19609f3cc79f"
        )
        proof = unhexlify(
            "534c00190001dc18066224b9e30e306303436dc18ab881c7266c13790350a3fe415e438135ec0001401b553e5b9cc787b531bbc78417aea901272b4ea905136a2babc4d6ca471549743b5e0e39ddc14e620b254e42faa7f6d5bd953e97aa231d764d21bc5a58e8b7d9"
        )
        self.assertTrue(
            ownership.verify_nonownership(
                proof, script_pubkey, commitment_data, keychain, coin
            )
        )

    def test_p2wsh_gen_proof(self):
        # SLIP-0019 test vector 4
        coin = coins.by_name("Bitcoin")
        seed1 = bip39.seed(" ".join(["all"] * 12), "")
        seed2 = bip39.seed(
            "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about",
            "",
        )
        seed3 = bip39.seed("zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo wrong", "")
        commitment_data = b"TREZOR"

        nodes = []
        keychains = []
        for seed in [seed1, seed2, seed3]:
            keychain = Keychain(
                seed,
                coin.curve_name,
                [AlwaysMatchingSchema],
                slip21_namespaces=[[b"SLIP-0019"]],
            )
            keychains.append(keychain)
            node = keychain.derive([84 | HARDENED, 0 | HARDENED, 0 | HARDENED])
            nodes.append(
                HDNodeType(
                    depth=node.depth(),
                    child_num=node.child_num(),
                    fingerprint=node.fingerprint(),
                    chain_code=node.chain_code(),
                    public_key=node.public_key(),
                )
            )

        multisig = MultisigRedeemScriptType(
            nodes=nodes,
            address_n=[1, 0],
            signatures=[b"", b"", b""],
            m=2,
        )

        pubkeys = multisig_get_pubkeys(multisig)
        address = _address_multisig_p2wsh(pubkeys, multisig.m, coin.bech32_prefix)
        script_pubkey = scripts.output_derive_script(address, coin)
        ownership_ids = [
            ownership.get_identifier(script_pubkey, keychain) for keychain in keychains
        ]
        self.assertEqual(
            ownership_ids[0],
            unhexlify(
                "309c4ffec5c228cc836b51d572c0a730dbabd39df9f01862502ac9eabcdeb94a"
            ),
        )
        self.assertEqual(
            ownership_ids[1],
            unhexlify(
                "46307177b959c48bf2eb516e0463bb651aad388c7f8f597320df7854212fa344"
            ),
        )
        self.assertEqual(
            ownership_ids[2],
            unhexlify(
                "3892f9573e08cedff9160b243759520733a980fed45b131a8bba171317ae5d94"
            ),
        )

        # Sign with the first key.
        _, signature = ownership.generate_proof(
            node=keychains[0].derive([84 | HARDENED, 0 | HARDENED, 0 | HARDENED, 1, 0]),
            script_type=InputScriptType.SPENDWITNESS,
            multisig=multisig,
            coin=coin,
            user_confirmed=False,
            ownership_ids=ownership_ids,
            script_pubkey=script_pubkey,
            commitment_data=commitment_data,
        )
        self.assertEqual(
            signature,
            unhexlify(
                "30450221009d8cd2d792633732b3a406ea86072e94c72c0d1ffb5ddde466993ee2142eeef502206fa9c6273ab35400ebf689028ebcf8d2031edb3326106339e92d499652dc4303"
            ),
        )
        multisig.signatures[0] = signature

        # Sign with the third key.
        proof, signature = ownership.generate_proof(
            node=keychain.derive([84 | HARDENED, 0 | HARDENED, 0 | HARDENED, 1, 0]),
            script_type=InputScriptType.SPENDWITNESS,
            multisig=multisig,
            coin=coin,
            user_confirmed=False,
            ownership_ids=ownership_ids,
            script_pubkey=script_pubkey,
            commitment_data=commitment_data,
        )
        self.assertEqual(
            signature,
            unhexlify(
                "304402205fae1218bc4600ad6c28b6093e8f3757603681b024e60f1d92fca579bfce210b022011d6f1c6ef1c7f7601f635ed237dafc774386dd9f4be0aef85e3af3f095d8a92"
            ),
        )
        self.assertEqual(
            proof,
            unhexlify(
                "534c00190003309c4ffec5c228cc836b51d572c0a730dbabd39df9f01862502ac9eabcdeb94a46307177b959c48bf2eb516e0463bb651aad388c7f8f597320df7854212fa3443892f9573e08cedff9160b243759520733a980fed45b131a8bba171317ae5d940004004830450221009d8cd2d792633732b3a406ea86072e94c72c0d1ffb5ddde466993ee2142eeef502206fa9c6273ab35400ebf689028ebcf8d2031edb3326106339e92d499652dc43030147304402205fae1218bc4600ad6c28b6093e8f3757603681b024e60f1d92fca579bfce210b022011d6f1c6ef1c7f7601f635ed237dafc774386dd9f4be0aef85e3af3f095d8a9201695221032ef68318c8f6aaa0adec0199c69901f0db7d3485eb38d9ad235221dc3d61154b2103025324888e429ab8e3dbaf1f7802648b9cd01e9b418485c5fa4c1b9b5700e1a621033057150eb57e2b21d69866747f3d377e928f864fa88ecc5ddb1c0e501cce3f8153ae"
            ),
        )
        self.assertFalse(
            ownership.verify_nonownership(
                proof, script_pubkey, commitment_data, keychain, coin
            )
        )

    def test_p2wsh_in_p2sh_gen_proof(self):
        coin = coins.by_name("Bitcoin")
        seed = bip39.seed(" ".join(["all"] * 12), "")
        keychain = Keychain(
            seed,
            coin.curve_name,
            [AlwaysMatchingSchema],
            slip21_namespaces=[[b"SLIP-0019"]],
        )
        commitment_data = b""

        nodes = []
        for index in range(1, 6):
            node = keychain.derive([49 | HARDENED, 0 | HARDENED, index | HARDENED])
            nodes.append(
                HDNodeType(
                    depth=node.depth(),
                    child_num=node.child_num(),
                    fingerprint=node.fingerprint(),
                    chain_code=node.chain_code(),
                    public_key=node.public_key(),
                )
            )

        multisig = MultisigRedeemScriptType(
            nodes=nodes,
            address_n=[0, 1],
            signatures=[b"", b"", b"", b"", b""],
            m=3,
        )

        pubkeys = multisig_get_pubkeys(multisig)
        address = _address_multisig_p2wsh_in_p2sh(pubkeys, multisig.m, coin)
        script_pubkey = scripts.output_derive_script(address, coin)
        ownership_id = ownership.get_identifier(script_pubkey, keychain)
        ownership_ids = [b"\x00" * 32, b"\x01" * 32, b"\x02" * 32, ownership_id]
        self.assertEqual(
            ownership_id,
            unhexlify(
                "66f99db388dfa7ae137f7bdb5f0004b4d6968014921cfaff1fec042e3bb83ae0"
            ),
        )

        # Sign with the second key.
        _, signature = ownership.generate_proof(
            node=keychain.derive([49 | HARDENED, 0 | HARDENED, 2 | HARDENED, 0, 1]),
            script_type=InputScriptType.SPENDP2SHWITNESS,
            multisig=multisig,
            coin=coin,
            user_confirmed=False,
            ownership_ids=ownership_ids,
            script_pubkey=script_pubkey,
            commitment_data=commitment_data,
        )
        self.assertEqual(
            signature,
            unhexlify(
                "30450221008c2c61ac2b50fd5f644baf5e8815b41caaf41d3b085d6e79c1ab38ab9ff4ef0702206742f837eddd4484ebf642e0bcb9621fe39165d3c9d62706bb01b2a8d854fb39"
            ),
        )
        multisig.signatures[1] = signature

        # Sign with the fourth key.
        proof, signature = ownership.generate_proof(
            node=keychain.derive([49 | HARDENED, 0 | HARDENED, 4 | HARDENED, 0, 1]),
            script_type=InputScriptType.SPENDP2SHWITNESS,
            multisig=multisig,
            coin=coin,
            user_confirmed=False,
            ownership_ids=ownership_ids,
            script_pubkey=script_pubkey,
            commitment_data=commitment_data,
        )
        self.assertEqual(
            signature,
            unhexlify(
                "304402200f5ec86b369f6a980a237944a1a06e6615afb147c6d84baf28cd1b8a58faf52702205614240e1582adeaa84685398a24d3678d0781371678b402b290ae3de3e058ee"
            ),
        )
        multisig.signatures[3] = signature

        # Sign with the fifth key.
        proof, signature = ownership.generate_proof(
            node=keychain.derive([49 | HARDENED, 0 | HARDENED, 5 | HARDENED, 0, 1]),
            script_type=InputScriptType.SPENDP2SHWITNESS,
            multisig=multisig,
            coin=coin,
            user_confirmed=False,
            ownership_ids=ownership_ids,
            script_pubkey=script_pubkey,
            commitment_data=commitment_data,
        )
        self.assertEqual(
            signature,
            unhexlify(
                "304402201ce53fcd797b6f5ceefa839817d6285551ff420457503ae2dab3f90ca1f6f2330220522f030423c22d5582c4f8fe243839031f584642ba5c085af712145d1e8146b7"
            ),
        )
        self.assertEqual(
            proof,
            unhexlify(
                "534c0019000400000000000000000000000000000000000000000000000000000000000000000101010101010101010101010101010101010101010101010101010101010101020202020202020202020202020202020202020202020202020202020202020266f99db388dfa7ae137f7bdb5f0004b4d6968014921cfaff1fec042e3bb83ae0232200208c256ed80a97a421656daa1468f6d4d43f475cb52ed79532d8bcb3155182981205004830450221008c2c61ac2b50fd5f644baf5e8815b41caaf41d3b085d6e79c1ab38ab9ff4ef0702206742f837eddd4484ebf642e0bcb9621fe39165d3c9d62706bb01b2a8d854fb390147304402200f5ec86b369f6a980a237944a1a06e6615afb147c6d84baf28cd1b8a58faf52702205614240e1582adeaa84685398a24d3678d0781371678b402b290ae3de3e058ee0147304402201ce53fcd797b6f5ceefa839817d6285551ff420457503ae2dab3f90ca1f6f2330220522f030423c22d5582c4f8fe243839031f584642ba5c085af712145d1e8146b701ad5321032922ce9b0b71ae2d2d8a7f239610ae8226e0fb8c0f445ec4c88cf9aa4787f44b21028373a1cdb9a1afbc67e57f75eeea1f53e7210ae8ec4b3441a5f2bc4a250b663c21028ab4c06e3ad19053b370eff097697d4cb6d3738712ebcdcdc27c58a5639ac3aa2103e3247fab300aeba459257e4605245f85378ecbfe092ca3bc55ec1259baa456f521023b0d8d97398d97c4dba10f788344abd4bd1058ad3959724d32079ad04bdbde8a55ae"
            ),
        )
        self.assertFalse(
            ownership.verify_nonownership(
                proof, script_pubkey, commitment_data, keychain, coin
            )
        )

    def test_p2sh_gen_proof(self):
        coin = coins.by_name("Bitcoin")
        seed = bip39.seed(" ".join(["all"] * 12), "")
        keychain = Keychain(
            seed,
            coin.curve_name,
            [AlwaysMatchingSchema],
            slip21_namespaces=[[b"SLIP-0019"]],
        )
        commitment_data = b"TREZOR"

        nodes = []
        for index in range(1, 3):
            node = keychain.derive([48 | HARDENED, 0 | HARDENED, index | HARDENED])
            nodes.append(
                HDNodeType(
                    depth=node.depth(),
                    child_num=node.child_num(),
                    fingerprint=node.fingerprint(),
                    chain_code=node.chain_code(),
                    public_key=node.public_key(),
                )
            )

        multisig = MultisigRedeemScriptType(
            nodes=nodes,
            address_n=[0, 0],
            signatures=[b"", b""],
            m=2,
        )

        pubkeys = multisig_get_pubkeys(multisig)
        address = _address_multisig_p2sh(pubkeys, multisig.m, coin)
        script_pubkey = scripts.output_derive_script(address, coin)
        ownership_id = ownership.get_identifier(script_pubkey, keychain)
        ownership_ids = [b"\x00" * 32, ownership_id]
        self.assertEqual(
            ownership_id,
            unhexlify(
                "ce4ee8298ad105c3495a1d2b620343133521ab34de2450deeb32eec39475fef4"
            ),
        )

        # Sign with the first key.
        _, signature = ownership.generate_proof(
            node=keychain.derive([48 | HARDENED, 0 | HARDENED, 1 | HARDENED, 0, 0]),
            script_type=InputScriptType.SPENDMULTISIG,
            multisig=multisig,
            coin=coin,
            user_confirmed=False,
            ownership_ids=ownership_ids,
            script_pubkey=script_pubkey,
            commitment_data=commitment_data,
        )
        self.assertEqual(
            signature,
            unhexlify(
                "3044022058091b367ab67281963029435046abcb51057d143077a36737780a7cbcd6c1af02202f54147645b970c60b5b631b233ed93c15304294a4214b2c44b57db84815ca14"
            ),
        )
        multisig.signatures[0] = signature

        # Sign with the third key.
        proof, signature = ownership.generate_proof(
            node=keychain.derive([48 | HARDENED, 0 | HARDENED, 2 | HARDENED, 0, 0]),
            script_type=InputScriptType.SPENDMULTISIG,
            multisig=multisig,
            coin=coin,
            user_confirmed=False,
            ownership_ids=ownership_ids,
            script_pubkey=script_pubkey,
            commitment_data=commitment_data,
        )
        self.assertEqual(
            signature,
            unhexlify(
                "304402200d8f270ea9a80678f266b3fbe6e4aa59aab46b440d8066dcf46fb46a4beaf58202201198d73e355158ebf532ca6527e28ea97b79594e016a65c7a0c68813c26271ff"
            ),
        )
        self.assertEqual(
            proof,
            unhexlify(
                "534c001900020000000000000000000000000000000000000000000000000000000000000000ce4ee8298ad105c3495a1d2b620343133521ab34de2450deeb32eec39475fef4d900473044022058091b367ab67281963029435046abcb51057d143077a36737780a7cbcd6c1af02202f54147645b970c60b5b631b233ed93c15304294a4214b2c44b57db84815ca140147304402200d8f270ea9a80678f266b3fbe6e4aa59aab46b440d8066dcf46fb46a4beaf58202201198d73e355158ebf532ca6527e28ea97b79594e016a65c7a0c68813c26271ff014752210203ed6187880ae932660086e55d4561a57952dd200aa3ed2aa66b73e5723a0ce7210360e7f32fd3c8dee27a166f6614c598929699ee66acdcbda5fb24571bf2ae1ca052ae00"
            ),
        )
        self.assertFalse(
            ownership.verify_nonownership(
                proof, script_pubkey, commitment_data, keychain, coin
            )
        )


if __name__ == "__main__":
    unittest.main()
