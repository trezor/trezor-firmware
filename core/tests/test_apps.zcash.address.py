from common import *

from apps.zcash import address
from apps.zcash.address import P2PKH, P2SH, SAPLING, ORCHARD

# (receivers, unified_address)
TESTVECTORS_UNIFIED = [
	({
		ORCHARD: unhexlify("8ff3386971cb64b8e7789908dd8ebd7de92a68e586a34db8fea999efd2016fae76750afae7ee941646bcb9"),
	},"u1qylzskzykhk5l5vk6zlyqqruvskzv74hk20lmrllzy3vdz6pvny5t9zwlrm86ukw77y5pu8uep2m33s7sc7gn6aq0jm9neg5tsektyn9"),
	({
		ORCHARD: unhexlify("56e84b1adc9423c3676c0463f7125df4836fd2816b024ee70efe09fb9a7b3863c6eacdf95e03894950692c"),
	},"u17j4lvw84jd238ev9ukr0lvqhv4z32v98pxcglctaj3aqfqj7rr2wwvh73247ekczw4smyrvm2wf2v5nfxvn3sl0ycc6w4455yg49yf2m"),
	({
		SAPLING: unhexlify("3484fc3fce5048621e1e164acf29528ce2fa39c9ca97a8114fb3deba18068a68d487c5d063a4a3ce614ec2"),
		ORCHARD: unhexlify("513d01f7b5d37f5433c336af84a342af9d833bc01635ceb7a2139d23510ae4f26e42fc79f4f6c467154115"),
	},"u1xnkv2m5x02kc5h4fqv3yk0s8z6k4ya7n92an98gsk5dc467ny0rkwevvq3nw7sjll4hvhr2u58xw4cryguzeq0h5yzu4xk3esxgl3glqqth5jqse0za8w5y2ym93ht3zv8wvyw7kvs7ejuvk6xkc375j77ukuzwxkznhuy3x6yvxeq5c"),
	({
		P2SH: unhexlify("3dc166d56a1d62f5a8d7551db5fd9313e8c7203d"),
		ORCHARD: unhexlify("1038c28960629162fdd46aca1eb067a1de41e4385d19f92b53341de8b3eeecb0afcbc130808bf42e8de128"),
	},"u1qld9m8deq56mpvma9gpvm5ths62f9fcqa9udwn7jvjts3msldpet509nnuguvl6zq0atz9s8t53wm207zq2xyhawanjg4xt2yzqvuwt6kzx2lzzmk9w45mlh6vmacmywmeh6c584t8u"),
	({
		P2SH: unhexlify("362697b0e4e4c763ccb8f676495c222f7fba1e31"),
		ORCHARD: unhexlify("3a6f91fb15f130f2778292577d9f32e137ab22c51fafc959b16d42578387b297a124a53bd9b32af59d7f1f"),
	},"u1rw3fjc02enpe09gx57ada7rdvy2xy8mxs7kalvq2uhyg2qqmt77ycealmp30wujndt02cdeffrrrgg6d858awwxadspg8yqwmf56w04tqagt0chhg9z7s6h7ndwn92yjnrwky7207zz"),
	({
		P2SH: unhexlify("acd20b183e31d49f25c9a138f49b1a537edcf04b"),
		SAPLING: unhexlify("24e657b33ec5d1679d072ba830c1c4412bc775c520e2a1ca9617680397c6708effd84b61fb950222e62516"),
		ORCHARD: unhexlify("a391f728b786bbd102ddbfd1318ca4e03e6045c23c3c4826686696c7ba949216adf0e06e6b4bd16b28ac39"),
	},"u1j7zuzyc5n2mvp3tvgdztsx0gz3er4n5rl7jvre3hh6tgusnft5lpsme3ldndk482v9t3pcl9umkj2eucnua80vqk9jmelg7had8x5ryqlp2et48tmq9qu824xankrktyms8x6x4dnfyan98fgl7rr7wfxsmrsxqs2x7qwd57qltf5rlrdecevm4tjmz8m6kqkvjlqj3s5uywcr6za7f"),
	({
		P2PKH: unhexlify("47f1e191e00c7a1d48af046827591e9733a97fa6"),
		ORCHARD: unhexlify("6424f71a3ad197426498f4eccb6a5780204237987232bc098f89acc475c3f74bd69e2f35d44736f48f3c14"),
	},"u1kts2hcsm3nnzm290gh29ga32eg2euvkp9l20yhptwtzqlp0c6tskc59yeywq4e6y64uggzc2pzf9x8yuc805xdjfp0waezff8gzmaxc8rdmp9wr82r78ts2nwk24yrakua84sll8z9h"),
	({
		P2PKH: unhexlify("f73476f21a482ec9378365c8f7393c94e2885315"),
		ORCHARD: unhexlify("b4eed75afb7f6b02b626ebb20b0b211507fda98d12229395fdf0d67b6b40d8496ee159251933bbbd7b8228"),
	},"u1hn3fgwa6m4h3uulnrlz78x74khmfda20jej5495pxhcteadp8xrpl9z644e7pf3pk4a3wuld24fat7r2z33wxqfaeakhgl9nssnh0sg9ggyadr4696n4p6mdrfnzum5luxs42uc7x7m"),
	({
		P2PKH: unhexlify("03880d780cb07fcfaabe3f1a84b27db59a4a153d"),
		SAPLING: unhexlify("137419a9a2123e27dce5836ac3ecdcf9d628b25a744248eae8cf0223f5c444c55650df2301d1417ed3ca59"),
		ORCHARD: unhexlify("db8c305524bc0deaa85d9704ea8c1320ffbbadfe96f0c6ff16b607111b5583bfb6f1ea45275ef2aa2d879b"),
	},"u1wg3qy8cw9zfs6axtg6204ftf2c6gkx2mz8xksz83paxfaqcc52jfedfz0m2sk50a7ujp6gtlvp7572csfvz4t4rtv9pzfxa0dk9d8van09dymf5s2q3a2ccsevrscm2z6hw9fqw3swjjlcqh3muq703mlrmf5rstd476ngzq9dr4y0dwys4hnjz58wx9erhz7ycmuv7ynnjt2sm2epy")
]

@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestZcashAddress(unittest.TestCase):
	def test_encode_unified(self):
		for tv in TESTVECTORS_UNIFIED:
			receivers = tv[0]
			ua = address.encode_unified(receivers)
			self.assertEqual(ua, tv[1])

	def test_decode_unified(self):
		for tv in TESTVECTORS_UNIFIED:
			ua = tv[1]
			receivers = address.decode_unified(ua)
			self.assertEqual(receivers, tv[0])




if __name__ == '__main__':
	unittest.main()
