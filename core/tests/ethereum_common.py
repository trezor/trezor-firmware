from trezor.utils import ensure
from ubinascii import unhexlify  # noqa: F401

from trezor import messages
from apps.ethereum import networks, tokens


EXPECTED_FORMAT_VERSION = 1
EXPECTED_DATA_VERSION = 1657791892 # unix epoch time Thu Jul 14 2022 09:44:52 GMT+0000

class InfoWithDefinition():
    def __init__(self, definition, info):
        self.definition = definition
        self.info = info


# definitions created by `common/tools/cointool.py` and copied here
NETWORKS = {
    # chain_id: network info with encoded definition
    # Ethereum
    1: InfoWithDefinition(
        definition=unhexlify("74727a64310000000062d6384d0801103c1a034554482208457468657265756d28003342fb0073eb26285e8b50f402a346fee0d37b98721c516d13864043e54d7e33e31d82004024495138bc72b946b080f5d319ea41c8ba53aaffbf7988419f860e"),
        info=networks.NetworkInfo(
            chain_id=1,
            slip44=60,
            shortcut="ETH",
            name="Ethereum",
            rskip60=False,
        ),
    ),
    # Expanse
    2: InfoWithDefinition(
        definition=unhexlify("74727a64310000000062d6384d080210281a03455850220f457870616e7365204e6574776f726b2800b5f8aba1a056398b340fc16d66ca845db1cbd258cb1a560b6d1d227655ff1c88cd785a3005c31cc2a1da3b20edc69c09d470d0ebabb19f52e3cfb7139dac9104"),
        info=networks.NetworkInfo(
            chain_id=2,
            slip44=40,
            shortcut="EXP",
            name="Expanse Network",
            rskip60=False,
        ),
    ),
    # Ubiq
    8: InfoWithDefinition(
        definition=unhexlify("74727a64310000000062d6384d0808106c1a035542512204556269712800505661237b6e6c5ff7a7b4b6e9f5d6dbf70055507bb6ca48e1260e76a2a01a1788038d80588d643da576183842d6367d7f1c9fefc15d56fd8b15ee8f1165bb0c"),
        info=networks.NetworkInfo(
            chain_id=8,
            slip44=108,
            shortcut="UBQ",
            name="Ubiq",
            rskip60=False,
        ),
    ),
    # Ethereum Classic
    61: InfoWithDefinition(
        definition=unhexlify("74727a64310000000062d6384d083d103d1a034554432210457468657265756d20436c61737369632800095cb5be721429440fd9856d7c35acc7751c9cb1d006189a78f5693654b36c39bb4ab5add8d5cd6af3c345a8aa20307f79567c78c4f5940e3f16221a0c5bd30f"),
        info=networks.NetworkInfo(
            chain_id=61,
            slip44=61,
            shortcut="ETC",
            name="Ethereum Classic",
            rskip60=False,
        ),
    ),
}
SLIP44_TO_CHAIN_ID_MAP = {
    40: [2],
    60: [1],
    61: [61],
    108: [8],
}


# definitions created by `common/tools/cointool.py` and copied here
TOKENS = {
    # chain_id: { address: token info with encoded definition, address: token info with encoded definition,... }
    1: {
        # AAVE
        "7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9": InfoWithDefinition(
            definition=unhexlify("74727a64310000000162d6384d0a044141564510121a147fc66500c84a76ad7e9c93437bfc5ac33e2ddae920012a04416176652d5458fe6726f8dfad0af3d1bd0959199da25dba4f429c14517f54acdd4b4117b676f7467bb34fe9a64dbd95d1a875085774df7b30fdf09f0b33f4e52b2d900b"),
            info=tokens.TokenInfo(
                symbol="AAVE",
                decimals=18,
                address=unhexlify("7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9"),
                chain_id=1,
            ),
        ),
    },
    61: {
        # BEC
        "085fb4f24031eaedbc2b611aa528f22343eb52db": InfoWithDefinition(
            definition=unhexlify("74727a64310000000162d68cd70a0342454310081a14085fb4f24031eaedbc2b611aa528f22343eb52db203d2a03424543194264a2b334a93b8592997d311d65f1e0840c150eab051fd93cce8997d5200705e5d256abfcdd3c7b68fc5c72ebe6e32c5205d8f60c47d0986d313a4a92c80a"),
            info=tokens.TokenInfo(
                symbol="BEC",
                decimals=8,
                address=unhexlify("085fb4f24031eaedbc2b611aa528f22343eb52db"),
                chain_id=61,
            ),
        ),
    },
}


def equalNetworkInfo(n1: networks.NetworkInfo, n2: networks.NetworkInfo, msg: str = '') -> bool:
    ensure(
        cond=(
            n1.chain_id == n2.chain_id
            and n1.slip44 == n2.slip44
            and n1.shortcut == n2.shortcut
            and n1.name == n2.name
            and n1.rskip60 == n2.rskip60
        ),
        msg=msg,
    )


def equalTokenInfo(t1: tokens.TokenInfo, t2: tokens.TokenInfo, msg: str = '') -> bool:
    ensure(
        cond=(
            t1.symbol == t2.symbol
            and t1.decimals == t2.decimals
            and t1.address == t2.address
            and t1.chain_id == t2.chain_id
        ),
        msg=msg,
    )


def construct_network_info(chain_id: int = 0, slip44: int = 0, shortcut: str = "", name: str = "", rskip60: bool = False) -> networks.NetworkInfo:
    return networks.NetworkInfo(
        chain_id=chain_id,
        slip44=slip44,
        shortcut=shortcut,
        name=name,
        rskip60=rskip60,
    )


def construct_token_info(
        symbol: str = "",
        decimals: int = 0,
        address: bytes = b'',
        chain_id: int = 0,
        name: str = "",
    ) -> tokens.TokenInfo:
    return tokens.TokenInfo(
        symbol=symbol,
        decimals=decimals,
        address=address,
        chain_id=chain_id,
        name=name,
    )


def get_ethereum_network_info_with_definition(chain_id: int | None = None, slip44: int | None = None) -> InfoWithDefinition | None:
    def slip44_to_chain_ids() -> list:
        return SLIP44_TO_CHAIN_ID_MAP.get(slip44, [])

    # resolve network
    if chain_id is not None:
        if slip44 is not None and chain_id not in slip44_to_chain_ids():
            raise ValueError("Chain ID and slip44 are incompatible")
        return NETWORKS.get(chain_id)
    elif slip44 is not None:
        cid = slip44_to_chain_ids()
        if cid is not None:
            return NETWORKS.get(cid[0])


def get_ethereum_token_info_with_definition(chain_id: int, token_address: str = None) -> InfoWithDefinition | None:
    if chain_id is None:
        return None

    if token_address is None:
        # if we do not have address, get any of the tokens
        token_address = list(TOKENS[chain_id].keys())[0]

    return TOKENS[chain_id][token_address]


def get_ethereum_encoded_network_definition(chain_id: int | None = None, slip44: int | None = None) -> bytes | None:
    network_info = get_ethereum_network_info_with_definition(chain_id, slip44)
    return network_info.definition if network_info is not None else None


def get_ethereum_encoded_definition(chain_id: int | None = None, slip44: int | None = None, token_address: str | None = None) -> messages.EthereumEncodedDefinitions:
    return messages.EthereumEncodedDefinitions(
        encoded_network=get_ethereum_encoded_network_definition(chain_id, slip44),
        encoded_token=None, # TODO
    )
