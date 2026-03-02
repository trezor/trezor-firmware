from micropython import const

# smart contract 'data' field lengths in bytes
SC_FUNC_SIG_BYTES = const(4)
SC_ARGUMENT_BYTES = const(32)
SC_ARGUMENT_ADDRESS_BYTES = const(20)
assert SC_ARGUMENT_ADDRESS_BYTES <= SC_ARGUMENT_BYTES
