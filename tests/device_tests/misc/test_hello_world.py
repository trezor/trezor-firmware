import pytest

from trezorlib import hello_world
from trezorlib.debuglink import SessionDebugWrapper as Session

VECTORS = (  # name, amount, show_display
    ("George", 2, True),
    ("John", 3, False),
    ("Hannah", None, False),
)


@pytest.mark.models("core")
@pytest.mark.parametrize("name, amount, show_display", VECTORS)
def test_hello_world(
    session: Session, name: str, amount: int | None, show_display: bool
):
    greeting_text = hello_world.say_hello(
        session, name=name, amount=amount, show_display=show_display
    )
    greeting_lines = greeting_text.strip().splitlines()

    assert len(greeting_lines) == amount or 1
    assert all(name in line for line in greeting_lines)
