from common import *
from ubinascii import unhexlify
from trezor.crypto import bip32
from apps.nem.helpers import NEM_NETWORK_MAINNET, NEM_CURVE


class TestNemAddress(unittest.TestCase):

    # test vectors from https://raw.githubusercontent.com/NemProject/nem-test-vectors/master/1.test-keys.dat
    def test_addresses(self):
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
                curve_name=NEM_CURVE
            )

            self.assertEqual(node.nem_address(NEM_NETWORK_MAINNET), test[2])
            # public key is prepended with 1, removing
            self.assertEqual(node.public_key()[1:], unhexlify(test[1]))


if __name__ == '__main__':
    unittest.main()
