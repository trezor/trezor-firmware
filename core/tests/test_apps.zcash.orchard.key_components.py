from common import *
from apps.zcash.orchard.keychain import ExtendedSpendingKey

TEST_VECTORS = [
  {'ak': unhexlify("740bbe5d0580b2cad430180d02cc128b9a140d5e07c151721dc16d25d4e20f15"),
  'ask': unhexlify("8eb8c401c287a6c13a2c345ad82172d86be4a8853525db602d14f630f4e61c17"),
  'default_d': unhexlify("8ff3386971cb64b8e77899"),
  'default_pk_d': unhexlify("08dd8ebd7de92a68e586a34db8fea999efd2016fae76750afae7ee941646bcb9"),
  'dk': unhexlify("31d6a685be570f9faf3ca8b052e887840b2c9f8d67224ca82aefb9e2ee5bedaf"),
  'internal_dk': unhexlify("6d61a03f746ba93b932402ac1071fc2759d4f4d684b2c5056d5b177af0fa8aa9"),
  'internal_ivk': unhexlify("906e2d20d00dc0bf7c520687d9df3ce9814d30ee05c215f8764a32c362f9262f"),
  'internal_ovk': unhexlify("d7268bebbee692286252ac60bd4df405ea499d697c454773c5c43cb170930123"),
  'internal_rivk': unhexlify("901a30b99ae1570cb80bb616aeef3bb916c640c4cc620f9b4b4499c74332eb2a"),
  'ivk': unhexlify("85c8b5cd1ac3ec3ad7092132f97f0178b075c81a139fd460bbe0dfcd75514724"),
  'nk': unhexlify("9f2f826738945ad01f47f70db0c367c246c20c61ff5583948c39dea968fefd1b"),
  'note_cmx': unhexlify("4502e339901e397717839167cbb4037e0ecf6813b51c81fe085a7b782f124228"),
  'note_nf': unhexlify("1b32edbbe4d18f28876de262518ad31122701f8c0a52e98047a337876e7eea19"),
  'note_rho': unhexlify("2cb5b406ed8985e18130ab33362697b0e4e4c763ccb8f676495c222f7fba1e31"),
  'note_rseed': unhexlify("defa3d5a57efc2e1e9b01a035587d5fb1a38e01d94903d3c3e0ad3360c1d3710"),
  'note_v': 15643327852135767324,
  'ovk': unhexlify("bcc7065e59910b35993f59505be209b14bf02488750bbc8b1acdcf108c362004"),
  'rivk': unhexlify("021ccf89604f5f7cc6e034b32d338908b819fbe325fee6458b56b4ca71a7e43d"),
  'sk': unhexlify("5d7a8f739a2d9e945b0ce152a8049e294c4d6e66b164939daffa2ef6ee692148")},
 {'ak': unhexlify("6de1349830d66d7b97fe231fc7b02ad64323629cfed1e3aa24ef052f56e4002a"),
  'ask': unhexlify("41d47cc96313b4821dfc129651c3137f44d9cad16b3dc08133c3d2df0d0c5320"),
  'default_d': unhexlify("7807ca650858814d5022a8"),
  'default_pk_d': unhexlify("3d3de4d52c77fd0b630a40dc38212487b2ff6eeef56d8c6a6163e854aff04189"),
  'dk': unhexlify("9d9bd44525e7ae06b03ae6d4aecde6ae0927a7c667d5d9f8176b544695dfec11"),
  'internal_dk': unhexlify("6eea18fd0d50707f90df002cbf309eca3c00d398aede1fdc2abffc88353859af"),
  'internal_ivk': unhexlify("121183cb3b8d06f599bb38b37322851e5fc95ad0c9707ee85fb65e21f1a30d13"),
  'internal_ovk': unhexlify("93252b24b491d9c9c99765c84d4ac7c2bff054cd9cadcd3e01b26f21e2840909"),
  'internal_rivk': unhexlify("8a22a7f5a1e91a92ad394b18eb7338b592470dd42be8ef84c93e7cd845ecfa32"),
  'ivk': unhexlify("563a6db60c74c2db08492cbae3bb083f1aeabffbcf42551d0ac64f2690536711"),
  'nk': unhexlify("a8b73d979b6eaada8924bcbdc63a9ef4e87346f230aba6bbe1e2b43c5bea6b22"),
  'note_cmx': unhexlify("c7ad794c563e32cad47d47dcda7884692848dce29ba4febd93202b7305f90300"),
  'note_nf': unhexlify("2cf067bc21d66320e51b9fbdc8ae031c2c96373db43b7b1a45056c00c65d4320"),
  'note_rho': unhexlify("a51b0052ad8084a8b9da948d320dadd64f5431e61ddf658d24ae67c22c8d1309"),
  'note_rseed': unhexlify("131fc00fe7f235734276d38d47f1e191e00c7a1d48af046827591e9733a97fa6"),
  'note_v': 4481649511318637270,
  'ovk': unhexlify("71cd30640fdb63f8d1305029e940e53fd5ec04a8ccad419578c242fec05b9af7"),
  'rivk': unhexlify("dacb2f2a9ced363171821aaf5d8cd902bc5e3a5a41fb51ae61a9f02dc89d1d12"),
  'sk': unhexlify("acd20b183e31d49f25c9a138f49b1a537edcf04be34a9851a7af9db6990ed83d")},
 {'ak': unhexlify("efa5f1debeead0940a619ce0017bedb426657b2d07406664d895312ea1c3b334"),
  'ask': unhexlify("ce8b65a7236511b2eaf19f72a3d6db7d062b66f516307d198706e5f6928e1615"),
  'default_d': unhexlify("6424f71a3ad197426498f4"),
  'default_pk_d': unhexlify("eccb6a5780204237987232bc098f89acc475c3f74bd69e2f35d44736f48f3c14"),
  'dk': unhexlify("236bc3f3d02f960280eedede108d3685049f239aa67c48558f7c01d3fd469ecd"),
  'internal_dk': unhexlify("3656b545a50a6b26287476641b2b68c63c36f332e74557e916050f0b9111179b"),
  'internal_ivk': unhexlify("a06abd29d5a199e1c21025b0337e941f6d4d84eb7cc35a397f9e753fdaed810d"),
  'internal_ovk': unhexlify("f82eb24906e294ff6571ac7d8368ea8280d422f3477ce72aef5f9b9eca48468f"),
  'internal_rivk': unhexlify("0aa9aaaa2cf18490ddf9a7e521071407ea9bfffe843429bc94a288e8a606a710"),
  'ivk': unhexlify("609ecbc3d8cee3be2b2a2362951f58b74482adfaeee1c40f94030440f558aa30"),
  'nk': unhexlify("04514ea048b94363dea7cb3be8d62582ac52922e0865f662743b05eae8715f17"),
  'note_cmx': unhexlify("03ce20cea194b7559a8a90471d28a3c053c3720ad49f40d27c2dcce335005616"),
  'note_nf': unhexlify("16fa2c3497fc09ad90dd349202a24b69892dc80629b2d1bfebaf41708f0fb10c"),
  'note_rho': unhexlify("32b4f473f468a008e72389fc03880d780cb07fcfaabe3f1a84b27db59a4a153d"),
  'note_rseed': unhexlify("882d2b2103596555ed9494c6ac893c49723833ec8926c1039586a7afcf4a0d9c"),
  'note_v': 14496603531126387959,
  'ovk': unhexlify("dfd30f62aa319c6f53e24c1f48c1de961b9001cb988b80b3eda244fcfeb25f83"),
  'rivk': unhexlify("2a328f994f6e5ad29ca811ed344968ea2cfc3fd231030e37bbd56db42640231c"),
  'sk': unhexlify("b679f3dc601d008285edcbdae69ce8fc1be4aac00ff2711ebd931de518856878")},
 {'ak': unhexlify("b1e0acbc69bf377b85abf0f5a10be72c3b640006ff08505280e4f00fadf76328"),
  'ask': unhexlify("426a7844f305b9d4e07ea52a39001c9b336cfc0d6fa15ef3d11c3d7b74f08c2d"),
  'default_d': unhexlify("db8c305524bc0deaa85d97"),
  'default_pk_d': unhexlify("04ea8c1320ffbbadfe96f0c6ff16b607111b5583bfb6f1ea45275ef2aa2d879b"),
  'dk': unhexlify("803e348573022bf8932f23ee7a325ea283879c652412b8606be3198c4b782c47"),
  'internal_dk': unhexlify("d71a68cfd6c768f43073f698189ac75ee421b4204bb6f3c5d0fc432849aa7161"),
  'internal_ivk': unhexlify("3ba93b0fc3f27ab217635d03f90d0b842d99a12cdc37a81c181ec018e5f44c11"),
  'internal_ovk': unhexlify("e3c7f86c1b2383b3bd41ad1a8f11efa2554a410a98c89207aeb4319b1abd7879"),
  'internal_rivk': unhexlify("9e452ab72c6c8eccf2e439a0cec0a0ac394a1aa121ac6032a7ebc29db4856226"),
  'ivk': unhexlify("f79fe802e4d24307a6aaf85d19f5e0833740bae598dc7c880ac609631de15819"),
  'nk': unhexlify("cf36ad6a066cd213e1d767ab071dc1167885c4168bc2e2175448563ad13f333d"),
  'note_cmx': unhexlify("a9b11baf3034b65c6424841bfe023f8eda1313c30aa27de92e21a108316e8219"),
  'note_nf': unhexlify("72d6308960351f7b26fa64603fe4dfd867bd5eb367ba2b7ca491c923c0ead222"),
  'note_rho': unhexlify("4b192232ecb9f0c02411e52596bc5e90457e745939ffedbd12863ce71a02af11"),
  'note_rseed': unhexlify("7d417adb3d15cc54dcb1fce467500c6b8fb86b12b56da9c382857deecc40a98d"),
  'note_v': 6792346249443327211,
  'ovk': unhexlify("f96366bc6eabd232549ebb43b4ed6fd81d330373c5b566904e9af11a6bab8d77"),
  'rivk': unhexlify("c41bbad35105a80314b79624b675241220b331f12592617bdb705bfcce72ae38"),
  'sk': unhexlify("731e985d99589c8bb838e8aaf745533ed9e8ae3a1cd074a51a20da8aba18d1db")},
 {'ak': unhexlify("0d262de3609433fe5b7c862bc48ef56d832009f7242e1f7c770a12241dfa2807"),
  'ask': unhexlify("118073285164e6557358fbc41a8135cb062f8676cb61f9aa52d19a09fac55802"),
  'default_d': unhexlify("aae36e094de07bc16f898e"),
  'default_pk_d': unhexlify("b6533dcbfff0f6c1ceefa84799bda3de7334326ccd65f7ce92ff3d9e6e1f140b"),
  'dk': unhexlify("ee19f8ddd9da0634245143c4b43afc7d78c549c82054a9d84007b56217dbfdd6"),
  'internal_dk': unhexlify("02b52c6ed9ad49fb38e4447c69b570ebd055e4c7fd91c020ff43461d14e02f29"),
  'internal_ivk': unhexlify("bad4837ba78822b8b165b0a16e1104c705c3c0e382d3f13c195c0ef311bb8004"),
  'internal_ovk': unhexlify("b9113a952dcc1e15c34d136603a2ef254a38755a557fa9f88c143bd3076441b0"),
  'internal_rivk': unhexlify("254406723b0667af27e51cb3ce8fa1388164d94376c850bddb39e9bea5fa9605"),
  'ivk': unhexlify("76f49cf8a3192185616a9a0da0c76ec2c2756159bce186a1862b6e6e59442d11"),
  'nk': unhexlify("51baf333cff1f2d0c7e3cff4d301299dc1efe98300314a541938029b45cc1521"),
  'note_cmx': unhexlify("0ffbca1d5921fa0a8c5116ae137e37f2c118d52125628d8a3f412ce0e6530e04"),
  'note_nf': unhexlify("e62b8ed83540146cd23cac74eed7d773d80224a5aa30d68e35572ee883d1b704"),
  'note_rho': unhexlify("2670dc82d39026c6cb4cd4b0f7f5aa2a4f5a5341ec5dd715406f2fdd2afa733f"),
  'note_rseed': unhexlify("5f641c8c21862a1bafce2609d9eecfa158cfb5cd79f88008e315dc7d8388e76c"),
  'note_v': 4079549063511228677,
  'ovk': unhexlify("eb72b6c31e837fd837aacb61fabace75a19dd9dd5b4b3a3ee723c14da77b4be8"),
  'rivk': unhexlify("228feb79219873c7a7606e52973c85f460465a6059083919ed73eb805c118301"),
  'sk': unhexlify("5f2935395ee4762dd21afdbb5d47fa9a6dd984d567db2857b927b7fae2db5871")}
]



@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestZcashOrchardKeyComponents(unittest.TestCase):
    def test_zcash_orchard_key_components(self):
        for tv in TEST_VECTORS:
            sk = ExtendedSpendingKey(sk=tv["sk"], c=b"")
            fvk = sk.full_viewing_key()
            self.assertEqual(fvk.raw()[0:32], tv["ak"])
            self.assertEqual(fvk.raw()[32:64], tv["nk"])
            self.assertEqual(fvk.raw()[64:96], tv["rivk"])
            ivk = fvk.incoming_viewing_key()
            self.assertEqual(ivk[0:32], tv["dk"])
            self.assertEqual(ivk[32:64], tv["ivk"])
            ovk = fvk.outgoing_viewing_key()
            self.assertEqual(ovk, tv["ovk"])
            address = fvk.address(0)
            self.assertEqual(address[0:11], tv["default_d"])
            self.assertEqual(address[11:43], tv["default_pk_d"])

if __name__ == '__main__':
    unittest.main()
