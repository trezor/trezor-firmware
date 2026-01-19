from __future__ import annotations

from typing import TYPE_CHECKING

from . import messages

if TYPE_CHECKING:
    from .transport.session import Session


def say_hello(
    session: "Session",
    name: str,
    amount: int | None,
    show_display: bool,
) -> str:
    return session.call(
        messages.HelloWorldRequest(
            name=name,
            amount=amount,
            show_display=show_display,
        ),
        expect=messages.HelloWorldResponse,
    ).text
