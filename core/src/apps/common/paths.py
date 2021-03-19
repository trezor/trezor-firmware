from trezor.ui.constants import MONO_CHARS_PER_LINE
from trezor.ui.layouts import confirm_path_warning

from . import HARDENED
from .layout import address_n_to_str

if False:
    from typing import (
        Any,
        Callable,
        Collection,
        Container,
        Iterable,
        Sequence,
        TypeVar,
    )
    from typing_extensions import Protocol
    from trezor import wire

    Bip32Path = Sequence[int]
    Slip21Path = Sequence[bytes]
    PathType = TypeVar("PathType", Bip32Path, Slip21Path)

    class PathSchemaType(Protocol):
        def match(self, path: Bip32Path) -> bool:
            ...

    class KeychainValidatorType(Protocol):
        def is_in_keychain(self, path: Bip32Path) -> bool:
            ...

        def verify_path(self, path: Bip32Path) -> None:
            ...


class Interval:
    """Helper for testing membership in an interval."""

    def __init__(self, min: int, max: int) -> None:
        self.min = min
        self.max = max

    def __contains__(self, x: object) -> bool:
        if not isinstance(x, int):
            return False
        return self.min <= x <= self.max


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
        "*": Interval(0, HARDENED - 1),
        "*'": Interval(HARDENED, 0xFFFF_FFFF),
        "**": Interval(0, 0xFFFF_FFFF),
    }

    _EMPTY_TUPLE = ()

    @staticmethod
    def _parse_hardened(s: str) -> int:
        return int(s) | HARDENED

    @staticmethod
    def _copy_container(container: Container[int]) -> Container[int]:
        if isinstance(container, Interval):
            return Interval(container.min, container.max)
        if isinstance(container, set):
            return set(container)
        if isinstance(container, tuple):
            return container[:]
        raise RuntimeError("Unsupported container for copy")

    def __init__(
        self,
        schema: list[Container[int]],
        trailing_components: Container[int] = (),
        compact: bool = False,
    ) -> None:
        """Create a new PathSchema from a list of containers and trailing components.

        Mainly for internal use in `PathSchema.parse`, which is the method you should
        be using.

        Can be used to create a schema manually without parsing a path string:

        >>> SCHEMA_MINE = PathSchema([
        >>>         (44 | HARDENED,),
        >>>         (0 | HARDENED,),
        >>>         Interval(0 | HARDENED, 10 | HARDENED),
        >>>     ],
        >>>     trailing_components=Interval(0, 0xFFFF_FFFF),
        >>> )

        Setting `compact=True` creates a compact copy of the provided components, so
        as to prevent memory fragmentation.
        """
        if compact:
            self.schema: list[Container[int]] = [self._EMPTY_TUPLE] * len(schema)
            for i in range(len(schema)):
                self.schema[i] = self._copy_container(schema[i])
            self.trailing_components = self._copy_container(trailing_components)

        else:
            self.schema = schema
            self.trailing_components = trailing_components

    @classmethod
    def parse(cls, pattern: str, slip44_id: int | Iterable[int]) -> "PathSchema":
        """Parse a path schema string into a PathSchema instance.

        The parsing process trashes the memory layout, so at the end a compact-allocated
        copy of the resulting structures is returned.
        """
        if not pattern.startswith("m/"):
            raise ValueError  # unsupported path template
        components = pattern[2:].split("/")

        if isinstance(slip44_id, int):
            slip44_id = (slip44_id,)

        schema: list[Container[int]] = []
        trailing_components: Container[int] = ()

        for component in components:
            if component in cls.WILDCARD_RANGES:
                if len(schema) != len(components) - 1:
                    # every component should have resulted in extending schema
                    # so if schema does not have the appropriate length (yet),
                    # the asterisk is not the last item
                    raise ValueError  # asterisk is not last item of pattern

                trailing_components = cls.WILDCARD_RANGES[component]
                break

            # figure out if the component is hardened
            if component[-1] == "'":
                component = component[:-1]
                parse: Callable[[Any], int] = cls._parse_hardened
            else:
                parse = int

            # strip brackets
            if component[0] == "[" and component[-1] == "]":
                component = component[1:-1]

            # optionally replace a keyword
            component = cls.REPLACEMENTS.get(component, component)

            if "-" in component:
                # parse as a range
                a, b = [parse(s) for s in component.split("-", 1)]
                schema.append(Interval(a, b))

            elif "," in component:
                # parse as a list of values
                schema.append(set(parse(s) for s in component.split(",")))

            elif component == "coin_type":
                # substitute SLIP-44 ids
                schema.append(set(parse(s) for s in slip44_id))

            else:
                # plain constant
                schema.append((parse(component),))

        return cls(schema, trailing_components, compact=True)

    def copy(self) -> "PathSchema":
        """Create a compact copy of the schema.

        Useful when creating multiple schemas in a row. The following code ensures
        that the set of schemas is allocated in a contiguous block of memory:

        >>> some_schemas = make_multiple_schemas()
        >>> some_schemas = [s.copy() for s in some_schemas]
        """
        return PathSchema(self.schema, self.trailing_components, compact=True)

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
                if isinstance(component, Interval):
                    a, b = component.min, component.max
                    components.append(
                        "[{}-{}]{}".format(
                            unharden(a), unharden(b), "'" if a & HARDENED else ""
                        )
                    )
                else:
                    # mypy thinks component is a Contanier but we're using it as a Collection.
                    # Which in practice it is, the only non-Collection is Interval.
                    # But we're not going to introduce an additional type requirement
                    # for the sake of __repr__ that doesn't exist in production anyway
                    collection: Collection[int] = component  # type: ignore
                    component_str = ",".join(str(unharden(i)) for i in collection)
                    if len(collection) > 1:
                        component_str = "[" + component_str + "]"
                    if next(iter(collection)) & HARDENED:
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
    ctx: wire.Context,
    keychain: KeychainValidatorType,
    path: Bip32Path,
    *additional_checks: bool,
) -> None:
    keychain.verify_path(path)
    if not keychain.is_in_keychain(path) or not all(additional_checks):
        await show_path_warning(ctx, path)


async def show_path_warning(ctx: wire.Context, path: Bip32Path) -> None:
    await confirm_path_warning(ctx, address_n_to_str(path))


def is_hardened(i: int) -> bool:
    return bool(i & HARDENED)


def path_is_hardened(address_n: Bip32Path) -> bool:
    return all(is_hardened(n) for n in address_n)


def break_address_n_to_lines(address_n: Bip32Path) -> list[str]:
    lines = []
    path_str = address_n_to_str(address_n)

    per_line = MONO_CHARS_PER_LINE
    while len(path_str) > per_line:
        i = path_str[:per_line].rfind("/")
        lines.append(path_str[:i])
        path_str = path_str[i:]
    lines.append(path_str)

    return lines
