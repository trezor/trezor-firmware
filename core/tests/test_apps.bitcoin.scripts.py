from common import *

from apps.bitcoin.scripts import output_script_native_segwit, output_script_p2sh, redeem_script_paytolnswap
from trezor.crypto.hashlib import sha256
from trezor.crypto.scripts import sha256_ripemd160

class TestScripts(unittest.TestCase):

    def test_redeem_script_paytolnswap(self):
        VECTORS = [
            (
                unhexlify("53ada8e6de01c26ff43040887ba7b22bddce19f8658fd1ba00716ed79d15cd5e"),
                unhexlify("03f8109578aae1e5cfc497e466cf6ae6625497cd31886e87b2f4f54f3f0f46b539"),
                515924,
                unhexlify("03ec0c1e45b709d708cd376a6f2daf19ac27be229647780d592e27d7fb7efb207a"),
                unhexlify("76a914e2ac8cb97af3d59b1c057db4b0c4f9aa12a912738763752103f8109578aae1e5cfc497e466cf6ae6625497cd31886e87b2f4f54f3f0f46b539670354df07b17576a914ce99030daa71c4dfb155de212e475284d7a2cedb8868ac"),
                unhexlify("0020727f212ed5f7c03cc0b9674ca383935ac9215006072db397aa305e11f43d7240"),
                unhexlify("a914dd0d74da9b0b8b2d899c9c4f3e5ad2b2336f002987"),
            ),
            (
                unhexlify("0f817af9d08abe80e2d4980903ec329deaedb81ecfccada6a5cd6794e2a5a3a2"),
                unhexlify("027f1d103826584b3c216d6a62600d8b6c7e2de62ab059d38dfd6427f3e3d7deca"),
                725440,
                unhexlify("0396070f2813933502e907c011ae7ba928683a9c2f0e888dae7ebd2c41120ee6b5"),
                unhexlify("76a91426282c115718ef107f305272fb7d7723bacfd46a87637521027f1d103826584b3c216d6a62600d8b6c7e2de62ab059d38dfd6427f3e3d7deca6703c0110bb17576a914ece6935b2a5a5b5ff997c87370b16fa10f1644108868ac"),
                unhexlify("00200600ace6f612cb757b0cfacaf5cfbdf36ea59b2b9350e7de958e1f98ff06621b"),
                unhexlify("a91482e95b5ab909b8d560bdfb4dc2d70fe75aa48b3787"),
            ),
            (
                unhexlify("72d29ccfd52ca94b69e14fc8efdf41ad845ece4bac1ee04627a8f9c83a49de8c"),
                unhexlify("022e05052f864845f67640651f5463e4a2921f07a46e24e79dd8bd0a4fdc896208"),
                725457,
                unhexlify("0396070f2813933502e907c011ae7ba928683a9c2f0e888dae7ebd2c41120ee6b5"),
                unhexlify("76a91403d7eba1e13f81e87221be9392d7afdefdcb8ed987637521022e05052f864845f67640651f5463e4a2921f07a46e24e79dd8bd0a4fdc8962086703d1110bb17576a914ece6935b2a5a5b5ff997c87370b16fa10f1644108868ac"),
                unhexlify("00200c2965d3a25f0207a013da7dfa208989f493e1f3ef45c920dcdc85d1af837e8a"),
                unhexlify("a9142b503fe62b792866933ddeaa087dac5abbc1fcf987"),
            ),
        ]
        for payment_hash, destination, ctlv, refund_pubkey, redeem_script, script_witness, script_p2sh_witness in VECTORS:
            s = redeem_script_paytolnswap(payment_hash, destination, ctlv, refund_pubkey)
            self.assertEqual(s, redeem_script)
            h = sha256(s).digest()
            w = output_script_native_segwit(0, h)
            self.assertEqual(w, script_witness)
            h = sha256_ripemd160(w).digest()
            p = output_script_p2sh(h)
            self.assertEqual(p, script_p2sh_witness)


if __name__ == '__main__':
    unittest.main()
