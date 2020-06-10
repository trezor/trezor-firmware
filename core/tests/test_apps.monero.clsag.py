from common import *

if not utils.BITCOIN_ONLY:
    from apps.monero.xmr import crypto, mlsag
    from apps.monero.xmr.serialize_messages.tx_ct_key import CtKey
    from trezor.crypto import random
    import ubinascii


class TmpKey:
    def __init__(self, d, c):
        self.dest = d
        self.commitment = c


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestMoneroClsag(unittest.TestCase):
    def verify_clsag(self, msg, ss, sc1, sI, sD, pubs, C_offset):
        n = len(pubs)
        c = crypto.new_scalar()
        D_8 = crypto.new_point()
        tmp_bf = bytearray(32)
        C_offset_bf = crypto.encodepoint(C_offset)

        crypto.sc_copy(c, sc1)
        crypto.point_mul8_into(D_8, sD)

        hsh_P = crypto.get_keccak()  # domain, I, D, P, C, C_offset
        hsh_C = crypto.get_keccak()  # domain, I, D, P, C, C_offset
        hsh_P.update(mlsag._HASH_KEY_CLSAG_AGG_0)
        hsh_C.update(mlsag._HASH_KEY_CLSAG_AGG_1)

        def hsh_PC(x):
            hsh_P.update(x)
            hsh_C.update(x)

        for x in pubs:
            hsh_PC(x.dest)

        for x in pubs:
            hsh_PC(x.commitment)

        hsh_PC(crypto.encodepoint_into(tmp_bf, sI))
        hsh_PC(crypto.encodepoint_into(tmp_bf, sD))
        hsh_PC(C_offset_bf)
        mu_P = crypto.decodeint(hsh_P.digest())
        mu_C = crypto.decodeint(hsh_C.digest())

        c_to_hash = crypto.get_keccak()  # domain, P, C, C_offset, message, L, R
        c_to_hash.update(mlsag._HASH_KEY_CLSAG_ROUND)
        for i in range(len(pubs)):
            c_to_hash.update(pubs[i].dest)
        for i in range(len(pubs)):
            c_to_hash.update(pubs[i].commitment)
        c_to_hash.update(C_offset_bf)
        c_to_hash.update(msg)

        c_p = crypto.new_scalar()
        c_c = crypto.new_scalar()
        L = crypto.new_point()
        R = crypto.new_point()
        tmp_pt = crypto.new_point()
        i = 0
        while i < n:
            crypto.sc_mul_into(c_p, mu_P, c)
            crypto.sc_mul_into(c_c, mu_C, c)

            C_P = crypto.point_sub(
                crypto.decodepoint_into(tmp_pt, pubs[i].commitment), C_offset
            )
            crypto.add_keys2_into(
                L, ss[i], c_p, crypto.decodepoint_into(tmp_pt, pubs[i].dest)
            )
            crypto.point_add_into(L, L, crypto.scalarmult_into(tmp_pt, C_P, c_c))

            HP = crypto.hash_to_point(pubs[i].dest)
            crypto.add_keys3_into(R, ss[i], HP, c_p, sI)
            crypto.point_add_into(R, R, crypto.scalarmult_into(tmp_pt, D_8, c_c))

            chasher = c_to_hash.copy()
            chasher.update(crypto.encodepoint_into(tmp_bf, L))
            chasher.update(crypto.encodepoint_into(tmp_bf, R))
            crypto.decodeint_into(c, chasher.digest())
            i += 1
        res = crypto.sc_sub(c, sc1)
        if not crypto.sc_eq(res, crypto.sc_0()):
            raise ValueError("Signature error")

    def gen_clsag_test(self, ring_size=11, index=None):
        res = self.gen_clsag_sig(ring_size=11, index=index)
        msg, scalars, sc1, sI, sD, ring2, Cp = res
        self.verify_clsag(msg, scalars, sc1, sI, sD, ring2, Cp)

    def gen_clsag_sig(self, ring_size=11, index=None):
        msg = random.bytes(32)
        amnt = crypto.sc_init(random.uniform(0xFFFFFF) + 12)
        priv = crypto.random_scalar()
        msk = crypto.random_scalar()
        alpha = crypto.random_scalar()
        P = crypto.scalarmult_base(priv)
        C = crypto.add_keys2(msk, amnt, crypto.xmr_H())
        Cp = crypto.add_keys2(alpha, amnt, crypto.xmr_H())

        ring = []
        for i in range(ring_size - 1):
            tk = TmpKey(
                crypto.encodepoint(crypto.scalarmult_base(crypto.random_scalar())),
                crypto.encodepoint(crypto.scalarmult_base(crypto.random_scalar())),
            )
            ring.append(tk)

        index = index if index is not None else random.uniform(len(ring))
        ring.insert(index, TmpKey(crypto.encodepoint(P), crypto.encodepoint(C)))
        ring2 = list(ring)
        mg_buffer = []

        self.assertTrue(
            crypto.point_eq(
                crypto.scalarmult_base(priv), crypto.decodepoint(ring[index].dest)
            )
        )
        self.assertTrue(
            crypto.point_eq(
                crypto.scalarmult_base(crypto.sc_sub(msk, alpha)),
                crypto.point_sub(crypto.decodepoint(ring[index].commitment), Cp),
            )
        )

        mlsag.generate_clsag_simple(
            msg, ring, CtKey(priv, msk), alpha, Cp, index, mg_buffer,
        )

        sD = crypto.decodepoint(mg_buffer[-1])
        sc1 = crypto.decodeint(mg_buffer[-2])
        scalars = [crypto.decodeint(x) for x in mg_buffer[1:-2]]
        H = crypto.new_point()
        sI = crypto.new_point()

        crypto.hash_to_point_into(H, crypto.encodepoint(P))
        crypto.scalarmult_into(sI, H, priv)  # I = p*H
        return msg, scalars, sc1, sI, sD, ring2, Cp

    def verify_monero_generated(self, clsag):
        msg = ubinascii.unhexlify(clsag["msg"])
        sI = crypto.decodepoint(ubinascii.unhexlify(clsag["sI"]))
        sD = crypto.decodepoint(ubinascii.unhexlify(clsag["sD"]))
        sc1 = crypto.decodeint(ubinascii.unhexlify(clsag["sc1"]))
        Cout = crypto.decodepoint(ubinascii.unhexlify(clsag["cout"]))
        scalars = [crypto.decodeint(ubinascii.unhexlify(x)) for x in clsag["ss"]]
        ring = []
        for e in clsag["ring"]:
            ring.append(TmpKey(ubinascii.unhexlify(e[0]), ubinascii.unhexlify(e[1])))

        self.verify_clsag(msg, scalars, sc1, sI, sD, ring, Cout)

    def test_monero_generated_clsag_01(self):
        clsag = {
            "msg": "0100000000000000000000000000000000000000000000000000000000000000",
            "cout": "8e3afb92d8ae1264417489259e38f7205a62baea86ae9592cd91988b9cc48102",
            "sI": "a1c7f4a316ddd16374fe495d402be60566047ae5a1352554e98ebff118705303",
            "sD": "cd80b5c7f3f597de6e20bcef669a4ba9eb3eb89ead12ab1c24c92acd609afcb2",
            "sc1": "cf4f48ed60771d4e8d02e9e0af37281ceeb66573bd528ac256a7e17794a75602",
            "ss":
                ["aaeffa564b5b0ff1e4ed72c9b595cd0241ac64eeb41b902a35688e369922d704"
                    , "1defc134a853252d734d19b29d8f2fabc85a8ae24ebcf8f050d4daf8a335e901"
                    , "cdf9ac576f0c7ceb7eb22c1a1254a801d0d2915e59870be8b1ab68cd1281120d"
                    , "d1973493d8224aaa9732878b9a88d448ea16185f94e5bafd82816277682fa108"
                    , "a130e076845e512687575942bf3694bcb44eb19eb1181af9a1fc2254949b7c0f"
                    , "26f5b6ea154d6bd4a969c742563d75f1bfcd5ded3af78669e45ba95e76c48605"
                    , "5b695d3be46b826fd11e043028dee2aa25cf36910e86537fcd1cd3f5cb49650e"
                    , "37e811ebb4a2b9c35556b4af911a03a93468f599956c034092c3ece9e1169208"
                    , "a361ceec9aacd65da6d3e686fbcd0c1aef26096321be7f01653157ee6096a201"
                    , "f9b762ef1df69bb12ca76a97dce11f7840b8ec63c3dc2683f7ae71cb79c49103"
                    , "ea010fa6a35f3bd3d7899a7a2a8df4d3ef9c9dfbbd56fe43ff5c7442821d3508"
                 ]
            , "ring": [
                ["241c0295b4c3a149e5ac7997963e125d0fc6cc8adad9349df3b01ff611936c87",
                 "3a24a4c418ccb2ceb83672d01534a73ff1e9f548937d5ddd7f1971c9b398868c"],
                ["ec432ccfbf730077cb2d8c59968e2796148a590eec7928ecf268d883ced0de5b",
                 "2973d6e9c27538fd0f7c003e014311e9403dcb6e7d86b66df65176a579943bda"],
                ["0cfeafc313a6a2e60110778d53d61fa1705e9049b8afba0f51c1127f6855c07f",
                 "ffa4d4c77202907832294243a96886920017b67fbe5b3800bcc1457c4a4a1ff0"],
                ["bd4eca22dc010a214524901b88bdda27e427217ff784c47520ee76743caba036",
                 "e07135f8398459133c2969184e70610b9b995f73e44acf54b6eaed6227e68bbc"],
                ["73c8d57d0128c99fc2ab0be8cee5fe5c1288b98e51822a6681846035fcc53fea",
                 "2987499fde3f4353013206d89fe2d7c6ad3cd9a66c9a36d17749e39112513572"],
                ["385c538901b79c6bd2ddea5191e808b1414c9dfdcaf424841d843dd788cb89ad",
                 "ec5f987fe138c6cb1d47ff75d77852b7c0a94ba1f0b93d22c0463f75986605bd"],
                ["fed06cb761745a6f087d1af13f84670ecbf1523d72b46e8bd0698d1cdfb398bc",
                 "5d81df981fb885f947b9404cb63cb06fe4e001be281f2bdfb3c638d54ec6e49e"],
                ["667d1edfb83a17bd81fcf7831362b6c9038f26340ee1fe56d41f62cb0b32e989",
                 "e9ceba97867b43cd5420c94fa61cc5f11e440e261df74dfc8b1c07ec4b13aa3c"],
                ["e1e76da5bd52fc065f9af40efde5f733f9673974d14c6af8d200d8576ac3a90d",
                 "97358d6ddad38b2707fb864bfcaaab935851af66d50bcbac569d159d740bdf71"],
                ["4fd5d0db88283c63905d5095a76b11a75337e43f403f8469175ba9c49741552e",
                 "af0ab85872a6355d5c82c1f9a2a41488146e19b272887a1f7385cc26bef3f1d8"],
                ["37e1a4c49a22340fa5ac2c22c1b7a891e7191cdc53911700a317c0d8b92bbf4e",
                 "5c89d29dad77de7d76ece8bb81c7c8cd15008f63c5a14ab1c984b3833e7bbce3"]
            ]
        }
        self.verify_monero_generated(clsag)

    def test_monero_generated_clsag_02(self):
        clsag = {
            "msg": "0100000000000000000000000000000000000000000000000000000000000000",
            "cout": "fdf2503d3217dbf73ababd16f5ab5a63d64c047db1d02b0888a50d2570f3a793",
            "sI": "917fdd3086c056503ffdb1840f03c78d48bfe6d9d60b4efb194bd9798d03acaa",
            "sD": "769d0ca9b272ac02c5efad7df6b5c00f2995c99ca80f4597136decba9a0dd36f",
            "sc1": "fe5c7eb39a32d2aea12e6d127d847b72ea810bfbf3d5bbe23c40e7abdd12900e",
            "ss":
                ["da2940c66cc2405032d959325c8804e216f76b36e71b2ae6b76417ed9c10a80a"
                    , "ca763505c2e5ebacf72098f8cba89ea6826aa448501f03d439c7a838a88bba0e"
                    , "b2eadee4c121e85b0c2a09d56c665ba19ee8ebc451f1e9e96cf72c874f945104"
                    , "5a79523fdc0df9a54ab3937c878bd5a02e62bff77efc338728deb060ecda4509"
                    , "dfadddc51866cde5206269270f44ca2f6350ca0b1328a968773fcacf57031502"
                    , "a964f3549a10fc8bdb2f8217df0e9b08e90477be19a665b94b73ce417622450b"
                    , "48e805427109268b04bf378c869501dbebb79c0cbe664bf7eb0ca222376d1c0f"
                    , "33f36d9a699e92a66d4b9fdf6c1123ae99701b117fbe8f0af9faec51e45eb409"
                    , "25ef746a03aaf59701d1d47ea3b9e9f092662cebc9d44902ce18e81cc5035f01"
                    , "2ba3022d4f9b57da7429499715592073f1608cf270318840a5fd3890bbf5950a"
                    , "8149ec0d965c9881d6a4adedca7d3c9090359dbfae56dbab526be102722aab09"
                 ]
            , "ring": [
                ["081b048be784e1ff6f3b7ebe602690c27723b5d9952405bcdcbed31d16125067",
                 "6090eccb73d2e1fc7bc7644a4fad04e5fe93d953a1258307c44d5b23cd636bf9"],
                ["e2f0f100f1634d7c7dd5a09bc6dd7ee53506d73536aa743e8ea049528e4cb2aa",
                 "632438f9aeda72eb9c6c434391cf9fa2f71788bea598a5d5729a5d502865932a"],
                ["6744197cfde37ad1901d518f112c0f4d820c23122a016949e300eec2ab88916c",
                 "1b251d5b32e22de29a4f99a0ed1de32754636175075e21b25d7283036eb85541"],
                ["0e86bb7ee0b4728f2fedde7ac5019b54de7b2bb19b44d1864e6346dac6c171ab",
                 "5a3c85e93890f802d4148140733dcdcd676353fce1bd774ce28034fc2ec00253"],
                ["1847ce49d9552651395b2fa80637c131a31036f0bfc5abb63526701cd1a32320",
                 "a9cb55bc24e6e1fb894c511f2edd4b7bda4c75a608657d952e85bab83ec98a52"],
                ["5c5d0b678f5045b0304e3c48027bd7e9ccaee1dac4449ed1f34b204868ca5651",
                 "badf83ccba38f2194f924a4f7fb7c2fd966b1e16c1fddeb3658033aa009febe0"],
                ["81961aa4c241a91d498d8f3057b31373d9fc72b6e7d7f98bf497e3dfe705eeaa",
                 "a0e632fbb801d6bce99ef97d7bb6acd945aff5cd7fab56c0e6fec6900a3babd7"],
                ["cbd89f10ddf152bd9c756d145ef4cda1d56a31f1e1936759bee04b7a8a815c76",
                 "8b835b8180f36e79ba79528e0d3401f439cc1c7f99e4bcfb3cb4aa2b60b1afc1"],
                ["a7bc55e955a825730f5dcdc3f8126717d7647cbca8a6b90e08b77269aeed3533",
                 "8da31e80698c9b5181b2e8d9773136083a34e3e72c92134d8201d9c368d89284"],
                ["a7902cec90d3f2de25c8ddc87075159fd00f219a51a1e7dcac17c2b8a91887e9",
                 "2b1e848b6649abefbd6b399504a169252358e7ff6bde8fa7a773b9cf0a167069"],
                ["9fc3d5fb7de8cfc59982f7b20f3f5c145ad191088e7f59c10908dc5d55863bee",
                 "b8de2bc9bb46d475007230a92af14afb6f9dd2804b5c31355a282b40ccdadc92"]
            ]
        }

        self.verify_monero_generated(clsag)

    def test_clsag(self):
        self.gen_clsag_test(ring_size=11, index=None)
        self.gen_clsag_test(ring_size=11, index=None)
        self.gen_clsag_test(ring_size=11, index=None)
        self.gen_clsag_test(ring_size=11, index=0)
        self.gen_clsag_test(ring_size=11, index=9)
        self.gen_clsag_test(ring_size=11, index=10)
        self.gen_clsag_test(ring_size=2, index=0)

    def test_clsag_invalid_sI(self):
        res = self.gen_clsag_sig(ring_size=11, index=5)
        msg, scalars, sc1, sI, sD, ring2, Cp = res
        with self.assertRaises(ValueError):
            sI = crypto.point_mul8(sI)
            self.verify_clsag(msg, scalars, sc1, sI, sD, ring2, Cp)

    def test_clsag_invalid_sD(self):
        res = self.gen_clsag_sig(ring_size=11, index=5)
        msg, scalars, sc1, sI, sD, ring2, Cp = res
        with self.assertRaises(ValueError):
            sD = crypto.scalarmult_base(crypto.random_scalar())
            self.verify_clsag(msg, scalars, sc1, sI, sD, ring2, Cp)

    def test_clsag_invalid_P(self):
        res = self.gen_clsag_sig(ring_size=11, index=5)
        msg, scalars, sc1, sI, sD, ring2, Cp = res
        with self.assertRaises(ValueError):
            ring2[5].dest = crypto.encodepoint(
                crypto.point_mul8(crypto.decodepoint(ring2[5].dest))
            )
            self.verify_clsag(msg, scalars, sc1, sI, sD, ring2, Cp)

    def test_clsag_invalid_P(self):
        res = self.gen_clsag_sig(ring_size=11, index=5)
        msg, scalars, sc1, sI, sD, ring2, Cp = res
        with self.assertRaises(ValueError):
            ring2[5].commitment = crypto.encodepoint(
                crypto.point_mul8(crypto.decodepoint(ring2[5].dest))
            )
            self.verify_clsag(msg, scalars, sc1, sI, sD, ring2, Cp)

    def test_clsag_invalid_Cp(self):
        res = self.gen_clsag_sig(ring_size=11, index=5)
        msg, scalars, sc1, sI, sD, ring2, Cp = res
        with self.assertRaises(ValueError):
            Cp = crypto.point_add(Cp, crypto.scalarmult_base(crypto.sc_init(1)))
            self.verify_clsag(msg, scalars, sc1, sI, sD, ring2, Cp)

    def test_clsag_invalid_index(self):
        res = self.gen_clsag_sig(ring_size=11, index=5)
        msg, scalars, sc1, sI, sD, ring2, Cp = res
        with self.assertRaises(ValueError):
            ring2[5], ring2[6] = ring2[6], ring2[5]
            self.verify_clsag(msg, scalars, sc1, sI, sD, ring2, Cp)


if __name__ == "__main__":
    unittest.main()
