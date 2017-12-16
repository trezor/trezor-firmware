from common import *

from trezor.crypto.hashlib import ripemd160

from trezor.crypto import base58


def digestfunc_graphene(x):
    return ripemd160(x).digest()[:4]


class TestCryptoBase58(unittest.TestCase):

    # vectors from https://github.com/bitcoin/bitcoin/blob/master/src/test/data/base58_keys_valid.json
    vectors = [
        ('0065a16059864a2fdbc7c99a4723a8395bc6f188eb', '1AGNa15ZQXAZUgFiqJ2i7Z2DPU2J6hW62i'),
        ('0574f209f6ea907e2ea48f74fae05782ae8a665257', '3CMNFxN1oHBc4R1EpboAL5yzHGgE611Xou'),
        ('6f53c0307d6851aa0ce7825ba883c6bd9ad242b486', 'mo9ncXisMeAoXwqcV5EWuyncbmCcQN4rVs'),
        ('c46349a418fc4578d10a372b54b45c280cc8c4382f', '2N2JD6wb56AfK4tfmM6PwdVmoYk2dCKf4Br'),
        ('80eddbdc1168f1daeadbd3e44c1e3f8f5a284c2029f78ad26af98583a499de5b19', '5Kd3NBUAdUnhyzenEwVLy9pBKxSwXvE9FMPyR4UKZvpe6E3AgLr'),
        ('8055c9bccb9ed68446d1b75273bbce89d7fe013a8acd1625514420fb2aca1a21c401', 'Kz6UJmQACJmLtaQj5A3JAge4kVTNQ8gbvXuwbmCj7bsaabudb3RD'),
        ('ef36cb93b9ab1bdabf7fb9f2c04f1b9cc879933530ae7842398eef5a63a56800c2', '9213qJab2HNEpMpYNBa7wHGFKKbkDn24jpANDs2huN3yi4J11ko'),
        ('efb9f4892c9e8282028fea1d2667c4dc5213564d41fc5783896a0d843fc15089f301', 'cTpB4YiyKiBcPxnefsDpbnDxFDffjqJob8wGCEDXxgQ7zQoMXJdH'),
        ('006d23156cbbdcc82a5a47eee4c2c7c583c18b6bf4', '1Ax4gZtb7gAit2TivwejZHYtNNLT18PUXJ'),
        ('05fcc5460dd6e2487c7d75b1963625da0e8f4c5975', '3QjYXhTkvuj8qPaXHTTWb5wjXhdsLAAWVy'),
        ('6ff1d470f9b02370fdec2e6b708b08ac431bf7a5f7', 'n3ZddxzLvAY9o7184TB4c6FJasAybsw4HZ'),
        ('c4c579342c2c4c9220205e2cdc285617040c924a0a', '2NBFNJTktNa7GZusGbDbGKRZTxdK9VVez3n'),
        ('80a326b95ebae30164217d7a7f57d72ab2b54e3be64928a19da0210b9568d4015e', '5K494XZwps2bGyeL71pWid4noiSNA2cfCibrvRWqcHSptoFn7rc'),
        ('807d998b45c219a1e38e99e7cbd312ef67f77a455a9b50c730c27f02c6f730dfb401', 'L1RrrnXkcKut5DEMwtDthjwRcTTwED36thyL1DebVrKuwvohjMNi'),
        ('efd6bca256b5abc5602ec2e1c121a08b0da2556587430bcf7e1898af2224885203', '93DVKyFYwSN6wEo3E2fCrFPUp17FtrtNi2Lf7n4G3garFb16CRj'),
        ('efa81ca4e8f90181ec4b61b6a7eb998af17b2cb04de8a03b504b9e34c4c61db7d901', 'cTDVKtMGVYWTHCb1AFjmVbEbWjvKpKqKgMaR3QJxToMSQAhmCeTN'),
        ('007987ccaa53d02c8873487ef919677cd3db7a6912', '1C5bSj1iEGUgSTbziymG7Cn18ENQuT36vv'),
        ('0563bcc565f9e68ee0189dd5cc67f1b0e5f02f45cb', '3AnNxabYGoTxYiTEZwFEnerUoeFXK2Zoks'),
        ('6fef66444b5b17f14e8fae6e7e19b045a78c54fd79', 'n3LnJXCqbPjghuVs8ph9CYsAe4Sh4j97wk'),
        ('c4c3e55fceceaa4391ed2a9677f4a4d34eacd021a0', '2NB72XtkjpnATMggui83aEtPawyyKvnbX2o'),
        ('80e75d936d56377f432f404aabb406601f892fd49da90eb6ac558a733c93b47252', '5KaBW9vNtWNhc3ZEDyNCiXLPdVPHCikRxSBWwV9NrpLLa4LsXi9'),
        ('808248bd0375f2f75d7e274ae544fb920f51784480866b102384190b1addfbaa5c01', 'L1axzbSyynNYA8mCAhzxkipKkfHtAXYF4YQnhSKcLV8YXA874fgT'),
        ('ef44c4f6a096eac5238291a94cc24c01e3b19b8d8cef72874a079e00a242237a52', '927CnUkUbasYtDwYwVn2j8GdTuACNnKkjZ1rpZd2yBB1CLcnXpo'),
        ('efd1de707020a9059d6d3abaf85e17967c6555151143db13dbb06db78df0f15c6901', 'cUcfCMRjiQf85YMzzQEk9d1s5A4K7xL5SmBCLrezqXFuTVefyhY7'),
        ('00adc1cc2081a27206fae25792f28bbc55b831549d', '1Gqk4Tv79P91Cc1STQtU3s1W6277M2CVWu'),
        ('05188f91a931947eddd7432d6e614387e32b244709', '33vt8ViH5jsr115AGkW6cEmEz9MpvJSwDk'),
        ('6f1694f5bc1a7295b600f40018a618a6ea48eeb498', 'mhaMcBxNh5cqXm4aTQ6EcVbKtfL6LGyK2H'),
        ('c43b9b3fd7a50d4f08d1a5b0f62f644fa7115ae2f3', '2MxgPqX1iThW3oZVk9KoFcE5M4JpiETssVN'),
        ('80091035445ef105fa1bb125eccfb1882f3fe69592265956ade751fd095033d8d0', '5HtH6GdcwCJA4ggWEL1B3jzBBUB8HPiBi9SBc5h9i4Wk4PSeApR'),
        ('80ab2b4bcdfc91d34dee0ae2a8c6b6668dadaeb3a88b9859743156f462325187af01', 'L2xSYmMeVo3Zek3ZTsv9xUrXVAmrWxJ8Ua4cw8pkfbQhcEFhkXT8'),
        ('efb4204389cef18bbe2b353623cbf93e8678fbc92a475b664ae98ed594e6cf0856', '92xFEve1Z9N8Z641KQQS7ByCSb8kGjsDzw6fAmjHN1LZGKQXyMq'),
        ('efe7b230133f1b5489843260236b06edca25f66adb1be455fbd38d4010d48faeef01', 'cVM65tdYu1YK37tNoAyGoJTR13VBYFva1vg9FLuPAsJijGvG6NEA'),
        ('00c4c1b72491ede1eedaca00618407ee0b772cad0d', '1JwMWBVLtiqtscbaRHai4pqHokhFCbtoB4'),
        ('05f6fe69bcb548a829cce4c57bf6fff8af3a5981f9', '3QCzvfL4ZRvmJFiWWBVwxfdaNBT8EtxB5y'),
        ('6f261f83568a098a8638844bd7aeca039d5f2352c0', 'mizXiucXRCsEriQCHUkCqef9ph9qtPbZZ6'),
        ('c4e930e1834a4d234702773951d627cce82fbb5d2e', '2NEWDzHWwY5ZZp8CQWbB7ouNMLqCia6YRda'),
        ('80d1fab7ab7385ad26872237f1eb9789aa25cc986bacc695e07ac571d6cdac8bc0', '5KQmDryMNDcisTzRp3zEq9e4awRmJrEVU1j5vFRTKpRNYPqYrMg'),
        ('80b0bbede33ef254e8376aceb1510253fc3550efd0fcf84dcd0c9998b288f166b301', 'L39Fy7AC2Hhj95gh3Yb2AU5YHh1mQSAHgpNixvm27poizcJyLtUi'),
        ('ef037f4192c630f399d9271e26c575269b1d15be553ea1a7217f0cb8513cef41cb', '91cTVUcgydqyZLgaANpf1fvL55FH53QMm4BsnCADVNYuWuqdVys'),
        ('ef6251e205e8ad508bab5596bee086ef16cd4b239e0cc0c5d7c4e6035441e7d5de01', 'cQspfSzsgLeiJGB2u8vrAiWpCU4MxUT6JseWo2SjXy4Qbzn2fwDw'),
        ('005eadaf9bb7121f0f192561a5a62f5e5f54210292', '19dcawoKcZdQz365WpXWMhX6QCUpR9SY4r'),
        ('053f210e7277c899c3a155cc1c90f4106cbddeec6e', '37Sp6Rv3y4kVd1nQ1JV5pfqXccHNyZm1x3'),
        ('6fc8a3c2a09a298592c3e180f02487cd91ba3400b5', 'myoqcgYiehufrsnnkqdqbp69dddVDMopJu'),
        ('c499b31df7c9068d1481b596578ddbb4d3bd90baeb', '2N7FuwuUuoTBrDFdrAZ9KxBmtqMLxce9i1C'),
        ('80c7666842503db6dc6ea061f092cfb9c388448629a6fe868d068c42a488b478ae', '5KL6zEaMtPRXZKo1bbMq7JDjjo1bJuQcsgL33je3oY8uSJCR5b4'),
        ('8007f0803fc5399e773555ab1e8939907e9badacc17ca129e67a2f5f2ff84351dd01', 'KwV9KAfwbwt51veZWNscRTeZs9CKpojyu1MsPnaKTF5kz69H1UN2'),
        ('efea577acfb5d1d14d3b7b195c321566f12f87d2b77ea3a53f68df7ebf8604a801', '93N87D6uxSBzwXvpokpzg8FFmfQPmvX4xHoWQe3pLdYpbiwT5YV'),
        ('ef0b3b34f0958d8a268193a9814da92c3e8b58b4a4378a542863e34ac289cd830c01', 'cMxXusSihaX58wpJ3tNuuUcZEQGt6DKJ1wEpxys88FFaQCYjku9h'),
        ('001ed467017f043e91ed4c44b4e8dd674db211c4e6', '13p1ijLwsnrcuyqcTvJXkq2ASdXqcnEBLE'),
        ('055ece0cadddc415b1980f001785947120acdb36fc', '3ALJH9Y951VCGcVZYAdpA3KchoP9McEj1G'),
    ]

    vectors_graphene = [
        ('02e649f63f8e8121345fd7f47d0d185a3ccaa843115cd2e9392dcd9b82263bc680', '6dumtt9swxCqwdPZBGXh9YmHoEjFFnNfwHaTqRbQTghGAY2gRz'),
        ('021c7359cd885c0e319924d97e3980206ad64387aff54908241125b3a88b55ca16', '5725vivYpuFWbeyTifZ5KevnHyqXCi5hwHbNU9cYz1FHbFXCxX'),
        ('02f561e0b57a552df3fa1df2d87a906b7a9fc33a83d5d15fa68a644ecb0806b49a', '6kZKHSuxqAwdCYsMvwTcipoTsNE2jmEUNBQufGYywpniBKXWZK'),
        ('03e7595c3e6b58f907bee951dc29796f3757307e700ecf3d09307a0cc4a564eba3', '8b82mpnH8YX1E9RHnU2a2YgLTZ8ooevEGP9N15c1yFqhoBvJur'),
    ]

    def test_decode_check(self):
        for a, b in self.vectors:
            self.assertEqual(base58.decode_check(b), unhexlify(a))
        for a, b in self.vectors_graphene:
            self.assertEqual(base58.decode_check(b, digestfunc=digestfunc_graphene), unhexlify(a))

    def test_encode_check(self):
        for a, b in self.vectors:
            self.assertEqual(base58.encode_check(unhexlify(a)), b)
        for a, b in self.vectors_graphene:
            self.assertEqual(base58.encode_check(unhexlify(a), digestfunc=digestfunc_graphene), b)


if __name__ == '__main__':
    unittest.main()
