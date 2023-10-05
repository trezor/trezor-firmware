from micropython import const

ADDRESS_SIZE = const(32)

ADDRESS_SIG = const(0)
ADDRESS_SIG_READ_ONLY = const(1)
ADDRESS_READ_ONLY = const(2)
ADDRESS_RW = const(3)

SOLANA_BASE_FEE_LAMPORTS    = const(5000)
SOLANA_CU_LIMIT             = const(200000)
