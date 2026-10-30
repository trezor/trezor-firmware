"""One fact of a request, as the screens take it.

An app says what a fact is, never how it looks: the kind decides the styling,
the grouping and the paging of that kind on every model.

A `data` fact is pulled by core, one chunk at a time, while the person pages:
the app keeps the bytes or hands them out from a source, and core asks for the
range it draws.
"""

from micropython import const
from typing import TYPE_CHECKING

from trezor import utils
from trezor.wire.errors import DataError

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Iterable

    # A decoded `data` fact: `(total, offset, chunk)`. Core fills in each chunk.
    Data = tuple[int, int, bytes]
    # A decoded fact: `(kind, label, value)`, `Data` for the raw-bytes kind.
    Field = tuple[int, "str | None", "str | bytes | Data"]
    # A fact as the renderers take it: `(key, value, kind)`.
    Item = tuple["str | None", "str | bytes", int]
    # A fact as `confirm_with_info` takes it: `(text, is_data)`.
    InfoItem = tuple[str, bool]

# The wire's `FieldKind` discriminants, as `deserialize_ui_message` decodes them.
TEXT = 0
AMOUNT = 1
ADDRESS = 2
DATA = 3
NOTE = 4
WARNING = 5

# Kinds with no label: the sentence is the whole fact.
_SENTENCE = (NOTE, WARNING)

# How many bytes core pulls at a time. One chunk is three pages of the layout's own
# pager (`MAX_HEX_CHARS_ON_SCREEN` hex chars each, two per byte), as the app-side
# paging used to send: the whole value never crosses, and the person confirms once
# per chunk.
DATA_CHUNK_BYTES = const(384)

# How many extras one review may carry. The app's SDK refuses more before it
# sends, so an app never hits this; core checks again rather than trust it.
MAX_EXTRAS = const(5)

# Core's puller, set by the extapp driver while a request is shown.
_data_puller: "Callable[[int, int, int], Awaitable[bytes]] | None" = None


def set_data_puller(
    puller: "Callable[[int, int, int], Awaitable[bytes]] | None",
) -> None:
    """Set (or clear) the function that pulls a data chunk from the app."""
    global _data_puller
    _data_puller = puller


async def _pull(index: int, offset: int, length: int) -> bytes:
    """Ask the app for `length` bytes of the data field at `offset`."""
    if _data_puller is None:
        raise DataError("No data puller")
    return await _data_puller(index, offset, length)


def values(fields: Iterable["Field"]) -> "list[Field]":
    """The facts that carry a value, in the order shown."""
    return [field for field in fields if field[0] not in _SENTENCE]


def has_warning(fields: Iterable["Field"]) -> bool:
    """Whether any fact is a warning."""
    return any(field[0] == WARNING for field in fields)


def notes(fields: Iterable["Field"]) -> str:
    """The sentences of the request, one per line."""
    lines = []
    for kind, _, text in fields:
        if kind in _SENTENCE:
            assert isinstance(text, str)
            lines.append(text)
    return "\n".join(lines)


def items(fields: Iterable["Field"]) -> "list[Item]":
    """The facts as the renderers take them, each with its kind."""
    return [(label, _chunk(value), kind) for kind, label, value in fields]


def details_items(fields: Iterable["Field"]) -> "list[InfoItem]":
    """The facts as `confirm_with_info` takes them: one line each, bytes as hex.

    Only a data value is drawn as monospace; an address keeps the plain style,
    as core's own details screens do.
    """
    return [
        (utils.hexlify_if_bytes(_chunk(value)), kind == DATA)
        for kind, _, value in fields
    ]


def _chunk(value: "str | bytes | Data") -> "str | bytes":
    """The current chunk of a `data` fact, or the value itself for any other."""
    return value[2] if isinstance(value, tuple) else value


def data_fields(
    fields: Iterable["Field"], base_index: int = 0
) -> "list[tuple[int, int]]":
    """`(flat index, total)` for every data fact, in the order core counts them.

    The flat index is the fact's position in the request: its own facts first,
    then each extra's facts in order.
    """
    data = []
    index = base_index
    for kind, _, value in fields:
        if kind == DATA:
            assert isinstance(value, tuple)
            total, _, _ = value
            data.append((index, total))
        index += 1
    return data


def with_data_chunks(
    fields: Iterable["Field"],
    base_index: int,
    chunks: "dict[int, bytes]",
) -> "list[Field]":
    """The facts with each data value replaced by its current chunk."""
    result = []
    index = base_index
    for kind, label, value in fields:
        if kind == DATA:
            result.append((kind, label, chunks[index]))
        else:
            result.append((kind, label, value))
        index += 1
    return result


class Pager:
    """The pages of a request's facts, pulling a data chunk only when asked.

    The first chunk is pulled before the first page is drawn, and each later one
    only after the person asked for the page before it — so a page pulls only what
    it draws, and a refusal between pages pulls nothing more.

    Every range is pulled once, in order, and the person pages forward only: this
    is what lets the app's source hash the bytes it hands out, so that the bytes on
    the screen are the bytes that get signed.
    """

    def __init__(
        self,
        fields: Iterable["Field"],
        base_index: int = 0,
    ) -> None:
        self.fields = list(fields)
        self.base_index = base_index
        self.data = data_fields(self.fields, base_index)
        self.offsets = [0] * len(self.data)
        self.done = False
        self.page = 0

    async def next(self) -> "tuple[list[Field], bool] | None":
        """The next page and whether it is the last, or `None` when there is none."""
        if self.done:
            return None
        if not self.data:
            self.done = True
            self.page += 1
            return self.fields, True

        pulled = {}
        last = True
        for position, (index, total) in enumerate(self.data):
            offset = self.offsets[position]
            length = min(DATA_CHUNK_BYTES, total - offset)
            if length:
                pulled[index] = await _pull(index, offset, length)
                self.offsets[position] = offset + length
            else:
                pulled[index] = b""
            if self.offsets[position] < total:
                last = False
        self.done = last
        self.page += 1
        return with_data_chunks(self.fields, self.base_index, pulled), last


def button_request_name(app_id: str, step: str) -> str:
    """The name a host sees for a step of the app.

    Core prefixes the app's identity, the image ID (`testapp.trezor.io`), so the
    app names the step alone.
    """
    return f"{app_id}/{step}"
