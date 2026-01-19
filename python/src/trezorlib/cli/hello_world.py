from __future__ import annotations

from typing import TYPE_CHECKING

import click

from .. import hello_world
from . import with_session

if TYPE_CHECKING:
    from ..transport.session import Session


@click.group(name="helloworld")
def cli() -> None:
    """Hello world commands."""


@cli.command()
@click.argument("name")
@click.option("-a", "--amount", type=int, help="How many times to greet.")
@click.option(
    "-d", "--show-display", is_flag=True, help="Whether to show confirmation screen."
)
@with_session
def say_hello(
    session: "Session", name: str, amount: int | None, show_display: bool
) -> str:
    """Simply say hello to the supplied name."""
    return hello_world.say_hello(session, name, amount, show_display=show_display)
