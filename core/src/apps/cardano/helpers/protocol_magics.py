MAINNET = 764824073
TESTNET = 42

NAMES = {
    MAINNET: "Mainnet",
    TESTNET: "Testnet",
}


def is_mainnet(protocol_magic: int) -> bool:
    return protocol_magic == MAINNET


def to_ui_string(value: int) -> str:
    return NAMES.get(value, "Unknown")
