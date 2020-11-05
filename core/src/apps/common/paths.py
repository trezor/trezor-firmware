from micropython import const

from trezor import ui
from trezor.messages import ButtonRequestType
from trezor.ui.text import Text

from . import HARDENED
from .confirm import require_confirm

if False:
    from typing import (
        Any,
        Callable,
        Collection,
        Iterable,
        List,
        Sequence,
        TypeVar,
        Union,
    )
    from typing_extensions import Protocol
    from trezor import wire

    # XXX this is a circular import, but it's only for typing
    from .keychain import Keychain

    Bip32Path = Sequence[int]
    Slip21Path = Sequence[bytes]
    PathType = TypeVar("PathType", Bip32Path, Slip21Path)

    class PathSchemaType(Protocol):
        def match(self, path: Bip32Path) -> bool:
            ...


class _FastInclusiveRange(range):
    """Inclusive range with a fast membership test, suitable for PathSchema use.

    Micropython's `range` does not implement the `__contains__` method. This makes
    checking whether `x in range(BIG_NUMBER)` slow. This class fixes the problem.

    In addition, convenience modifications have been made:
    * both `min` and `max` belong to the range (so `stop == max + 1`).
    * both `min` and `max` must be set, `step` is not allowed (we don't need it and it
      would make the `__contains__` method more complex)
    """

    def __init__(self, min: int, max: int) -> None:
        super().__init__(min, max + 1)

    def __contains__(self, x: object) -> bool:
        if not isinstance(x, int):
            return False
        return self.start <= x < self.stop


class PathSchema:
    """General BIP-32 path schema.

    Loosely based on the BIP-32 path template proposal [1].

    Each path component can be one of the following:
    - constant, e.g., `7`
    - list of constants, e.g., `[1,2,3]`
    - range, e.g., `[0-19]`

    Brackets are recommended but not enforced.

    The following substitutions are available:
    - `coin_type` is substituted with the coin's SLIP-44 identifier
    - `account` is substituted with `[0-100]`, Trezor's default range of accounts
    - `change` is substituted with `[0,1]`
    - `address_index` is substituted with `[0-1000000]`, Trezor's default range of
      addresses

    Hardened flag is indicated by an apostrophe and applies to the whole path component.
    It is impossible to specify both hardened and non-hardened values for the same
    component.

    See examples of valid path formats below and in `apps.bitcoin.keychain`.

    E.g. the following are equivalent definitions of a BIP-84 schema:

        m/84'/coin_type'/[0-100]'/[0,1]/[0-1000000]
        m/84'/coin_type'/0-100'/0,1/0-1000000
        m/84'/coin_type'/account'/change/address_index

    Adding an asterisk at the end of the pattern acts as a wildcard for zero or more
    path components:
    - m/* can be followed by any number of _unhardened_ path components
    - m/*' can be followed by any number of _hardened_ path components
    - m/** can be followed by any number of _any_ path components

    The following is a BIP-44 generic `GetPublicKey` schema:

        m/44'/coin_type'/account'/*

    The asterisk expression can only appear at end of pattern.

    [1] https://github.com/dgpv/bip32_template_parse_tplaplus_spec/blob/master/bip-path-templates.mediawiki
    """

    REPLACEMENTS = {
        "account": "0-100",
        "change": "0,1",
        "address_index": "0-1000000",
    }

    WILDCARD_RANGES = {
        "*": _FastInclusiveRange(0, HARDENED - 1),
        "*'": _FastInclusiveRange(HARDENED, 0xFFFF_FFFF),
        "**": _FastInclusiveRange(0, 0xFFFF_FFFF),
    }

    def __init__(self, pattern: str, slip44_id: Union[int, Iterable[int]]) -> None:
        if not pattern.startswith("m/"):
            raise ValueError  # unsupported path template
        components = pattern[2:].split("/")

        if isinstance(slip44_id, int):
            slip44_id = (slip44_id,)

        self.schema: List[Collection[int]] = []
        self.trailing_components: Collection[int] = ()

        for component in components:
            if component in self.WILDCARD_RANGES:
                if len(self.schema) != len(components) - 1:
                    # every component should have resulted in extending self.schema
                    # so if self.schema does not have the appropriate length (yet),
                    # the asterisk is not the last item
                    raise ValueError  # asterisk is not last item of pattern

                self.trailing_components = self.WILDCARD_RANGES[component]
                break

            # figure out if the component is hardened
            if component[-1] == "'":
                component = component[:-1]
                parse: Callable[[Any], int] = lambda s: int(s) | HARDENED  # noqa: E731
            else:
                parse = int

            # strip brackets
            if component[0] == "[" and component[-1] == "]":
                component = component[1:-1]

            # optionally replace a keyword
            component = self.REPLACEMENTS.get(component, component)

            if "-" in component:
                # parse as a range
                a, b = [parse(s) for s in component.split("-", 1)]
                self.schema.append(_FastInclusiveRange(a, b))

            elif "," in component:
                # parse as a list of values
                self.schema.append(set(parse(s) for s in component.split(",")))

            elif component == "coin_type":
                # substitute SLIP-44 ids
                self.schema.append(set(parse(s) for s in slip44_id))

            else:
                # plain constant
                self.schema.append((parse(component),))

    def match(self, path: Bip32Path) -> bool:
        # The path must not be _shorter_ than schema. It may be longer.
        if len(path) < len(self.schema):
            return False

        path_iter = iter(path)
        # iterate over length of schema, consuming path components
        for expected in self.schema:
            value = next(path_iter)
            if value not in expected:
                return False

        # iterate over remaining path components
        for value in path_iter:
            if value not in self.trailing_components:
                return False

        return True

    if __debug__:

        def __repr__(self) -> str:
            components = ["m"]

            def unharden(item: int) -> int:
                return item ^ (item & HARDENED)

            for component in self.schema:
                if isinstance(component, range):
                    a, b = component.start, component.stop - 1
                    components.append(
                        "[{}-{}]{}".format(
                            unharden(a), unharden(b), "'" if a & HARDENED else ""
                        )
                    )
                else:
                    component_str = ",".join(str(unharden(i)) for i in component)
                    if len(component) > 1:
                        component_str = "[" + component_str + "]"
                    if next(iter(component)) & HARDENED:
                        component_str += "'"
                    components.append(component_str)

            if self.trailing_components:
                for key, val in self.WILDCARD_RANGES.items():
                    if self.trailing_components is val:
                        components.append(key)
                        break
                else:
                    components.append("???")

            return "<schema:" + "/".join(components) + ">"


class _AlwaysMatchingSchema:
    @staticmethod
    def match(path: Bip32Path) -> bool:
        return True


class _NeverMatchingSchema:
    @staticmethod
    def match(path: Bip32Path) -> bool:
        return False


# type objects _AlwaysMatchingSchema and _NeverMatching schema conform to the
# PathSchemaType protocol, but mypy fails to recognize this due to:
# https://github.com/python/mypy/issues/4536,
# hence the following trickery
AlwaysMatchingSchema: PathSchemaType = _AlwaysMatchingSchema  # type: ignore
NeverMatchingSchema: PathSchemaType = _NeverMatchingSchema  # type: ignore

# BIP-44 for basic (legacy) Bitcoin accounts, and widely used for other currencies:
# https://github.com/bitcoin/bips/blob/master/bip-0044.mediawiki
PATTERN_BIP44 = "m/44'/coin_type'/account'/change/address_index"
# BIP-44 public key export, starting at end of the hardened part
PATTERN_BIP44_PUBKEY = "m/44'/coin_type'/account'/*"
# SEP-0005 for non-UTXO-based currencies, defined by Stellar:
# https://github.com/stellar/stellar-protocol/blob/master/ecosystem/sep-0005.md
PATTERN_SEP5 = "m/44'/coin_type'/account'"


async def validate_path(
    ctx: wire.Context, keychain: Keychain, path: Bip32Path, *additional_checks: bool
) -> None:
    keychain.verify_path(path)
    if not keychain.is_in_keychain(path) or not all(additional_checks):
        await show_path_warning(ctx, path)


async def show_path_warning(ctx: wire.Context, path: Bip32Path) -> None:
    text = Text("Confirm path", ui.ICON_WRONG, ui.RED)
    text.normal("Path")
    text.mono(*break_address_n_to_lines(path))
    text.normal("is unknown.")
    text.normal("Are you sure?")
    await require_confirm(ctx, text, ButtonRequestType.UnknownDerivationPath)


def is_hardened(i: int) -> bool:
    return bool(i & HARDENED)


def path_is_hardened(address_n: Bip32Path) -> bool:
    return all(is_hardened(n) for n in address_n)


def address_n_to_str(address_n: Bip32Path) -> str:
    def path_item(i: int) -> str:
        if i & HARDENED:
            return str(i ^ HARDENED) + "'"
        else:
            return str(i)

    return "m/" + "/".join([path_item(i) for i in address_n])


def break_address_n_to_lines(address_n: Bip32Path) -> List[str]:
    lines = []
    path_str = address_n_to_str(address_n)

    per_line = const(17)
    while len(path_str) > per_line:
        i = path_str[:per_line].rfind("/")
        lines.append(path_str[:i])
        path_str = path_str[i:]
    lines.append(path_str)

    return lines
