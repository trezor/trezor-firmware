MAINNET = 764824073
TESTNET = 42

NAMES = {
    MAINNET: "Mainnet",
    TESTNET: "Testnet",
}


def to_ui_string(value: int) -> str:
    return NAMES.get(value, "Unknown")
