"""One fact of a request, as the screens take it.

An app says what a fact is, never how it looks: the kind decides the styling,
the grouping and the paging of that kind on every model.
"""

from typing import TYPE_CHECKING

from trezor import utils

if TYPE_CHECKING:
    from collections.abc import Iterable

    # A decoded fact: `(kind, label, value)`, bytes only for `DATA`.
    Field = tuple[int, "str | None", "str | bytes"]
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
    return [(label, value, kind) for kind, label, value in fields]


def details_items(fields: Iterable["Field"]) -> "list[InfoItem]":
    """The facts as `confirm_with_info` takes them: one line each, bytes as hex.

    Only a data value is drawn as monospace; an address keeps the plain style,
    as core's own details screens do.
    """
    return [(utils.hexlify_if_bytes(value), kind == DATA) for kind, _, value in fields]


def button_request_name(app_id: str, step: str) -> str:
    """The name a host sees for a step of the app.

    Core prefixes the app's identity, the image ID (`testapp.trezor.io`), so the
    app names the step alone.
    """
    return f"{app_id}/{step}"
