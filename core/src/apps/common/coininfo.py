# generated from coininfo.py.mako
# (by running `make templates` in `core`)
# do not edit manually!

# NOTE: using positional arguments saves 4500 bytes of flash size

from typing import Any

from trezor import utils
from trezor.crypto.base58 import blake256d_32, groestl512d_32, keccak_32, sha256d_32
from trezor.crypto.scripts import blake256_ripemd160, sha256_ripemd160

# flake8: noqa


class CoinInfo:
    def __init__(
        self,
        coin_name: str,
        coin_shortcut: str,
        decimals: int,
        address_type: int,
        address_type_p2sh: int,
        maxfee_kb: int,
        signed_message_header: str,
        xpub_magic: int,
        xpub_magic_segwit_p2sh: int | None,
        xpub_magic_segwit_native: int | None,
        xpub_magic_multisig_segwit_p2sh: int | None,
        xpub_magic_multisig_segwit_native: int | None,
        bech32_prefix: str | None,
        cashaddr_prefix: str | None,
        slip44: int,
        segwit: bool,
        taproot: bool,
        fork_id: int | None,
        force_bip143: bool,
        decred: bool,
        negative_fee: bool,
        curve_name: str,
        extra_data: bool,
        timestamp: bool,
        overwintered: bool,
        confidential_assets: dict[str, Any] | None,
    ) -> None:
        self.coin_name = coin_name
        self.coin_shortcut = coin_shortcut
        self.decimals = decimals
        self.address_type = address_type
        self.address_type_p2sh = address_type_p2sh
        self.maxfee_kb = maxfee_kb
        self.signed_message_header = signed_message_header
        self.xpub_magic = xpub_magic
        self.xpub_magic_segwit_p2sh = xpub_magic_segwit_p2sh
        self.xpub_magic_segwit_native = xpub_magic_segwit_native
        self.xpub_magic_multisig_segwit_p2sh = xpub_magic_multisig_segwit_p2sh
        self.xpub_magic_multisig_segwit_native = xpub_magic_multisig_segwit_native
        self.bech32_prefix = bech32_prefix
        self.cashaddr_prefix = cashaddr_prefix
        self.slip44 = slip44
        self.segwit = segwit
        self.taproot = taproot
        self.fork_id = fork_id
        self.force_bip143 = force_bip143
        self.decred = decred
        self.negative_fee = negative_fee
        self.curve_name = curve_name
        self.extra_data = extra_data
        self.timestamp = timestamp
        self.overwintered = overwintered
        self.confidential_assets = confidential_assets
        if curve_name == "secp256k1-groestl":
            self.b58_hash = groestl512d_32
            self.sign_hash_double = False
            self.script_hash: type[utils.HashContextInitable] = sha256_ripemd160
        elif curve_name == "secp256k1-decred":
            self.b58_hash = blake256d_32
            self.sign_hash_double = False
            self.script_hash = blake256_ripemd160
        elif curve_name == "secp256k1-smart":
            self.b58_hash = keccak_32
            self.sign_hash_double = False
            self.script_hash = sha256_ripemd160
        else:
            self.b58_hash = sha256d_32
            self.sign_hash_double = True
            self.script_hash = sha256_ripemd160

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, CoinInfo):
            return NotImplemented
        return self.coin_name == other.coin_name


# fmt: off
def by_name(name: str) -> CoinInfo:
    if utils.INTERNAL_MODEL == "T1B1":
        if name == "Bitcoin":
            return CoinInfo(
                name,  # coin_name
                "BTC",  # coin_shortcut
                8,  # decimals
                0,  # address_type
                5,  # address_type_p2sh
                2000000,  # maxfee_kb
                "Bitcoin Signed Message:\n",  # signed_message_header
                0x0488b21e,  # xpub_magic
                0x049d7cb2,  # xpub_magic_segwit_p2sh
                0x04b24746,  # xpub_magic_segwit_native
                0x0295b43f,  # xpub_magic_multisig_segwit_p2sh
                0x02aa7ed3,  # xpub_magic_multisig_segwit_native
                "bc",  # bech32_prefix
                None,  # cashaddr_prefix
                0,  # slip44
                True,  # segwit
                True,  # taproot
                None,  # fork_id
                False,  # force_bip143
                False,  # decred
                False,  # negative_fee
                'secp256k1',  # curve_name
                False,  # extra_data
                False,  # timestamp
                False,  # overwintered
                None,  # confidential_assets
            )
        if name == "Regtest":
            return CoinInfo(
                name,  # coin_name
                "REGTEST",  # coin_shortcut
                8,  # decimals
                111,  # address_type
                196,  # address_type_p2sh
                10000000,  # maxfee_kb
                "Bitcoin Signed Message:\n",  # signed_message_header
                0x043587cf,  # xpub_magic
                0x044a5262,  # xpub_magic_segwit_p2sh
                0x045f1cf6,  # xpub_magic_segwit_native
                0x024289ef,  # xpub_magic_multisig_segwit_p2sh
                0x02575483,  # xpub_magic_multisig_segwit_native
                "bcrt",  # bech32_prefix
                None,  # cashaddr_prefix
                1,  # slip44
                True,  # segwit
                True,  # taproot
                None,  # fork_id
                False,  # force_bip143
                False,  # decred
                False,  # negative_fee
                'secp256k1',  # curve_name
                False,  # extra_data
                False,  # timestamp
                False,  # overwintered
                None,  # confidential_assets
            )
        if name == "Testnet":
            return CoinInfo(
                name,  # coin_name
                "TEST",  # coin_shortcut
                8,  # decimals
                111,  # address_type
                196,  # address_type_p2sh
                10000000,  # maxfee_kb
                "Bitcoin Signed Message:\n",  # signed_message_header
                0x043587cf,  # xpub_magic
                0x044a5262,  # xpub_magic_segwit_p2sh
                0x045f1cf6,  # xpub_magic_segwit_native
                0x024289ef,  # xpub_magic_multisig_segwit_p2sh
                0x02575483,  # xpub_magic_multisig_segwit_native
                "tb",  # bech32_prefix
                None,  # cashaddr_prefix
                1,  # slip44
                True,  # segwit
                True,  # taproot
                None,  # fork_id
                False,  # force_bip143
                False,  # decred
                False,  # negative_fee
                'secp256k1',  # curve_name
                False,  # extra_data
                False,  # timestamp
                False,  # overwintered
                None,  # confidential_assets
            )
        if not utils.BITCOIN_ONLY:
            if name == "Actinium":
                return CoinInfo(
                    name,  # coin_name
                    "ACM",  # coin_shortcut
                    8,  # decimals
                    53,  # address_type
                    55,  # address_type_p2sh
                    320000000000,  # maxfee_kb
                    "Actinium Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "acm",  # bech32_prefix
                    None,  # cashaddr_prefix
                    228,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Axe":
                return CoinInfo(
                    name,  # coin_name
                    "AXE",  # coin_shortcut
                    8,  # decimals
                    55,  # address_type
                    16,  # address_type_p2sh
                    21000000000,  # maxfee_kb
                    "DarkCoin Signed Message:\n",  # signed_message_header
                    0x02fe52cc,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    4242,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Bcash":
                return CoinInfo(
                    name,  # coin_name
                    "BCH",  # coin_shortcut
                    8,  # decimals
                    0,  # address_type
                    5,  # address_type_p2sh
                    14000000,  # maxfee_kb
                    "Bitcoin Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    "bitcoincash",  # cashaddr_prefix
                    145,  # slip44
                    False,  # segwit
                    False,  # taproot
                    0,  # fork_id
                    True,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Bcash Testnet":
                return CoinInfo(
                    name,  # coin_name
                    "TBCH",  # coin_shortcut
                    8,  # decimals
                    111,  # address_type
                    196,  # address_type_p2sh
                    10000000,  # maxfee_kb
                    "Bitcoin Signed Message:\n",  # signed_message_header
                    0x043587cf,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    "bchtest",  # cashaddr_prefix
                    1,  # slip44
                    False,  # segwit
                    False,  # taproot
                    0,  # fork_id
                    True,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Bgold":
                return CoinInfo(
                    name,  # coin_name
                    "BTG",  # coin_shortcut
                    8,  # decimals
                    38,  # address_type
                    23,  # address_type_p2sh
                    380000000,  # maxfee_kb
                    "Bitcoin Gold Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "btg",  # bech32_prefix
                    None,  # cashaddr_prefix
                    156,  # slip44
                    True,  # segwit
                    False,  # taproot
                    79,  # fork_id
                    True,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Bgold Testnet":
                return CoinInfo(
                    name,  # coin_name
                    "TBTG",  # coin_shortcut
                    8,  # decimals
                    111,  # address_type
                    196,  # address_type_p2sh
                    500000,  # maxfee_kb
                    "Bitcoin Gold Signed Message:\n",  # signed_message_header
                    0x043587cf,  # xpub_magic
                    0x044a5262,  # xpub_magic_segwit_p2sh
                    0x045f1cf6,  # xpub_magic_segwit_native
                    0x043587cf,  # xpub_magic_multisig_segwit_p2sh
                    0x043587cf,  # xpub_magic_multisig_segwit_native
                    "tbtg",  # bech32_prefix
                    None,  # cashaddr_prefix
                    1,  # slip44
                    True,  # segwit
                    False,  # taproot
                    79,  # fork_id
                    True,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Bprivate":
                return CoinInfo(
                    name,  # coin_name
                    "BTCP",  # coin_shortcut
                    8,  # decimals
                    4901,  # address_type
                    5039,  # address_type_p2sh
                    32000000000,  # maxfee_kb
                    "BitcoinPrivate Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    183,  # slip44
                    False,  # segwit
                    False,  # taproot
                    42,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Bitcore":
                return CoinInfo(
                    name,  # coin_name
                    "BTX",  # coin_shortcut
                    8,  # decimals
                    3,  # address_type
                    125,  # address_type_p2sh
                    14000000000,  # maxfee_kb
                    "BitCore Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "btx",  # bech32_prefix
                    None,  # cashaddr_prefix
                    160,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "CPUchain":
                return CoinInfo(
                    name,  # coin_name
                    "CPU",  # coin_shortcut
                    8,  # decimals
                    28,  # address_type
                    30,  # address_type_p2sh
                    8700000000000,  # maxfee_kb
                    "CPUchain Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "cpu",  # bech32_prefix
                    None,  # cashaddr_prefix
                    363,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Crown":
                return CoinInfo(
                    name,  # coin_name
                    "CRW",  # coin_shortcut
                    8,  # decimals
                    95495,  # address_type
                    95473,  # address_type_p2sh
                    52000000000,  # maxfee_kb
                    "Crown Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    72,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Dash":
                return CoinInfo(
                    name,  # coin_name
                    "DASH",  # coin_shortcut
                    8,  # decimals
                    76,  # address_type
                    16,  # address_type_p2sh
                    45000000,  # maxfee_kb
                    "DarkCoin Signed Message:\n",  # signed_message_header
                    0x02fe52cc,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    5,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    True,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Dash Testnet":
                return CoinInfo(
                    name,  # coin_name
                    "tDASH",  # coin_shortcut
                    8,  # decimals
                    140,  # address_type
                    19,  # address_type_p2sh
                    100000,  # maxfee_kb
                    "DarkCoin Signed Message:\n",  # signed_message_header
                    0x043587cf,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    1,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    True,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Decred":
                return CoinInfo(
                    name,  # coin_name
                    "DCR",  # coin_shortcut
                    8,  # decimals
                    1855,  # address_type
                    1818,  # address_type_p2sh
                    220000000,  # maxfee_kb
                    "Decred Signed Message:\n",  # signed_message_header
                    0x02fda926,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    42,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    True,  # decred
                    False,  # negative_fee
                    'secp256k1-decred',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Decred Testnet":
                return CoinInfo(
                    name,  # coin_name
                    "TDCR",  # coin_shortcut
                    8,  # decimals
                    3873,  # address_type
                    3836,  # address_type_p2sh
                    10000000,  # maxfee_kb
                    "Decred Signed Message:\n",  # signed_message_header
                    0x043587d1,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    1,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    True,  # decred
                    False,  # negative_fee
                    'secp256k1-decred',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "DigiByte":
                return CoinInfo(
                    name,  # coin_name
                    "DGB",  # coin_shortcut
                    8,  # decimals
                    30,  # address_type
                    63,  # address_type_p2sh
                    130000000000,  # maxfee_kb
                    "DigiByte Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "dgb",  # bech32_prefix
                    None,  # cashaddr_prefix
                    20,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Dogecoin":
                return CoinInfo(
                    name,  # coin_name
                    "DOGE",  # coin_shortcut
                    8,  # decimals
                    30,  # address_type
                    22,  # address_type_p2sh
                    1200000000000,  # maxfee_kb
                    "Dogecoin Signed Message:\n",  # signed_message_header
                    0x02facafd,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    3,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Elements":
                return CoinInfo(
                    name,  # coin_name
                    "ELEMENTS",  # coin_shortcut
                    8,  # decimals
                    235,  # address_type
                    75,  # address_type_p2sh
                    10000000,  # maxfee_kb
                    "Bitcoin Signed Message:\n",  # signed_message_header
                    0x043587cf,  # xpub_magic
                    0x044a5262,  # xpub_magic_segwit_p2sh
                    0x045f1cf6,  # xpub_magic_segwit_native
                    0x043587cf,  # xpub_magic_multisig_segwit_p2sh
                    0x043587cf,  # xpub_magic_multisig_segwit_native
                    "ert",  # bech32_prefix
                    None,  # cashaddr_prefix
                    1,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    {'address_prefix': 4, 'blech32_prefix': 'el'},  # confidential_assets
                )
            if name == "Feathercoin":
                return CoinInfo(
                    name,  # coin_name
                    "FTC",  # coin_shortcut
                    8,  # decimals
                    14,  # address_type
                    5,  # address_type_p2sh
                    390000000000,  # maxfee_kb
                    "Feathercoin Signed Message:\n",  # signed_message_header
                    0x0488bc26,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488bc26,  # xpub_magic_multisig_segwit_p2sh
                    0x0488bc26,  # xpub_magic_multisig_segwit_native
                    "fc",  # bech32_prefix
                    None,  # cashaddr_prefix
                    8,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Firo":
                return CoinInfo(
                    name,  # coin_name
                    "FIRO",  # coin_shortcut
                    8,  # decimals
                    82,  # address_type
                    7,  # address_type_p2sh
                    640000000,  # maxfee_kb
                    "Zcoin Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    136,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    True,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Firo Testnet":
                return CoinInfo(
                    name,  # coin_name
                    "tFIRO",  # coin_shortcut
                    8,  # decimals
                    65,  # address_type
                    178,  # address_type_p2sh
                    1000000,  # maxfee_kb
                    "Zcoin Signed Message:\n",  # signed_message_header
                    0x043587cf,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    1,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    True,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Florincoin":
                return CoinInfo(
                    name,  # coin_name
                    "FLO",  # coin_shortcut
                    8,  # decimals
                    35,  # address_type
                    94,  # address_type_p2sh
                    78000000000,  # maxfee_kb
                    "Florincoin Signed Message:\n",  # signed_message_header
                    0x00174921,  # xpub_magic
                    0x01b26ef6,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x00174921,  # xpub_magic_multisig_segwit_p2sh
                    0x00174921,  # xpub_magic_multisig_segwit_native
                    "flo",  # bech32_prefix
                    None,  # cashaddr_prefix
                    216,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    True,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Fujicoin":
                return CoinInfo(
                    name,  # coin_name
                    "FJC",  # coin_shortcut
                    8,  # decimals
                    36,  # address_type
                    16,  # address_type_p2sh
                    35000000000000,  # maxfee_kb
                    "FujiCoin Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0295b43f,  # xpub_magic_multisig_segwit_p2sh
                    0x02aa7ed3,  # xpub_magic_multisig_segwit_native
                    "fc",  # bech32_prefix
                    None,  # cashaddr_prefix
                    75,  # slip44
                    True,  # segwit
                    True,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Groestlcoin":
                return CoinInfo(
                    name,  # coin_name
                    "GRS",  # coin_shortcut
                    8,  # decimals
                    36,  # address_type
                    5,  # address_type_p2sh
                    16000000000,  # maxfee_kb
                    "GroestlCoin Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "grs",  # bech32_prefix
                    None,  # cashaddr_prefix
                    17,  # slip44
                    True,  # segwit
                    True,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1-groestl',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Groestlcoin Testnet":
                return CoinInfo(
                    name,  # coin_name
                    "tGRS",  # coin_shortcut
                    8,  # decimals
                    111,  # address_type
                    196,  # address_type_p2sh
                    100000,  # maxfee_kb
                    "GroestlCoin Signed Message:\n",  # signed_message_header
                    0x043587cf,  # xpub_magic
                    0x044a5262,  # xpub_magic_segwit_p2sh
                    0x045f1cf6,  # xpub_magic_segwit_native
                    0x043587cf,  # xpub_magic_multisig_segwit_p2sh
                    0x043587cf,  # xpub_magic_multisig_segwit_native
                    "tgrs",  # bech32_prefix
                    None,  # cashaddr_prefix
                    1,  # slip44
                    True,  # segwit
                    True,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1-groestl',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Komodo":
                return CoinInfo(
                    name,  # coin_name
                    "KMD",  # coin_shortcut
                    8,  # decimals
                    60,  # address_type
                    85,  # address_type_p2sh
                    4800000000,  # maxfee_kb
                    "Komodo Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    141,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    True,  # negative_fee
                    'secp256k1',  # curve_name
                    True,  # extra_data
                    False,  # timestamp
                    True,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Koto":
                return CoinInfo(
                    name,  # coin_name
                    "KOTO",  # coin_shortcut
                    8,  # decimals
                    6198,  # address_type
                    6203,  # address_type_p2sh
                    1000000,  # maxfee_kb
                    "Koto Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    510,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    True,  # extra_data
                    False,  # timestamp
                    True,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Litecoin":
                return CoinInfo(
                    name,  # coin_name
                    "LTC",  # coin_shortcut
                    8,  # decimals
                    48,  # address_type
                    50,  # address_type_p2sh
                    67000000,  # maxfee_kb
                    "Litecoin Signed Message:\n",  # signed_message_header
                    0x019da462,  # xpub_magic
                    0x01b26ef6,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x019da462,  # xpub_magic_multisig_segwit_p2sh
                    0x019da462,  # xpub_magic_multisig_segwit_native
                    "ltc",  # bech32_prefix
                    None,  # cashaddr_prefix
                    2,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Litecoin Testnet":
                return CoinInfo(
                    name,  # coin_name
                    "tLTC",  # coin_shortcut
                    8,  # decimals
                    111,  # address_type
                    58,  # address_type_p2sh
                    40000000,  # maxfee_kb
                    "Litecoin Signed Message:\n",  # signed_message_header
                    0x043587cf,  # xpub_magic
                    0x044a5262,  # xpub_magic_segwit_p2sh
                    0x045f1cf6,  # xpub_magic_segwit_native
                    0x043587cf,  # xpub_magic_multisig_segwit_p2sh
                    0x043587cf,  # xpub_magic_multisig_segwit_native
                    "tltc",  # bech32_prefix
                    None,  # cashaddr_prefix
                    1,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Monacoin":
                return CoinInfo(
                    name,  # coin_name
                    "MONA",  # coin_shortcut
                    8,  # decimals
                    50,  # address_type
                    55,  # address_type_p2sh
                    2100000000,  # maxfee_kb
                    "Monacoin Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "mona",  # bech32_prefix
                    None,  # cashaddr_prefix
                    22,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Namecoin":
                return CoinInfo(
                    name,  # coin_name
                    "NMC",  # coin_shortcut
                    8,  # decimals
                    52,  # address_type
                    5,  # address_type_p2sh
                    8700000000,  # maxfee_kb
                    "Namecoin Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    7,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Peercoin":
                return CoinInfo(
                    name,  # coin_name
                    "PPC",  # coin_shortcut
                    6,  # decimals
                    55,  # address_type
                    117,  # address_type_p2sh
                    13000000000,  # maxfee_kb
                    "Peercoin Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "pc",  # bech32_prefix
                    None,  # cashaddr_prefix
                    6,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    True,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Peercoin Testnet":
                return CoinInfo(
                    name,  # coin_name
                    "tPPC",  # coin_shortcut
                    6,  # decimals
                    111,  # address_type
                    196,  # address_type_p2sh
                    2000000,  # maxfee_kb
                    "Peercoin Signed Message:\n",  # signed_message_header
                    0x043587cf,  # xpub_magic
                    0x044a5262,  # xpub_magic_segwit_p2sh
                    0x045f1cf6,  # xpub_magic_segwit_native
                    0x043587cf,  # xpub_magic_multisig_segwit_p2sh
                    0x043587cf,  # xpub_magic_multisig_segwit_native
                    "tpc",  # bech32_prefix
                    None,  # cashaddr_prefix
                    1,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    True,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Primecoin":
                return CoinInfo(
                    name,  # coin_name
                    "XPM",  # coin_shortcut
                    8,  # decimals
                    23,  # address_type
                    83,  # address_type_p2sh
                    89000000000,  # maxfee_kb
                    "Primecoin Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    24,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Qtum":
                return CoinInfo(
                    name,  # coin_name
                    "QTUM",  # coin_shortcut
                    8,  # decimals
                    58,  # address_type
                    50,  # address_type_p2sh
                    1000000000,  # maxfee_kb
                    "Qtum Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "qc",  # bech32_prefix
                    None,  # cashaddr_prefix
                    2301,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Qtum Testnet":
                return CoinInfo(
                    name,  # coin_name
                    "tQTUM",  # coin_shortcut
                    8,  # decimals
                    120,  # address_type
                    110,  # address_type_p2sh
                    40000000,  # maxfee_kb
                    "Qtum Signed Message:\n",  # signed_message_header
                    0x043587cf,  # xpub_magic
                    0x044a5262,  # xpub_magic_segwit_p2sh
                    0x045f1cf6,  # xpub_magic_segwit_native
                    0x043587cf,  # xpub_magic_multisig_segwit_p2sh
                    0x043587cf,  # xpub_magic_multisig_segwit_native
                    "tq",  # bech32_prefix
                    None,  # cashaddr_prefix
                    1,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Ravencoin":
                return CoinInfo(
                    name,  # coin_name
                    "RVN",  # coin_shortcut
                    8,  # decimals
                    60,  # address_type
                    122,  # address_type_p2sh
                    170000000000,  # maxfee_kb
                    "Raven Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    175,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Ravencoin Testnet":
                return CoinInfo(
                    name,  # coin_name
                    "tRVN",  # coin_shortcut
                    8,  # decimals
                    111,  # address_type
                    196,  # address_type_p2sh
                    170000000000,  # maxfee_kb
                    "Raven Signed Message:\n",  # signed_message_header
                    0x043587cf,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    1,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Ritocoin":
                return CoinInfo(
                    name,  # coin_name
                    "RITO",  # coin_shortcut
                    8,  # decimals
                    25,  # address_type
                    105,  # address_type_p2sh
                    39000000000000,  # maxfee_kb
                    "Rito Signed Message:\n",  # signed_message_header
                    0x0534e7ca,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    19169,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "SmartCash":
                return CoinInfo(
                    name,  # coin_name
                    "SMART",  # coin_shortcut
                    8,  # decimals
                    63,  # address_type
                    18,  # address_type_p2sh
                    780000000000,  # maxfee_kb
                    "SmartCash Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    224,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1-smart',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "SmartCash Testnet":
                return CoinInfo(
                    name,  # coin_name
                    "tSMART",  # coin_shortcut
                    8,  # decimals
                    65,  # address_type
                    21,  # address_type_p2sh
                    1000000,  # maxfee_kb
                    "SmartCash Signed Message:\n",  # signed_message_header
                    0x043587cf,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    1,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1-smart',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Stakenet":
                return CoinInfo(
                    name,  # coin_name
                    "XSN",  # coin_shortcut
                    8,  # decimals
                    76,  # address_type
                    16,  # address_type_p2sh
                    11000000000,  # maxfee_kb
                    "DarkCoin Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "xc",  # bech32_prefix
                    None,  # cashaddr_prefix
                    199,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    True,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Syscoin":
                return CoinInfo(
                    name,  # coin_name
                    "SYS",  # coin_shortcut
                    8,  # decimals
                    63,  # address_type
                    5,  # address_type_p2sh
                    42000000000,  # maxfee_kb
                    "Syscoin Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "sys",  # bech32_prefix
                    None,  # cashaddr_prefix
                    57,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Unobtanium":
                return CoinInfo(
                    name,  # coin_name
                    "UNO",  # coin_shortcut
                    8,  # decimals
                    130,  # address_type
                    30,  # address_type_p2sh
                    53000000,  # maxfee_kb
                    "Unobtanium Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    92,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "VIPSTARCOIN":
                return CoinInfo(
                    name,  # coin_name
                    "VIPS",  # coin_shortcut
                    8,  # decimals
                    70,  # address_type
                    50,  # address_type_p2sh
                    140000000000000,  # maxfee_kb
                    "VIPSTARCOIN Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "vips",  # bech32_prefix
                    None,  # cashaddr_prefix
                    1919,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Verge":
                return CoinInfo(
                    name,  # coin_name
                    "XVG",  # coin_shortcut
                    6,  # decimals
                    30,  # address_type
                    33,  # address_type_p2sh
                    550000000000,  # maxfee_kb
                    "Name: Dogecoin Dark\n",  # signed_message_header
                    0x022d2533,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    77,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    True,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Vertcoin":
                return CoinInfo(
                    name,  # coin_name
                    "VTC",  # coin_shortcut
                    8,  # decimals
                    71,  # address_type
                    5,  # address_type_p2sh
                    13000000000,  # maxfee_kb
                    "Vertcoin Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "vtc",  # bech32_prefix
                    None,  # cashaddr_prefix
                    28,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Viacoin":
                return CoinInfo(
                    name,  # coin_name
                    "VIA",  # coin_shortcut
                    8,  # decimals
                    71,  # address_type
                    33,  # address_type_p2sh
                    14000000000,  # maxfee_kb
                    "Viacoin Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "via",  # bech32_prefix
                    None,  # cashaddr_prefix
                    14,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "ZCore":
                return CoinInfo(
                    name,  # coin_name
                    "ZCR",  # coin_shortcut
                    8,  # decimals
                    142,  # address_type
                    145,  # address_type_p2sh
                    170000000000,  # maxfee_kb
                    "DarkNet Signed Message:\n",  # signed_message_header
                    0x04b24746,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    428,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Zcash":
                return CoinInfo(
                    name,  # coin_name
                    "ZEC",  # coin_shortcut
                    8,  # decimals
                    7352,  # address_type
                    7357,  # address_type_p2sh
                    51000000,  # maxfee_kb
                    "Zcash Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    133,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    True,  # extra_data
                    False,  # timestamp
                    True,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Zcash Testnet":
                return CoinInfo(
                    name,  # coin_name
                    "TAZ",  # coin_shortcut
                    8,  # decimals
                    7461,  # address_type
                    7354,  # address_type_p2sh
                    10000000,  # maxfee_kb
                    "Zcash Signed Message:\n",  # signed_message_header
                    0x043587cf,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    1,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    True,  # extra_data
                    False,  # timestamp
                    True,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Brhodium":
                return CoinInfo(
                    name,  # coin_name
                    "XRC",  # coin_shortcut
                    8,  # decimals
                    61,  # address_type
                    123,  # address_type_p2sh
                    1000000000,  # maxfee_kb
                    "BitCoin Rhodium Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    10291,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
        raise ValueError  # Unknown coin name
    if utils.INTERNAL_MODEL == "T2B1":
        if name == "Bitcoin":
            return CoinInfo(
                name,  # coin_name
                "BTC",  # coin_shortcut
                8,  # decimals
                0,  # address_type
                5,  # address_type_p2sh
                2000000,  # maxfee_kb
                "Bitcoin Signed Message:\n",  # signed_message_header
                0x0488b21e,  # xpub_magic
                0x049d7cb2,  # xpub_magic_segwit_p2sh
                0x04b24746,  # xpub_magic_segwit_native
                0x0295b43f,  # xpub_magic_multisig_segwit_p2sh
                0x02aa7ed3,  # xpub_magic_multisig_segwit_native
                "bc",  # bech32_prefix
                None,  # cashaddr_prefix
                0,  # slip44
                True,  # segwit
                True,  # taproot
                None,  # fork_id
                False,  # force_bip143
                False,  # decred
                False,  # negative_fee
                'secp256k1',  # curve_name
                False,  # extra_data
                False,  # timestamp
                False,  # overwintered
                None,  # confidential_assets
            )
        if name == "Regtest":
            return CoinInfo(
                name,  # coin_name
                "REGTEST",  # coin_shortcut
                8,  # decimals
                111,  # address_type
                196,  # address_type_p2sh
                10000000,  # maxfee_kb
                "Bitcoin Signed Message:\n",  # signed_message_header
                0x043587cf,  # xpub_magic
                0x044a5262,  # xpub_magic_segwit_p2sh
                0x045f1cf6,  # xpub_magic_segwit_native
                0x024289ef,  # xpub_magic_multisig_segwit_p2sh
                0x02575483,  # xpub_magic_multisig_segwit_native
                "bcrt",  # bech32_prefix
                None,  # cashaddr_prefix
                1,  # slip44
                True,  # segwit
                True,  # taproot
                None,  # fork_id
                False,  # force_bip143
                False,  # decred
                False,  # negative_fee
                'secp256k1',  # curve_name
                False,  # extra_data
                False,  # timestamp
                False,  # overwintered
                None,  # confidential_assets
            )
        if name == "Testnet":
            return CoinInfo(
                name,  # coin_name
                "TEST",  # coin_shortcut
                8,  # decimals
                111,  # address_type
                196,  # address_type_p2sh
                10000000,  # maxfee_kb
                "Bitcoin Signed Message:\n",  # signed_message_header
                0x043587cf,  # xpub_magic
                0x044a5262,  # xpub_magic_segwit_p2sh
                0x045f1cf6,  # xpub_magic_segwit_native
                0x024289ef,  # xpub_magic_multisig_segwit_p2sh
                0x02575483,  # xpub_magic_multisig_segwit_native
                "tb",  # bech32_prefix
                None,  # cashaddr_prefix
                1,  # slip44
                True,  # segwit
                True,  # taproot
                None,  # fork_id
                False,  # force_bip143
                False,  # decred
                False,  # negative_fee
                'secp256k1',  # curve_name
                False,  # extra_data
                False,  # timestamp
                False,  # overwintered
                None,  # confidential_assets
            )
        if not utils.BITCOIN_ONLY:
            if name == "Actinium":
                return CoinInfo(
                    name,  # coin_name
                    "ACM",  # coin_shortcut
                    8,  # decimals
                    53,  # address_type
                    55,  # address_type_p2sh
                    320000000000,  # maxfee_kb
                    "Actinium Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "acm",  # bech32_prefix
                    None,  # cashaddr_prefix
                    228,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Axe":
                return CoinInfo(
                    name,  # coin_name
                    "AXE",  # coin_shortcut
                    8,  # decimals
                    55,  # address_type
                    16,  # address_type_p2sh
                    21000000000,  # maxfee_kb
                    "DarkCoin Signed Message:\n",  # signed_message_header
                    0x02fe52cc,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    4242,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Bcash":
                return CoinInfo(
                    name,  # coin_name
                    "BCH",  # coin_shortcut
                    8,  # decimals
                    0,  # address_type
                    5,  # address_type_p2sh
                    14000000,  # maxfee_kb
                    "Bitcoin Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    "bitcoincash",  # cashaddr_prefix
                    145,  # slip44
                    False,  # segwit
                    False,  # taproot
                    0,  # fork_id
                    True,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Bcash Testnet":
                return CoinInfo(
                    name,  # coin_name
                    "TBCH",  # coin_shortcut
                    8,  # decimals
                    111,  # address_type
                    196,  # address_type_p2sh
                    10000000,  # maxfee_kb
                    "Bitcoin Signed Message:\n",  # signed_message_header
                    0x043587cf,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    "bchtest",  # cashaddr_prefix
                    1,  # slip44
                    False,  # segwit
                    False,  # taproot
                    0,  # fork_id
                    True,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Bprivate":
                return CoinInfo(
                    name,  # coin_name
                    "BTCP",  # coin_shortcut
                    8,  # decimals
                    4901,  # address_type
                    5039,  # address_type_p2sh
                    32000000000,  # maxfee_kb
                    "BitcoinPrivate Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    183,  # slip44
                    False,  # segwit
                    False,  # taproot
                    42,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Bitcore":
                return CoinInfo(
                    name,  # coin_name
                    "BTX",  # coin_shortcut
                    8,  # decimals
                    3,  # address_type
                    125,  # address_type_p2sh
                    14000000000,  # maxfee_kb
                    "BitCore Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "btx",  # bech32_prefix
                    None,  # cashaddr_prefix
                    160,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "CPUchain":
                return CoinInfo(
                    name,  # coin_name
                    "CPU",  # coin_shortcut
                    8,  # decimals
                    28,  # address_type
                    30,  # address_type_p2sh
                    8700000000000,  # maxfee_kb
                    "CPUchain Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "cpu",  # bech32_prefix
                    None,  # cashaddr_prefix
                    363,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Crown":
                return CoinInfo(
                    name,  # coin_name
                    "CRW",  # coin_shortcut
                    8,  # decimals
                    95495,  # address_type
                    95473,  # address_type_p2sh
                    52000000000,  # maxfee_kb
                    "Crown Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    72,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Dogecoin":
                return CoinInfo(
                    name,  # coin_name
                    "DOGE",  # coin_shortcut
                    8,  # decimals
                    30,  # address_type
                    22,  # address_type_p2sh
                    1200000000000,  # maxfee_kb
                    "Dogecoin Signed Message:\n",  # signed_message_header
                    0x02facafd,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    3,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Elements":
                return CoinInfo(
                    name,  # coin_name
                    "ELEMENTS",  # coin_shortcut
                    8,  # decimals
                    235,  # address_type
                    75,  # address_type_p2sh
                    10000000,  # maxfee_kb
                    "Bitcoin Signed Message:\n",  # signed_message_header
                    0x043587cf,  # xpub_magic
                    0x044a5262,  # xpub_magic_segwit_p2sh
                    0x045f1cf6,  # xpub_magic_segwit_native
                    0x043587cf,  # xpub_magic_multisig_segwit_p2sh
                    0x043587cf,  # xpub_magic_multisig_segwit_native
                    "ert",  # bech32_prefix
                    None,  # cashaddr_prefix
                    1,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    {'address_prefix': 4, 'blech32_prefix': 'el'},  # confidential_assets
                )
            if name == "Feathercoin":
                return CoinInfo(
                    name,  # coin_name
                    "FTC",  # coin_shortcut
                    8,  # decimals
                    14,  # address_type
                    5,  # address_type_p2sh
                    390000000000,  # maxfee_kb
                    "Feathercoin Signed Message:\n",  # signed_message_header
                    0x0488bc26,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488bc26,  # xpub_magic_multisig_segwit_p2sh
                    0x0488bc26,  # xpub_magic_multisig_segwit_native
                    "fc",  # bech32_prefix
                    None,  # cashaddr_prefix
                    8,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Firo":
                return CoinInfo(
                    name,  # coin_name
                    "FIRO",  # coin_shortcut
                    8,  # decimals
                    82,  # address_type
                    7,  # address_type_p2sh
                    640000000,  # maxfee_kb
                    "Zcoin Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    136,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    True,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Firo Testnet":
                return CoinInfo(
                    name,  # coin_name
                    "tFIRO",  # coin_shortcut
                    8,  # decimals
                    65,  # address_type
                    178,  # address_type_p2sh
                    1000000,  # maxfee_kb
                    "Zcoin Signed Message:\n",  # signed_message_header
                    0x043587cf,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    1,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    True,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Florincoin":
                return CoinInfo(
                    name,  # coin_name
                    "FLO",  # coin_shortcut
                    8,  # decimals
                    35,  # address_type
                    94,  # address_type_p2sh
                    78000000000,  # maxfee_kb
                    "Florincoin Signed Message:\n",  # signed_message_header
                    0x00174921,  # xpub_magic
                    0x01b26ef6,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x00174921,  # xpub_magic_multisig_segwit_p2sh
                    0x00174921,  # xpub_magic_multisig_segwit_native
                    "flo",  # bech32_prefix
                    None,  # cashaddr_prefix
                    216,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    True,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Fujicoin":
                return CoinInfo(
                    name,  # coin_name
                    "FJC",  # coin_shortcut
                    8,  # decimals
                    36,  # address_type
                    16,  # address_type_p2sh
                    35000000000000,  # maxfee_kb
                    "FujiCoin Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0295b43f,  # xpub_magic_multisig_segwit_p2sh
                    0x02aa7ed3,  # xpub_magic_multisig_segwit_native
                    "fc",  # bech32_prefix
                    None,  # cashaddr_prefix
                    75,  # slip44
                    True,  # segwit
                    True,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Groestlcoin":
                return CoinInfo(
                    name,  # coin_name
                    "GRS",  # coin_shortcut
                    8,  # decimals
                    36,  # address_type
                    5,  # address_type_p2sh
                    16000000000,  # maxfee_kb
                    "GroestlCoin Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "grs",  # bech32_prefix
                    None,  # cashaddr_prefix
                    17,  # slip44
                    True,  # segwit
                    True,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1-groestl',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Groestlcoin Testnet":
                return CoinInfo(
                    name,  # coin_name
                    "tGRS",  # coin_shortcut
                    8,  # decimals
                    111,  # address_type
                    196,  # address_type_p2sh
                    100000,  # maxfee_kb
                    "GroestlCoin Signed Message:\n",  # signed_message_header
                    0x043587cf,  # xpub_magic
                    0x044a5262,  # xpub_magic_segwit_p2sh
                    0x045f1cf6,  # xpub_magic_segwit_native
                    0x043587cf,  # xpub_magic_multisig_segwit_p2sh
                    0x043587cf,  # xpub_magic_multisig_segwit_native
                    "tgrs",  # bech32_prefix
                    None,  # cashaddr_prefix
                    1,  # slip44
                    True,  # segwit
                    True,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1-groestl',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Komodo":
                return CoinInfo(
                    name,  # coin_name
                    "KMD",  # coin_shortcut
                    8,  # decimals
                    60,  # address_type
                    85,  # address_type_p2sh
                    4800000000,  # maxfee_kb
                    "Komodo Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    141,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    True,  # negative_fee
                    'secp256k1',  # curve_name
                    True,  # extra_data
                    False,  # timestamp
                    True,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Koto":
                return CoinInfo(
                    name,  # coin_name
                    "KOTO",  # coin_shortcut
                    8,  # decimals
                    6198,  # address_type
                    6203,  # address_type_p2sh
                    1000000,  # maxfee_kb
                    "Koto Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    510,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    True,  # extra_data
                    False,  # timestamp
                    True,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Litecoin":
                return CoinInfo(
                    name,  # coin_name
                    "LTC",  # coin_shortcut
                    8,  # decimals
                    48,  # address_type
                    50,  # address_type_p2sh
                    67000000,  # maxfee_kb
                    "Litecoin Signed Message:\n",  # signed_message_header
                    0x019da462,  # xpub_magic
                    0x01b26ef6,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x019da462,  # xpub_magic_multisig_segwit_p2sh
                    0x019da462,  # xpub_magic_multisig_segwit_native
                    "ltc",  # bech32_prefix
                    None,  # cashaddr_prefix
                    2,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Litecoin Testnet":
                return CoinInfo(
                    name,  # coin_name
                    "tLTC",  # coin_shortcut
                    8,  # decimals
                    111,  # address_type
                    58,  # address_type_p2sh
                    40000000,  # maxfee_kb
                    "Litecoin Signed Message:\n",  # signed_message_header
                    0x043587cf,  # xpub_magic
                    0x044a5262,  # xpub_magic_segwit_p2sh
                    0x045f1cf6,  # xpub_magic_segwit_native
                    0x043587cf,  # xpub_magic_multisig_segwit_p2sh
                    0x043587cf,  # xpub_magic_multisig_segwit_native
                    "tltc",  # bech32_prefix
                    None,  # cashaddr_prefix
                    1,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Monacoin":
                return CoinInfo(
                    name,  # coin_name
                    "MONA",  # coin_shortcut
                    8,  # decimals
                    50,  # address_type
                    55,  # address_type_p2sh
                    2100000000,  # maxfee_kb
                    "Monacoin Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "mona",  # bech32_prefix
                    None,  # cashaddr_prefix
                    22,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Peercoin":
                return CoinInfo(
                    name,  # coin_name
                    "PPC",  # coin_shortcut
                    6,  # decimals
                    55,  # address_type
                    117,  # address_type_p2sh
                    13000000000,  # maxfee_kb
                    "Peercoin Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "pc",  # bech32_prefix
                    None,  # cashaddr_prefix
                    6,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    True,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Peercoin Testnet":
                return CoinInfo(
                    name,  # coin_name
                    "tPPC",  # coin_shortcut
                    6,  # decimals
                    111,  # address_type
                    196,  # address_type_p2sh
                    2000000,  # maxfee_kb
                    "Peercoin Signed Message:\n",  # signed_message_header
                    0x043587cf,  # xpub_magic
                    0x044a5262,  # xpub_magic_segwit_p2sh
                    0x045f1cf6,  # xpub_magic_segwit_native
                    0x043587cf,  # xpub_magic_multisig_segwit_p2sh
                    0x043587cf,  # xpub_magic_multisig_segwit_native
                    "tpc",  # bech32_prefix
                    None,  # cashaddr_prefix
                    1,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    True,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Primecoin":
                return CoinInfo(
                    name,  # coin_name
                    "XPM",  # coin_shortcut
                    8,  # decimals
                    23,  # address_type
                    83,  # address_type_p2sh
                    89000000000,  # maxfee_kb
                    "Primecoin Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    24,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Qtum":
                return CoinInfo(
                    name,  # coin_name
                    "QTUM",  # coin_shortcut
                    8,  # decimals
                    58,  # address_type
                    50,  # address_type_p2sh
                    1000000000,  # maxfee_kb
                    "Qtum Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "qc",  # bech32_prefix
                    None,  # cashaddr_prefix
                    2301,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Qtum Testnet":
                return CoinInfo(
                    name,  # coin_name
                    "tQTUM",  # coin_shortcut
                    8,  # decimals
                    120,  # address_type
                    110,  # address_type_p2sh
                    40000000,  # maxfee_kb
                    "Qtum Signed Message:\n",  # signed_message_header
                    0x043587cf,  # xpub_magic
                    0x044a5262,  # xpub_magic_segwit_p2sh
                    0x045f1cf6,  # xpub_magic_segwit_native
                    0x043587cf,  # xpub_magic_multisig_segwit_p2sh
                    0x043587cf,  # xpub_magic_multisig_segwit_native
                    "tq",  # bech32_prefix
                    None,  # cashaddr_prefix
                    1,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Ravencoin":
                return CoinInfo(
                    name,  # coin_name
                    "RVN",  # coin_shortcut
                    8,  # decimals
                    60,  # address_type
                    122,  # address_type_p2sh
                    170000000000,  # maxfee_kb
                    "Raven Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    175,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Ravencoin Testnet":
                return CoinInfo(
                    name,  # coin_name
                    "tRVN",  # coin_shortcut
                    8,  # decimals
                    111,  # address_type
                    196,  # address_type_p2sh
                    170000000000,  # maxfee_kb
                    "Raven Signed Message:\n",  # signed_message_header
                    0x043587cf,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    1,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Ritocoin":
                return CoinInfo(
                    name,  # coin_name
                    "RITO",  # coin_shortcut
                    8,  # decimals
                    25,  # address_type
                    105,  # address_type_p2sh
                    39000000000000,  # maxfee_kb
                    "Rito Signed Message:\n",  # signed_message_header
                    0x0534e7ca,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    19169,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "SmartCash":
                return CoinInfo(
                    name,  # coin_name
                    "SMART",  # coin_shortcut
                    8,  # decimals
                    63,  # address_type
                    18,  # address_type_p2sh
                    780000000000,  # maxfee_kb
                    "SmartCash Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    224,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1-smart',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "SmartCash Testnet":
                return CoinInfo(
                    name,  # coin_name
                    "tSMART",  # coin_shortcut
                    8,  # decimals
                    65,  # address_type
                    21,  # address_type_p2sh
                    1000000,  # maxfee_kb
                    "SmartCash Signed Message:\n",  # signed_message_header
                    0x043587cf,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    1,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1-smart',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Stakenet":
                return CoinInfo(
                    name,  # coin_name
                    "XSN",  # coin_shortcut
                    8,  # decimals
                    76,  # address_type
                    16,  # address_type_p2sh
                    11000000000,  # maxfee_kb
                    "DarkCoin Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "xc",  # bech32_prefix
                    None,  # cashaddr_prefix
                    199,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    True,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Syscoin":
                return CoinInfo(
                    name,  # coin_name
                    "SYS",  # coin_shortcut
                    8,  # decimals
                    63,  # address_type
                    5,  # address_type_p2sh
                    42000000000,  # maxfee_kb
                    "Syscoin Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "sys",  # bech32_prefix
                    None,  # cashaddr_prefix
                    57,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Unobtanium":
                return CoinInfo(
                    name,  # coin_name
                    "UNO",  # coin_shortcut
                    8,  # decimals
                    130,  # address_type
                    30,  # address_type_p2sh
                    53000000,  # maxfee_kb
                    "Unobtanium Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    92,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "VIPSTARCOIN":
                return CoinInfo(
                    name,  # coin_name
                    "VIPS",  # coin_shortcut
                    8,  # decimals
                    70,  # address_type
                    50,  # address_type_p2sh
                    140000000000000,  # maxfee_kb
                    "VIPSTARCOIN Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "vips",  # bech32_prefix
                    None,  # cashaddr_prefix
                    1919,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Verge":
                return CoinInfo(
                    name,  # coin_name
                    "XVG",  # coin_shortcut
                    6,  # decimals
                    30,  # address_type
                    33,  # address_type_p2sh
                    550000000000,  # maxfee_kb
                    "Name: Dogecoin Dark\n",  # signed_message_header
                    0x022d2533,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    77,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    True,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Viacoin":
                return CoinInfo(
                    name,  # coin_name
                    "VIA",  # coin_shortcut
                    8,  # decimals
                    71,  # address_type
                    33,  # address_type_p2sh
                    14000000000,  # maxfee_kb
                    "Viacoin Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "via",  # bech32_prefix
                    None,  # cashaddr_prefix
                    14,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "ZCore":
                return CoinInfo(
                    name,  # coin_name
                    "ZCR",  # coin_shortcut
                    8,  # decimals
                    142,  # address_type
                    145,  # address_type_p2sh
                    170000000000,  # maxfee_kb
                    "DarkNet Signed Message:\n",  # signed_message_header
                    0x04b24746,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    428,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Zcash":
                return CoinInfo(
                    name,  # coin_name
                    "ZEC",  # coin_shortcut
                    8,  # decimals
                    7352,  # address_type
                    7357,  # address_type_p2sh
                    51000000,  # maxfee_kb
                    "Zcash Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    133,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    True,  # extra_data
                    False,  # timestamp
                    True,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Zcash Testnet":
                return CoinInfo(
                    name,  # coin_name
                    "TAZ",  # coin_shortcut
                    8,  # decimals
                    7461,  # address_type
                    7354,  # address_type_p2sh
                    10000000,  # maxfee_kb
                    "Zcash Signed Message:\n",  # signed_message_header
                    0x043587cf,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    1,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    True,  # extra_data
                    False,  # timestamp
                    True,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Brhodium":
                return CoinInfo(
                    name,  # coin_name
                    "XRC",  # coin_shortcut
                    8,  # decimals
                    61,  # address_type
                    123,  # address_type_p2sh
                    1000000000,  # maxfee_kb
                    "BitCoin Rhodium Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    10291,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
        raise ValueError  # Unknown coin name
    if utils.INTERNAL_MODEL == "T2T1":
        if name == "Bitcoin":
            return CoinInfo(
                name,  # coin_name
                "BTC",  # coin_shortcut
                8,  # decimals
                0,  # address_type
                5,  # address_type_p2sh
                2000000,  # maxfee_kb
                "Bitcoin Signed Message:\n",  # signed_message_header
                0x0488b21e,  # xpub_magic
                0x049d7cb2,  # xpub_magic_segwit_p2sh
                0x04b24746,  # xpub_magic_segwit_native
                0x0295b43f,  # xpub_magic_multisig_segwit_p2sh
                0x02aa7ed3,  # xpub_magic_multisig_segwit_native
                "bc",  # bech32_prefix
                None,  # cashaddr_prefix
                0,  # slip44
                True,  # segwit
                True,  # taproot
                None,  # fork_id
                False,  # force_bip143
                False,  # decred
                False,  # negative_fee
                'secp256k1',  # curve_name
                False,  # extra_data
                False,  # timestamp
                False,  # overwintered
                None,  # confidential_assets
            )
        if name == "Regtest":
            return CoinInfo(
                name,  # coin_name
                "REGTEST",  # coin_shortcut
                8,  # decimals
                111,  # address_type
                196,  # address_type_p2sh
                10000000,  # maxfee_kb
                "Bitcoin Signed Message:\n",  # signed_message_header
                0x043587cf,  # xpub_magic
                0x044a5262,  # xpub_magic_segwit_p2sh
                0x045f1cf6,  # xpub_magic_segwit_native
                0x024289ef,  # xpub_magic_multisig_segwit_p2sh
                0x02575483,  # xpub_magic_multisig_segwit_native
                "bcrt",  # bech32_prefix
                None,  # cashaddr_prefix
                1,  # slip44
                True,  # segwit
                True,  # taproot
                None,  # fork_id
                False,  # force_bip143
                False,  # decred
                False,  # negative_fee
                'secp256k1',  # curve_name
                False,  # extra_data
                False,  # timestamp
                False,  # overwintered
                None,  # confidential_assets
            )
        if name == "Testnet":
            return CoinInfo(
                name,  # coin_name
                "TEST",  # coin_shortcut
                8,  # decimals
                111,  # address_type
                196,  # address_type_p2sh
                10000000,  # maxfee_kb
                "Bitcoin Signed Message:\n",  # signed_message_header
                0x043587cf,  # xpub_magic
                0x044a5262,  # xpub_magic_segwit_p2sh
                0x045f1cf6,  # xpub_magic_segwit_native
                0x024289ef,  # xpub_magic_multisig_segwit_p2sh
                0x02575483,  # xpub_magic_multisig_segwit_native
                "tb",  # bech32_prefix
                None,  # cashaddr_prefix
                1,  # slip44
                True,  # segwit
                True,  # taproot
                None,  # fork_id
                False,  # force_bip143
                False,  # decred
                False,  # negative_fee
                'secp256k1',  # curve_name
                False,  # extra_data
                False,  # timestamp
                False,  # overwintered
                None,  # confidential_assets
            )
        if not utils.BITCOIN_ONLY:
            if name == "Actinium":
                return CoinInfo(
                    name,  # coin_name
                    "ACM",  # coin_shortcut
                    8,  # decimals
                    53,  # address_type
                    55,  # address_type_p2sh
                    320000000000,  # maxfee_kb
                    "Actinium Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "acm",  # bech32_prefix
                    None,  # cashaddr_prefix
                    228,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Axe":
                return CoinInfo(
                    name,  # coin_name
                    "AXE",  # coin_shortcut
                    8,  # decimals
                    55,  # address_type
                    16,  # address_type_p2sh
                    21000000000,  # maxfee_kb
                    "DarkCoin Signed Message:\n",  # signed_message_header
                    0x02fe52cc,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    4242,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Bcash":
                return CoinInfo(
                    name,  # coin_name
                    "BCH",  # coin_shortcut
                    8,  # decimals
                    0,  # address_type
                    5,  # address_type_p2sh
                    14000000,  # maxfee_kb
                    "Bitcoin Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    "bitcoincash",  # cashaddr_prefix
                    145,  # slip44
                    False,  # segwit
                    False,  # taproot
                    0,  # fork_id
                    True,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Bcash Testnet":
                return CoinInfo(
                    name,  # coin_name
                    "TBCH",  # coin_shortcut
                    8,  # decimals
                    111,  # address_type
                    196,  # address_type_p2sh
                    10000000,  # maxfee_kb
                    "Bitcoin Signed Message:\n",  # signed_message_header
                    0x043587cf,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    "bchtest",  # cashaddr_prefix
                    1,  # slip44
                    False,  # segwit
                    False,  # taproot
                    0,  # fork_id
                    True,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Bgold":
                return CoinInfo(
                    name,  # coin_name
                    "BTG",  # coin_shortcut
                    8,  # decimals
                    38,  # address_type
                    23,  # address_type_p2sh
                    380000000,  # maxfee_kb
                    "Bitcoin Gold Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "btg",  # bech32_prefix
                    None,  # cashaddr_prefix
                    156,  # slip44
                    True,  # segwit
                    False,  # taproot
                    79,  # fork_id
                    True,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Bgold Testnet":
                return CoinInfo(
                    name,  # coin_name
                    "TBTG",  # coin_shortcut
                    8,  # decimals
                    111,  # address_type
                    196,  # address_type_p2sh
                    500000,  # maxfee_kb
                    "Bitcoin Gold Signed Message:\n",  # signed_message_header
                    0x043587cf,  # xpub_magic
                    0x044a5262,  # xpub_magic_segwit_p2sh
                    0x045f1cf6,  # xpub_magic_segwit_native
                    0x043587cf,  # xpub_magic_multisig_segwit_p2sh
                    0x043587cf,  # xpub_magic_multisig_segwit_native
                    "tbtg",  # bech32_prefix
                    None,  # cashaddr_prefix
                    1,  # slip44
                    True,  # segwit
                    False,  # taproot
                    79,  # fork_id
                    True,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Bprivate":
                return CoinInfo(
                    name,  # coin_name
                    "BTCP",  # coin_shortcut
                    8,  # decimals
                    4901,  # address_type
                    5039,  # address_type_p2sh
                    32000000000,  # maxfee_kb
                    "BitcoinPrivate Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    183,  # slip44
                    False,  # segwit
                    False,  # taproot
                    42,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Bitcore":
                return CoinInfo(
                    name,  # coin_name
                    "BTX",  # coin_shortcut
                    8,  # decimals
                    3,  # address_type
                    125,  # address_type_p2sh
                    14000000000,  # maxfee_kb
                    "BitCore Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "btx",  # bech32_prefix
                    None,  # cashaddr_prefix
                    160,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "CPUchain":
                return CoinInfo(
                    name,  # coin_name
                    "CPU",  # coin_shortcut
                    8,  # decimals
                    28,  # address_type
                    30,  # address_type_p2sh
                    8700000000000,  # maxfee_kb
                    "CPUchain Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "cpu",  # bech32_prefix
                    None,  # cashaddr_prefix
                    363,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Crown":
                return CoinInfo(
                    name,  # coin_name
                    "CRW",  # coin_shortcut
                    8,  # decimals
                    95495,  # address_type
                    95473,  # address_type_p2sh
                    52000000000,  # maxfee_kb
                    "Crown Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    72,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Dash":
                return CoinInfo(
                    name,  # coin_name
                    "DASH",  # coin_shortcut
                    8,  # decimals
                    76,  # address_type
                    16,  # address_type_p2sh
                    45000000,  # maxfee_kb
                    "DarkCoin Signed Message:\n",  # signed_message_header
                    0x02fe52cc,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    5,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    True,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Dash Testnet":
                return CoinInfo(
                    name,  # coin_name
                    "tDASH",  # coin_shortcut
                    8,  # decimals
                    140,  # address_type
                    19,  # address_type_p2sh
                    100000,  # maxfee_kb
                    "DarkCoin Signed Message:\n",  # signed_message_header
                    0x043587cf,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    1,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    True,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Decred":
                return CoinInfo(
                    name,  # coin_name
                    "DCR",  # coin_shortcut
                    8,  # decimals
                    1855,  # address_type
                    1818,  # address_type_p2sh
                    220000000,  # maxfee_kb
                    "Decred Signed Message:\n",  # signed_message_header
                    0x02fda926,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    42,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    True,  # decred
                    False,  # negative_fee
                    'secp256k1-decred',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Decred Testnet":
                return CoinInfo(
                    name,  # coin_name
                    "TDCR",  # coin_shortcut
                    8,  # decimals
                    3873,  # address_type
                    3836,  # address_type_p2sh
                    10000000,  # maxfee_kb
                    "Decred Signed Message:\n",  # signed_message_header
                    0x043587d1,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    1,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    True,  # decred
                    False,  # negative_fee
                    'secp256k1-decred',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "DigiByte":
                return CoinInfo(
                    name,  # coin_name
                    "DGB",  # coin_shortcut
                    8,  # decimals
                    30,  # address_type
                    63,  # address_type_p2sh
                    130000000000,  # maxfee_kb
                    "DigiByte Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "dgb",  # bech32_prefix
                    None,  # cashaddr_prefix
                    20,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Dogecoin":
                return CoinInfo(
                    name,  # coin_name
                    "DOGE",  # coin_shortcut
                    8,  # decimals
                    30,  # address_type
                    22,  # address_type_p2sh
                    1200000000000,  # maxfee_kb
                    "Dogecoin Signed Message:\n",  # signed_message_header
                    0x02facafd,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    3,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Elements":
                return CoinInfo(
                    name,  # coin_name
                    "ELEMENTS",  # coin_shortcut
                    8,  # decimals
                    235,  # address_type
                    75,  # address_type_p2sh
                    10000000,  # maxfee_kb
                    "Bitcoin Signed Message:\n",  # signed_message_header
                    0x043587cf,  # xpub_magic
                    0x044a5262,  # xpub_magic_segwit_p2sh
                    0x045f1cf6,  # xpub_magic_segwit_native
                    0x043587cf,  # xpub_magic_multisig_segwit_p2sh
                    0x043587cf,  # xpub_magic_multisig_segwit_native
                    "ert",  # bech32_prefix
                    None,  # cashaddr_prefix
                    1,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    {'address_prefix': 4, 'blech32_prefix': 'el'},  # confidential_assets
                )
            if name == "Feathercoin":
                return CoinInfo(
                    name,  # coin_name
                    "FTC",  # coin_shortcut
                    8,  # decimals
                    14,  # address_type
                    5,  # address_type_p2sh
                    390000000000,  # maxfee_kb
                    "Feathercoin Signed Message:\n",  # signed_message_header
                    0x0488bc26,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488bc26,  # xpub_magic_multisig_segwit_p2sh
                    0x0488bc26,  # xpub_magic_multisig_segwit_native
                    "fc",  # bech32_prefix
                    None,  # cashaddr_prefix
                    8,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Firo":
                return CoinInfo(
                    name,  # coin_name
                    "FIRO",  # coin_shortcut
                    8,  # decimals
                    82,  # address_type
                    7,  # address_type_p2sh
                    640000000,  # maxfee_kb
                    "Zcoin Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    136,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    True,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Firo Testnet":
                return CoinInfo(
                    name,  # coin_name
                    "tFIRO",  # coin_shortcut
                    8,  # decimals
                    65,  # address_type
                    178,  # address_type_p2sh
                    1000000,  # maxfee_kb
                    "Zcoin Signed Message:\n",  # signed_message_header
                    0x043587cf,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    1,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    True,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Florincoin":
                return CoinInfo(
                    name,  # coin_name
                    "FLO",  # coin_shortcut
                    8,  # decimals
                    35,  # address_type
                    94,  # address_type_p2sh
                    78000000000,  # maxfee_kb
                    "Florincoin Signed Message:\n",  # signed_message_header
                    0x00174921,  # xpub_magic
                    0x01b26ef6,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x00174921,  # xpub_magic_multisig_segwit_p2sh
                    0x00174921,  # xpub_magic_multisig_segwit_native
                    "flo",  # bech32_prefix
                    None,  # cashaddr_prefix
                    216,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    True,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Fujicoin":
                return CoinInfo(
                    name,  # coin_name
                    "FJC",  # coin_shortcut
                    8,  # decimals
                    36,  # address_type
                    16,  # address_type_p2sh
                    35000000000000,  # maxfee_kb
                    "FujiCoin Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0295b43f,  # xpub_magic_multisig_segwit_p2sh
                    0x02aa7ed3,  # xpub_magic_multisig_segwit_native
                    "fc",  # bech32_prefix
                    None,  # cashaddr_prefix
                    75,  # slip44
                    True,  # segwit
                    True,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Groestlcoin":
                return CoinInfo(
                    name,  # coin_name
                    "GRS",  # coin_shortcut
                    8,  # decimals
                    36,  # address_type
                    5,  # address_type_p2sh
                    16000000000,  # maxfee_kb
                    "GroestlCoin Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "grs",  # bech32_prefix
                    None,  # cashaddr_prefix
                    17,  # slip44
                    True,  # segwit
                    True,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1-groestl',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Groestlcoin Testnet":
                return CoinInfo(
                    name,  # coin_name
                    "tGRS",  # coin_shortcut
                    8,  # decimals
                    111,  # address_type
                    196,  # address_type_p2sh
                    100000,  # maxfee_kb
                    "GroestlCoin Signed Message:\n",  # signed_message_header
                    0x043587cf,  # xpub_magic
                    0x044a5262,  # xpub_magic_segwit_p2sh
                    0x045f1cf6,  # xpub_magic_segwit_native
                    0x043587cf,  # xpub_magic_multisig_segwit_p2sh
                    0x043587cf,  # xpub_magic_multisig_segwit_native
                    "tgrs",  # bech32_prefix
                    None,  # cashaddr_prefix
                    1,  # slip44
                    True,  # segwit
                    True,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1-groestl',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Komodo":
                return CoinInfo(
                    name,  # coin_name
                    "KMD",  # coin_shortcut
                    8,  # decimals
                    60,  # address_type
                    85,  # address_type_p2sh
                    4800000000,  # maxfee_kb
                    "Komodo Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    141,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    True,  # negative_fee
                    'secp256k1',  # curve_name
                    True,  # extra_data
                    False,  # timestamp
                    True,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Koto":
                return CoinInfo(
                    name,  # coin_name
                    "KOTO",  # coin_shortcut
                    8,  # decimals
                    6198,  # address_type
                    6203,  # address_type_p2sh
                    1000000,  # maxfee_kb
                    "Koto Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    510,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    True,  # extra_data
                    False,  # timestamp
                    True,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Litecoin":
                return CoinInfo(
                    name,  # coin_name
                    "LTC",  # coin_shortcut
                    8,  # decimals
                    48,  # address_type
                    50,  # address_type_p2sh
                    67000000,  # maxfee_kb
                    "Litecoin Signed Message:\n",  # signed_message_header
                    0x019da462,  # xpub_magic
                    0x01b26ef6,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x019da462,  # xpub_magic_multisig_segwit_p2sh
                    0x019da462,  # xpub_magic_multisig_segwit_native
                    "ltc",  # bech32_prefix
                    None,  # cashaddr_prefix
                    2,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Litecoin Testnet":
                return CoinInfo(
                    name,  # coin_name
                    "tLTC",  # coin_shortcut
                    8,  # decimals
                    111,  # address_type
                    58,  # address_type_p2sh
                    40000000,  # maxfee_kb
                    "Litecoin Signed Message:\n",  # signed_message_header
                    0x043587cf,  # xpub_magic
                    0x044a5262,  # xpub_magic_segwit_p2sh
                    0x045f1cf6,  # xpub_magic_segwit_native
                    0x043587cf,  # xpub_magic_multisig_segwit_p2sh
                    0x043587cf,  # xpub_magic_multisig_segwit_native
                    "tltc",  # bech32_prefix
                    None,  # cashaddr_prefix
                    1,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Monacoin":
                return CoinInfo(
                    name,  # coin_name
                    "MONA",  # coin_shortcut
                    8,  # decimals
                    50,  # address_type
                    55,  # address_type_p2sh
                    2100000000,  # maxfee_kb
                    "Monacoin Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "mona",  # bech32_prefix
                    None,  # cashaddr_prefix
                    22,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Namecoin":
                return CoinInfo(
                    name,  # coin_name
                    "NMC",  # coin_shortcut
                    8,  # decimals
                    52,  # address_type
                    5,  # address_type_p2sh
                    8700000000,  # maxfee_kb
                    "Namecoin Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    7,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Peercoin":
                return CoinInfo(
                    name,  # coin_name
                    "PPC",  # coin_shortcut
                    6,  # decimals
                    55,  # address_type
                    117,  # address_type_p2sh
                    13000000000,  # maxfee_kb
                    "Peercoin Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "pc",  # bech32_prefix
                    None,  # cashaddr_prefix
                    6,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    True,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Peercoin Testnet":
                return CoinInfo(
                    name,  # coin_name
                    "tPPC",  # coin_shortcut
                    6,  # decimals
                    111,  # address_type
                    196,  # address_type_p2sh
                    2000000,  # maxfee_kb
                    "Peercoin Signed Message:\n",  # signed_message_header
                    0x043587cf,  # xpub_magic
                    0x044a5262,  # xpub_magic_segwit_p2sh
                    0x045f1cf6,  # xpub_magic_segwit_native
                    0x043587cf,  # xpub_magic_multisig_segwit_p2sh
                    0x043587cf,  # xpub_magic_multisig_segwit_native
                    "tpc",  # bech32_prefix
                    None,  # cashaddr_prefix
                    1,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    True,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Primecoin":
                return CoinInfo(
                    name,  # coin_name
                    "XPM",  # coin_shortcut
                    8,  # decimals
                    23,  # address_type
                    83,  # address_type_p2sh
                    89000000000,  # maxfee_kb
                    "Primecoin Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    24,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Qtum":
                return CoinInfo(
                    name,  # coin_name
                    "QTUM",  # coin_shortcut
                    8,  # decimals
                    58,  # address_type
                    50,  # address_type_p2sh
                    1000000000,  # maxfee_kb
                    "Qtum Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "qc",  # bech32_prefix
                    None,  # cashaddr_prefix
                    2301,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Qtum Testnet":
                return CoinInfo(
                    name,  # coin_name
                    "tQTUM",  # coin_shortcut
                    8,  # decimals
                    120,  # address_type
                    110,  # address_type_p2sh
                    40000000,  # maxfee_kb
                    "Qtum Signed Message:\n",  # signed_message_header
                    0x043587cf,  # xpub_magic
                    0x044a5262,  # xpub_magic_segwit_p2sh
                    0x045f1cf6,  # xpub_magic_segwit_native
                    0x043587cf,  # xpub_magic_multisig_segwit_p2sh
                    0x043587cf,  # xpub_magic_multisig_segwit_native
                    "tq",  # bech32_prefix
                    None,  # cashaddr_prefix
                    1,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Ravencoin":
                return CoinInfo(
                    name,  # coin_name
                    "RVN",  # coin_shortcut
                    8,  # decimals
                    60,  # address_type
                    122,  # address_type_p2sh
                    170000000000,  # maxfee_kb
                    "Raven Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    175,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Ravencoin Testnet":
                return CoinInfo(
                    name,  # coin_name
                    "tRVN",  # coin_shortcut
                    8,  # decimals
                    111,  # address_type
                    196,  # address_type_p2sh
                    170000000000,  # maxfee_kb
                    "Raven Signed Message:\n",  # signed_message_header
                    0x043587cf,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    1,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Ritocoin":
                return CoinInfo(
                    name,  # coin_name
                    "RITO",  # coin_shortcut
                    8,  # decimals
                    25,  # address_type
                    105,  # address_type_p2sh
                    39000000000000,  # maxfee_kb
                    "Rito Signed Message:\n",  # signed_message_header
                    0x0534e7ca,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    19169,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "SmartCash":
                return CoinInfo(
                    name,  # coin_name
                    "SMART",  # coin_shortcut
                    8,  # decimals
                    63,  # address_type
                    18,  # address_type_p2sh
                    780000000000,  # maxfee_kb
                    "SmartCash Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    224,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1-smart',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "SmartCash Testnet":
                return CoinInfo(
                    name,  # coin_name
                    "tSMART",  # coin_shortcut
                    8,  # decimals
                    65,  # address_type
                    21,  # address_type_p2sh
                    1000000,  # maxfee_kb
                    "SmartCash Signed Message:\n",  # signed_message_header
                    0x043587cf,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    1,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1-smart',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Stakenet":
                return CoinInfo(
                    name,  # coin_name
                    "XSN",  # coin_shortcut
                    8,  # decimals
                    76,  # address_type
                    16,  # address_type_p2sh
                    11000000000,  # maxfee_kb
                    "DarkCoin Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "xc",  # bech32_prefix
                    None,  # cashaddr_prefix
                    199,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    True,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Syscoin":
                return CoinInfo(
                    name,  # coin_name
                    "SYS",  # coin_shortcut
                    8,  # decimals
                    63,  # address_type
                    5,  # address_type_p2sh
                    42000000000,  # maxfee_kb
                    "Syscoin Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "sys",  # bech32_prefix
                    None,  # cashaddr_prefix
                    57,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Unobtanium":
                return CoinInfo(
                    name,  # coin_name
                    "UNO",  # coin_shortcut
                    8,  # decimals
                    130,  # address_type
                    30,  # address_type_p2sh
                    53000000,  # maxfee_kb
                    "Unobtanium Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    92,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "VIPSTARCOIN":
                return CoinInfo(
                    name,  # coin_name
                    "VIPS",  # coin_shortcut
                    8,  # decimals
                    70,  # address_type
                    50,  # address_type_p2sh
                    140000000000000,  # maxfee_kb
                    "VIPSTARCOIN Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "vips",  # bech32_prefix
                    None,  # cashaddr_prefix
                    1919,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Verge":
                return CoinInfo(
                    name,  # coin_name
                    "XVG",  # coin_shortcut
                    6,  # decimals
                    30,  # address_type
                    33,  # address_type_p2sh
                    550000000000,  # maxfee_kb
                    "Name: Dogecoin Dark\n",  # signed_message_header
                    0x022d2533,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    77,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    True,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Vertcoin":
                return CoinInfo(
                    name,  # coin_name
                    "VTC",  # coin_shortcut
                    8,  # decimals
                    71,  # address_type
                    5,  # address_type_p2sh
                    13000000000,  # maxfee_kb
                    "Vertcoin Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "vtc",  # bech32_prefix
                    None,  # cashaddr_prefix
                    28,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Viacoin":
                return CoinInfo(
                    name,  # coin_name
                    "VIA",  # coin_shortcut
                    8,  # decimals
                    71,  # address_type
                    33,  # address_type_p2sh
                    14000000000,  # maxfee_kb
                    "Viacoin Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "via",  # bech32_prefix
                    None,  # cashaddr_prefix
                    14,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "ZCore":
                return CoinInfo(
                    name,  # coin_name
                    "ZCR",  # coin_shortcut
                    8,  # decimals
                    142,  # address_type
                    145,  # address_type_p2sh
                    170000000000,  # maxfee_kb
                    "DarkNet Signed Message:\n",  # signed_message_header
                    0x04b24746,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    428,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Zcash":
                return CoinInfo(
                    name,  # coin_name
                    "ZEC",  # coin_shortcut
                    8,  # decimals
                    7352,  # address_type
                    7357,  # address_type_p2sh
                    51000000,  # maxfee_kb
                    "Zcash Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    133,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    True,  # extra_data
                    False,  # timestamp
                    True,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Zcash Testnet":
                return CoinInfo(
                    name,  # coin_name
                    "TAZ",  # coin_shortcut
                    8,  # decimals
                    7461,  # address_type
                    7354,  # address_type_p2sh
                    10000000,  # maxfee_kb
                    "Zcash Signed Message:\n",  # signed_message_header
                    0x043587cf,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    1,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    True,  # extra_data
                    False,  # timestamp
                    True,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Brhodium":
                return CoinInfo(
                    name,  # coin_name
                    "XRC",  # coin_shortcut
                    8,  # decimals
                    61,  # address_type
                    123,  # address_type_p2sh
                    1000000000,  # maxfee_kb
                    "BitCoin Rhodium Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    10291,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
        raise ValueError  # Unknown coin name
    if utils.INTERNAL_MODEL == "T3B1":
        if name == "Bitcoin":
            return CoinInfo(
                name,  # coin_name
                "BTC",  # coin_shortcut
                8,  # decimals
                0,  # address_type
                5,  # address_type_p2sh
                2000000,  # maxfee_kb
                "Bitcoin Signed Message:\n",  # signed_message_header
                0x0488b21e,  # xpub_magic
                0x049d7cb2,  # xpub_magic_segwit_p2sh
                0x04b24746,  # xpub_magic_segwit_native
                0x0295b43f,  # xpub_magic_multisig_segwit_p2sh
                0x02aa7ed3,  # xpub_magic_multisig_segwit_native
                "bc",  # bech32_prefix
                None,  # cashaddr_prefix
                0,  # slip44
                True,  # segwit
                True,  # taproot
                None,  # fork_id
                False,  # force_bip143
                False,  # decred
                False,  # negative_fee
                'secp256k1',  # curve_name
                False,  # extra_data
                False,  # timestamp
                False,  # overwintered
                None,  # confidential_assets
            )
        if name == "Regtest":
            return CoinInfo(
                name,  # coin_name
                "REGTEST",  # coin_shortcut
                8,  # decimals
                111,  # address_type
                196,  # address_type_p2sh
                10000000,  # maxfee_kb
                "Bitcoin Signed Message:\n",  # signed_message_header
                0x043587cf,  # xpub_magic
                0x044a5262,  # xpub_magic_segwit_p2sh
                0x045f1cf6,  # xpub_magic_segwit_native
                0x024289ef,  # xpub_magic_multisig_segwit_p2sh
                0x02575483,  # xpub_magic_multisig_segwit_native
                "bcrt",  # bech32_prefix
                None,  # cashaddr_prefix
                1,  # slip44
                True,  # segwit
                True,  # taproot
                None,  # fork_id
                False,  # force_bip143
                False,  # decred
                False,  # negative_fee
                'secp256k1',  # curve_name
                False,  # extra_data
                False,  # timestamp
                False,  # overwintered
                None,  # confidential_assets
            )
        if name == "Testnet":
            return CoinInfo(
                name,  # coin_name
                "TEST",  # coin_shortcut
                8,  # decimals
                111,  # address_type
                196,  # address_type_p2sh
                10000000,  # maxfee_kb
                "Bitcoin Signed Message:\n",  # signed_message_header
                0x043587cf,  # xpub_magic
                0x044a5262,  # xpub_magic_segwit_p2sh
                0x045f1cf6,  # xpub_magic_segwit_native
                0x024289ef,  # xpub_magic_multisig_segwit_p2sh
                0x02575483,  # xpub_magic_multisig_segwit_native
                "tb",  # bech32_prefix
                None,  # cashaddr_prefix
                1,  # slip44
                True,  # segwit
                True,  # taproot
                None,  # fork_id
                False,  # force_bip143
                False,  # decred
                False,  # negative_fee
                'secp256k1',  # curve_name
                False,  # extra_data
                False,  # timestamp
                False,  # overwintered
                None,  # confidential_assets
            )
        if not utils.BITCOIN_ONLY:
            if name == "Actinium":
                return CoinInfo(
                    name,  # coin_name
                    "ACM",  # coin_shortcut
                    8,  # decimals
                    53,  # address_type
                    55,  # address_type_p2sh
                    320000000000,  # maxfee_kb
                    "Actinium Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "acm",  # bech32_prefix
                    None,  # cashaddr_prefix
                    228,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Axe":
                return CoinInfo(
                    name,  # coin_name
                    "AXE",  # coin_shortcut
                    8,  # decimals
                    55,  # address_type
                    16,  # address_type_p2sh
                    21000000000,  # maxfee_kb
                    "DarkCoin Signed Message:\n",  # signed_message_header
                    0x02fe52cc,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    4242,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Bcash":
                return CoinInfo(
                    name,  # coin_name
                    "BCH",  # coin_shortcut
                    8,  # decimals
                    0,  # address_type
                    5,  # address_type_p2sh
                    14000000,  # maxfee_kb
                    "Bitcoin Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    "bitcoincash",  # cashaddr_prefix
                    145,  # slip44
                    False,  # segwit
                    False,  # taproot
                    0,  # fork_id
                    True,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Bcash Testnet":
                return CoinInfo(
                    name,  # coin_name
                    "TBCH",  # coin_shortcut
                    8,  # decimals
                    111,  # address_type
                    196,  # address_type_p2sh
                    10000000,  # maxfee_kb
                    "Bitcoin Signed Message:\n",  # signed_message_header
                    0x043587cf,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    "bchtest",  # cashaddr_prefix
                    1,  # slip44
                    False,  # segwit
                    False,  # taproot
                    0,  # fork_id
                    True,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Bprivate":
                return CoinInfo(
                    name,  # coin_name
                    "BTCP",  # coin_shortcut
                    8,  # decimals
                    4901,  # address_type
                    5039,  # address_type_p2sh
                    32000000000,  # maxfee_kb
                    "BitcoinPrivate Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    183,  # slip44
                    False,  # segwit
                    False,  # taproot
                    42,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Bitcore":
                return CoinInfo(
                    name,  # coin_name
                    "BTX",  # coin_shortcut
                    8,  # decimals
                    3,  # address_type
                    125,  # address_type_p2sh
                    14000000000,  # maxfee_kb
                    "BitCore Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "btx",  # bech32_prefix
                    None,  # cashaddr_prefix
                    160,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "CPUchain":
                return CoinInfo(
                    name,  # coin_name
                    "CPU",  # coin_shortcut
                    8,  # decimals
                    28,  # address_type
                    30,  # address_type_p2sh
                    8700000000000,  # maxfee_kb
                    "CPUchain Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "cpu",  # bech32_prefix
                    None,  # cashaddr_prefix
                    363,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Crown":
                return CoinInfo(
                    name,  # coin_name
                    "CRW",  # coin_shortcut
                    8,  # decimals
                    95495,  # address_type
                    95473,  # address_type_p2sh
                    52000000000,  # maxfee_kb
                    "Crown Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    72,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Dogecoin":
                return CoinInfo(
                    name,  # coin_name
                    "DOGE",  # coin_shortcut
                    8,  # decimals
                    30,  # address_type
                    22,  # address_type_p2sh
                    1200000000000,  # maxfee_kb
                    "Dogecoin Signed Message:\n",  # signed_message_header
                    0x02facafd,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    3,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Elements":
                return CoinInfo(
                    name,  # coin_name
                    "ELEMENTS",  # coin_shortcut
                    8,  # decimals
                    235,  # address_type
                    75,  # address_type_p2sh
                    10000000,  # maxfee_kb
                    "Bitcoin Signed Message:\n",  # signed_message_header
                    0x043587cf,  # xpub_magic
                    0x044a5262,  # xpub_magic_segwit_p2sh
                    0x045f1cf6,  # xpub_magic_segwit_native
                    0x043587cf,  # xpub_magic_multisig_segwit_p2sh
                    0x043587cf,  # xpub_magic_multisig_segwit_native
                    "ert",  # bech32_prefix
                    None,  # cashaddr_prefix
                    1,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    {'address_prefix': 4, 'blech32_prefix': 'el'},  # confidential_assets
                )
            if name == "Feathercoin":
                return CoinInfo(
                    name,  # coin_name
                    "FTC",  # coin_shortcut
                    8,  # decimals
                    14,  # address_type
                    5,  # address_type_p2sh
                    390000000000,  # maxfee_kb
                    "Feathercoin Signed Message:\n",  # signed_message_header
                    0x0488bc26,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488bc26,  # xpub_magic_multisig_segwit_p2sh
                    0x0488bc26,  # xpub_magic_multisig_segwit_native
                    "fc",  # bech32_prefix
                    None,  # cashaddr_prefix
                    8,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Firo":
                return CoinInfo(
                    name,  # coin_name
                    "FIRO",  # coin_shortcut
                    8,  # decimals
                    82,  # address_type
                    7,  # address_type_p2sh
                    640000000,  # maxfee_kb
                    "Zcoin Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    136,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    True,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Firo Testnet":
                return CoinInfo(
                    name,  # coin_name
                    "tFIRO",  # coin_shortcut
                    8,  # decimals
                    65,  # address_type
                    178,  # address_type_p2sh
                    1000000,  # maxfee_kb
                    "Zcoin Signed Message:\n",  # signed_message_header
                    0x043587cf,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    1,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    True,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Florincoin":
                return CoinInfo(
                    name,  # coin_name
                    "FLO",  # coin_shortcut
                    8,  # decimals
                    35,  # address_type
                    94,  # address_type_p2sh
                    78000000000,  # maxfee_kb
                    "Florincoin Signed Message:\n",  # signed_message_header
                    0x00174921,  # xpub_magic
                    0x01b26ef6,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x00174921,  # xpub_magic_multisig_segwit_p2sh
                    0x00174921,  # xpub_magic_multisig_segwit_native
                    "flo",  # bech32_prefix
                    None,  # cashaddr_prefix
                    216,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    True,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Fujicoin":
                return CoinInfo(
                    name,  # coin_name
                    "FJC",  # coin_shortcut
                    8,  # decimals
                    36,  # address_type
                    16,  # address_type_p2sh
                    35000000000000,  # maxfee_kb
                    "FujiCoin Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0295b43f,  # xpub_magic_multisig_segwit_p2sh
                    0x02aa7ed3,  # xpub_magic_multisig_segwit_native
                    "fc",  # bech32_prefix
                    None,  # cashaddr_prefix
                    75,  # slip44
                    True,  # segwit
                    True,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Groestlcoin":
                return CoinInfo(
                    name,  # coin_name
                    "GRS",  # coin_shortcut
                    8,  # decimals
                    36,  # address_type
                    5,  # address_type_p2sh
                    16000000000,  # maxfee_kb
                    "GroestlCoin Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "grs",  # bech32_prefix
                    None,  # cashaddr_prefix
                    17,  # slip44
                    True,  # segwit
                    True,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1-groestl',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Groestlcoin Testnet":
                return CoinInfo(
                    name,  # coin_name
                    "tGRS",  # coin_shortcut
                    8,  # decimals
                    111,  # address_type
                    196,  # address_type_p2sh
                    100000,  # maxfee_kb
                    "GroestlCoin Signed Message:\n",  # signed_message_header
                    0x043587cf,  # xpub_magic
                    0x044a5262,  # xpub_magic_segwit_p2sh
                    0x045f1cf6,  # xpub_magic_segwit_native
                    0x043587cf,  # xpub_magic_multisig_segwit_p2sh
                    0x043587cf,  # xpub_magic_multisig_segwit_native
                    "tgrs",  # bech32_prefix
                    None,  # cashaddr_prefix
                    1,  # slip44
                    True,  # segwit
                    True,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1-groestl',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Komodo":
                return CoinInfo(
                    name,  # coin_name
                    "KMD",  # coin_shortcut
                    8,  # decimals
                    60,  # address_type
                    85,  # address_type_p2sh
                    4800000000,  # maxfee_kb
                    "Komodo Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    141,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    True,  # negative_fee
                    'secp256k1',  # curve_name
                    True,  # extra_data
                    False,  # timestamp
                    True,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Koto":
                return CoinInfo(
                    name,  # coin_name
                    "KOTO",  # coin_shortcut
                    8,  # decimals
                    6198,  # address_type
                    6203,  # address_type_p2sh
                    1000000,  # maxfee_kb
                    "Koto Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    510,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    True,  # extra_data
                    False,  # timestamp
                    True,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Litecoin":
                return CoinInfo(
                    name,  # coin_name
                    "LTC",  # coin_shortcut
                    8,  # decimals
                    48,  # address_type
                    50,  # address_type_p2sh
                    67000000,  # maxfee_kb
                    "Litecoin Signed Message:\n",  # signed_message_header
                    0x019da462,  # xpub_magic
                    0x01b26ef6,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x019da462,  # xpub_magic_multisig_segwit_p2sh
                    0x019da462,  # xpub_magic_multisig_segwit_native
                    "ltc",  # bech32_prefix
                    None,  # cashaddr_prefix
                    2,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Litecoin Testnet":
                return CoinInfo(
                    name,  # coin_name
                    "tLTC",  # coin_shortcut
                    8,  # decimals
                    111,  # address_type
                    58,  # address_type_p2sh
                    40000000,  # maxfee_kb
                    "Litecoin Signed Message:\n",  # signed_message_header
                    0x043587cf,  # xpub_magic
                    0x044a5262,  # xpub_magic_segwit_p2sh
                    0x045f1cf6,  # xpub_magic_segwit_native
                    0x043587cf,  # xpub_magic_multisig_segwit_p2sh
                    0x043587cf,  # xpub_magic_multisig_segwit_native
                    "tltc",  # bech32_prefix
                    None,  # cashaddr_prefix
                    1,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Monacoin":
                return CoinInfo(
                    name,  # coin_name
                    "MONA",  # coin_shortcut
                    8,  # decimals
                    50,  # address_type
                    55,  # address_type_p2sh
                    2100000000,  # maxfee_kb
                    "Monacoin Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "mona",  # bech32_prefix
                    None,  # cashaddr_prefix
                    22,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Peercoin":
                return CoinInfo(
                    name,  # coin_name
                    "PPC",  # coin_shortcut
                    6,  # decimals
                    55,  # address_type
                    117,  # address_type_p2sh
                    13000000000,  # maxfee_kb
                    "Peercoin Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "pc",  # bech32_prefix
                    None,  # cashaddr_prefix
                    6,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    True,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Peercoin Testnet":
                return CoinInfo(
                    name,  # coin_name
                    "tPPC",  # coin_shortcut
                    6,  # decimals
                    111,  # address_type
                    196,  # address_type_p2sh
                    2000000,  # maxfee_kb
                    "Peercoin Signed Message:\n",  # signed_message_header
                    0x043587cf,  # xpub_magic
                    0x044a5262,  # xpub_magic_segwit_p2sh
                    0x045f1cf6,  # xpub_magic_segwit_native
                    0x043587cf,  # xpub_magic_multisig_segwit_p2sh
                    0x043587cf,  # xpub_magic_multisig_segwit_native
                    "tpc",  # bech32_prefix
                    None,  # cashaddr_prefix
                    1,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    True,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Primecoin":
                return CoinInfo(
                    name,  # coin_name
                    "XPM",  # coin_shortcut
                    8,  # decimals
                    23,  # address_type
                    83,  # address_type_p2sh
                    89000000000,  # maxfee_kb
                    "Primecoin Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    24,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Qtum":
                return CoinInfo(
                    name,  # coin_name
                    "QTUM",  # coin_shortcut
                    8,  # decimals
                    58,  # address_type
                    50,  # address_type_p2sh
                    1000000000,  # maxfee_kb
                    "Qtum Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "qc",  # bech32_prefix
                    None,  # cashaddr_prefix
                    2301,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Qtum Testnet":
                return CoinInfo(
                    name,  # coin_name
                    "tQTUM",  # coin_shortcut
                    8,  # decimals
                    120,  # address_type
                    110,  # address_type_p2sh
                    40000000,  # maxfee_kb
                    "Qtum Signed Message:\n",  # signed_message_header
                    0x043587cf,  # xpub_magic
                    0x044a5262,  # xpub_magic_segwit_p2sh
                    0x045f1cf6,  # xpub_magic_segwit_native
                    0x043587cf,  # xpub_magic_multisig_segwit_p2sh
                    0x043587cf,  # xpub_magic_multisig_segwit_native
                    "tq",  # bech32_prefix
                    None,  # cashaddr_prefix
                    1,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Ravencoin":
                return CoinInfo(
                    name,  # coin_name
                    "RVN",  # coin_shortcut
                    8,  # decimals
                    60,  # address_type
                    122,  # address_type_p2sh
                    170000000000,  # maxfee_kb
                    "Raven Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    175,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Ravencoin Testnet":
                return CoinInfo(
                    name,  # coin_name
                    "tRVN",  # coin_shortcut
                    8,  # decimals
                    111,  # address_type
                    196,  # address_type_p2sh
                    170000000000,  # maxfee_kb
                    "Raven Signed Message:\n",  # signed_message_header
                    0x043587cf,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    1,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Ritocoin":
                return CoinInfo(
                    name,  # coin_name
                    "RITO",  # coin_shortcut
                    8,  # decimals
                    25,  # address_type
                    105,  # address_type_p2sh
                    39000000000000,  # maxfee_kb
                    "Rito Signed Message:\n",  # signed_message_header
                    0x0534e7ca,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    19169,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "SmartCash":
                return CoinInfo(
                    name,  # coin_name
                    "SMART",  # coin_shortcut
                    8,  # decimals
                    63,  # address_type
                    18,  # address_type_p2sh
                    780000000000,  # maxfee_kb
                    "SmartCash Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    224,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1-smart',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "SmartCash Testnet":
                return CoinInfo(
                    name,  # coin_name
                    "tSMART",  # coin_shortcut
                    8,  # decimals
                    65,  # address_type
                    21,  # address_type_p2sh
                    1000000,  # maxfee_kb
                    "SmartCash Signed Message:\n",  # signed_message_header
                    0x043587cf,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    1,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1-smart',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Stakenet":
                return CoinInfo(
                    name,  # coin_name
                    "XSN",  # coin_shortcut
                    8,  # decimals
                    76,  # address_type
                    16,  # address_type_p2sh
                    11000000000,  # maxfee_kb
                    "DarkCoin Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "xc",  # bech32_prefix
                    None,  # cashaddr_prefix
                    199,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    True,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Syscoin":
                return CoinInfo(
                    name,  # coin_name
                    "SYS",  # coin_shortcut
                    8,  # decimals
                    63,  # address_type
                    5,  # address_type_p2sh
                    42000000000,  # maxfee_kb
                    "Syscoin Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "sys",  # bech32_prefix
                    None,  # cashaddr_prefix
                    57,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Unobtanium":
                return CoinInfo(
                    name,  # coin_name
                    "UNO",  # coin_shortcut
                    8,  # decimals
                    130,  # address_type
                    30,  # address_type_p2sh
                    53000000,  # maxfee_kb
                    "Unobtanium Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    92,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "VIPSTARCOIN":
                return CoinInfo(
                    name,  # coin_name
                    "VIPS",  # coin_shortcut
                    8,  # decimals
                    70,  # address_type
                    50,  # address_type_p2sh
                    140000000000000,  # maxfee_kb
                    "VIPSTARCOIN Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "vips",  # bech32_prefix
                    None,  # cashaddr_prefix
                    1919,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Verge":
                return CoinInfo(
                    name,  # coin_name
                    "XVG",  # coin_shortcut
                    6,  # decimals
                    30,  # address_type
                    33,  # address_type_p2sh
                    550000000000,  # maxfee_kb
                    "Name: Dogecoin Dark\n",  # signed_message_header
                    0x022d2533,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    77,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    True,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Viacoin":
                return CoinInfo(
                    name,  # coin_name
                    "VIA",  # coin_shortcut
                    8,  # decimals
                    71,  # address_type
                    33,  # address_type_p2sh
                    14000000000,  # maxfee_kb
                    "Viacoin Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "via",  # bech32_prefix
                    None,  # cashaddr_prefix
                    14,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "ZCore":
                return CoinInfo(
                    name,  # coin_name
                    "ZCR",  # coin_shortcut
                    8,  # decimals
                    142,  # address_type
                    145,  # address_type_p2sh
                    170000000000,  # maxfee_kb
                    "DarkNet Signed Message:\n",  # signed_message_header
                    0x04b24746,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    428,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Zcash":
                return CoinInfo(
                    name,  # coin_name
                    "ZEC",  # coin_shortcut
                    8,  # decimals
                    7352,  # address_type
                    7357,  # address_type_p2sh
                    51000000,  # maxfee_kb
                    "Zcash Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    133,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    True,  # extra_data
                    False,  # timestamp
                    True,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Zcash Testnet":
                return CoinInfo(
                    name,  # coin_name
                    "TAZ",  # coin_shortcut
                    8,  # decimals
                    7461,  # address_type
                    7354,  # address_type_p2sh
                    10000000,  # maxfee_kb
                    "Zcash Signed Message:\n",  # signed_message_header
                    0x043587cf,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    1,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    True,  # extra_data
                    False,  # timestamp
                    True,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Brhodium":
                return CoinInfo(
                    name,  # coin_name
                    "XRC",  # coin_shortcut
                    8,  # decimals
                    61,  # address_type
                    123,  # address_type_p2sh
                    1000000000,  # maxfee_kb
                    "BitCoin Rhodium Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    10291,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
        raise ValueError  # Unknown coin name
    if utils.INTERNAL_MODEL == "T3T1":
        if name == "Bitcoin":
            return CoinInfo(
                name,  # coin_name
                "BTC",  # coin_shortcut
                8,  # decimals
                0,  # address_type
                5,  # address_type_p2sh
                2000000,  # maxfee_kb
                "Bitcoin Signed Message:\n",  # signed_message_header
                0x0488b21e,  # xpub_magic
                0x049d7cb2,  # xpub_magic_segwit_p2sh
                0x04b24746,  # xpub_magic_segwit_native
                0x0295b43f,  # xpub_magic_multisig_segwit_p2sh
                0x02aa7ed3,  # xpub_magic_multisig_segwit_native
                "bc",  # bech32_prefix
                None,  # cashaddr_prefix
                0,  # slip44
                True,  # segwit
                True,  # taproot
                None,  # fork_id
                False,  # force_bip143
                False,  # decred
                False,  # negative_fee
                'secp256k1',  # curve_name
                False,  # extra_data
                False,  # timestamp
                False,  # overwintered
                None,  # confidential_assets
            )
        if name == "Regtest":
            return CoinInfo(
                name,  # coin_name
                "REGTEST",  # coin_shortcut
                8,  # decimals
                111,  # address_type
                196,  # address_type_p2sh
                10000000,  # maxfee_kb
                "Bitcoin Signed Message:\n",  # signed_message_header
                0x043587cf,  # xpub_magic
                0x044a5262,  # xpub_magic_segwit_p2sh
                0x045f1cf6,  # xpub_magic_segwit_native
                0x024289ef,  # xpub_magic_multisig_segwit_p2sh
                0x02575483,  # xpub_magic_multisig_segwit_native
                "bcrt",  # bech32_prefix
                None,  # cashaddr_prefix
                1,  # slip44
                True,  # segwit
                True,  # taproot
                None,  # fork_id
                False,  # force_bip143
                False,  # decred
                False,  # negative_fee
                'secp256k1',  # curve_name
                False,  # extra_data
                False,  # timestamp
                False,  # overwintered
                None,  # confidential_assets
            )
        if name == "Testnet":
            return CoinInfo(
                name,  # coin_name
                "TEST",  # coin_shortcut
                8,  # decimals
                111,  # address_type
                196,  # address_type_p2sh
                10000000,  # maxfee_kb
                "Bitcoin Signed Message:\n",  # signed_message_header
                0x043587cf,  # xpub_magic
                0x044a5262,  # xpub_magic_segwit_p2sh
                0x045f1cf6,  # xpub_magic_segwit_native
                0x024289ef,  # xpub_magic_multisig_segwit_p2sh
                0x02575483,  # xpub_magic_multisig_segwit_native
                "tb",  # bech32_prefix
                None,  # cashaddr_prefix
                1,  # slip44
                True,  # segwit
                True,  # taproot
                None,  # fork_id
                False,  # force_bip143
                False,  # decred
                False,  # negative_fee
                'secp256k1',  # curve_name
                False,  # extra_data
                False,  # timestamp
                False,  # overwintered
                None,  # confidential_assets
            )
        if not utils.BITCOIN_ONLY:
            if name == "Actinium":
                return CoinInfo(
                    name,  # coin_name
                    "ACM",  # coin_shortcut
                    8,  # decimals
                    53,  # address_type
                    55,  # address_type_p2sh
                    320000000000,  # maxfee_kb
                    "Actinium Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "acm",  # bech32_prefix
                    None,  # cashaddr_prefix
                    228,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Axe":
                return CoinInfo(
                    name,  # coin_name
                    "AXE",  # coin_shortcut
                    8,  # decimals
                    55,  # address_type
                    16,  # address_type_p2sh
                    21000000000,  # maxfee_kb
                    "DarkCoin Signed Message:\n",  # signed_message_header
                    0x02fe52cc,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    4242,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Bcash":
                return CoinInfo(
                    name,  # coin_name
                    "BCH",  # coin_shortcut
                    8,  # decimals
                    0,  # address_type
                    5,  # address_type_p2sh
                    14000000,  # maxfee_kb
                    "Bitcoin Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    "bitcoincash",  # cashaddr_prefix
                    145,  # slip44
                    False,  # segwit
                    False,  # taproot
                    0,  # fork_id
                    True,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Bcash Testnet":
                return CoinInfo(
                    name,  # coin_name
                    "TBCH",  # coin_shortcut
                    8,  # decimals
                    111,  # address_type
                    196,  # address_type_p2sh
                    10000000,  # maxfee_kb
                    "Bitcoin Signed Message:\n",  # signed_message_header
                    0x043587cf,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    "bchtest",  # cashaddr_prefix
                    1,  # slip44
                    False,  # segwit
                    False,  # taproot
                    0,  # fork_id
                    True,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Bprivate":
                return CoinInfo(
                    name,  # coin_name
                    "BTCP",  # coin_shortcut
                    8,  # decimals
                    4901,  # address_type
                    5039,  # address_type_p2sh
                    32000000000,  # maxfee_kb
                    "BitcoinPrivate Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    183,  # slip44
                    False,  # segwit
                    False,  # taproot
                    42,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Bitcore":
                return CoinInfo(
                    name,  # coin_name
                    "BTX",  # coin_shortcut
                    8,  # decimals
                    3,  # address_type
                    125,  # address_type_p2sh
                    14000000000,  # maxfee_kb
                    "BitCore Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "btx",  # bech32_prefix
                    None,  # cashaddr_prefix
                    160,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "CPUchain":
                return CoinInfo(
                    name,  # coin_name
                    "CPU",  # coin_shortcut
                    8,  # decimals
                    28,  # address_type
                    30,  # address_type_p2sh
                    8700000000000,  # maxfee_kb
                    "CPUchain Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "cpu",  # bech32_prefix
                    None,  # cashaddr_prefix
                    363,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Crown":
                return CoinInfo(
                    name,  # coin_name
                    "CRW",  # coin_shortcut
                    8,  # decimals
                    95495,  # address_type
                    95473,  # address_type_p2sh
                    52000000000,  # maxfee_kb
                    "Crown Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    72,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Dogecoin":
                return CoinInfo(
                    name,  # coin_name
                    "DOGE",  # coin_shortcut
                    8,  # decimals
                    30,  # address_type
                    22,  # address_type_p2sh
                    1200000000000,  # maxfee_kb
                    "Dogecoin Signed Message:\n",  # signed_message_header
                    0x02facafd,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    3,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Elements":
                return CoinInfo(
                    name,  # coin_name
                    "ELEMENTS",  # coin_shortcut
                    8,  # decimals
                    235,  # address_type
                    75,  # address_type_p2sh
                    10000000,  # maxfee_kb
                    "Bitcoin Signed Message:\n",  # signed_message_header
                    0x043587cf,  # xpub_magic
                    0x044a5262,  # xpub_magic_segwit_p2sh
                    0x045f1cf6,  # xpub_magic_segwit_native
                    0x043587cf,  # xpub_magic_multisig_segwit_p2sh
                    0x043587cf,  # xpub_magic_multisig_segwit_native
                    "ert",  # bech32_prefix
                    None,  # cashaddr_prefix
                    1,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    {'address_prefix': 4, 'blech32_prefix': 'el'},  # confidential_assets
                )
            if name == "Feathercoin":
                return CoinInfo(
                    name,  # coin_name
                    "FTC",  # coin_shortcut
                    8,  # decimals
                    14,  # address_type
                    5,  # address_type_p2sh
                    390000000000,  # maxfee_kb
                    "Feathercoin Signed Message:\n",  # signed_message_header
                    0x0488bc26,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488bc26,  # xpub_magic_multisig_segwit_p2sh
                    0x0488bc26,  # xpub_magic_multisig_segwit_native
                    "fc",  # bech32_prefix
                    None,  # cashaddr_prefix
                    8,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Firo":
                return CoinInfo(
                    name,  # coin_name
                    "FIRO",  # coin_shortcut
                    8,  # decimals
                    82,  # address_type
                    7,  # address_type_p2sh
                    640000000,  # maxfee_kb
                    "Zcoin Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    136,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    True,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Firo Testnet":
                return CoinInfo(
                    name,  # coin_name
                    "tFIRO",  # coin_shortcut
                    8,  # decimals
                    65,  # address_type
                    178,  # address_type_p2sh
                    1000000,  # maxfee_kb
                    "Zcoin Signed Message:\n",  # signed_message_header
                    0x043587cf,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    1,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    True,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Florincoin":
                return CoinInfo(
                    name,  # coin_name
                    "FLO",  # coin_shortcut
                    8,  # decimals
                    35,  # address_type
                    94,  # address_type_p2sh
                    78000000000,  # maxfee_kb
                    "Florincoin Signed Message:\n",  # signed_message_header
                    0x00174921,  # xpub_magic
                    0x01b26ef6,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x00174921,  # xpub_magic_multisig_segwit_p2sh
                    0x00174921,  # xpub_magic_multisig_segwit_native
                    "flo",  # bech32_prefix
                    None,  # cashaddr_prefix
                    216,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    True,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Fujicoin":
                return CoinInfo(
                    name,  # coin_name
                    "FJC",  # coin_shortcut
                    8,  # decimals
                    36,  # address_type
                    16,  # address_type_p2sh
                    35000000000000,  # maxfee_kb
                    "FujiCoin Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0295b43f,  # xpub_magic_multisig_segwit_p2sh
                    0x02aa7ed3,  # xpub_magic_multisig_segwit_native
                    "fc",  # bech32_prefix
                    None,  # cashaddr_prefix
                    75,  # slip44
                    True,  # segwit
                    True,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Groestlcoin":
                return CoinInfo(
                    name,  # coin_name
                    "GRS",  # coin_shortcut
                    8,  # decimals
                    36,  # address_type
                    5,  # address_type_p2sh
                    16000000000,  # maxfee_kb
                    "GroestlCoin Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "grs",  # bech32_prefix
                    None,  # cashaddr_prefix
                    17,  # slip44
                    True,  # segwit
                    True,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1-groestl',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Groestlcoin Testnet":
                return CoinInfo(
                    name,  # coin_name
                    "tGRS",  # coin_shortcut
                    8,  # decimals
                    111,  # address_type
                    196,  # address_type_p2sh
                    100000,  # maxfee_kb
                    "GroestlCoin Signed Message:\n",  # signed_message_header
                    0x043587cf,  # xpub_magic
                    0x044a5262,  # xpub_magic_segwit_p2sh
                    0x045f1cf6,  # xpub_magic_segwit_native
                    0x043587cf,  # xpub_magic_multisig_segwit_p2sh
                    0x043587cf,  # xpub_magic_multisig_segwit_native
                    "tgrs",  # bech32_prefix
                    None,  # cashaddr_prefix
                    1,  # slip44
                    True,  # segwit
                    True,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1-groestl',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Komodo":
                return CoinInfo(
                    name,  # coin_name
                    "KMD",  # coin_shortcut
                    8,  # decimals
                    60,  # address_type
                    85,  # address_type_p2sh
                    4800000000,  # maxfee_kb
                    "Komodo Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    141,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    True,  # negative_fee
                    'secp256k1',  # curve_name
                    True,  # extra_data
                    False,  # timestamp
                    True,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Koto":
                return CoinInfo(
                    name,  # coin_name
                    "KOTO",  # coin_shortcut
                    8,  # decimals
                    6198,  # address_type
                    6203,  # address_type_p2sh
                    1000000,  # maxfee_kb
                    "Koto Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    510,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    True,  # extra_data
                    False,  # timestamp
                    True,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Litecoin":
                return CoinInfo(
                    name,  # coin_name
                    "LTC",  # coin_shortcut
                    8,  # decimals
                    48,  # address_type
                    50,  # address_type_p2sh
                    67000000,  # maxfee_kb
                    "Litecoin Signed Message:\n",  # signed_message_header
                    0x019da462,  # xpub_magic
                    0x01b26ef6,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x019da462,  # xpub_magic_multisig_segwit_p2sh
                    0x019da462,  # xpub_magic_multisig_segwit_native
                    "ltc",  # bech32_prefix
                    None,  # cashaddr_prefix
                    2,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Litecoin Testnet":
                return CoinInfo(
                    name,  # coin_name
                    "tLTC",  # coin_shortcut
                    8,  # decimals
                    111,  # address_type
                    58,  # address_type_p2sh
                    40000000,  # maxfee_kb
                    "Litecoin Signed Message:\n",  # signed_message_header
                    0x043587cf,  # xpub_magic
                    0x044a5262,  # xpub_magic_segwit_p2sh
                    0x045f1cf6,  # xpub_magic_segwit_native
                    0x043587cf,  # xpub_magic_multisig_segwit_p2sh
                    0x043587cf,  # xpub_magic_multisig_segwit_native
                    "tltc",  # bech32_prefix
                    None,  # cashaddr_prefix
                    1,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Monacoin":
                return CoinInfo(
                    name,  # coin_name
                    "MONA",  # coin_shortcut
                    8,  # decimals
                    50,  # address_type
                    55,  # address_type_p2sh
                    2100000000,  # maxfee_kb
                    "Monacoin Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "mona",  # bech32_prefix
                    None,  # cashaddr_prefix
                    22,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Peercoin":
                return CoinInfo(
                    name,  # coin_name
                    "PPC",  # coin_shortcut
                    6,  # decimals
                    55,  # address_type
                    117,  # address_type_p2sh
                    13000000000,  # maxfee_kb
                    "Peercoin Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "pc",  # bech32_prefix
                    None,  # cashaddr_prefix
                    6,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    True,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Peercoin Testnet":
                return CoinInfo(
                    name,  # coin_name
                    "tPPC",  # coin_shortcut
                    6,  # decimals
                    111,  # address_type
                    196,  # address_type_p2sh
                    2000000,  # maxfee_kb
                    "Peercoin Signed Message:\n",  # signed_message_header
                    0x043587cf,  # xpub_magic
                    0x044a5262,  # xpub_magic_segwit_p2sh
                    0x045f1cf6,  # xpub_magic_segwit_native
                    0x043587cf,  # xpub_magic_multisig_segwit_p2sh
                    0x043587cf,  # xpub_magic_multisig_segwit_native
                    "tpc",  # bech32_prefix
                    None,  # cashaddr_prefix
                    1,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    True,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Primecoin":
                return CoinInfo(
                    name,  # coin_name
                    "XPM",  # coin_shortcut
                    8,  # decimals
                    23,  # address_type
                    83,  # address_type_p2sh
                    89000000000,  # maxfee_kb
                    "Primecoin Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    24,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Qtum":
                return CoinInfo(
                    name,  # coin_name
                    "QTUM",  # coin_shortcut
                    8,  # decimals
                    58,  # address_type
                    50,  # address_type_p2sh
                    1000000000,  # maxfee_kb
                    "Qtum Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "qc",  # bech32_prefix
                    None,  # cashaddr_prefix
                    2301,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Qtum Testnet":
                return CoinInfo(
                    name,  # coin_name
                    "tQTUM",  # coin_shortcut
                    8,  # decimals
                    120,  # address_type
                    110,  # address_type_p2sh
                    40000000,  # maxfee_kb
                    "Qtum Signed Message:\n",  # signed_message_header
                    0x043587cf,  # xpub_magic
                    0x044a5262,  # xpub_magic_segwit_p2sh
                    0x045f1cf6,  # xpub_magic_segwit_native
                    0x043587cf,  # xpub_magic_multisig_segwit_p2sh
                    0x043587cf,  # xpub_magic_multisig_segwit_native
                    "tq",  # bech32_prefix
                    None,  # cashaddr_prefix
                    1,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Ravencoin":
                return CoinInfo(
                    name,  # coin_name
                    "RVN",  # coin_shortcut
                    8,  # decimals
                    60,  # address_type
                    122,  # address_type_p2sh
                    170000000000,  # maxfee_kb
                    "Raven Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    175,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Ravencoin Testnet":
                return CoinInfo(
                    name,  # coin_name
                    "tRVN",  # coin_shortcut
                    8,  # decimals
                    111,  # address_type
                    196,  # address_type_p2sh
                    170000000000,  # maxfee_kb
                    "Raven Signed Message:\n",  # signed_message_header
                    0x043587cf,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    1,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Ritocoin":
                return CoinInfo(
                    name,  # coin_name
                    "RITO",  # coin_shortcut
                    8,  # decimals
                    25,  # address_type
                    105,  # address_type_p2sh
                    39000000000000,  # maxfee_kb
                    "Rito Signed Message:\n",  # signed_message_header
                    0x0534e7ca,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    19169,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "SmartCash":
                return CoinInfo(
                    name,  # coin_name
                    "SMART",  # coin_shortcut
                    8,  # decimals
                    63,  # address_type
                    18,  # address_type_p2sh
                    780000000000,  # maxfee_kb
                    "SmartCash Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    224,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1-smart',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "SmartCash Testnet":
                return CoinInfo(
                    name,  # coin_name
                    "tSMART",  # coin_shortcut
                    8,  # decimals
                    65,  # address_type
                    21,  # address_type_p2sh
                    1000000,  # maxfee_kb
                    "SmartCash Signed Message:\n",  # signed_message_header
                    0x043587cf,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    1,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1-smart',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Stakenet":
                return CoinInfo(
                    name,  # coin_name
                    "XSN",  # coin_shortcut
                    8,  # decimals
                    76,  # address_type
                    16,  # address_type_p2sh
                    11000000000,  # maxfee_kb
                    "DarkCoin Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "xc",  # bech32_prefix
                    None,  # cashaddr_prefix
                    199,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    True,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Syscoin":
                return CoinInfo(
                    name,  # coin_name
                    "SYS",  # coin_shortcut
                    8,  # decimals
                    63,  # address_type
                    5,  # address_type_p2sh
                    42000000000,  # maxfee_kb
                    "Syscoin Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "sys",  # bech32_prefix
                    None,  # cashaddr_prefix
                    57,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Unobtanium":
                return CoinInfo(
                    name,  # coin_name
                    "UNO",  # coin_shortcut
                    8,  # decimals
                    130,  # address_type
                    30,  # address_type_p2sh
                    53000000,  # maxfee_kb
                    "Unobtanium Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    92,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "VIPSTARCOIN":
                return CoinInfo(
                    name,  # coin_name
                    "VIPS",  # coin_shortcut
                    8,  # decimals
                    70,  # address_type
                    50,  # address_type_p2sh
                    140000000000000,  # maxfee_kb
                    "VIPSTARCOIN Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "vips",  # bech32_prefix
                    None,  # cashaddr_prefix
                    1919,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Verge":
                return CoinInfo(
                    name,  # coin_name
                    "XVG",  # coin_shortcut
                    6,  # decimals
                    30,  # address_type
                    33,  # address_type_p2sh
                    550000000000,  # maxfee_kb
                    "Name: Dogecoin Dark\n",  # signed_message_header
                    0x022d2533,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    77,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    True,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Viacoin":
                return CoinInfo(
                    name,  # coin_name
                    "VIA",  # coin_shortcut
                    8,  # decimals
                    71,  # address_type
                    33,  # address_type_p2sh
                    14000000000,  # maxfee_kb
                    "Viacoin Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    0x049d7cb2,  # xpub_magic_segwit_p2sh
                    0x04b24746,  # xpub_magic_segwit_native
                    0x0488b21e,  # xpub_magic_multisig_segwit_p2sh
                    0x0488b21e,  # xpub_magic_multisig_segwit_native
                    "via",  # bech32_prefix
                    None,  # cashaddr_prefix
                    14,  # slip44
                    True,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "ZCore":
                return CoinInfo(
                    name,  # coin_name
                    "ZCR",  # coin_shortcut
                    8,  # decimals
                    142,  # address_type
                    145,  # address_type_p2sh
                    170000000000,  # maxfee_kb
                    "DarkNet Signed Message:\n",  # signed_message_header
                    0x04b24746,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    428,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Zcash":
                return CoinInfo(
                    name,  # coin_name
                    "ZEC",  # coin_shortcut
                    8,  # decimals
                    7352,  # address_type
                    7357,  # address_type_p2sh
                    51000000,  # maxfee_kb
                    "Zcash Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    133,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    True,  # extra_data
                    False,  # timestamp
                    True,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Zcash Testnet":
                return CoinInfo(
                    name,  # coin_name
                    "TAZ",  # coin_shortcut
                    8,  # decimals
                    7461,  # address_type
                    7354,  # address_type_p2sh
                    10000000,  # maxfee_kb
                    "Zcash Signed Message:\n",  # signed_message_header
                    0x043587cf,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    1,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    True,  # extra_data
                    False,  # timestamp
                    True,  # overwintered
                    None,  # confidential_assets
                )
            if name == "Brhodium":
                return CoinInfo(
                    name,  # coin_name
                    "XRC",  # coin_shortcut
                    8,  # decimals
                    61,  # address_type
                    123,  # address_type_p2sh
                    1000000000,  # maxfee_kb
                    "BitCoin Rhodium Signed Message:\n",  # signed_message_header
                    0x0488b21e,  # xpub_magic
                    None,  # xpub_magic_segwit_p2sh
                    None,  # xpub_magic_segwit_native
                    None,  # xpub_magic_multisig_segwit_p2sh
                    None,  # xpub_magic_multisig_segwit_native
                    None,  # bech32_prefix
                    None,  # cashaddr_prefix
                    10291,  # slip44
                    False,  # segwit
                    False,  # taproot
                    None,  # fork_id
                    False,  # force_bip143
                    False,  # decred
                    False,  # negative_fee
                    'secp256k1',  # curve_name
                    False,  # extra_data
                    False,  # timestamp
                    False,  # overwintered
                    None,  # confidential_assets
                )
        raise ValueError  # Unknown coin name
    raise ValueError  # Unknown model
