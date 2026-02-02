from micropython import const
from ubinascii import unhexlify

# smart contract 'data' field lengths in bytes
SC_FUNC_SIG_BYTES = const(4)
SC_ARGUMENT_BYTES = const(32)
SC_ARGUMENT_ADDRESS_BYTES = const(20)
SC_FUNC_APPROVE_REVOKE_AMOUNT = const(0)

assert SC_ARGUMENT_ADDRESS_BYTES <= SC_ARGUMENT_BYTES

# Known ERC-20 functions

SC_FUNC_SIG_TRANSFER = unhexlify("a9059cbb")
SC_FUNC_SIG_APPROVE = unhexlify("095ea7b3")
SC_FUNC_SIG_STAKE = unhexlify("3a29dbae")
SC_FUNC_SIG_UNSTAKE = unhexlify("76ec871c")
SC_FUNC_SIG_CLAIM = unhexlify("33986ffa")
