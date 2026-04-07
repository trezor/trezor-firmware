from micropython import const
from ubinascii import unhexlify

# smart contract 'data' field lengths in bytes
SC_FUNC_SIG_BYTES = const(4)
SC_ARGUMENT_BYTES = const(32)
SC_ARGUMENT_ADDRESS_BYTES = const(20)

assert SC_ARGUMENT_ADDRESS_BYTES <= SC_ARGUMENT_BYTES

# Known TRC-20/ERC-20 functions

SC_FUNC_SIG_TRANSFER = unhexlify("a9059cbb")
SC_FUNC_SIG_APPROVE = unhexlify("095ea7b3")
