from typing import Any

from trezor import wire


def one_of(*fields: Any) -> Any:
    """Check that at most one of the provided fields is set.

    If exactly one of the fields is set, return it. If none of the fields is set,
    return None. If more than one of the fields is set, raise an exception.

    Example:
    >>> field = one_of(msg.buy_order, msg.sell_order, msg.cancel_order)
    >>> if BuyOrder.is_type_of(field):
    >>>     process_buy_order(field)
    >>> elif SellOrder.is_type_of(field):
    >>>     process_sell_order(field)
    >>> elif CancelOrder.is_type_of(field):
    >>>     process_cancel_order(field)
    >>> else:
    >>>     raise wire.DataError("Please specify one of the supported orders.")
    """
    field = None
    count = 0
    for field in fields:
        if field is None:
            continue
        count += 1

    if count > 1:
        raise wire.DataError("More than one field from an one_of is set.")

    return field


def ensure_one_of(*fields: Any) -> Any:
    """Ensure that exactly one of the provided fields is set."""
    field = one_of(*fields)
    if field is None:
        raise wire.DataError("Missing required one_of field.")
    return field
