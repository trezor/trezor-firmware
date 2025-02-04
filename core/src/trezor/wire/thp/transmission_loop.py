from micropython import const
from typing import TYPE_CHECKING

from trezor import loop

from .writer import write_payload_to_wire_and_add_checksum

if TYPE_CHECKING:
    from . import PacketHeader
    from .channel import Channel

MAX_RETRANSMISSION_COUNT = const(50)
MIN_RETRANSMISSION_COUNT = const(2)


class TransmissionLoop:

    def __init__(
        self, channel: Channel, header: PacketHeader, transport_payload: bytes
    ) -> None:
        self.channel: Channel = channel
        self.header: PacketHeader = header
        self.transport_payload: bytes = transport_payload
        self.wait_task: loop.spawn | None = None
        self.min_retransmisson_count_achieved: bool = False

    async def start(
        self, max_retransmission_count: int = MAX_RETRANSMISSION_COUNT
    ) -> None:
        self.min_retransmisson_count_achieved = False
        for i in range(max_retransmission_count):
            if i >= MIN_RETRANSMISSION_COUNT:
                self.min_retransmisson_count_achieved = True
            await write_payload_to_wire_and_add_checksum(
                self.channel.iface, self.header, self.transport_payload
            )
            self.wait_task = loop.spawn(self._wait(i))
            try:
                await self.wait_task
            except loop.TaskClosed:
                self.wait_task = None
                break

    def stop_immediately(self) -> None:
        if self.wait_task is not None:
            self.wait_task.close()
        self.wait_task = None

    async def _wait(self, counter: int = 0) -> None:
        timeout_ms = round(10200 - 1010000 / (counter + 100))
        await loop.sleep(timeout_ms)

    def __del__(self) -> None:
        self.stop_immediately()
