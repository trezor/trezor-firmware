from ubinascii import unhexlify  # noqa: F401

from trezor import messages


EXPECTED_FORMAT_VERSION = 1
EXPECTED_DATA_VERSION = 1663054984 # unix epoch time

class InfoWithDefinition():
    def __init__(self, definition: bytes | None, info: messages.EthereumNetworkInfo | messages.EthereumTokenInfo):
        self.definition = definition
        self.info = info


# definitions created by `common/tools/ethereum_definitions.py` and copied here
NETWORKS = {
    # chain_id: network info with encoded definition
    1: InfoWithDefinition(
        definition=unhexlify("74727a643100634ff57f00130801103c1a034554482208457468657265756d0ebd90de8446200230eaddb1dd542272e6f1abeffe77eaa54d1e2584249cb70d1def1342b6085111c5fef26566f9e482a33b8edb6e4cc4bd7c01d45b0a043d66d4845643ceb579306f39820874d66bef280620f7b42979889f4c95abf461d2c38312fd9416e0d8fb524bc4be7389ff7d6624a1ab2d7b69c0aa3d1fdac5b7cdf7bf748f08f6b8c8ef8c095d79c79c3ecf45a2514da6b40cf663fd576c0035af1385cf738e0f8c3249935b363ce61702fd9f4604f4036c7b8f78f6371531334bcca5fde4ba3f8535a86bb92fd9a6d195085969c6137906a136df04186321182196222ee9fe72f5062c761df397a438296625fbcd3da1b3ca257612a0a5a4a8b0bb750e4fdf0fc1346af487421fcce838a3853e6f7e4c87388281dfa9ebd018c20af0655213c9e2f6501236b26566ff0762e2fc33133068720d95523c481dec966d5b520010b01a1011fdd8c21954d005db9c10957273adccf39cddf5dd43366fb2a6cb18691c8849cb82519e79cf0c9b9ad77cf8c48e994c61e99caa7bc01a361dd755a48d9742549a02e5b12a97e1b4fe1d3cde3652d4de30d46c86f999a4a5072aa86a9ca6ecaa0344c96f1e673654db09da221b22ed4d4018ba3bd0c23ecd4344055e4521fabb0b79faa9a638c8652c8a18f429d60bbfa462a8305506ca7894be5a8abec4f1c2a003b75f061f26c683df02b72d5196815e410e09ce275df6650a"),
        info=messages.EthereumNetworkInfo(
            chain_id=1,
            slip44=60,
            shortcut="ETH",
            name="Ethereum",
        ),
    ),
    4: InfoWithDefinition(
        definition=unhexlify("74727a643100634ff57f0013080410011a047452494e220752696e6b6562790e4585ee14bf04be31e484fbdbf33fa091f4b164cd9c1440e2ac777227bab903376f8425cf7a1443f71d24c5b10129d04d73195894c1ae1d059cd53463e8a994a9845643ceb579306f39820874d66bef280620f7b42979889f4c95abf461d2c38312fd9416e0d8fb524bc4be7389ff7d6624a1ab2d7b69c0aa3d1fdac5b7cdf7bf748f08f6b8c8ef8c095d79c79c3ecf45a2514da6b40cf663fd576c0035af1385cf738e0f8c3249935b363ce61702fd9f4604f4036c7b8f78f6371531334bcca5fde4ba3f8535a86bb92fd9a6d195085969c6137906a136df04186321182196222ee9fe72f5062c761df397a438296625fbcd3da1b3ca257612a0a5a4a8b0bb750e4fdf0fc1346af487421fcce838a3853e6f7e4c87388281dfa9ebd018c20af0655213c9e2f6501236b26566ff0762e2fc33133068720d95523c481dec966d5b520010b01a1011fdd8c21954d005db9c10957273adccf39cddf5dd43366fb2a6cb18691c8849cb82519e79cf0c9b9ad77cf8c48e994c61e99caa7bc01a361dd755a48d9742549a02e5b12a97e1b4fe1d3cde3652d4de30d46c86f999a4a5072aa86a9ca6ecaa0344c96f1e673654db09da221b22ed4d4018ba3bd0c23ecd4344055e4521fabb0b79faa9a638c8652c8a18f429d60bbfa462a8305506ca7894be5a8abec4f1c2a003b75f061f26c683df02b72d5196815e410e09ce275df6650a"),
        info=messages.EthereumNetworkInfo(
            chain_id=4,
            slip44=1,
            shortcut="tRIN",
            name="Rinkeby",
        ),
    ),
    8: InfoWithDefinition(
        definition=unhexlify("74727a643100634ff57f000f0808106c1a035542512204556269710e7c6b24cf46bb6776fba57be1d523d99398dace19e402817ba052231a7f19172f4171b7bb7110c2e6ceabce81d66dcf533dd150f3bd39febbd25a8aae428ef767c1578fefee2e6ed98fefe60b68f0c45eb06138bddd8befcba5890de9cc6886aa12fd9416e0d8fb524bc4be7389ff7d6624a1ab2d7b69c0aa3d1fdac5b7cdf7bf748f08f6b8c8ef8c095d79c79c3ecf45a2514da6b40cf663fd576c0035af1385cf738e0f8c3249935b363ce61702fd9f4604f4036c7b8f78f6371531334bcca5fde4ba3f8535a86bb92fd9a6d195085969c6137906a136df04186321182196222ee9fe72f5062c761df397a438296625fbcd3da1b3ca257612a0a5a4a8b0bb750e4fdf0fc1346af487421fcce838a3853e6f7e4c87388281dfa9ebd018c20af0655213c9e2f6501236b26566ff0762e2fc33133068720d95523c481dec966d5b520010b01a1011fdd8c21954d005db9c10957273adccf39cddf5dd43366fb2a6cb18691c8849cb82519e79cf0c9b9ad77cf8c48e994c61e99caa7bc01a361dd755a48d9742549a02e5b12a97e1b4fe1d3cde3652d4de30d46c86f999a4a5072aa86a9ca6ecaa0344c96f1e673654db09da221b22ed4d4018ba3bd0c23ecd4344055e4521fabb0b79faa9a638c8652c8a18f429d60bbfa462a8305506ca7894be5a8abec4f1c2a003b75f061f26c683df02b72d5196815e410e09ce275df6650a"),
        info=messages.EthereumNetworkInfo(
            chain_id=8,
            slip44=108,
            shortcut="UBQ",
            name="Ubiq",
        ),
    ),
    61: InfoWithDefinition(
        definition=unhexlify("74727a643100634ff57f001b083d103d1a034554432210457468657265756d20436c61737369630e1e48dfb4c80fe3b3dbb1966b0f0592809cb3f0f26f28d1d0f5aa3f7456267434ef440a7ab20c61e344d2b7f1873fc25f6e705020d2eb727b38f5b793131db4d10dc4b8b316b3a1233ee8035b287c9415d67d33d916f4a9fff293d3d95bf2cff3ce7b4655e716ad71ee7cd74940ad2714deb158f9a1315dd55333a79c878281a3096b8cfbf6aeefae9ed8bcf2487bf85cad3149e7cffb41fb42d37fb192e4261a519ec800e899171e59ed7f18a47b4cbae843ce160a42234b8846efc42d4c41e3fde4ba3f8535a86bb92fd9a6d195085969c6137906a136df04186321182196222ee9fe72f5062c761df397a438296625fbcd3da1b3ca257612a0a5a4a8b0bb750e4fdf0fc1346af487421fcce838a3853e6f7e4c87388281dfa9ebd018c20af0655213c9e2f6501236b26566ff0762e2fc33133068720d95523c481dec966d5b520010b01a1011fdd8c21954d005db9c10957273adccf39cddf5dd43366fb2a6cb18691c8849cb82519e79cf0c9b9ad77cf8c48e994c61e99caa7bc01a361dd755a48d9742549a02e5b12a97e1b4fe1d3cde3652d4de30d46c86f999a4a5072aa86a9ca6ecaa0344c96f1e673654db09da221b22ed4d4018ba3bd0c23ecd4344055e4521fabb0b79faa9a638c8652c8a18f429d60bbfa462a8305506ca7894be5a8abec4f1c2a003b75f061f26c683df02b72d5196815e410e09ce275df6650a"),
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
        "7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9": InfoWithDefinition(
            definition=unhexlify("74727a643101634ff57f00260a044141564510121a147fc66500c84a76ad7e9c93437bfc5ac33e2ddae920012a04416176650e82b7e150ae36a8e67d8974a723bb6637143f81bfb078bd83a49ac30e05660613476905517a80fe16339509b2c89723fbe315ddf5a0cd8f225befaa40054513d6d26f0bf5ed615a5b859e9c44902cbe7cc809f90c028971846bd774f5b1f5b093cc3401644629f8bb1a0a333b4d1527ff91e99f285a89a659f117d97f305f5613d5eebe535e9a6f7cc0cad472c0ce31857bb936bc780f6f42bb995e1b9d0ec592edb304fd281981fc1d218808770dc4c2c23116d682b2592e772458bec747675a407b33dbb70c4317286122c939ef93460268ce991eda73f0461ddb39ad7f1ba5be9380d9c02b6e082f0d97c6e9598ac378579b5950fde761684540fb98f02c67e9ec332bfff9a74a046e9ec3f14726a4b5bbf4c10d668f0022405aff3952a01aa201c917a882ecc82fbc07abb17de83c801cbddbaaa79c2cb1f6242fe02a94271ae6bfff1fe4830e784258a1b148cc5485b5d694e2d26e7d4f6dd0aa42c8337549776b17a2ff4ed022c2401c2556e457a53fccec06014758e0089ca03b72b00055a48d9742549a02e5b12a97e1b4fe1d3cde3652d4de30d46c86f999a4a5072aa86a9ca6ecaa0344c96f1e673654db09da221b22ed4d4018ba3bd0c23ecd4344055e4521fabb0b79faa9a638c8652c8a18f429d60bbfa462a8305506ca7894be5a8abec4f1c2a003b75f061f26c683df02b72d5196815e410e09ce275df6650a"),
            info=messages.EthereumTokenInfo(
                symbol="AAVE",
                decimals=18,
                address=unhexlify("7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9"),
                chain_id=1,
                name="Aave",
            ),
        ),
        "d0d6d6c5fe4a677d343cc433536bb717bae167dd": InfoWithDefinition(
            definition=unhexlify("74727a643101634ff57f00280a0341445410091a14d0d6d6c5fe4a677d343cc433536bb717bae167dd20012a076164436861696e0e31799beb14bd8e10aede4e2ac48c1426a119c2517d58155574c201239909ee2cf2c61acefce7c6c4552878e635a3db259272b3328f9e3e3524fb58c34898a94518313d2dcf229a4b6566ec3d5fc53a6045da8ea1a094dd2026ece16c3c72440bf4d5f2c0ea74636420d5fb5452833926d476abcf3050cd17559d32ed2bba1bc243398514db41e8a02541742a0f11bc412f825707c7c1b9124f1e6611a42939166c818816e2f7bea875a9530ef7f0dd3d1ca85b98ff09f631fdc13d916c7408a8b183f0109bc19ba2112bcce59ece1eb076968cd6c65c45a401afbf792ce5ace6e9ac2b3071314b1ba075de79b8221ff9cbc67823499bc16902b11a698960745502947b4410270b07865e320f254e720d0f3b62d38660104dc79acd6c22255988aa305f88c0e4a2fe67104c039996dc1e1fa04d1319d0da2e0992558e0dad290f541f224bce21762a1ea1146becd7d46ac1e05f23b707274ea8bade5010b1b75014ae35d6bc07c87dc65a61fb61e7922e1d74447565d9b224eccb2103e918c866d5829b2629688ae6a677cde42960e6ae747f4d7cb30454d58d6726d140f7c4afa86a9ca6ecaa0344c96f1e673654db09da221b22ed4d4018ba3bd0c23ecd4344055e4521fabb0b79faa9a638c8652c8a18f429d60bbfa462a8305506ca7894be5a8abec4f1c2a003b75f061f26c683df02b72d5196815e410e09ce275df6650a"),
            info=messages.EthereumTokenInfo(
                symbol="ADT",
                decimals=9,
                address=unhexlify("d0d6d6c5fe4a677d343cc433536bb717bae167dd"),
                chain_id=1,
                name="adChain",
            ),
        ),
    },
    4: {
        "275a5b346599b56917e7b1c9de019dcf9ead861a": InfoWithDefinition(
            definition=unhexlify("74727a643101634ff57f002b0a024b4310121a14275a5b346599b56917e7b1c9de019dcf9ead861a20042a0b4b61726d6120546f6b656e0e1f728edc97d6437c3ee0e36f0aae678cab87468a03f989349d46e3f47a24582729ff2c1ff4ba752d3be9dec7e0617ef7847b16b8a2ae3c1fdc8278672cd130fbbb76acd69a6467cf866e9895b421812797e833813f1e04a858fbc7e439bb70b4c81eeecb74ee303f1c9db394985e63a5016c19a6839522394da90e314b9227eba8f4acafa01fc8cc1040c3666f3f41eb380e065a79950fde2856990091262d4d526e7f6c9a09be0a97982b9d829ea6c378f895e2cfb15b7e4724c63f4431deb02ed73088fa7bedf6c5ac723c2140f46701b718b9ada7635ed51e8b726f7398f3fcdbe577ea82312adc4c102804f15377f350331a74048441a0455407c2603c22b565444bb3e1d0649c7c69487c7465fbac21593468a463f6ded44e6733e9931ebccaf1fdbe89ba777c2530f9412d1b382940623eab413f5d2b1f2542b86bc369b8e7379a56b56c1344a6a89e554e328f19ab317d0d26a8ab17e07470591e1cccbd4ccd99a506080325539de0fad893a6e07232dc7cc820e94373747d63a5a8ead5829b2629688ae6a677cde42960e6ae747f4d7cb30454d58d6726d140f7c4afa86a9ca6ecaa0344c96f1e673654db09da221b22ed4d4018ba3bd0c23ecd4344055e4521fabb0b79faa9a638c8652c8a18f429d60bbfa462a8305506ca7894be5a8abec4f1c2a003b75f061f26c683df02b72d5196815e410e09ce275df6650a"),
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


def get_ethereum_encoded_definition(chain_id: int | None = None, slip44: int | None = None) -> messages.EthereumDefinitions:
    return messages.EthereumDefinitions(
        encoded_network=get_ethereum_encoded_network_definition(chain_id, slip44),
        encoded_token=None, # TODO
    )
