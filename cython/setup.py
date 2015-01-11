from distutils.core import setup
from distutils.extension import Extension
from Cython.Build import cythonize
from Cython.Distutils import build_ext

crypto_srcs = [
	'base58.c',
	'bignum.c',
	'bip32.c',
	'ecdsa.c',
	'hmac.c',
	'rand.c',
	'ripemd160.c',
	'secp256k1.c',
	'sha2.c',
]

crypto_srcs = [ '../%s' % x for x in crypto_srcs ]

extensions = [
	Extension('TrezorCrypto',
		sources = ['TrezorCrypto.pyx', 'c.pxd'] + crypto_srcs,
		extra_compile_args = ['-DUSE_PUBKEY_VALIDATE=0'],
	)
]

setup(
	name = 'TrezorCrypto',
	version = '0',
	description = 'Cython wrapper around trezor-crypto library',
	author = 'Pavol Rusnak',
	author_email = 'stick@satoshilabs.com',
	url = 'https://github.com/trezor/trezor-crypto',
	cmdclass = {'build_ext': build_ext},
	ext_modules = cythonize(extensions),
)
