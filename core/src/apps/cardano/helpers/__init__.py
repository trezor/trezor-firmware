from trezor import wire

INVALID_ADDRESS = wire.ProcessError("Invalid address")
NETWORK_MISMATCH = wire.ProcessError("Output address network mismatch!")
INVALID_CERTIFICATE = wire.ProcessError("Invalid certificate")
INVALID_WITHDRAWAL = wire.ProcessError("Invalid withdrawal")
INVALID_METADATA = wire.ProcessError("Invalid metadata")
