from micropython import const

ADDRESS_SIZE = const(32)

SOLANA_BASE_FEE_LAMPORTS = const(5000)
SOLANA_COMPUTE_UNIT_LIMIT = const(200000)

SOLANA_RENT_EXEMPTION_MULTIPLIER = const(2)
# NOTE: this is a hard-coded network parameter,
#       it CAN change in the future
SOLANA_RENT_PER_BYTE_EPOCH = const(3480)

SOLANA_ACCOUNT_METADATA_SIZE = const(128)
SOLANA_ASSOCIATED_TOKEN_ACCOUNT_SIZE = const(165)
