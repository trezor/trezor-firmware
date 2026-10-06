from typing import TYPE_CHECKING

import trezorward
from trezorward import WardError

if TYPE_CHECKING:
    from typing import TypeVar

    from . import WardField, WardSchema

    FieldType = TypeVar("FieldType", bound=WardField)


def _type_id(schema: WardSchema, field_type: type[WardField]) -> int:
    type_id = schema.ids.get(field_type)
    if type_id is None:
        raise ValueError("Type not in the WARD schema")
    return type_id


def _encode(schema: WardSchema, field: WardField) -> bytes:
    """Serialize `field`, prefixed with its type id."""
    return bytes([_type_id(schema, type(field))]) + field.to_bytes()


def _decode(schema: WardSchema, data: bytes) -> WardField | None:
    """Deserialize a field serialized by `_encode`, None if it is not possible."""
    field_type = schema.types.get(data[0]) if data else None
    if field_type is None:
        return None
    try:
        return field_type.from_bytes(data[1:])
    except ValueError:
        return None


def _format(schema: WardSchema, data: bytes) -> str:
    """Describe a field serialized by `_encode` to the user."""
    field = _decode(schema, data)
    if field is None:
        return data.hex()
    return field.format()


class WardStore:
    """Records of one app in one passphrase wallet.

    Obtain it via `apps.ward.with_ward` or `apps.ward.open_ward`. Keys and
    values are fields of the types in the app's schema. Every change is shown
    to the user, who has to approve it.
    """

    def __init__(self, wallet_id: bytes, schema: WardSchema) -> None:
        self._wallet_id = wallet_id
        self._schema = schema

    def _get(self, key: bytes) -> bytes | None:
        return trezorward.get(self._wallet_id, self._schema.app, key)

    async def get(
        self, key: WardField, value_type: type[FieldType]
    ) -> FieldType | None:
        """Return the value stored under `key`, or None if there is none.

        Raise WardError if the stored value is not of type `value_type`.
        """
        type_id = _type_id(self._schema, value_type)
        data = self._get(_encode(self._schema, key))
        if data is None:
            return None
        if not data or data[0] != type_id:
            raise WardError("Unexpected value type")
        try:
            return value_type.from_bytes(data[1:])
        except ValueError:
            raise WardError("Malformed value")

    def entries(self) -> "WardIterator":
        """Iterate over all `(key, value)` records, one record at a time.

        Records that cannot be decoded using the schema are skipped.
        """
        return WardIterator(self._wallet_id, self._schema)

    async def set(self, key: WardField, value: WardField) -> None:
        """Store `value` under `key`, replacing the current value, if any.

        The user is asked to approve the change first.
        """
        from .layout import confirm_store

        key_data = _encode(self._schema, key)
        value_data = _encode(self._schema, value)
        old = self._get(key_data)
        if old == value_data:
            return
        await confirm_store(
            self._schema.app,
            key.format(),
            value.format(),
            None if old is None else _format(self._schema, old),
        )
        trezorward.set(self._wallet_id, self._schema.app, key_data, value_data)

    async def delete(self, key: WardField) -> bool:
        """Delete the record stored under `key`, return whether there was one.

        The user is asked to approve the deletion first.
        """
        from .layout import confirm_delete

        key_data = _encode(self._schema, key)
        old = self._get(key_data)
        if old is None:
            return False
        await confirm_delete(self._schema.app, key.format(), _format(self._schema, old))
        return trezorward.delete(self._wallet_id, self._schema.app, key_data)


class WardIterator:
    def __init__(self, wallet_id: bytes, schema: WardSchema) -> None:
        self._wallet_id = wallet_id
        self._schema = schema
        self._cursor = 0

    def __iter__(self) -> "WardIterator":
        return self

    def __next__(self) -> tuple[WardField, WardField]:
        while True:
            entry = trezorward.next_entry(
                self._wallet_id, self._schema.app, self._cursor
            )
            if entry is None:
                raise StopIteration
            self._cursor, key_data, value_data = entry
            key = _decode(self._schema, key_data)
            value = _decode(self._schema, value_data)
            if key is not None and value is not None:
                return key, value
