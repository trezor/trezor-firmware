from micropython import const
from ubinascii import unhexlify
from typing import Any

# smart contract 'data' field lengths in bytes
SC_FUNC_SIG_BYTES = const(4)
SC_ARGUMENT_BYTES = const(32)

# staking operations function signatures
SC_FUNC_SIG_STAKE = unhexlify("3a29dbae")
SC_FUNC_SIG_UNSTAKE = unhexlify("76ec871c")
SC_FUNC_SIG_CLAIM = unhexlify("33986ffa")

# addresses for pool (stake/unstake) and accounting (claim) operations
ADDRESSES_POOL = (
    unhexlify("AFA848357154a6a624686b348303EF9a13F63264"),  # holesky testnet
    unhexlify("D523794C879D9eC028960a231F866758e405bE34"),  # mainnet
)
ADDRESSES_ACCOUNTING = (
    unhexlify("624087DD1904ab122A32878Ce9e933C7071F53B9"),  # holesky testnet
    unhexlify("7a7f0b3c23C23a31cFcb0c44709be70d4D545c6e"),  # mainnet
)


ERC20_FUNCTIONS_DEF: dict[bytes, dict[str, Any]] = {
    b"\xa9\x05\x9c\xbb": {
        "name": "transfer",
        "args": [
            ("Recipient", "address"),
            ("Amount", "int"),
        ],
        "transfer": (True, 1),
    },
    b"\x09\x5e\xa7\xb3": {
        "name": "approve",
        "args": [
            ("Address", "address"),
            ("Amount", "int"),
        ],
        "transfer": (False, 0),
    },
    b"\x00\x00\x00\x42": {
        "name": "args_test",
        "args": [
            ("Arg0_int", "int"),
            ("Arg1_str", "str"),
            ("Arg2_bytes", "bytes"),
            ("Arg3_address", "address"),
        ],
        "transfer": (False, 0),
        # TODO token to address assignment is done by additional entry, where:
        #   - 1st value is the idx of the value of a token
        #   - 2nd value is the idx of the address of the token -> to be used in the `definitions.get_token(addr)` call
        #   - if 1st == 2nd: token is assigned based on contract address
        # "token_assign": (0, 3),
    },
}
