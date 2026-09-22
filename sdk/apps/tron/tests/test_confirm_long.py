# TMP: device test exercising trezor_app_sdk::ui::confirm_long (and Core's
# LongContentScreen paging) via the tron app's demo ConfirmLong handler.
# Not a real Tron feature test.

from trezorlib.debuglink import DebugSession as Session

from . import tron_ext
from .input_flows import InputFlowConfirmLong

# ~19 screens at 96 chars/screen -> exercises real paging, not a single page.
LONG_CONTENT = " ".join(f"word{i:04d}" for i in range(200))


def test_confirm_long(session: Session, instance_id: int):
    with session.test_ctx as client:
        IF = InputFlowConfirmLong(client, LONG_CONTENT)
        client.set_input_flow(IF.get())

        tron_ext.confirm_long(session, instance_id, "Very Long Screen", LONG_CONTENT)
