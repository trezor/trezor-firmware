from micropython import const
from typing import TYPE_CHECKING

from trezor import loop
from trezor.wire.thp.thp_messages import PacketHeader
from trezor.wire.thp.writer import write_payload_to_wire_and_add_checksum

if TYPE_CHECKING:
    from trezor.wire.thp.channel import Channel

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

    async def start(self):
        self.min_retransmisson_count_achieved = False
        for i in range(MAX_RETRANSMISSION_COUNT):
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

    def stop_immediately(self):
        if self.wait_task is not None:
            self.wait_task.close()
        self.wait_task = None

    async def stop_after_min_retransmission(self):
        while not self.min_retransmisson_count_achieved and self.wait_task is not None:
            await self._short_wait()
        self.stop_immediately()

    async def _wait(self, counter: int = 0) -> None:
        timeout_ms = round(10200 - 1010000 / (counter + 100))
        await loop.sleep(timeout_ms)

    async def _short_wait(self):
        loop.wait(50)

    def __del__(self):
        self.stop_immediately()
