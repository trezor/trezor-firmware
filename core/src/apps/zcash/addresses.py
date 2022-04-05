from trezor.crypto.bech32 import bech32_encode, bech32_decode, convertbits, Encoding
from trezor.crypto import base58

from trezor.utils import BufferReader, empty_bytearray
from trezor.wire import DataError
from apps.common.readers import read_compact_size
from apps.common.writers import write_compact_size, write_bytes_fixed
from apps.bitcoin.keychain import get_coin_by_name

from apps.common.coininfo import CoinInfo
from apps.common import address_type
from trezor.crypto import orchardlib

if False:
	# TODO: network_type should be IntEnum
	# TODO: recerivers should be IntEnum
	from enum import IntEnum
	from typing import Dict
else:
	IntEnum = object  # type: ignore

# receiver typecodes according to ZIP-316
P2PKH = 0x00
P2SH = 0x01
SAPLING = 0x02
ORCHARD = 0x03

receiver_length = {
	P2PKH: 20,
	P2SH: 20,
	SAPLING: 43,
	ORCHARD: 43
}

# prefixes for Unified Adresses
# source: https://zips.z.cash/zip-0316
U_PREFIXES = {
	"Zcash": "u",
	"Zcash Testnet": "utest"
}

def encode_p2pkh(raw_address: bytes, coin: CoinInfo) -> str:
	return base58.encode_check(
		address_type.tobytes(coin.address_type) + raw_address
	)

def padding(hrp: str) -> bytes:
	assert(len(hrp) <= 16)
	return bytes(hrp, "utf8") + bytes(16 - len(hrp))

def encode_unified(receivers: Dict[int, bytes], coin: CoinInfo) -> str:
	assert not (P2PKH in receivers and P2SH in receivers), "multiple transparent receivers"

	length = 16 # 16 bytes for padding
	for typecode in receivers.keys():
		length += 2 + receiver_length[typecode]

	w = empty_bytearray(length)

	# receivers in decreasing order
	receivers = list(receivers.items())
	receivers.sort(reverse=True)

	for (typecode, raw_bytes) in receivers:
		write_compact_size(w, typecode)
		write_compact_size(w, receiver_length[typecode])
		write_bytes_fixed(w, raw_bytes, receiver_length[typecode])

	hrp = U_PREFIXES[coin.coin_name]
	write_bytes_fixed(w, padding(hrp), 16)
	orchardlib.f4jumble(w)
	converted = convertbits(w, 8, 5)
	return bech32_encode(hrp, converted, Encoding.BECH32M)


def decode_unified(addr_str: str, coin: CoinInfo) -> Dict[int,bytes]:
	(hrp, data, encoding) = bech32_decode(addr_str, max_bech_len=1000)
	if (hrp, data, encoding) == (None, None, None):
		raise DataError("Bech32m decoding failed.")
	if hrp != U_PREFIXES[coin.coin_name]:
		raise DataError("Unexpected address prefix.")
	if encoding != Encoding.BECH32M:
		raise DataError("Bech32m encoding required.")

	decoded = bytearray(convertbits(data, 5, 8, False))
	orchardlib.f4jumble_inv(decoded)

	# check trailing padding bytes
	if decoded[-16:] != padding(hrp):
		raise DataError("Invalid unified address.")

	r = BufferReader(decoded[:-16])

	receivers = {}
	while r.remaining_count() > 0:
		typecode = read_compact_size(r)
		if typecode in receivers:
			raise DataError("Duplicated typecode")
		if typecode > 0x02000000:
			raise DataError("Invalid typecode")

		length = read_compact_size(r)
		expected_length = receiver_length.get(typecode)
		if expected_length is not None:
			if length != expected_length:
				raise DataError("Unexpected receiver length")

		if r.remaining_count() < length:
			raise DataError("Invalid receiver length")

		receivers[typecode] = r.read(length)

	return receivers
