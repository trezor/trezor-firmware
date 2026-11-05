from typing import *
from buffer_types import *
from trezorui_api import LayoutObj, UiResult
# A fact as the screens take it: `(kind, label, value)`, with the
# page's chunk as the value of a `Data` field.
Field = tuple[int, str | None, str | bytes]
TEXT: int
AMOUNT: int
ADDRESS: int
DATA: int
NOTE: int
WARNING: int
CONFIRM: int
STRONG: int
DANGER: int
DETAILS: int
MAX_DATA_FIELDS: int


# rust/src/ui/api/modui_micropython.rs
def max_extras(answer: int) -> int:
    """How many extras a review with this answer may offer: what is left
    of the menu's entries after the answer's own."""


# rust/src/ui/api/modui_micropython.rs
def review(
    *,
    title: str,
    fields: Sequence[Field],
    verb: str | None = None,
    hold: bool = False,
    menu: bool = False,
) -> LayoutObj[UiResult]:
    """One page of a review. The model picks the screen from the facts.
    With `menu`, a menu button answers `INFO` and the way out lives in
    the menu; without it the screen offers its own."""


# rust/src/ui/api/modui_micropython.rs
def extra(
    *,
    title: str,
    fields: Sequence[Field],
) -> LayoutObj[UiResult]:
    """One page of an extra: read-only, left without a decision."""


# rust/src/ui/api/modui_micropython.rs
def danger(
    *,
    title: str,
    fields: Sequence[Field],
) -> LayoutObj[UiResult]:
    """One page of a danger: refusing is the default."""


# rust/src/ui/api/modui_micropython.rs
def verify_address(
    *,
    address: str,
    account: str | None = None,
    path: str | None = None,
    br_name: str,
) -> LayoutObj[UiResult]:
    """The person's own address to check; the screen sends its own
    ButtonRequest."""


# rust/src/ui/api/modui_micropython.rs
def verify_pubkey(
    *,
    pubkey: str,
    account: str | None = None,
    path: str | None = None,
    br_name: str,
) -> LayoutObj[UiResult]:
    """The person's own public key to check; the screen sends its own
    ButtonRequest."""


# rust/src/ui/api/modui_micropython.rs
def done(
    *,
    text: str,
    time_ms: int = 0,
) -> LayoutObj[UiResult]:
    """The flow is finished. Goes away after `time_ms`, or on a tap when
    it is 0."""
REQUEST_REVIEW: int
REQUEST_VERIFY_ADDRESS: int
REQUEST_VERIFY_PUBKEY: int
REQUEST_DONE: int
RESULT_CONFIRMED: int
RESULT_CANCELLED: int
RESULT_SHOW_DETAILS: int
MSG_DECISION: int
MSG_CHUNK: int
MSG_CHUNK_FAILED: int
PROGRESS_INIT: int
PROGRESS_STEP: int
PROGRESS_LABEL: int
PROGRESS_END: int


# rust/src/ui/api/modui_micropython.rs
def deserialize_ui_message(
    *,
    data: bytes,
) -> tuple[Any, ...]:
    """Read an app's UI request into plain data. The first element is the
    request's kind (`REQUEST_*`) and the second its step; a review goes on
    with `(title, fields, extras, answer)`, a verification with `(value,
    account, path)` and a done with `(text,)`. `fields` is a list of
    `(kind, label, value, ticker)` whose `Data` value is its total
    length, and `extras` is a list of `(label, fields)`."""


# rust/src/ui/api/modui_micropython.rs
def encode_ui_result(
    *,
    result: int,
) -> bytes:
    """Serialize a decision (`RESULT_*`) into the bytes sent back to the
    app."""


# rust/src/ui/api/modui_micropython.rs
def encode_chunk_request(
    *,
    field: int,
    offset: int,
    length: int,
) -> bytes:
    """Serialize a request for one chunk of a `Data` field: its flat index,
    the offset and the length."""


# rust/src/ui/api/modui_micropython.rs
def deserialize_progress_message(
    *,
    data: bytes,
) -> Any:
    """Read an app's progress message: `(label, total)` for a start, the
    units for a step, the label for a change of label, `None` for the
    end."""
