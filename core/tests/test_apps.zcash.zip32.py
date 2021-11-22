from common import *

from apps.zcash import zip32

TESTVECTORS_ZIP32 = [
	{
		"seed": unhexlify("5d7a8f739a2d9e945b0ce152a8049e294c4d6e66b164939daffa2ef6ee692148"),
		"path": [2147483680, 2147483781, 2147483648], # m/32'/133'/0'
		"sk": unhexlify("8dd600f2e9d677246e1448f3a4489fb930e7a547ae5a04f19e3391bed58035e2"),
	},
	{
		"seed": unhexlify("1cdd86b3cc4318d9614fc820905d042bb1ef9ca3f24988c7b3534201cfb1cd8d"),
		"path": [2147483680, 2147483781, 2147483653], # m/32'/133'/5'
		"sk": unhexlify("15a5adaa3e945d215bdc1727cb8b27a074a809952742c918303cbc266243b9bb"),
	},
	{
		"seed": unhexlify("bf69b8250c18ef41294ca97993db546c1fe01f7e9c8e36d6a5e29d4e30a73594"),
		"path": [2147483680, 2147483781, 2147483747], # m/32'/133'/99'
		"sk": unhexlify("fa8a57242c64de944b079798ed46dae913195dd586522e248fdea11a72867276"),
	},
	{
		"seed": unhexlify("bf5098421c69378af1e40f64e125946f62c2fa7b2fecbcb64b6968912a6381ce"),
		"path": [2147483680, 2147483649, 2147483648], # m/32'/1'/0'
		"sk": unhexlify("b4a8f0103d329045f950b20f64d03d3c5a583e0ec3fafc8ef438b859688992a1"),
	},
	{
		"seed": unhexlify("3dc166d56a1d62f5a8d7551db5fd9313e8c7203d996af7d477083756d59af80d"),
		"path": [2147483680, 2147483649, 2147483651], # m/32'/1'/3'
		"sk": unhexlify("8d3ff56d2bc065fb2bf767639be058227047822449fb854b07f52703003ea8ab"),
	},
]



@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestZcashZIP32(unittest.TestCase):
	def test_zip32(self):
		for tv in TESTVECTORS_ZIP32:
			sk = zip32.master(tv["seed"]).derive(tv["path"])
			self.assertEqual(sk, tv["sk"])
			

if __name__ == '__main__':
	unittest.main()