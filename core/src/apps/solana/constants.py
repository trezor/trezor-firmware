from micropython import const

ADDRESS_SIZE = const(32)

SOLANA_BASE_FEE_LAMPORTS = const(5000)
SOLANA_COMPUTE_UNIT_LIMIT = const(200000)

# 1 lamport has 1M microlamports
MICROLAMPORTS_PER_LAMPORT = const(1000000)
