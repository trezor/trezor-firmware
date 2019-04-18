from trezorlib import protobuf as p


class CoinDef(p.MessageType):
    FIELDS = {
        1: ("coin_name", p.UnicodeType, 0),
        2: ("coin_shortcut", p.UnicodeType, 0),
        3: ("coin_label", p.UnicodeType, 0),
        4: ("curve_name", p.UnicodeType, 0),
        5: ("address_type", p.UVarintType, 0),
        6: ("address_type_p2sh", p.UVarintType, 0),
        7: ("maxfee_kb", p.UVarintType, 0),
        8: ("minfee_kb", p.UVarintType, 0),
        9: ("signed_message_header", p.BytesType, 0),
        10: ("hash_genesis_block", p.BytesType, 0),
        11: ("xprv_magic", p.UVarintType, 0),
        12: ("xpub_magic", p.UVarintType, 0),
        13: ("xpub_magic_segwit_p2sh", p.UVarintType, 0),
        14: ("xpub_magic_segwit_native", p.UVarintType, 0),
        15: ("bech32_prefix", p.UnicodeType, 0),
        16: ("cashaddr_prefix", p.UnicodeType, 0),
        17: ("slip44", p.UVarintType, 0),
        18: ("segwit", p.BoolType, 0),
        19: ("decred", p.BoolType, 0),
        20: ("fork_id", p.UVarintType, 0),
        21: ("force_bip143", p.BoolType, 0),
        22: ("dust_limit", p.UVarintType, 0),
        23: ("uri_prefix", p.UnicodeType, 0),
        24: ("min_address_length", p.UVarintType, 0),
        25: ("max_address_length", p.UVarintType, 0),
        26: ("icon", p.BytesType, 0),
        28: ("website", p.UnicodeType, 0),
        29: ("github", p.UnicodeType, 0),
        30: ("maintainer", p.UnicodeType, 0),
        31: ("blocktime_seconds", p.UVarintType, 0),
        32: ("bip115", p.BoolType, 0),
        33: ("cooldown", p.UVarintType, 0),
    }

    def __init__(
        self,
        coin_name: str = None,
        coin_shortcut: str = None,
        coin_label: str = None,
        curve_name: str = None,
        address_type: int = None,
        address_type_p2sh: int = None,
        maxfee_kb: int = None,
        minfee_kb: int = None,
        signed_message_header: bytes = None,
        hash_genesis_block: bytes = None,
        xprv_magic: int = None,
        xpub_magic: int = None,
        xpub_magic_segwit_p2sh: int = None,
        xpub_magic_segwit_native: int = None,
        bech32_prefix: str = None,
        cashaddr_prefix: str = None,
        slip44: int = None,
        segwit: bool = None,
        decred: bool = None,
        fork_id: int = None,
        force_bip143: bool = None,
        bip115: bool = None,
        dust_limit: int = None,
        uri_prefix: str = None,
        min_address_length: int = None,
        max_address_length: int = None,
        icon: bytes = None,
        website: str = None,
        github: str = None,
        maintainer: str = None,
        blocktime_seconds: int = None,
        default_fee_b: dict = None,
        bitcore: dict = None,
        blockbook: dict = None,
        cooldown: int = None,
    ):
        self.coin_name = coin_name
        self.coin_shortcut = coin_shortcut
        self.coin_label = coin_label
        self.curve_name = curve_name
        self.address_type = address_type
        self.address_type_p2sh = address_type_p2sh
        self.maxfee_kb = maxfee_kb
        self.minfee_kb = minfee_kb
        self.signed_message_header = signed_message_header
        self.hash_genesis_block = hash_genesis_block
        self.xprv_magic = xprv_magic
        self.xpub_magic = xpub_magic
        self.xpub_magic_segwit_p2sh = xpub_magic_segwit_p2sh
        self.xpub_magic_segwit_native = xpub_magic_segwit_native
        self.bech32_prefix = bech32_prefix
        self.cashaddr_prefix = cashaddr_prefix
        self.slip44 = slip44
        self.segwit = segwit
        self.decred = decred
        self.fork_id = fork_id
        self.force_bip143 = force_bip143
        self.bip115 = bip115
        self.dust_limit = dust_limit
        self.uri_prefix = uri_prefix
        self.min_address_length = min_address_length
        self.max_address_length = max_address_length
        self.icon = icon
        self.website = website
        self.github = github
        self.maintainer = maintainer
        self.blocktime_seconds = blocktime_seconds
        self.default_fee_b = default_fee_b
        self.bitcore = bitcore
        self.blockbook = blockbook
        self.cooldown = cooldown
        p.MessageType.__init__(self)
