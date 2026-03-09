# flake8: noqa: F403,F405
from common import *  # isort:skip

if utils.USE_THP:
    from typing import TYPE_CHECKING

    from mock import patch
    from mock_wire_interface import MockHID
    from storage import cache_thp
    from trezor.wire import context
    from trezor.wire.thp.channel import Channel
    from trezor.wire.thp.channel_manager import create_new_channel
    from trezor.wire.thp.interface_context import ThpContext
    from trezor.wire.thp.memory_manager import ThpBuffer
    from trezor.wire.thp.session_context import SessionContext

    if TYPE_CHECKING:
        from typing import Any, Type

        from trezor import protobuf
        from trezor.wire import WireInterface

    def prepare_context() -> None:
        mock_iface = MockHID()
        channel = get_new_channel(mock_iface)
        session_cache = cache_thp.create_or_replace_session(
            channel.channel_cache, session_id=b"\x01"
        )
        context.CURRENT_CONTEXT = SessionContext(channel, session_cache)

    def get_new_channel(iface: WireInterface) -> Channel:
        channel_cache = create_new_channel(iface)
        thp_ctx = ThpContext(iface)
        (iface_ctx,) = thp_ctx._iface_ctxs
        return Channel(channel_cache, iface_ctx, (ThpBuffer(), ThpBuffer()))

    def _encrypt_patch() -> patch:
        return patch(Channel, "_encrypt", lambda self, buffer, noise_payload_len: None)

    class TrackedChannel:

        def __init__(self) -> None:
            self.messages_to_write = []
            self.expected_messages_to_write = []
            self.inner_channel = context.get_channel_context()
            self.original_write = self.inner_channel.write

        def __getattr__(self, name: str) -> Any:
            return getattr(self.inner_channel, name)

        def set_expected_messages_to_write(
            self, messages: list[Type[protobuf.MessageType]]
        ) -> None:
            self.expected_messages_to_write = messages

        def __enter__(self) -> None:
            self.messages_to_write: list[protobuf.MessageType] = []
            # To track recursive calls in channel.write
            self.inner_channel.write = self.write

        def __exit__(self, exc_type, exc_value, tb) -> None:
            self.inner_channel.write = self.original_write
            if not self.expected_messages_to_write:
                return
            actual = self.messages_to_write
            expected = self.expected_messages_to_write
            if len(actual) != len(expected):
                raise AssertionError(
                    f"Count mismatch for actual and expected messages {len(actual)}/{len(expected)}"
                )
            for act, exp in zip(actual, expected):
                if not exp.is_type_of(act):
                    raise AssertionError(
                        f"Expected {exp.MESSAGE_NAME}, got {act.MESSAGE_NAME}"
                    )

        async def write(
            self,
            msg: protobuf.MessageType,
            session_id: int = 0,
        ) -> None:
            self.messages_to_write.append(msg)
            with _encrypt_patch():
                # encryption is disabled
                return await self.original_write(msg, session_id)
