from micropython import const
from typing import TYPE_CHECKING

from trezor.enums import InputScriptType
from trezor.messages import AuthorizeCoinJoin, SignMessage

from apps.common.paths import PATTERN_BIP44, PATTERN_CASA, PathSchema, unharden

from . import authorization
from .common import BITCOIN_NAMES

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Iterable
    from typing import TypeVar

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

# Model 1 firmware signing.
# 826421588 is ASCII string "T1B1" as a little-endian 32-bit integer.
PATTERN_SLIP26_T1_FW = "m/10026'/826421588'/2'/0'"

# SLIP-44 coin type for Bitcoin
SLIP44_BITCOIN = const(0)

# SLIP-44 coin type for all Testnet coins
SLIP44_TESTNET = const(1)


def _get_patterns_for_script_type(
    coin: coininfo.CoinInfo,
    script_type: InputScriptType,
    multisig: bool,
    include_fw_signing: bool = False,
) -> list[str]:
    patterns: list[str] = []
    append = patterns.append  # local_cache_attribute
    slip44 = coin.slip44  # local_cache_attribute

    if script_type == InputScriptType.SPENDADDRESS and not multisig:
        append(PATTERN_BIP44)
        if slip44 == SLIP44_BITCOIN:
            append(PATTERN_GREENADDRESS_A)
            append(PATTERN_GREENADDRESS_B)

        if include_fw_signing:
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
        if coin.coin_name in BITCOIN_NAMES and multisig:
            append(PATTERN_UNCHAINED_HARDENED)
            append(PATTERN_UNCHAINED_UNHARDENED)

    elif coin.taproot and script_type == InputScriptType.SPENDTAPROOT:
        append(PATTERN_BIP86)
        append(PATTERN_SLIP25_TAPROOT)

    return patterns


def validate_path_against_script_type(
    coin: coininfo.CoinInfo,
    msg: MsgWithAddressScriptType | None = None,
    address_n: Bip32Path | None = None,
    script_type: InputScriptType | None = None,
    multisig: bool = False,
) -> bool:
    if msg is not None:
        assert address_n is None and script_type is None
        address_n = msg.address_n
        script_type = msg.script_type or InputScriptType.SPENDADDRESS
        multisig = bool(getattr(msg, "multisig", False))

    else:
        assert address_n is not None and script_type is not None

    patterns = _get_patterns_for_script_type(
        coin, script_type, multisig, include_fw_signing=SignMessage.is_type_of(msg)
    )

    if SignMessage.is_type_of(msg):
        patterns += _get_patterns_for_script_type(coin, script_type, multisig=True)
        patterns += _sign_message_export_patterns(coin)

    return any(
        PathSchema.parse(pattern, coin.slip44).match(address_n) for pattern in patterns
    )


def _xpub_export_patterns(
    coin: coininfo.CoinInfo,
    script_type: InputScriptType,
) -> list[str]:
    """Prefixes of the supported patterns at which an xpub may be exported.

    A prefix ending at the deepest hardened level, or at the account level
    where that is deeper.
    """
    patterns = _get_patterns_for_script_type(coin, script_type, multisig=False)
    patterns += _get_patterns_for_script_type(coin, script_type, multisig=True)

    export_patterns: list[str] = []
    for pattern in patterns:
        for prefix in _pattern_export_points(pattern):
            if prefix not in export_patterns:
                export_patterns.append(prefix)

    return export_patterns


def _pattern_export_points(pattern: str) -> list[str]:
    components = pattern.split("/")[1:]

    deepest_hardened = 0
    account = 0
    for i, component in enumerate(components):
        # No pattern here uses a wildcard; "*'" would read as hardened.
        if component.endswith("'"):
            deepest_hardened = i + 1
        if component in ("account", "account'"):
            account = i + 1

    if deepest_hardened == 0:
        return []

    prefixes: list[str] = []
    for depth in (deepest_hardened, max(deepest_hardened, account)):
        prefix = "m/" + "/".join(components[:depth])
        if prefix not in prefixes:
            prefixes.append(prefix)

    return prefixes


def _sign_message_export_patterns(coin: coininfo.CoinInfo) -> list[str]:
    """Export points of every script type sign_message() can sign with."""
    patterns: list[str] = []
    for script_type in (
        InputScriptType.SPENDADDRESS,
        InputScriptType.SPENDP2SHWITNESS,
        InputScriptType.SPENDWITNESS,
    ):
        for pattern in _xpub_export_patterns(coin, script_type):
            if pattern not in patterns:
                patterns.append(pattern)

    return patterns


def validate_xpub_path_against_script_type(
    coin: coininfo.CoinInfo,
    address_n: Bip32Path,
    script_type: InputScriptType,
) -> bool:
    return any(
        PathSchema.parse(pattern, coin.slip44).match(address_n)
        for pattern in _xpub_export_patterns(coin, script_type)
    )


def _get_schemas_for_coin(
    coin: coininfo.CoinInfo, extra_schemas: Iterable[PathSchema] = ()
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
    schemas.extend(extra_schemas)

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
    extra_schemas: Iterable[PathSchema] = (),
) -> Keychain:
    from apps.common.keychain import get_keychain

    schemas = _get_schemas_for_coin(coin, extra_schemas)
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
        msg: BitcoinMessage,
        auth_msg: MessageType | None = None,
    ) -> MsgOut:
        coin = _get_coin_by_name(msg.coin_name)
        extra_schemas = _get_unlock_schemas(msg, auth_msg, coin)
        if SignMessage.is_type_of(msg):
            # Only the export points need granting; leaf patterns are already
            # in _get_schemas_for_coin(), and no Bitcoin-path aliases for forks.
            extra_schemas += [
                PathSchema.parse(pattern, coin.slip44)
                for pattern in _sign_message_export_patterns(coin)
            ]
        keychain = await _get_keychain_for_coin(coin, extra_schemas)
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
        script_types: tuple[InputScriptType, ...],
        require_segwit: bool,
        require_bech32: bool,
        require_taproot: bool,
        require_bitcoin: bool = False,
    ) -> None:
        self.account_name = account_name
        self.pattern = pattern
        self.script_types = script_types
        self.require_segwit = require_segwit
        self.require_bech32 = require_bech32
        self.require_taproot = require_taproot
        self.require_bitcoin = require_bitcoin

    def get_name(
        self,
        coin: coininfo.CoinInfo,
        address_n: Bip32Path,
        script_type: InputScriptType | None,
        show_account_str: bool,
        export_point: bool,
    ) -> str | None:
        if export_point:
            patterns = _pattern_export_points(self.pattern)
        else:
            patterns = [self.pattern]

        if (
            (script_type is not None and script_type not in self.script_types)
            or not any(
                PathSchema.parse(pattern, coin.slip44).match(address_n)
                for pattern in patterns
            )
            or (not coin.segwit and self.require_segwit)
            or (not coin.bech32_prefix and self.require_bech32)
            or (not coin.taproot and self.require_taproot)
            or (coin.slip44 != SLIP44_BITCOIN and self.require_bitcoin)
        ):
            return None

        name = self.account_name
        if show_account_str:
            name = f"{self.account_name} account"
        account_pos = self.pattern.find("/account")
        if account_pos >= 0:
            i = self.pattern.count("/", 0, account_pos)
            # An export point can be shallower than the account level.
            if i < len(address_n):
                name += f" #{unharden(address_n[i]) + 1}"

        return name


def address_n_to_name(
    coin: coininfo.CoinInfo,
    address_n: Bip32Path,
    script_type: InputScriptType | None = None,
    export_point: bool = False,
    show_account_str: bool = False,
) -> str | None:
    ACCOUNT_TYPES = (
        AccountType(
            "Legacy",
            PATTERN_BIP44,
            (InputScriptType.SPENDADDRESS,),
            require_segwit=True,
            require_bech32=False,
            require_taproot=False,
        ),
        AccountType(
            "",
            PATTERN_BIP44,
            (InputScriptType.SPENDADDRESS,),
            require_segwit=False,
            require_bech32=False,
            require_taproot=False,
        ),
        AccountType(
            "L. SegWit",
            PATTERN_BIP49,
            (InputScriptType.SPENDP2SHWITNESS,),
            require_segwit=True,
            require_bech32=False,
            require_taproot=False,
        ),
        AccountType(
            "SegWit",
            PATTERN_BIP84,
            (InputScriptType.SPENDWITNESS,),
            require_segwit=True,
            require_bech32=True,
            require_taproot=False,
        ),
        AccountType(
            "Taproot",
            PATTERN_BIP86,
            (InputScriptType.SPENDTAPROOT,),
            require_segwit=False,
            require_bech32=True,
            require_taproot=True,
        ),
        AccountType(
            "Coinjoin",
            PATTERN_SLIP25_TAPROOT,
            (InputScriptType.SPENDTAPROOT,),
            require_segwit=False,
            require_bech32=True,
            require_taproot=True,
        ),
        AccountType(
            "BIP 48 multisig",
            PATTERN_BIP48_RAW,
            (InputScriptType.SPENDADDRESS, InputScriptType.SPENDMULTISIG),
            require_segwit=False,
            require_bech32=False,
            require_taproot=False,
        ),
        AccountType(
            "BIP 48 multisig",
            PATTERN_BIP48_P2SHSEGWIT,
            (InputScriptType.SPENDP2SHWITNESS,),
            require_segwit=True,
            require_bech32=False,
            require_taproot=False,
        ),
        AccountType(
            "BIP 48 multisig",
            PATTERN_BIP48_SEGWIT,
            (InputScriptType.SPENDWITNESS,),
            require_segwit=True,
            require_bech32=True,
            require_taproot=False,
        ),
        AccountType(
            "BIP 45 multisig",
            PATTERN_BIP45,
            (InputScriptType.SPENDADDRESS, InputScriptType.SPENDMULTISIG),
            require_segwit=False,
            require_bech32=False,
            require_taproot=False,
        ),
        # GreenAddress subaccounts, offered for Bitcoin only. PATTERN_GREENADDRESS_A
        # is unhardened throughout and so has no export point at all.
        AccountType(
            "GreenAddress",
            PATTERN_GREENADDRESS_B,
            (
                InputScriptType.SPENDADDRESS,
                InputScriptType.SPENDMULTISIG,
                InputScriptType.SPENDP2SHWITNESS,
                InputScriptType.SPENDWITNESS,
            ),
            require_segwit=False,
            require_bech32=False,
            require_taproot=False,
            require_bitcoin=True,
        ),
        AccountType(
            "Casa",
            PATTERN_CASA,
            (InputScriptType.SPENDP2SHWITNESS,),
            require_segwit=True,
            require_bech32=False,
            require_taproot=False,
        ),
        # Unhardened throughout, so it has no export point and is named only
        # at its leaves.
        AccountType(
            "Casa",
            PATTERN_CASA_UNHARDENED,
            (InputScriptType.SPENDP2SHWITNESS,),
            require_segwit=True,
            require_bech32=False,
            require_taproot=False,
        ),
        AccountType(
            "Unchained",
            PATTERN_UNCHAINED_HARDENED,
            (
                InputScriptType.SPENDADDRESS,
                InputScriptType.SPENDMULTISIG,
                InputScriptType.SPENDWITNESS,
            ),
            require_segwit=False,
            require_bech32=False,
            require_taproot=False,
        ),
        AccountType(
            "Unchained",
            PATTERN_UNCHAINED_UNHARDENED,
            (
                InputScriptType.SPENDADDRESS,
                InputScriptType.SPENDMULTISIG,
                InputScriptType.SPENDWITNESS,
            ),
            require_segwit=False,
            require_bech32=False,
            require_taproot=False,
        ),
    )

    for account in ACCOUNT_TYPES:
        name = account.get_name(
            coin, address_n, script_type, show_account_str, export_point
        )
        if name:
            return name

    return None


def address_n_to_name_or_unknown(
    coin: coininfo.CoinInfo,
    address_n: Bip32Path,
    script_type: InputScriptType | None = None,
    allow_export_point: bool = False,
) -> str:
    from trezor import TR

    account_name = address_n_to_name(coin, address_n, script_type)
    if account_name is None and allow_export_point:
        account_name = address_n_to_name(
            coin, address_n, script_type, export_point=True
        )
    if account_name is None:
        return TR.bitcoin__unknown_path
    elif account_name == "":
        return coin.coin_shortcut
    else:
        return f"{coin.coin_shortcut} {account_name}"
