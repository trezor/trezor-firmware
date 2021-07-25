from trezor import wire

INVALID_ADDRESS = wire.ProcessError("Invalid address")
INVALID_ADDRESS_PARAMETERS = wire.ProcessError("Invalid address parameters")
NETWORK_MISMATCH = wire.ProcessError("Output address network mismatch")
INVALID_CERTIFICATE = wire.ProcessError("Invalid certificate")
INVALID_WITHDRAWAL = wire.ProcessError("Invalid withdrawal")
INVALID_TOKEN_BUNDLE_OUTPUT = wire.ProcessError("Invalid token bundle in output")
INVALID_AUXILIARY_DATA = wire.ProcessError("Invalid auxiliary data")
INVALID_STAKE_POOL_REGISTRATION_TX_STRUCTURE = wire.ProcessError(
    "Stakepool registration transaction cannot contain other certificates nor withdrawals"
)
INVALID_STAKEPOOL_REGISTRATION_TX_INPUTS = wire.ProcessError(
    "Stakepool registration transaction can contain only external inputs"
)

LOVELACE_MAX_SUPPLY = 45_000_000_000 * 1_000_000
ADDRESS_KEY_HASH_SIZE = 28
