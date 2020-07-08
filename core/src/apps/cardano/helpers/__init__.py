from trezor import wire

INVALID_ADDRESS = wire.ProcessError("Invalid address")
NETWORK_MISMATCH = wire.ProcessError("Output address network mismatch!")
