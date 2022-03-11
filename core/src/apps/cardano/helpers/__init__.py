from trezor import wire

INVALID_ADDRESS = wire.ProcessError("Invalid address")
INVALID_ADDRESS_PARAMETERS = wire.ProcessError("Invalid address parameters")
NETWORK_MISMATCH = wire.ProcessError("Output address network mismatch")
INVALID_TX_SIGNING_REQUEST = wire.ProcessError("Invalid tx signing request")
INVALID_INPUT = wire.ProcessError("Invalid input")
INVALID_OUTPUT = wire.ProcessError("Invalid output")
INVALID_CERTIFICATE = wire.ProcessError("Invalid certificate")
INVALID_WITHDRAWAL = wire.ProcessError("Invalid withdrawal")
INVALID_TOKEN_BUNDLE_OUTPUT = wire.ProcessError("Invalid token bundle in output")
INVALID_AUXILIARY_DATA = wire.ProcessError("Invalid auxiliary data")
INVALID_STAKE_POOL_REGISTRATION_TX_STRUCTURE = wire.ProcessError(
    "Stakepool registration transaction cannot contain other certificates, withdrawals or minting"
)
INVALID_STAKEPOOL_REGISTRATION_TX_WITNESSES = wire.ProcessError(
    "Stakepool registration transaction can only contain staking witnesses"
)
INVALID_WITNESS_REQUEST = wire.ProcessError("Invalid witness request")
INVALID_NATIVE_SCRIPT = wire.ProcessError("Invalid native script")
INVALID_TOKEN_BUNDLE_MINT = wire.ProcessError("Invalid mint token bundle")
INVALID_OUTPUT_DATUM_HASH = wire.ProcessError("Invalid output datum hash")
INVALID_SCRIPT_DATA_HASH = wire.ProcessError("Invalid script data hash")
INVALID_COLLATERAL_INPUT = wire.ProcessError("Invalid collateral input")
INVALID_REQUIRED_SIGNER = wire.ProcessError("Invalid required signer")

LOVELACE_MAX_SUPPLY = 45_000_000_000 * 1_000_000
INPUT_PREV_HASH_SIZE = 32
ADDRESS_KEY_HASH_SIZE = 28
SCRIPT_HASH_SIZE = 28
OUTPUT_DATUM_HASH_SIZE = 32
SCRIPT_DATA_HASH_SIZE = 32
