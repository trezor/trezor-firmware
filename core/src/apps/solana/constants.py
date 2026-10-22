from micropython import const

ADDRESS_SIZE = const(32)

SOLANA_BASE_FEE_LAMPORTS = const(5000)

# Default compute unit limit, if not set by the transaction:
# https://github.com/anza-xyz/agave/blob/a203300045b405f86c9c84308b2eae76af69ac3b/compute-budget-instruction/src/compute_budget_instruction_details.rs#L196-L219
SOLANA_BUILTIN_INSTRUCTION_COMPUTE_UNIT_LIMIT = const(3000)
SOLANA_DEFAULT_INSTRUCTION_COMPUTE_UNIT_LIMIT = const(200000)
SOLANA_MAX_COMPUTE_UNIT_LIMIT = const(1400000)
# Builtins may become non-builtins, so only the recognized ones are listed:
# https://github.com/anza-xyz/agave/blob/a203300045b405f86c9c84308b2eae76af69ac3b/builtins-default-costs/src/lib.rs#L108-L120
SOLANA_BUILTIN_PROGRAM_IDS = (
    "11111111111111111111111111111111",  # System
    "ComputeBudget111111111111111111111111111111",
)

# 1 lamport has 1M microlamports
MICROLAMPORTS_PER_LAMPORT = const(1000000)

# Rent exemption is granted after two years of rent
SOLANA_RENT_EXEMPTION_YEARS = const(2)
# NOTE: this is a hard-coded network parameter,
#       it CAN change in the future
SOLANA_RENT_LAMPORTS_PER_BYTE_YEAR = const(3480)

# Size of a Token account
# https://github.com/solana-program/token/blob/08aa3ccecb30692bca18d6f927804337de82d5ff/program/src/state.rs#L134
SOLANA_TOKEN_ACCOUNT_SIZE = const(165)
# Max size of a Token22 account
# https://github.com/solana-program/token-2022/blob/d9cfcf32cf5fbb3ee32f9f873d3fe3c94356e981/program/src/extension/mod.rs#L1299
SOLANA_TOKEN22_MAX_ACCOUNT_SIZE = const(195)
# Each Solana account has a 128 bytes overhead
SOLANA_ACCOUNT_OVERHEAD_SIZE = const(128)
