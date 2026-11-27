from typing import TYPE_CHECKING

from trezor import ui
from trezor.ui.layouts.progress import progress
from trezormodui import MSG_PROGRESS, deserialize_progress_message

from .session import SERVICE_PROGRESS

if TYPE_CHECKING:
    from trezorio import IpcMessage

    from .session import Session


def handle(session: Session, msg: IpcMessage) -> None:
    """Show the progress state the app sent, and acknowledge it."""
    if msg.message_id != MSG_PROGRESS:
        session.die("Unknown progress message ID")
    label, done, total = deserialize_progress_message(data=bytes(msg.data))
    show(session, label, done, total)
    session.send(SERVICE_PROGRESS, MSG_PROGRESS, b"")


def show(session: Session, label: str, done: int, total: int) -> None:
    """Show `done` of `total` under `label` for the app. Past `total` the bar
    shows full, and a `total` of 0 shows motion without a fill.

    Each state the app sends describes the whole bar; only how it is drawn is
    kept here, never what it means.
    """
    layout = session.progress
    if layout is not None and session.progress_state is not None:
        shown_label, shown_done, shown_total = session.progress_state
        # A bar can move forward and keep its label; anything else is drawn
        # anew. Whether a bar is indeterminate is fixed when it is built, and
        # some models do not redraw a label when the value stays the same.
        if not (
            ui.CURRENT_LAYOUT is layout
            and shown_label == label
            and shown_total == total
            and shown_done <= done
        ):
            layout = None
    if layout is None:
        # A new layout is not on the screen yet: its first report puts it there.
        layout = progress(description=label, indeterminate=total == 0)
    done = min(done, total)
    layout.report(done * 1000 // total if total else 0, label)
    session.progress = layout
    session.progress_state = (label, done, total)
