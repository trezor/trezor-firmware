from typing import TYPE_CHECKING

from trezor.enums import MessageType

if TYPE_CHECKING:
    from buffer_types import AnyBytes
    from typing import Iterator, Tuple

    from trezor.messages import TronTransferContract

    TronMessageType = TronTransferContract

TYPE_URL_TEMPLATE = "type.googleapis.com/protocol."

# TODO: Use TypeVar like ethereum/keychain.py:MsgInSignTx
CONTRACT_TYPES = (
    MessageType.TronTransferContract,
    MessageType.TronTriggerSmartContract,
)

# https://github.com/tronprotocol/protocol/blob/37bb922a9967bbbef1e84de1c9e5cda56a2d7998/core/Tron.proto#L339-L379
CONTRACT_TYPE_NAMES = {
    1: "TransferContract",
    31: "TriggerSmartContract",
}


def get_contract_type_name(contract_type: int) -> str:
    """Get contract type name by its number."""
    if contract_type in CONTRACT_TYPE_NAMES:
        return CONTRACT_TYPE_NAMES[contract_type]
    raise ValueError(f"Unknown contract type: {contract_type}")


def token_iterator() -> Iterator[Tuple[AnyBytes, int, str]]:
    # https://shasta.tronscan.org/#/token20/TG3XXyExBkPp9nzdajDZsozEu4BkaSJozs
    yield (
        b"\x41\x42\xa1\xe3\x9a\xef\xa4\x92\x90\xf2\xb3\xf9\xed\x68\x8d\x7c\xec\xf8\x6c\xd6\xe0",
        6,
        "tUSDT",
    )
    # https://tronscan.org/#/token20/TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t
    yield (
        b"\x41\xa6\x14\xf8\x03\xb6\xfd\x78\x09\x86\xa4\x2c\x78\xec\x9c\x7f\x77\xe6\xde\xd1\x3c",
        6,
        "USDT",
    )
    # https://tronscan.org/#/token20/TXDk8mbtRbXeYuMNS83CfKPaYYT8XWv9Hz
    yield (
        b"\x41\xe9\x1a\x74\x11\xe5\x6c\xe7\x9e\x83\x57\x05\x70\xf4\x9b\x9f\xc3\x5b\x77\x27\xc5",
        18,
        "USDD",
    )
    # https://tronscan.org/#/token20/TSSMHYeV2uE9qYH95DqyoCuNCzEL1NvU3S
    yield (
        b"\x41\xb4\xa4\x28\xab\x70\x92\xc2\xf1\x39\x5f\x37\x6c\xe2\x97\x03\x3b\x3b\xb4\x46\xc1",
        18,
        "SUN",
    )
    # https://tronscan.org/#/token20/TCFLL5dx5ZJdKnWuesXxi1VPwjLVmWZZy9
    yield (
        b"\x41\x18\xfd\x06\x26\xda\xf3\xaf\x02\x38\x9a\xef\x3e\xd8\x7d\xb9\xc3\x3f\x63\x8f\xfa",
        18,
        "JST",
    )
    # https://tronscan.org/#/token20/TAFjULxiVgT4qWk6UZwjqwZXTSaGaqnVp4
    yield (
        b"\x41\x03\x20\x17\x41\x1f\x46\x63\xb3\x17\xfe\x77\xc2\x57\xd2\x8d\x5c\xd1\xb2\x6e\x3d",
        18,
        "BTT",
    )
    # https://tronscan.org/#/token20/TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7
    yield (
        b"\x41\x74\x47\x2e\x7d\x35\x39\x5a\x6b\x5a\xdd\x42\x7e\xec\xb7\xf4\xb6\x2a\xd2\xb0\x71",
        6,
        "WIN",
    )
    # https://tronscan.org/#/token20/TYhWwKpw43ENFWBTGpzLHn3882f2au7SMi
    yield (
        b"\x41\xf9\x53\x35\xa4\xd4\x2d\xb4\xb7\x0a\x96\x88\xa3\x93\x27\x9f\x2c\x90\xfa\x10\x25",
        8,
        "WBTC",
    )
    # https://tronscan.org/#/token20/THb4CqiFdwNHsWsQCs4JhzwjMWys4aqCbF
    yield (
        b"\x41\x53\x90\x83\x08\xf4\xaa\x22\x0f\xb1\x0d\x77\x8b\x5d\x1b\x34\x48\x9c\xd6\xed\xfc",
        18,
        "ETH(Tron)",
    )
    # https://tronscan.org/#/token20/TPFqcBAaaUMCSVRCqPaQ9QnzKhmuoLR6Rc
    yield (
        b"\x41\x91\xbe\xd8\xe7\x84\x24\x9c\x91\x61\x1e\x61\xc4\x58\x5c\x40\xe2\x1f\xd0\xac\xe2",
        18,
        "USD1",
    )
    # https://tronscan.org/#/token20/TUPM7K8REVzD2UdV4R5fe5M8XbnR2DdoJ6
    yield (
        b"\x41\xca\x03\x03\xe8\xb9\xa7\x38\x12\x17\x77\x11\x6d\xce\xa4\x19\xfe\x52\x4f\x27\x1a",
        18,
        "HTX",
    )
    # https://tronscan.org/#/token20/TUpMhErZL2fhh4sVNULAbNKLokS4GjC1F4
    yield (
        b"\x41\xce\xbd\xe7\x10\x77\xb8\x30\xb9\x58\xc8\xda\x17\xbc\xdd\xee\xb8\x5d\x0b\xcf\x25",
        18,
        "TUSD",
    )
