from common import unhexlify, unittest
from trezor.crypto import bip39
from trezor.enums import InputScriptType
from trezor.messages import MultisigRedeemScriptType
from trezor.messages import HDNodeType

from apps.common import coins
from apps.common.keychain import Keychain
from apps.common.paths import HARDENED, AlwaysMatchingSchema
from apps.bitcoin import ownership, scripts
from apps.bitcoin.addresses import address_p2wpkh, address_p2wpkh_in_p2sh, address_multisig_p2wsh, address_multisig_p2wsh_in_p2sh, address_multisig_p2sh
from apps.bitcoin.multisig import multisig_get_pubkeys


class TestOwnershipProof(unittest.TestCase):

    def test_p2wpkh_gen_proof(self):
        coin = coins.by_name('Bitcoin')
        seed = bip39.seed(' '.join(['all'] * 12), '')
        keychain = Keychain(seed, coin.curve_name, [AlwaysMatchingSchema], slip21_namespaces=[[b"SLIP-0019"]])
        commitment_data = b""

        node = keychain.derive([84 | HARDENED, 0 | HARDENED, 0 | HARDENED, 1, 0])
        address = address_p2wpkh(node.public_key(), coin)
        script_pubkey = scripts.output_derive_script(address, coin)
        ownership_id = ownership.get_identifier(script_pubkey, keychain)
        self.assertEqual(ownership_id, unhexlify("a122407efc198211c81af4450f40b235d54775efd934d16b9e31c6ce9bad5707"))

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
        self.assertEqual(signature, unhexlify("3045022100e5eaf2cb0a473b4545115c7b85323809e75cb106175ace38129fd62323d73df30220363dbc7acb7afcda022b1f8d97acb8f47c42043cfe0595583aa26e30bc8b3bb5"))
        self.assertEqual(proof, unhexlify("534c00190001a122407efc198211c81af4450f40b235d54775efd934d16b9e31c6ce9bad57070002483045022100e5eaf2cb0a473b4545115c7b85323809e75cb106175ace38129fd62323d73df30220363dbc7acb7afcda022b1f8d97acb8f47c42043cfe0595583aa26e30bc8b3bb50121032ef68318c8f6aaa0adec0199c69901f0db7d3485eb38d9ad235221dc3d61154b"))
        self.assertFalse(ownership.verify_nonownership(proof, script_pubkey, commitment_data, keychain, coin))

    def test_p2wpkh_in_p2sh_gen_proof(self):
        coin = coins.by_name('Bitcoin')
        seed = bip39.seed(' '.join(['all'] * 12), '')
        keychain = Keychain(seed, coin.curve_name, [AlwaysMatchingSchema], slip21_namespaces=[[b"SLIP-0019"]])
        commitment_data = b""

        node = keychain.derive([49 | HARDENED, 0 | HARDENED, 0 | HARDENED, 1, 0])
        address = address_p2wpkh_in_p2sh(node.public_key(), coin)
        script_pubkey = scripts.output_derive_script(address, coin)
        ownership_id = ownership.get_identifier(script_pubkey, keychain)

        self.assertEqual(ownership_id, unhexlify("92caf0b8daf78f1d388dbbceaec34bd2dabc31b217e32343663667f6694a3f46"))

        proof, signature = ownership.generate_proof(
            node=node,
            script_type=InputScriptType.SPENDP2SHWITNESS,
            multisig=None,
            coin=coin,
            user_confirmed=False,
            ownership_ids=[ownership_id],
            script_pubkey=script_pubkey,
            commitment_data=commitment_data,
        )
        self.assertEqual(signature, unhexlify("3045022100a37330dca699725db613dd1b30059843d1248340642162a0adef114509c9849402201126c9044b998065d40b44fd2399b52c409794bbc3bfdd358cd5fb450c94316d"))
        self.assertEqual(proof, unhexlify("534c0019000192caf0b8daf78f1d388dbbceaec34bd2dabc31b217e32343663667f6694a3f4617160014e0cffbee1925a411844f44c3b8d81365ab51d03602483045022100a37330dca699725db613dd1b30059843d1248340642162a0adef114509c9849402201126c9044b998065d40b44fd2399b52c409794bbc3bfdd358cd5fb450c94316d012103a961687895a78da9aef98eed8e1f2a3e91cfb69d2f3cf11cbd0bb1773d951928"))
        self.assertFalse(ownership.verify_nonownership(proof, script_pubkey, commitment_data, keychain, coin))

    def test_p2pkh_gen_proof(self):
        coin = coins.by_name('Bitcoin')
        seed = bip39.seed(' '.join(['all'] * 12), 'TREZOR')
        keychain = Keychain(seed, coin.curve_name, [AlwaysMatchingSchema], slip21_namespaces=[[b"SLIP-0019"]])
        commitment_data = b""

        node = keychain.derive([44 | HARDENED, 0 | HARDENED, 0 | HARDENED, 1, 0])
        address = node.address(coin.address_type)
        script_pubkey = scripts.output_derive_script(address, coin)
        ownership_id = ownership.get_identifier(script_pubkey, keychain)
        self.assertEqual(ownership_id, unhexlify("ccc49ac5fede0efc80725fbda8b763d4e62a221c51cc5425076cffa7722c0bda"))

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
        self.assertEqual(signature, unhexlify("304402206682f40a12f3609a308acb872888470a07760f2f4790ee4ff62665a39c02a5fc022026f3f38a7c2b2668c2eff9cc1e712c7f254926a482bae411ad18947eba9fd21c"))
        self.assertEqual(proof, unhexlify("534c00190001ccc49ac5fede0efc80725fbda8b763d4e62a221c51cc5425076cffa7722c0bda6a47304402206682f40a12f3609a308acb872888470a07760f2f4790ee4ff62665a39c02a5fc022026f3f38a7c2b2668c2eff9cc1e712c7f254926a482bae411ad18947eba9fd21c012102f63159e21fbcb54221ec993def967ad2183a9c243c8bff6e7d60f4d5ed3b386500"))
        self.assertFalse(ownership.verify_nonownership(proof, script_pubkey, commitment_data, keychain, coin))

    def test_p2wpkh_verify_proof(self):
        coin = coins.by_name('Bitcoin')
        seed = bip39.seed(' '.join(['all'] * 12), 'TREZOR')
        keychain = Keychain(seed, coin.curve_name, [AlwaysMatchingSchema], slip21_namespaces=[[b"SLIP-0019"]])
        commitment_data = b""

        # Proof for "all all ... all" seed without passphrase.
        script_pubkey = unhexlify("0014b2f771c370ccf219cd3059cda92bdf7f00cf2103")
        proof = unhexlify("534c00190001a122407efc198211c81af4450f40b235d54775efd934d16b9e31c6ce9bad57070002483045022100e5eaf2cb0a473b4545115c7b85323809e75cb106175ace38129fd62323d73df30220363dbc7acb7afcda022b1f8d97acb8f47c42043cfe0595583aa26e30bc8b3bb50121032ef68318c8f6aaa0adec0199c69901f0db7d3485eb38d9ad235221dc3d61154b")
        self.assertTrue(ownership.verify_nonownership(proof, script_pubkey, commitment_data, keychain, coin))

    def test_p2wsh_gen_proof(self):
        coin = coins.by_name('Bitcoin')
        seed = bip39.seed(' '.join(['all'] * 12), '')
        keychain = Keychain(seed, coin.curve_name, [AlwaysMatchingSchema], slip21_namespaces=[[b"SLIP-0019"]])
        commitment_data = b"TREZOR"

        nodes = []
        for index in range(1, 4):
            node = keychain.derive([84 | HARDENED, 0 | HARDENED, index | HARDENED])
            nodes.append(HDNodeType(
                depth=node.depth(),
                child_num=node.child_num(),
                fingerprint=node.fingerprint(),
                chain_code=node.chain_code(),
                public_key=node.public_key(),
            ))

        multisig = MultisigRedeemScriptType(
            nodes=nodes,
            address_n=[0, 1],
            signatures=[b"", b"", b""],
            m=2,
        )

        pubkeys = multisig_get_pubkeys(multisig)
        address = address_multisig_p2wsh(pubkeys, multisig.m, coin.bech32_prefix)
        script_pubkey = scripts.output_derive_script(address, coin)
        ownership_id = ownership.get_identifier(script_pubkey, keychain)
        ownership_ids = [b'\x00' * 32, ownership_id, b'\x01' * 32]
        self.assertEqual(ownership_id, unhexlify("9c27411da79a23811856f897da890452ab9e17086038c4a3e70e9efa875cb3ef"))

        # Sign with the first key.
        _, signature = ownership.generate_proof(
            node=keychain.derive([84 | HARDENED, 0 | HARDENED, 1 | HARDENED, 0, 1]),
            script_type=InputScriptType.SPENDWITNESS,
            multisig=multisig,
            coin=coin,
            user_confirmed=False,
            ownership_ids=ownership_ids,
            script_pubkey=script_pubkey,
            commitment_data=commitment_data,
        )
        self.assertEqual(signature, unhexlify("304402207568cf003ff548c52ce8e3a46a1c1e681462ca8f1651b0c82f688d41280753b4022024f977fa96fd23cf71e35d4d3c5087c375fcf1b6eed6d11ab00d552817d39ba4"))
        multisig.signatures[0] = signature

        # Sign with the third key.
        proof, signature = ownership.generate_proof(
            node=keychain.derive([84 | HARDENED, 0 | HARDENED, 3 | HARDENED, 0, 1]),
            script_type=InputScriptType.SPENDWITNESS,
            multisig=multisig,
            coin=coin,
            user_confirmed=False,
            ownership_ids=ownership_ids,
            script_pubkey=script_pubkey,
            commitment_data=commitment_data,
        )
        self.assertEqual(signature, unhexlify("304402203c4fedba34aebd213aba5b5af1ae26240a10a05cfc1c5b75c629275aa21560bb02203b90b4079c20f792f4ec533c72af31435b1e5f648ca8302730c309690133a710"))
        self.assertEqual(proof, unhexlify("534c0019000300000000000000000000000000000000000000000000000000000000000000009c27411da79a23811856f897da890452ab9e17086038c4a3e70e9efa875cb3ef010101010101010101010101010101010101010101010101010101010101010100040047304402207568cf003ff548c52ce8e3a46a1c1e681462ca8f1651b0c82f688d41280753b4022024f977fa96fd23cf71e35d4d3c5087c375fcf1b6eed6d11ab00d552817d39ba40147304402203c4fedba34aebd213aba5b5af1ae26240a10a05cfc1c5b75c629275aa21560bb02203b90b4079c20f792f4ec533c72af31435b1e5f648ca8302730c309690133a71001695221022aff3e39acd2d510c661e097a9657962ad6bf75a977c2c905152d2eb2cd58c7b210241ec073f3bb3f701a87b78fbc5f7b4daec140b87da38303173eddd0860ac55e321030205585a3eb01cbebbbb7b9138f7796117cca8e30eba5cd143ff4e3e617d221553ae"))
        self.assertFalse(ownership.verify_nonownership(proof, script_pubkey, commitment_data, keychain, coin))

    def test_p2wsh_in_p2sh_gen_proof(self):
        coin = coins.by_name('Bitcoin')
        seed = bip39.seed(' '.join(['all'] * 12), '')
        keychain = Keychain(seed, coin.curve_name, [AlwaysMatchingSchema], slip21_namespaces=[[b"SLIP-0019"]])
        commitment_data = b""

        nodes = []
        for index in range(1, 6):
            node = keychain.derive([49 | HARDENED, 0 | HARDENED, index | HARDENED])
            nodes.append(HDNodeType(
                depth=node.depth(),
                child_num=node.child_num(),
                fingerprint=node.fingerprint(),
                chain_code=node.chain_code(),
                public_key=node.public_key(),
            ))

        multisig = MultisigRedeemScriptType(
            nodes=nodes,
            address_n=[0, 1],
            signatures=[b"", b"", b"", b"", b""],
            m=3,
        )

        pubkeys = multisig_get_pubkeys(multisig)
        address = address_multisig_p2wsh_in_p2sh(pubkeys, multisig.m, coin)
        script_pubkey = scripts.output_derive_script(address, coin)
        ownership_id = ownership.get_identifier(script_pubkey, keychain)
        ownership_ids = [b'\x00' * 32, b'\x01' * 32, b'\x02' * 32, ownership_id]
        self.assertEqual(ownership_id, unhexlify("66f99db388dfa7ae137f7bdb5f0004b4d6968014921cfaff1fec042e3bb83ae0"))

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
        self.assertEqual(signature, unhexlify("3045022100deccf7735da7a8236efd59d5759c4cbe9fa32d567bcd57d8d718cc689bc6972402202ce7fe49b0f0caea049be69c91bca9c9397d693d79388f1cfb65d51deadfb3d8"))
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
        self.assertEqual(signature, unhexlify("304402206e8219a013e94de493c4ff50b44d31f443d37a2c4dbcba6af1ac825b28cc631202200741a72035acd122a6f4fdb994c15ab19aa20cecdfdb19aa37490e7bb011a617"))
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
        self.assertEqual(signature, unhexlify("304402202f6066733abf4671b74f1f883dd3c8d4810aa71b7b7b5f6196b1ceff83d5370e022053aad3bde0fe6ce6c4553dd72ddf07e7f06447a7bd35edf6f0b4e9690ee7ce79"))
        self.assertEqual(proof, unhexlify("534c0019000400000000000000000000000000000000000000000000000000000000000000000101010101010101010101010101010101010101010101010101010101010101020202020202020202020202020202020202020202020202020202020202020266f99db388dfa7ae137f7bdb5f0004b4d6968014921cfaff1fec042e3bb83ae0232200208c256ed80a97a421656daa1468f6d4d43f475cb52ed79532d8bcb315518298120500483045022100deccf7735da7a8236efd59d5759c4cbe9fa32d567bcd57d8d718cc689bc6972402202ce7fe49b0f0caea049be69c91bca9c9397d693d79388f1cfb65d51deadfb3d80147304402206e8219a013e94de493c4ff50b44d31f443d37a2c4dbcba6af1ac825b28cc631202200741a72035acd122a6f4fdb994c15ab19aa20cecdfdb19aa37490e7bb011a6170147304402202f6066733abf4671b74f1f883dd3c8d4810aa71b7b7b5f6196b1ceff83d5370e022053aad3bde0fe6ce6c4553dd72ddf07e7f06447a7bd35edf6f0b4e9690ee7ce7901ad5321032922ce9b0b71ae2d2d8a7f239610ae8226e0fb8c0f445ec4c88cf9aa4787f44b21028373a1cdb9a1afbc67e57f75eeea1f53e7210ae8ec4b3441a5f2bc4a250b663c21028ab4c06e3ad19053b370eff097697d4cb6d3738712ebcdcdc27c58a5639ac3aa2103e3247fab300aeba459257e4605245f85378ecbfe092ca3bc55ec1259baa456f521023b0d8d97398d97c4dba10f788344abd4bd1058ad3959724d32079ad04bdbde8a55ae"))
        self.assertFalse(ownership.verify_nonownership(proof, script_pubkey, commitment_data, keychain, coin))

    def test_p2sh_gen_proof(self):
        coin = coins.by_name('Bitcoin')
        seed = bip39.seed(' '.join(['all'] * 12), '')
        keychain = Keychain(seed, coin.curve_name, [AlwaysMatchingSchema], slip21_namespaces=[[b"SLIP-0019"]])
        commitment_data = b"TREZOR"

        nodes = []
        for index in range(1, 3):
            node = keychain.derive([48 | HARDENED, 0 | HARDENED, index | HARDENED])
            nodes.append(HDNodeType(
                depth=node.depth(),
                child_num=node.child_num(),
                fingerprint=node.fingerprint(),
                chain_code=node.chain_code(),
                public_key=node.public_key(),
            ))

        multisig = MultisigRedeemScriptType(
            nodes=nodes,
            address_n=[0, 0],
            signatures=[b"", b""],
            m=2,
        )

        pubkeys = multisig_get_pubkeys(multisig)
        address = address_multisig_p2sh(pubkeys, multisig.m, coin)
        script_pubkey = scripts.output_derive_script(address, coin)
        ownership_id = ownership.get_identifier(script_pubkey, keychain)
        ownership_ids = [b'\x00' * 32, ownership_id]
        self.assertEqual(ownership_id, unhexlify("ce4ee8298ad105c3495a1d2b620343133521ab34de2450deeb32eec39475fef4"))

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
        self.assertEqual(signature, unhexlify("3045022100bc63486f167b911dc8ef2414c4bca6dcfac999797b67159957802a9c49c2179402201cec0d53fee78fcfde496e30be35bd855d93a5be89604c55dcfdbdc515fbb41a"))
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
        self.assertEqual(signature, unhexlify("3045022100d9d5966eb7858cc1a600a9c05be252c1df11d662f319a107d04e219a27c1386c02200674523e50e89164d6d5683dfbe9a50594b08011e11c18813b56cf855755afde"))
        self.assertEqual(proof, unhexlify("534c001900020000000000000000000000000000000000000000000000000000000000000000ce4ee8298ad105c3495a1d2b620343133521ab34de2450deeb32eec39475fef4db00483045022100bc63486f167b911dc8ef2414c4bca6dcfac999797b67159957802a9c49c2179402201cec0d53fee78fcfde496e30be35bd855d93a5be89604c55dcfdbdc515fbb41a01483045022100d9d5966eb7858cc1a600a9c05be252c1df11d662f319a107d04e219a27c1386c02200674523e50e89164d6d5683dfbe9a50594b08011e11c18813b56cf855755afde014752210203ed6187880ae932660086e55d4561a57952dd200aa3ed2aa66b73e5723a0ce7210360e7f32fd3c8dee27a166f6614c598929699ee66acdcbda5fb24571bf2ae1ca052ae00"))
        self.assertFalse(ownership.verify_nonownership(proof, script_pubkey, commitment_data, keychain, coin))


if __name__ == '__main__':
    unittest.main()
