from trezor import wire

INVALID_DERIVATION_PATH = wire.ProcessError("Invalid derivation path")
INVALID_ADDRESS = wire.ProcessError("Invalid address")
NETWORK_MISMATCH = wire.ProcessError("Output address network mismatch!")
INVALID_CERTIFICATE = wire.ProcessError("Invalid certificate")
INVALID_WITHDRAWAL = wire.ProcessError("Invalid withdrawal")
INVALID_METADATA = wire.ProcessError("Invalid metadata")
INVALID_STAKE_POOL_REGISTRATION_TX_STRUCTURE = wire.ProcessError(
    "Stakepool registration transaction cannot contain other certificates nor withdrawals"
)
INVALID_STAKEPOOL_REGISTRATION_TX_INPUTS = wire.ProcessError(
    "Stakepool registration transaction can contain only external inputs"
)
INVALID_SHELLEY_ADDRESS_PATH = wire.ProcessError("Invalid path for shelley address!")
INVALID_BYRON_ADDRESS_PATH = wire.ProcessError("Invalid path for byron address!")


LOVELACE_MAX_SUPPLY = 45_000_000_000 * 1_000_000
