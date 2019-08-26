from common import *
from trezor.crypto import bip32

if not utils.BITCOIN_ONLY:
    from apps.nem import CURVE
    from apps.nem.helpers import NEM_NETWORK_MAINNET


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestNemHDNode(unittest.TestCase):

    def test_addresses(self):
        # test vectors from https://raw.githubusercontent.com/NemProject/nem-test-vectors/master/1.test-keys.dat
        # private key, public key, address
        test_cases = [
            ('575dbb3062267eff57c970a336ebbc8fbcfe12c5bd3ed7bc11eb0481d7704ced',
             'c5f54ba980fcbb657dbaaa42700539b207873e134d2375efeab5f1ab52f87844',
             'NDD2CT6LQLIYQ56KIXI3ENTM6EK3D44P5JFXJ4R4'),
            ('5b0e3fa5d3b49a79022d7c1e121ba1cbbf4db5821f47ab8c708ef88defc29bfe',
             '96eb2a145211b1b7ab5f0d4b14f8abc8d695c7aee31a3cfc2d4881313c68eea3',
             'NABHFGE5ORQD3LE4O6B7JUFN47ECOFBFASC3SCAC'),
            ('738ba9bb9110aea8f15caa353aca5653b4bdfca1db9f34d0efed2ce1325aeeda',
             '2d8425e4ca2d8926346c7a7ca39826acd881a8639e81bd68820409c6e30d142a',
             'NAVOZX4HDVOAR4W6K4WJHWPD3MOFU27DFHC7KZOZ'),
            ('e8bf9bc0f35c12d8c8bf94dd3a8b5b4034f1063948e3cc5304e55e31aa4b95a6',
             '4feed486777ed38e44c489c7c4e93a830e4c4a907fa19a174e630ef0f6ed0409',
             'NBZ6JK5YOCU6UPSSZ5D3G27UHAPHTY5HDQMGE6TT'),
            ('c325ea529674396db5675939e7988883d59a5fc17a28ca977e3ba85370232a83',
             '83ee32e4e145024d29bca54f71fa335a98b3e68283f1a3099c4d4ae113b53e54',
             'NCQW2P5DNZ5BBXQVGS367DQ4AHC3RXOEVGRCLY6V'),
            ('a811cb7a80a7227ae61f6da536534ee3c2744e3c7e4b85f3e0df3c6a9c5613df',
             '6d34c04f3a0e42f0c3c6f50e475ae018cfa2f56df58c481ad4300424a6270cbb',
             'NA5IG3XFXZHIPJ5QLKX2FBJPEZYPMBPPK2ZRC3EH'),
            ('9c66de1ec77f4dfaaebdf9c8bc599ca7e8e6f0bc71390ffee2c9dd3f3619242a',
             'a8fefd72a3b833dc7c7ed7d57ed86906dac22f88f1f4331873eb2da3152a3e77',
             'NAABHVFJDBM74XMJJ52R7QN2MTTG2ZUXPQS62QZ7'),
            ('c56bc16ecf727878c15e24f4ae68569600ac7b251218a44ef50ce54175776edc',
             'c92f761e6d83d20068fd46fe4bd5b97f4c6ba05d23180679b718d1f3e4fb066e',
             'NCLK3OLMHR3F2E3KSBUIZ4K5PNWUDN37MLSJBJZP'),
            ('9dd73599283882fa1561ddfc9be5830b5dd453c90465d3fe5eeb646a3606374e',
             'eaf16a4833e59370a04ccd5c63395058de34877b48c17174c71db5ed37b537ed',
             'ND3AHW4VTI5R5QE5V44KIGPRU5FBJ5AFUCJXOY5H'),
            ('d9639dc6f49dad02a42fd8c217f1b1b4f8ce31ccd770388b645e639c72ff24fa',
             '0f74a2f537cd9c986df018994dde75bdeee05e35eb9fe27adf506ca8475064f7',
             'NCTZ4YAP43ONK3UYTASQVNDMBO24ZHJE65F3QPYE'),
            ('efc1992cd50b70ca55ac12c07aa5d026a8b78ffe28a7dbffc9228b26e02c38c1',
             '2ebff201255f6cf948c78f528658b99a7c13ac791942fa22d59af610558111f5',
             'NDQ2TMCMXBSFPZQPE2YKH6XLC24HD6LUMN6Z4GIC'),
            ('143a815e92e43f3ed1a921ee48cd143931b88b7c3d8e1e981f743c2a5be3c5ba',
             '419ed11d48730e4ae2c93f0ea4df853b8d578713a36dab227517cf965861af4e',
             'NA32IDDW2C53BDSBJNFL3Z6UU3J5CJZJMCZDXCF4'),
            ('bc1a082f5ac6fdd3a83ade211e5986ac0551bad6c7da96727ec744e5df963e2a',
             'a160e6f9112233a7ce94202ed7a4443e1dac444b5095f9fecbb965fba3f92cac',
             'NADUCEQLC3FTGB25GTA5HOUTB53CBVQNVOIP7NTJ'),
            ('4e47b4c6f4c7886e49ec109c61f4af5cfbb1637283218941d55a7f9fe1053f72',
             'fbb91b16df828e21a9802980a44fc757c588bc1382a4cea429d6fa2ae0333f56',
             'NBAF3BFLLPWH33MYE6VUPP5T6DQBZBKIDEQKZQOE'),
            ('efc4389da48ce49f85365cfa578c746530e9eac42db1b64ec346119b1becd347',
             '2232f24dda0f2ded3ecd831210d4e8521a096b50cadd5a34f3f7083374e1ec12',
             'NBOGTK2I2ATOGGD7ZFJHROG5MWL7XCKAUKSWIVSA'),
            ('bdba57c78ca7da16a3360efd13f06276284db8c40351de7fcd38ba0c35ac754d',
             'c334c6c0dad5aaa2a0d0fb4c6032cb6a0edd96bf61125b5ea9062d5a00ee0eee',
             'NCLERTEFYXKLK7RA4MVACEFMXMK3P7QMWTM7FBW2'),
            ('20694c1ec3c4a311bcdb29ed2edc428f6d4f9a4c429ad6a5bf3222084e35695f',
             '518c4de412efa93de06a55947d11f697639443916ec8fcf04ebc3e6d17d0bd93',
             'NB5V4BPIJHXVONO7UGMJDPFARMFA73BOBNOOYCOV'),
            ('e0d4f3760ac107b33c22c2cac24ab2f520b282684f5f66a4212ff95d926323ce',
             'b3d16f4ead9de67c290144da535a0ed2504b03c05e5f1ceb8c7863762f786857',
             'NC4PBAO5TPCAVQKBVOC4F6DMZP3CFSQBU46PSKBD'),
            ('efa9afc617412093c9c7a7c211a5332dd556f941e1a88c494ec860608610eea2',
             '7e7716e4cebceb731d6f1fd28676f34888e9a0000fcfa1471db1c616c2ddf559',
             'NCFW2LPXIWLBWAQN2QVIWEOD7IVDO3HQBD2OU56K'),
            ('d98499b3db61944684ce06a91735af4e14105338473fcf6ebe2b0bcada3dfd21',
             '114171230ad6f8522a000cdc73fbc5c733b30bb71f2b146ccbdf34499f79a810',
             'NCUKWDY3J3THKQHAKOK5ALF6ANJQABZHCH7VN6DP')
        ]

        for test in test_cases:
            private_key = bytearray(reversed(unhexlify(test[0])))

            node = bip32.HDNode(
                depth=0,
                fingerprint=0,
                child_num=0,
                chain_code=bytearray(32),
                private_key=private_key,
                curve_name=CURVE
            )

            self.assertEqual(node.nem_address(NEM_NETWORK_MAINNET), test[2])
            # public key is prepended with 1, removing
            self.assertEqual(node.public_key()[1:], unhexlify(test[1]))

    def test_encryption(self):
        # test vectors from https://raw.githubusercontent.com/NemProject/nem-test-vectors/master/4.test-cipher.dat
        # private key, transfer public key, salt, iv, plain text, cipher text
        test_cases = [
            {'private': '3140f94c79f249787d1ec75a97a885980eb8f0a7d9b7aa03e7200296e422b2b6',
             'public': '57a70eb553a7b3fd621f0dba6abf51312ea2e2a2a1e19d0305516730f4bcbd21',
             'salt': '83616c67f076d356fd1288a6e0fd7a60488ba312a3adf0088b1b33c7655c3e6a',
             'iv': 'a73ff5c32f8fd055b09775817a6a3f95',
             'input': '86ddb9e713a8ebf67a51830eff03b837e147c20d75e67b2a54aa29e98c',
             'output': '70815da779b1b954d7a7f00c16940e9917a0412a06a444b539bf147603eef87f'},
            {'private': '3140f94c79f249787d1ec75a97a885980eb8f0a7d9b7aa03e7200296e422b2b6',
             'public': '57a70eb553a7b3fd621f0dba6abf51312ea2e2a2a1e19d0305516730f4bcbd21',
             'salt': '703ce0b1d276b10eef35672df03234385a903460db18ba9d4e05b3ad31abb284',
             'iv': '91246c2d5493867c4fa3e78f85963677',
             'input': '86ddb9e713a8ebf67a51830eff03b837e147c20d75e67b2a54aa29e98c',
             'output': '564b2f40d42c0efc1bd6f057115a5abd1564cae36d7ccacf5d825d38401aa894'},
            {'private': '3140f94c79f249787d1ec75a97a885980eb8f0a7d9b7aa03e7200296e422b2b6',
             'public': '57a70eb553a7b3fd621f0dba6abf51312ea2e2a2a1e19d0305516730f4bcbd21',
             'salt': 'b22e8e8e7373ac31ca7f0f6eb8b93130aba5266772a658593f3a11792e7e8d92',
             'iv': '9f8e33d82374dad6aac0e3dbe7aea704',
             'input': '86ddb9e713a8ebf67a51830eff03b837e147c20d75e67b2a54aa29e98c',
             'output': '7cab88d00a3fc656002eccbbd966e1d5d14a3090d92cf502cdbf843515625dcf'},
            {'private': '3140f94c79f249787d1ec75a97a885980eb8f0a7d9b7aa03e7200296e422b2b6',
             'public': '57a70eb553a7b3fd621f0dba6abf51312ea2e2a2a1e19d0305516730f4bcbd21',
             'salt': 'af646c54cd153dffe453b60efbceeb85c1e95a414ea0036c4da94afb3366f5d9',
             'iv': '6acdf8e01acc8074ddc807281b6af888',
             'input': '86ddb9e713a8ebf67a51830eff03b837e147c20d75e67b2a54aa29e98c',
             'output': 'aa70543a485b63a4dd141bb7fd78019092ac6fad731e914280a287c7467bae1a'},
            {'private': '3140f94c79f249787d1ec75a97a885980eb8f0a7d9b7aa03e7200296e422b2b6',
             'public': '57a70eb553a7b3fd621f0dba6abf51312ea2e2a2a1e19d0305516730f4bcbd21',
             'salt': 'd9c0d386636c8a024935c024589f9cd39e820a16485b14951e690a967830e269',
             'iv': 'f2e9f18aeb374965f54d2f4e31189a8f',
             'input': '86ddb9e713a8ebf67a51830eff03b837e147c20d75e67b2a54aa29e98c',
             'output': '33d97c216ea6498dfddabf94c2e2403d73efc495e9b284d9d90aaff840217d25'},
            {'private': 'd5c0762ecea2cd6b5c56751b58debcb32713aab348f4a59c493e38beb3244f3a',
             'public': '66a35941d615b5644d19c2a602c363ada8b1a8a0dac3682623852dcab4afac04',
             'salt': '06c227baac1ae3b0b1dc583f4850f13f9ba5d53be4a98fa5c3ea16217847530d',
             'iv': '3735123e78c44895df6ea33fa57e9a72',
             'input': '86ddb9e713a8ebf67a51830eff03b837e147c20d75e67b2a54aa29e98c',
             'output': 'd5b5d66ba8cee0eb7ecf95b143fa77a46d6de13749e12eff40f5a7e649167ccb'},
            {'private': 'd5c0762ecea2cd6b5c56751b58debcb32713aab348f4a59c493e38beb3244f3a',
             'public': '66a35941d615b5644d19c2a602c363ada8b1a8a0dac3682623852dcab4afac04',
             'salt': '92f55ba5bc6fc2f23e3eedc299357c71518e36ba2447a4da7a9dfe9dfeb107b5',
             'iv': '1cbc4982e53e370052af97ab088fa942',
             'input': '86ddb9e713a8ebf67a51830eff03b837e147c20d75e67b2a54aa29e98c',
             'output': 'd48ef1ef526d805656cfc932aff259eadb17aa3391dde1877a722cba31d935b2'},
            {'private': 'd5c0762ecea2cd6b5c56751b58debcb32713aab348f4a59c493e38beb3244f3a',
             'public': '66a35941d615b5644d19c2a602c363ada8b1a8a0dac3682623852dcab4afac04',
             'salt': '10f15a39ba49866292a43b7781bc71ca8bbd4889f1616461caf056bcb91b0158',
             'iv': 'c40d531d92bfee969dce91417346c892',
             'input': '49de3cd5890e0cd0559f143807ff688ff62789b7236a332b7d7255ec0b4e73e6b3a4',
             'output': 'e6d75afdb542785669b42198577c5b358d95397d71ec6f5835dca46d332cc08dbf73ea790b7bcb169a65719c0d55054c'},
            {'private': 'd5c0762ecea2cd6b5c56751b58debcb32713aab348f4a59c493e38beb3244f3a',
             'public': '66a35941d615b5644d19c2a602c363ada8b1a8a0dac3682623852dcab4afac04',
             'salt': '9c01ed42b219b3bbe1a43ae9d7af5c1dd09363baacfdba8f4d03d1046915e26e',
             'iv': '059a35d5f83249e632790015ed6518b9',
             'input': '49de3cd5890e0cd0559f143807ff688ff62789b7236a332b7d7255ec0b4e73e6b3a4',
             'output': '5ef11aadff2eccee8b712dab968fa842eb770818ec0e6663ed242ea8b6bbc1c66d6285ee5b5f03d55dfee382fb4fa25d'},
            {'private': 'd5c0762ecea2cd6b5c56751b58debcb32713aab348f4a59c493e38beb3244f3a',
             'public': '66a35941d615b5644d19c2a602c363ada8b1a8a0dac3682623852dcab4afac04',
             'salt': 'bc1067e2a7415ea45ff1ca9894338c591ff15f2e57ae2789ae31b9d5bea0f11e',
             'iv': '8c73f0d6613898daeefa3cf8b0686d37',
             'input': '49de3cd5890e0cd0559f143807ff688ff62789b7236a332b7d7255ec0b4e73e6b3a4',
             'output': '6d220213b1878cd40a458f2a1e6e3b48040455fdf504dcd857f4f2ca1ad642e3a44fc401d04e339d302f66a9fad3d919'},
            {'private': '9ef87ba8aa2e664bdfdb978b98bc30fb61773d9298e7b8c72911683eeff41921',
             'public': '441e76d7e53be0a967181076a842f69c20fd8c0e3f0ce3aa421b490b059fe094',
             'salt': 'cf4a21cb790552165827b678ca9695fcaf77566d382325112ff79483455de667',
             'iv': 'bfbf5482e06f55b88bdd9e053b7eee6e',
             'input': '49de3cd5890e0cd0559f143807ff688ff62789b7236a332b7d7255ec0b4e73e6b3a4',
             'output': '1198a78c29c215d5c450f7b8513ead253160bc9fde80d9cc8e6bee2efe9713cf5a09d6293c41033271c9e8c22036a28b'},
            {'private': '9ef87ba8aa2e664bdfdb978b98bc30fb61773d9298e7b8c72911683eeff41921',
             'public': '441e76d7e53be0a967181076a842f69c20fd8c0e3f0ce3aa421b490b059fe094',
             'salt': 'eba5eae8aef79114082c3e70baef95bb02edf13b3897e8be7a70272962ef8838',
             'iv': 'af9a56da3da18e2fbd2948a16332532b',
             'input': '49de3cd5890e0cd0559f143807ff688ff62789b7236a332b7d7255ec0b4e73e6b3a4',
             'output': '1062ab5fbbdee9042ad35bdadfd3047c0a2127fe0f001da1be1b0582185edfc9687be8d68f85795833bb04af9cedd3bb'},
            {'private': '9ef87ba8aa2e664bdfdb978b98bc30fb61773d9298e7b8c72911683eeff41921',
             'public': '441e76d7e53be0a967181076a842f69c20fd8c0e3f0ce3aa421b490b059fe094',
             'salt': '518f8dfd0c138f1ffb4ea8029db15441d70abd893c3d767dc668f23ba7770e27',
             'iv': '42d28307974a1b2a2d921d270cfce03b',
             'input': '49de3cd5890e0cd0559f143807ff688ff62789b7236a332b7d7255ec0b4e73e6b3a4',
             'output': '005e49fb7c5da540a84b034c853fc9f78a6b901ea495aed0c2abd4f08f1a96f9ffefc6a57f1ac09e0aea95ca0f03ffd8'},
            {'private': '9ef87ba8aa2e664bdfdb978b98bc30fb61773d9298e7b8c72911683eeff41921',
             'public': '441e76d7e53be0a967181076a842f69c20fd8c0e3f0ce3aa421b490b059fe094',
             'salt': '582fdf58b53715c26e10ba809e8f2ab70502e5a3d4e9a81100b7227732ab0bbc',
             'iv': '91f2aad3189bb2edc93bc891e73911ba',
             'input': '49de3cd5890e0cd0559f143807ff688ff62789b7236a332b7d7255ec0b4e73e6b3a4',
             'output': '821a69cb16c57f0cb866e590b38069e35faec3ae18f158bb067db83a11237d29ab1e6b868b3147236a0958f15c2e2167'},
            {'private': '9ef87ba8aa2e664bdfdb978b98bc30fb61773d9298e7b8c72911683eeff41921',
             'public': '441e76d7e53be0a967181076a842f69c20fd8c0e3f0ce3aa421b490b059fe094',
             'salt': 'a415b4c006118fb72fc37b2746ef288e23ac45c8ff7ade5f368a31557b6ac93a',
             'iv': '2b7c5f75606c0b8106c6489ea5657a9e',
             'input': '24512b714aefd5cbc4bcc4ef44ce6c67ffc447c65460a6c6e4a92e85',
             'output': '2781d5ee8ef1cb1596f8902b33dfae5045f84a987ca58173af5830dbce386062'},
            {'private': 'ed93c5a101ab53382ceee4f7e6b5aa112621d3bb9d18891509b1834ede235bcc',
             'public': '5a5e14c633d7d269302849d739d80344ff14db51d7bcda86045723f05c4e4541',
             'salt': '47e73ec362ea82d3a7c5d55532ad51d2cdf5316b981b2b2bd542b0efa027e8ea',
             'iv': 'b2193f59030c8d05a7d3577b7f64dd33',
             'input': '24512b714aefd5cbc4bcc4ef44ce6c67ffc447c65460a6c6e4a92e85',
             'output': '3f43912db8dd6672b9996e5272e18c4b88fec9d7e8372db9c5f4709a4af1d86f'},
            {'private': 'ed93c5a101ab53382ceee4f7e6b5aa112621d3bb9d18891509b1834ede235bcc',
             'public': '5a5e14c633d7d269302849d739d80344ff14db51d7bcda86045723f05c4e4541',
             'salt': 'aaa006c57b6d1e402650577fe9787d8d285f4bacd7c01f998be49c766f8860c7',
             'iv': '130304ddb9adc8870cf56bcae9487b7f',
             'input': '24512b714aefd5cbc4bcc4ef44ce6c67ffc447c65460a6c6e4a92e85',
             'output': '878cc7d8c0ef8dac0182a78eedc8080a402f59d8062a6b4ca8f4a74f3c3b3de7'},
            {'private': 'ed93c5a101ab53382ceee4f7e6b5aa112621d3bb9d18891509b1834ede235bcc',
             'public': '5a5e14c633d7d269302849d739d80344ff14db51d7bcda86045723f05c4e4541',
             'salt': '28dc7ccd6c2a939eef64b8be7b9ae248295e7fcd8471c22fa2f98733fea97611',
             'iv': 'cb13890d3a11bc0a7433738263006710',
             'input': '24512b714aefd5cbc4bcc4ef44ce6c67ffc447c65460a6c6e4a92e85',
             'output': 'e74ded846bebfa912fa1720e4c1415e6e5df7e7a1a7fedb5665d68f1763209a4'},
            {'private': 'ed93c5a101ab53382ceee4f7e6b5aa112621d3bb9d18891509b1834ede235bcc',
             'public': '5a5e14c633d7d269302849d739d80344ff14db51d7bcda86045723f05c4e4541',
             'salt': '79974fa2cad95154d0873902c153ccc3e7d54b17f2eeb3f29b6344cad9365a9a',
             'iv': '22123357979d20f44cc8eb0263d84e0e',
             'input': '24512b714aefd5cbc4bcc4ef44ce6c67ffc447c65460a6c6e4a92e85',
             'output': 'eb14dec7b8b64d81a2ee4db07b0adf144d4f79a519bbf332b823583fa2d45405'},
            {'private': 'ed93c5a101ab53382ceee4f7e6b5aa112621d3bb9d18891509b1834ede235bcc',
             'public': '5a5e14c633d7d269302849d739d80344ff14db51d7bcda86045723f05c4e4541',
             'salt': '3409a6f8c4dcd9bd04144eb67e55a98696b674735b01bf1196191f29871ef966',
             'iv': 'a823a0965969380ea1f8659ea5fd8fdd',
             'input': '24512b714aefd5cbc4bcc4ef44ce6c67ffc447c65460a6c6e4a92e85',
             'output': '00a7eb708eae745847173f8217efb05be13059710aee632e3f471ac3c6202b51'},
        ]

        for test in test_cases:
            private_key = bytearray(reversed(unhexlify(test['private'])))
            node = bip32.HDNode(
                depth=0,
                fingerprint=0,
                child_num=0,
                chain_code=bytearray(32),
                private_key=private_key,
                curve_name=CURVE
            )

            encrypted = node.nem_encrypt(unhexlify(test['public']),
                                         unhexlify(test['iv']),
                                         unhexlify(test['salt']),
                                         unhexlify(test['input']))

            self.assertEqual(encrypted, unhexlify(test['output']))


if __name__ == '__main__':
    unittest.main()
