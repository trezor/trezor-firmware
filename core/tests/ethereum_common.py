from typing import Iterator
from trezor.utils import ensure
from ubinascii import hexlify, unhexlify  # noqa: F401

from trezor import messages
from apps.ethereum import tokens


EXPECTED_FORMAT_VERSION = 1
EXPECTED_DATA_VERSION = 1663054984 # unix epoch time

class InfoWithDefinition():
    def __init__(self, definition: bytes | None, info: messages.EthereumNetworkInfo | messages.EthereumTokenInfo):
        self.definition = definition
        self.info = info


# definitions created by `common/tools/ethereum_definitions.py` and copied here
NETWORKS = {
    # chain_id: network info with encoded definition
    # Ethereum
    1: InfoWithDefinition(
        definition=None, # built-in definitions are not encoded
        info=messages.EthereumNetworkInfo(
            chain_id=1,
            slip44=60,
            shortcut="ETH",
            name="Ethereum",
        ),
    ),
    # Rinkeby
    4: InfoWithDefinition(
        definition=unhexlify("74727a643100000000632034880015080410011a047452494e220752696e6b65627928000e8cc47ed4e657d9a9b98e1dd02164320c54a9724e17f91d1d79f6760169582c98ec70ca6f4e94d27e574175c59d2ae04e0cd30b65fb19acd8d2c5fb90bcb7db96f6102e4182c0cef5f412ac3c5fa94f9505b4df2633a0f7bdffa309588d722415624adeb8f329b1572ff9dfc81fbc86e61f1fcb2369f51ba85ea765c908ac254ba996f842a6277583f8d02f149c78bc0eeb8f3d41240403f85785dc3a3925ea768d76aae12342c8a24de223c1ea75e5f07f6b94b8f22189413631eed3c9a362b4501f68b645aa487b9d159a8161404a218507641453ebf045cec56710bb7d873e102777695b56903766e1af16f95576ec4f41874bdaf80cec02ee067d30e721515564d4f30fa74a6c61eb784ea65cc881ead7af2ffac02d5bf1fe1a756918fe37b74828a24b640025cd79443ada60063e3034444fc49ed6055dbba6a09fa4484c42cb85abb49103dc8c781c8f190c4632e2dec30081770448021313955dbb49e8a02fd49b34d030280452fe0a5c3bcba4958bc287c67e12519be4f4aec7ab0c8e574e53a663f635f75508f23d92c77b2147f29feb79c38d0f793fba295aae605c7e8226523edefc6ad1eefe088e5b8376028bf90116ece4fb876510b4ae1c89686dbcaacbbac8225baba429ca376fafac50f4bd1ff4ce1c61dd53318d0718bf513ea6f770cce81e07a653622e4dbd03bdaa570bfe43219eb0d4fab725c9a8da04"),
        info=messages.EthereumNetworkInfo(
            chain_id=4,
            slip44=1,
            shortcut="tRIN",
            name="Rinkeby",
        ),
    ),
    # Ubiq
    8: InfoWithDefinition(
        definition=unhexlify("74727a6431000000006320348800110808106c1a0355425122045562697128000e5641d82e3622b4e6addd4354efd933cf15947d1d608a60d324d1156b5a4999f70c41beb85bd866aa3059123447dfeef2e1b6c009b66ac8d04ebbca854ad30049edbbb2fbfda3bfedc6fdb4a76f1db8a4f210bd89d3c3ec1761157b0ec2b13e2f624adeb8f329b1572ff9dfc81fbc86e61f1fcb2369f51ba85ea765c908ac254ba996f842a6277583f8d02f149c78bc0eeb8f3d41240403f85785dc3a3925ea768d76aae12342c8a24de223c1ea75e5f07f6b94b8f22189413631eed3c9a362b4501f68b645aa487b9d159a8161404a218507641453ebf045cec56710bb7d873e102777695b56903766e1af16f95576ec4f41874bdaf80cec02ee067d30e721515564d4f30fa74a6c61eb784ea65cc881ead7af2ffac02d5bf1fe1a756918fe37b74828a24b640025cd79443ada60063e3034444fc49ed6055dbba6a09fa4484c42cb85abb49103dc8c781c8f190c4632e2dec30081770448021313955dbb49e8a02fd49b34d030280452fe0a5c3bcba4958bc287c67e12519be4f4aec7ab0c8e574e53a663f635f75508f23d92c77b2147f29feb79c38d0f793fba295aae605c7e8226523edefc6ad1eefe088e5b8376028bf90116ece4fb876510b4ae1c89686dbcaacbbac8225baba429ca376fafac50f4bd1ff4ce1c61dd53318d0718bf513ea6f770cce81e07a653622e4dbd03bdaa570bfe43219eb0d4fab725c9a8da04"),
        info=messages.EthereumNetworkInfo(
            chain_id=8,
            slip44=108,
            shortcut="UBQ",
            name="Ubiq",
        ),
    ),
    # Ethereum Classic
    61: InfoWithDefinition(
        definition=unhexlify("74727a64310000000063203488001d083d103d1a034554432210457468657265756d20436c617373696328000e6b891a57fe4c38c54b475f22f0d9242dd8ddab0b4f360bd86e37e2e8b79de5ef29237436351f7bc924cd110716b5adde7c28c03d76ac83b091dbce1b5d7d0edbddb221bd894806f7ea1b195443176e06830a83c0204e33f19c51d2fccc3a9f80ac2cca38822db998ddf76778dada240d39b3c6193c6335d7c693dea90d19a41f86855375c2f48c18cdc012ccac771aa316d776c8721c2b1f6d5980808337dfdae13b5be07e3cbc3526119b88c5eb44be0b1dab1094a5ec5215b47daf91736d16501f68b645aa487b9d159a8161404a218507641453ebf045cec56710bb7d873e102777695b56903766e1af16f95576ec4f41874bdaf80cec02ee067d30e721515564d4f30fa74a6c61eb784ea65cc881ead7af2ffac02d5bf1fe1a756918fe37b74828a24b640025cd79443ada60063e3034444fc49ed6055dbba6a09fa4484c42cb85abb49103dc8c781c8f190c4632e2dec30081770448021313955dbb49e8a02fd49b34d030280452fe0a5c3bcba4958bc287c67e12519be4f4aec7ab0c8e574e53a663f635f75508f23d92c77b2147f29feb79c38d0f793fba295aae605c7e8226523edefc6ad1eefe088e5b8376028bf90116ece4fb876510b4ae1c89686dbcaacbbac8225baba429ca376fafac50f4bd1ff4ce1c61dd53318d0718bf513ea6f770cce81e07a653622e4dbd03bdaa570bfe43219eb0d4fab725c9a8da04"),
        info=messages.EthereumNetworkInfo(
            chain_id=61,
            slip44=61,
            shortcut="ETC",
            name="Ethereum Classic",
        ),
    ),
}


SLIP44_TO_CHAIN_ID_MAP = {
    1: [4],
    60: [1],
    61: [61],
    108: [8],
}


# definitions created by `common/tools/ethereum_definitions.py` and copied here
TOKENS = {
    # chain_id: { address: token info with encoded definition, address: token info with encoded definition,... }
    1: {
        # AAVE
        "7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9": InfoWithDefinition(
            definition=None, # built-in definitions are not encoded
            info=messages.EthereumTokenInfo(
                symbol="AAVE",
                decimals=18,
                address=unhexlify("7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9"),
                chain_id=1,
                name="Aave",
            ),
        ),
        # TrueAUD
        "00006100f7090010005f1bd7ae6122c3c2cf0090": InfoWithDefinition(
            definition=unhexlify("74727a6431000000016320348800290a045441554410121a1400006100f7090010005f1bd7ae6122c3c2cf009020012a07547275654155440e310dad13f7d3012903a9a457134c9f38c62c04370cb92c7a528838e30a032dffbceeaa2aa849e590c4e6dbc69b0ea5359f3527b95b56ab59a33dc584105b35ea7c06afc296cc1c1e58cc3d6b461631c4c770b9409837ab3d29bc1b666fb9cf5245c4c218b0e9521c185d102f596905ba860e6f56a0a8b394f943855c74eea6fcac87210a9988ac02803f4cc61cf78e7e2409175a75f4f3a82eb84b1f2d1ea8177d5dccd62949d80d7942105e22a452be01859fe816736e803b120fb9bcc0c1117180dbda19e1ad1aafb9b9f1555c75275820bf7c1e568bcb265bdc4dfdae0511782026e11a151f6894d11128327c8c42958c9ae900af970fec13a11ffdeba6ac10733ca55a906142e0b9130312e8e85606108612581aca9087c452f38f14185db74828a24b640025cd79443ada60063e3034444fc49ed6055dbba6a09fa4484c42cb85abb49103dc8c781c8f190c4632e2dec30081770448021313955dbb49e8a02fd49b34d030280452fe0a5c3bcba4958bc287c67e12519be4f4aec7ab0c8e574e53a663f635f75508f23d92c77b2147f29feb79c38d0f793fba295aae605c7e8226523edefc6ad1eefe088e5b8376028bf90116ece4fb876510b4ae1c89686dbcaacbbac8225baba429ca376fafac50f4bd1ff4ce1c61dd53318d0718bf513ea6f770cce81e07a653622e4dbd03bdaa570bfe43219eb0d4fab725c9a8da04"),
            info=messages.EthereumTokenInfo(
                symbol="TAUD",
                decimals=18,
                address=unhexlify("00006100f7090010005f1bd7ae6122c3c2cf0090"),
                chain_id=1,
                name="TrueAUD",
            ),
        ),
    },
    4: {
        # Karma Token
        "275a5b346599b56917e7b1c9de019dcf9ead861a": InfoWithDefinition(
            definition=unhexlify("74727a64310000000163203488002b0a024b4310121a14275a5b346599b56917e7b1c9de019dcf9ead861a20042a0b4b61726d6120546f6b656e0e2b3cb176ff5a2cf431620c1a7eee9aa297f5de36d29ae6d423166cf7391e41c5826c57f30b11421a4bf10f336f12050f6d959e02bfb17a8ce7ae15087d4f083124c0cebed2ce45b15b2608b1a8f0ee443e8c4f33111d880a6a3c09a77c627f82d68b62a1bd39975b2a2c86f196b9a3dcb62bdc3554fbf85b75331bc0d39f23a46f5ed91f208757d1136bb20b3618294fbfb0a826e9c09e392fe8109181bc6c28cad78db1987947f461bfc1042b88a91d6d61297d0cf194dfeea981b4515c2ed09dc2966671f5c715c64ceb25e53e1df3c7234e3e0ddf0dcd54d40fde0c51903685f9dc7fa69c71184f17af852e74490ea7286e89a0aa4770629664f7dd8eab8c4e009ff4c24682f85f7e01d4e10ae5c06212d5a4f43bac2b4f0e79383666ef12054ddbf757809aa6b446d65f7fd1bdd76fb1d7770398bd17af50635027e680801d244bd7b4f14c57edc3cd961722315e076120bf1d35db8520edb812bfbb5bab8ff57cc2dc1b3d1f9d95b33dba5d759aef1123f2ef346b6328973fba204fd745e644c8e492f9a76c0019b2cf21715fba682b46b9c58013e0b0927e5272c808a67e8226523edefc6ad1eefe088e5b8376028bf90116ece4fb876510b4ae1c89686dbcaacbbac8225baba429ca376fafac50f4bd1ff4ce1c61dd53318d0718bf513ea6f770cce81e07a653622e4dbd03bdaa570bfe43219eb0d4fab725c9a8da04"),
            info=messages.EthereumTokenInfo(
                symbol="KC",
                decimals=18,
                address=unhexlify("275a5b346599b56917e7b1c9de019dcf9ead861a"),
                chain_id=4,
                name="Karma Token",
            ),
        ),
    },
}


def construct_network_info(chain_id: int = 0, slip44: int = 0, shortcut: str = "", name: str = "") -> messages.EthereumNetworkInfo:
    return messages.EthereumNetworkInfo(
        chain_id=chain_id,
        slip44=slip44,
        shortcut=shortcut,
        name=name,
    )


def construct_token_info(
        symbol: str = "",
        decimals: int = 0,
        address: bytes = b'',
        chain_id: int = 0,
        name: str = "",
    ) -> messages.EthereumTokenInfo:
    return messages.EthereumTokenInfo(
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


def builtin_networks_iterator() -> Iterator[messages.EthereumNetworkInfo]:
    """Mockup function replaces original function from core/src/apps/ethereum/networks.py used to get built-in network definitions."""
    for _, network in NETWORKS.items():
        if network.definition is None:
            yield network.info


def builtin_token_by_chain_address(chain_id: int, address: bytes) -> messages.EthereumTokenInfo:
    """Mockup function replaces original function from core/src/apps/ethereum/tokens.py used to get built-in token definitions."""
    address_str = hexlify(address).decode('hex')
    try:
        if TOKENS[chain_id][address_str].definition is None:
            return TOKENS[chain_id][address_str].info
    except KeyError:
        pass

    return tokens.UNKNOWN_TOKEN
