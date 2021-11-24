from trezor.crypto.bech32 import bech32_encode, bech32_decode, convertbits, Encoding
from trezor.crypto import base58

from trezor.utils import BufferReader, empty_bytearray
from apps.common.readers import read_bitcoin_varint
from apps.common.writers import write_bitcoin_varint, write_bytes_fixed

from trezor.crypto import zcash

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

# coin_type according to SLIP-44
MAINNET = 133
TESTNET = 1
# coin types for Zcash and Zcash-Testnet
SLIP44_ZCASH_COIN_TYPES = (MAINNET, TESTNET)

receiver_length = {
	P2PKH: 20,
	P2SH: 20,
	SAPLING: 43,
	ORCHARD: 43	
}

# transparent P2PKH prefixes
# source: https://zips.z.cash/protocol/protocol.pdf § 5.6.1.1
T_PREFIX = {
    MAINNET: bytes([0x1c, 0xb8]), # t1
    TESTNET: bytes([0x1d, 0x25])  # tm  
}

# prefixes for Unified Adresses
# source: https://zips.z.cash/zip-0032
U_PREFIX = {
	MAINNET: "u",
	TESTNET: "utest"
}

def encode_transparent(raw_address: bytes, network_type=MAINNET: int) -> str:
	return base58.encode_check(T_PREFIX[network_type] + raw_address)

def padding(hrp: str) -> bytes:
	assert(len(hrp) <= 16)
	return bytes(hrp, "utf8") + bytes(16 - len(hrp))

def encode_unified(receivers: Dict[int,bytes], network_type=MAINNET: int) -> str:
	assert not (P2PKH in receivers and P2SH in receivers), "multiple transparent receivers"

	length = 16 # 16 bytes for padding
	for typecode in receivers.keys(): 
		length += 2 + receiver_length[typecode]

	w = empty_bytearray(length)

	# receivers in decreasing order
	receivers = list(receivers.items())
	receivers.sort(reverse=True)

	for (typecode, raw_bytes) in receivers:
		write_bitcoin_varint(w, typecode)
		write_bitcoin_varint(w, receiver_length[typecode])
		write_bytes_fixed(w, raw_bytes, receiver_length[typecode])		

	hrp = U_PREFIX[network_type]
	write_bytes_fixed(w, padding(hrp), 16)
	zcash.f4jumble(w)
	converted = convertbits(w, 8, 5)
	return bech32_encode(hrp, converted, Encoding.BECH32M)

def decode_unified(addr_str: str) -> Dict[int,bytes]:
	# TODO: validation of receivers' encodings
	(hrp, data, encoding) = bech32_decode(addr_str, max_bech_len=1000)
	assert (hrp, data, encoding) != (None, None, None), "Bech32m decoding failed"
	assert hrp != "utest", "testnet not supported"
	assert hrp == "u", "unknown prefix"
	assert encoding == Encoding.BECH32M, "Bech32m encoding required"

	decoded = bytearray(convertbits(data, 5, 8, False))
	zcash.f4jumble_inv(decoded)

	# check trailing padding bytes
	assert decoded[-16:] == padding(hrp)
	r = BufferReader(decoded[:-16])

	receivers = {}
	while r.remaining_count() > 0:
		typecode = read_bitcoin_varint(r)
		assert not typecode in receivers, "duplicated typecode"
		assert typecode <= 0x02000000, "invalid typecode"

		length = read_bitcoin_varint(r)
		expected_length = receiver_length.get(typecode)
		if expected_length is not None:
			assert length == expected_length #, "incorrect receiver length"

		assert r.remaining_count() >= length
		receivers[typecode] = r.read(length)

	return receivers