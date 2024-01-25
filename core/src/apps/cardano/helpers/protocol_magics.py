from micropython import const

from trezor import TR

# https://book.world.dev.cardano.org/environments.html
MAINNET = const(764824073)
TESTNET_PREPROD = const(1)
TESTNET_PREVIEW = const(2)
TESTNET_LEGACY = const(1097911063)

NAMES = {
    MAINNET: "Mainnet",
    TESTNET_PREPROD: "Preprod Testnet",
    TESTNET_PREVIEW: "Preview Testnet",
    TESTNET_LEGACY: "Legacy Testnet",
}


def is_mainnet(protocol_magic: int) -> bool:
    return protocol_magic == MAINNET


def to_ui_string(value: int) -> str:
    return NAMES.get(value, TR.words__unknown)
