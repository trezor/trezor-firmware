from micropython import const
from typing import TYPE_CHECKING

from trezor.enums import InputScriptType
from trezor.messages import AuthorizeCoinJoin, SignMessage

from apps.common.paths import PATTERN_BIP44, PATTERN_CASA, PathSchema, unharden

from . import authorization
from .common import BIP32_WALLET_DEPTH, BITCOIN_NAMES

if TYPE_CHECKING:
    from typing import Awaitable, Callable, Iterable, TypeVar

    from trezor.messages import (
        GetAddress,
        GetOwnershipId,
        GetOwnershipProof,
        GetPublicKey,
        SignTx,
        VerifyMessage,
    )
    from trezor.protobuf import MessageType
    from typing_extensions import Protocol

    from apps.common import coininfo
    from apps.common.keychain import Handler, Keychain, MsgOut
    from apps.common.paths import Bip32Path

    BitcoinMessage = (
        AuthorizeCoinJoin
        | GetAddress
        | GetOwnershipId
        | GetOwnershipProof
        | GetPublicKey
        | SignMessage
        | SignTx
        | VerifyMessage
    )

    class MsgWithAddressScriptType(Protocol):
        address_n: Bip32Path
        script_type: InputScriptType

    MsgIn = TypeVar("MsgIn", bound=BitcoinMessage)
    HandlerWithCoinInfo = Callable[..., Awaitable[MsgOut]]

# BIP-45 for multisig: https://github.com/bitcoin/bips/blob/master/bip-0045.mediawiki
PATTERN_BIP45 = "m/45'/[0-100]/change/address_index"

# BIP-48 for multisig: https://github.com/bitcoin/bips/blob/master/bip-0048.mediawiki
# The raw script type is not part of the BIP (and Electrum, as a notable implementation,
# does not use it), it is included here for completeness.
PATTERN_BIP48_RAW = "m/48'/coin_type'/account'/0'/change/address_index"
PATTERN_BIP48_P2SHSEGWIT = "m/48'/coin_type'/account'/1'/change/address_index"
PATTERN_BIP48_SEGWIT = "m/48'/coin_type'/account'/2'/change/address_index"

# BIP-49 for segwit-in-P2SH: https://github.com/bitcoin/bips/blob/master/bip-0049.mediawiki
PATTERN_BIP49 = "m/49'/coin_type'/account'/change/address_index"
# BIP-84 for segwit: https://github.com/bitcoin/bips/blob/master/bip-0084.mediawiki
PATTERN_BIP84 = "m/84'/coin_type'/account'/change/address_index"
# BIP-86 for taproot: https://github.com/bitcoin/bips/blob/master/bip-0086.mediawiki
PATTERN_BIP86 = "m/86'/coin_type'/account'/change/address_index"
# SLIP-25 for coinjoin: https://github.com/satoshilabs/slips/blob/master/slip-0025.md
# Only account=0 and script_type=1 are supported for now.
PATTERN_SLIP25_TAPROOT = "m/10025'/coin_type'/0'/1'/change/address_index"
PATTERN_SLIP25_TAPROOT_EXTERNAL = "m/10025'/coin_type'/0'/1'/0/address_index"

# compatibility patterns, will be removed in the future
PATTERN_GREENADDRESS_A = "m/[1,4]/address_index"
PATTERN_GREENADDRESS_B = "m/3'/[1-100]'/[1,4]/address_index"
PATTERN_GREENADDRESS_SIGN_A = "m/1195487518"
PATTERN_GREENADDRESS_SIGN_B = "m/1195487518/6/address_index"

PATTERN_CASA_UNHARDENED = "m/49/coin_type/account/change/address_index"

PATTERN_UNCHAINED_HARDENED = (
    "m/45'/coin_type'/account'/[0-1000000]/change/address_index"
)
PATTERN_UNCHAINED_UNHARDENED = (
    "m/45'/coin_type/account/[0-1000000]/change/address_index"
)
PATTERN_UNCHAINED_DEPRECATED = "m/45'/coin_type'/account'/[0-1000000]/address_index"

# Model 1 firmware signing.
# 826421588 is ASCII string "T1B1" as a little-endian 32-bit integer.
PATTERN_SLIP26_T1_FW = "m/10026'/826421588'/2'/0'"

# SLIP-44 coin type for Bitcoin
SLIP44_BITCOIN = const(0)

# SLIP-44 coin type for all Testnet coins
SLIP44_TESTNET = const(1)


def validate_path_against_script_type(
    coin: coininfo.CoinInfo,
    msg: MsgWithAddressScriptType | None = None,
    address_n: Bip32Path | None = None,
    script_type: InputScriptType | None = None,
    multisig: bool = False,
) -> bool:
    from trezor.enums import InputScriptType

    patterns = []
    append = patterns.append  # local_cache_attribute
    slip44 = coin.slip44  # local_cache_attribute

    if msg is not None:
        assert address_n is None and script_type is None
        address_n = msg.address_n
        script_type = msg.script_type or InputScriptType.SPENDADDRESS
        multisig = bool(getattr(msg, "multisig", False))

    else:
        assert address_n is not None and script_type is not None

    if script_type == InputScriptType.SPENDADDRESS and not multisig:
        append(PATTERN_BIP44)
        if slip44 == SLIP44_BITCOIN:
            append(PATTERN_GREENADDRESS_A)
            append(PATTERN_GREENADDRESS_B)

        if SignMessage.is_type_of(msg):
            append(PATTERN_SLIP26_T1_FW)
    elif (
        script_type in (InputScriptType.SPENDADDRESS, InputScriptType.SPENDMULTISIG)
        and multisig
    ):
        append(PATTERN_BIP48_RAW)
        if slip44 == SLIP44_BITCOIN or (
            coin.fork_id is not None and slip44 != SLIP44_TESTNET
        ):
            append(PATTERN_BIP45)
        if slip44 == SLIP44_BITCOIN:
            append(PATTERN_GREENADDRESS_A)
            append(PATTERN_GREENADDRESS_B)
        if coin.coin_name in BITCOIN_NAMES:
            append(PATTERN_UNCHAINED_HARDENED)
            append(PATTERN_UNCHAINED_UNHARDENED)
            append(PATTERN_UNCHAINED_DEPRECATED)

    elif coin.segwit and script_type == InputScriptType.SPENDP2SHWITNESS:
        append(PATTERN_BIP49)
        append(PATTERN_CASA)
        if multisig:
            append(PATTERN_BIP48_P2SHSEGWIT)
        if slip44 == SLIP44_BITCOIN:
            append(PATTERN_GREENADDRESS_A)
            append(PATTERN_GREENADDRESS_B)
        if coin.coin_name in BITCOIN_NAMES:
            append(PATTERN_CASA_UNHARDENED)

    elif coin.segwit and script_type == InputScriptType.SPENDWITNESS:
        append(PATTERN_BIP84)
        if multisig:
            append(PATTERN_BIP48_SEGWIT)
        if slip44 == SLIP44_BITCOIN:
            append(PATTERN_GREENADDRESS_A)
            append(PATTERN_GREENADDRESS_B)

    elif coin.taproot and script_type == InputScriptType.SPENDTAPROOT:
        append(PATTERN_BIP86)
        append(PATTERN_SLIP25_TAPROOT)

    return any(
        PathSchema.parse(pattern, coin.slip44).match(address_n) for pattern in patterns
    )


def _get_schemas_for_coin(
    coin: coininfo.CoinInfo, unlock_schemas: Iterable[PathSchema] = ()
) -> Iterable[PathSchema]:
    import gc

    # basic patterns
    patterns = [
        PATTERN_BIP44,
        PATTERN_BIP48_RAW,
        PATTERN_CASA,
    ]

    # patterns without coin_type field must be treated as if coin_type == 0
    if coin.slip44 == SLIP44_BITCOIN or (
        coin.fork_id is not None and coin.slip44 != SLIP44_TESTNET
    ):
        patterns.append(PATTERN_BIP45)

    if coin.slip44 == SLIP44_BITCOIN:
        patterns.extend(
            (
                PATTERN_GREENADDRESS_A,
                PATTERN_GREENADDRESS_B,
                PATTERN_GREENADDRESS_SIGN_A,
                PATTERN_GREENADDRESS_SIGN_B,
                PATTERN_SLIP26_T1_FW,
            )
        )

    # compatibility patterns
    if coin.coin_name in BITCOIN_NAMES:
        patterns.extend(
            (
                PATTERN_CASA_UNHARDENED,
                PATTERN_UNCHAINED_HARDENED,
                PATTERN_UNCHAINED_UNHARDENED,
                PATTERN_UNCHAINED_DEPRECATED,
            )
        )

    # segwit patterns
    if coin.segwit:
        patterns.extend(
            (
                PATTERN_BIP49,
                PATTERN_BIP84,
                PATTERN_BIP48_P2SHSEGWIT,
                PATTERN_BIP48_SEGWIT,
            )
        )

    # taproot patterns
    if coin.taproot:
        patterns.append(PATTERN_BIP86)

    schemas = get_schemas_from_patterns(patterns, coin)
    schemas.extend(unlock_schemas)

    gc.collect()
    return [schema.copy() for schema in schemas]


def get_schemas_from_patterns(
    patterns: Iterable[str], coin: coininfo.CoinInfo
) -> list[PathSchema]:
    schemas = [PathSchema.parse(pattern, coin.slip44) for pattern in patterns]

    # Some wallets such as Electron-Cash (BCH) store coins on Bitcoin paths.
    # We can allow spending these coins from Bitcoin paths if the coin has
    # implemented strong replay protection via SIGHASH_FORKID. However, we
    # cannot allow spending any testnet coins from Bitcoin paths, because
    # otherwise an attacker could trick the user into spending BCH on a Bitcoin
    # path by signing a seemingly harmless BCH Testnet transaction.
    if coin.fork_id is not None and coin.slip44 != SLIP44_TESTNET:
        schemas.extend(
            PathSchema.parse(pattern, SLIP44_BITCOIN) for pattern in patterns
        )

    return schemas


def _get_coin_by_name(coin_name: str | None) -> coininfo.CoinInfo:
    from trezor import wire

    from apps.common import coininfo

    if coin_name is None:
        coin_name = "Bitcoin"

    try:
        return coininfo.by_name(coin_name)
    except ValueError:
        raise wire.DataError("Unsupported coin type")


async def _get_keychain_for_coin(
    coin: coininfo.CoinInfo,
    unlock_schemas: Iterable[PathSchema] = (),
) -> Keychain:
    from apps.common.keychain import get_keychain

    schemas = _get_schemas_for_coin(coin, unlock_schemas)
    slip21_namespaces = [[b"SLIP-0019"], [b"SLIP-0024"]]
    keychain = await get_keychain(coin.curve_name, schemas, slip21_namespaces)
    return keychain


def _get_unlock_schemas(
    msg: MessageType, auth_msg: MessageType | None, coin: coininfo.CoinInfo
) -> list[PathSchema]:
    """
    Provides additional keychain schemas that are unlocked by the particular
    combination of `msg` and `auth_msg`.
    """
    from trezor.messages import GetOwnershipProof, SignTx, UnlockPath

    if AuthorizeCoinJoin.is_type_of(msg):
        # When processing the AuthorizeCoinJoin message, validate_path() always
        # needs to treat SLIP-25 paths as valid, so add SLIP-25 to the schemas.
        return get_schemas_from_patterns([PATTERN_SLIP25_TAPROOT], coin)

    if AuthorizeCoinJoin.is_type_of(auth_msg) or UnlockPath.is_type_of(auth_msg):
        # The user has preauthorized access to certain paths. Here we create a
        # list of all the patterns that can be unlocked by AuthorizeCoinJoin or
        # by UnlockPath. At the moment only SLIP-25 paths can be unlocked.
        patterns = []
        if SignTx.is_type_of(msg) or GetOwnershipProof.is_type_of(msg):
            # SignTx and GetOwnershipProof need access to all SLIP-25 addresses
            # to create coinjoin outputs.
            patterns.append(PATTERN_SLIP25_TAPROOT)
        else:
            # In case of other messages like GetAddress or SignMessage there is
            # no reason for the user to work with SLIP-25 change-addresses. For
            # example, using a change-address to receive a payment may
            # compromise privacy.
            patterns.append(PATTERN_SLIP25_TAPROOT_EXTERNAL)

        # Convert the unlockable patterns to schemas and select only the ones
        # that are unlocked by the auth_msg, i.e. lie in a subtree of the
        # auth_msg's path.
        schemas = get_schemas_from_patterns(patterns, coin)
        return [s for s in schemas if s.restrict(auth_msg.address_n)]

    return []


def with_keychain(func: HandlerWithCoinInfo[MsgOut]) -> Handler[MsgIn, MsgOut]:
    async def wrapper(
        msg: MsgIn,
        auth_msg: MessageType | None = None,
    ) -> MsgOut:
        coin = _get_coin_by_name(msg.coin_name)
        unlock_schemas = _get_unlock_schemas(msg, auth_msg, coin)
        keychain = await _get_keychain_for_coin(coin, unlock_schemas)
        if AuthorizeCoinJoin.is_type_of(auth_msg):
            auth_obj = authorization.from_cached_message(auth_msg)
            return await func(msg, keychain, coin, auth_obj)
        else:
            with keychain:
                return await func(msg, keychain, coin)

    return wrapper


class AccountType:
    def __init__(
        self,
        account_name: str,
        pattern: str,
        script_type: InputScriptType,
        require_segwit: bool,
        require_bech32: bool,
        require_taproot: bool,
        account_level: bool = False,
    ):
        self.account_name = account_name
        self.pattern = pattern
        self.script_type = script_type
        self.require_segwit = require_segwit
        self.require_bech32 = require_bech32
        self.require_taproot = require_taproot
        self.account_level = account_level

    def get_name(
        self,
        coin: coininfo.CoinInfo,
        address_n: Bip32Path,
        script_type: InputScriptType | None,
        show_account_str: bool,
    ) -> str | None:
        pattern = self.pattern
        if self.account_level:
            # Discard the last two parts of the pattern. For bitcoin these generally are `change`
            # and `address_index`. The result can be used to match XPUB paths.
            pattern = "/".join(pattern.split("/")[:-BIP32_WALLET_DEPTH])

        if (
            (script_type is not None and script_type != self.script_type)
            or not PathSchema.parse(pattern, coin.slip44).match(address_n)
            or (not coin.segwit and self.require_segwit)
            or (not coin.bech32_prefix and self.require_bech32)
            or (not coin.taproot and self.require_taproot)
        ):
            return None

        name = self.account_name
        if show_account_str:
            name = f"{self.account_name} account"
        account_pos = pattern.find("/account'")
        if account_pos >= 0:
            i = pattern.count("/", 0, account_pos)
            account_number = unharden(address_n[i]) + 1
            name += f" #{account_number}"

        return name


def address_n_to_name(
    coin: coininfo.CoinInfo,
    address_n: Bip32Path,
    script_type: InputScriptType | None = None,
    account_level: bool = False,
    show_account_str: bool = False,
) -> str | None:
    ACCOUNT_TYPES = (
        AccountType(
            "Legacy",
            PATTERN_BIP44,
            InputScriptType.SPENDADDRESS,
            require_segwit=True,
            require_bech32=False,
            require_taproot=False,
            account_level=account_level,
        ),
        AccountType(
            "",
            PATTERN_BIP44,
            InputScriptType.SPENDADDRESS,
            require_segwit=False,
            require_bech32=False,
            require_taproot=False,
            account_level=account_level,
        ),
        AccountType(
            "L. SegWit",
            PATTERN_BIP49,
            InputScriptType.SPENDP2SHWITNESS,
            require_segwit=True,
            require_bech32=False,
            require_taproot=False,
            account_level=account_level,
        ),
        AccountType(
            "SegWit",
            PATTERN_BIP84,
            InputScriptType.SPENDWITNESS,
            require_segwit=True,
            require_bech32=True,
            require_taproot=False,
            account_level=account_level,
        ),
        AccountType(
            "Taproot",
            PATTERN_BIP86,
            InputScriptType.SPENDTAPROOT,
            require_segwit=False,
            require_bech32=True,
            require_taproot=True,
            account_level=account_level,
        ),
        AccountType(
            "Coinjoin",
            PATTERN_SLIP25_TAPROOT,
            InputScriptType.SPENDTAPROOT,
            require_segwit=False,
            require_bech32=True,
            require_taproot=True,
            account_level=account_level,
        ),
    )

    for account in ACCOUNT_TYPES:
        name = account.get_name(coin, address_n, script_type, show_account_str)
        if name:
            return name

    return None


def address_n_to_name_or_unknown(
    coin: coininfo.CoinInfo,
    address_n: Bip32Path,
    script_type: InputScriptType | None = None,
    account_level: bool = False,
    show_account_str: bool = False,
) -> str:
    account_name = address_n_to_name(coin, address_n, script_type)
    if account_name is None:
        return "Unknown path"
    elif account_name == "":
        return coin.coin_shortcut
    else:
        return f"{coin.coin_shortcut} {account_name}"
