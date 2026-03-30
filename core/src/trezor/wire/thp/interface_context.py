from micropython import const
from typing import TYPE_CHECKING

import trezorthp
from trezor import config, io, loop, utils
from trezor.loop import Timeout, race, sleep, wait

from . import get_encoded_device_properties
from .channel import TREZOR_STATE_PAIRED, TREZOR_STATE_UNPAIRED, Channel

if __debug__:
    from trezor import log

if utils.USE_BLE:
    import trezorble as ble
    from trezor.workflow import idle_timer

if TYPE_CHECKING:
    from buffer_types import AnyBuffer, AnyBytes
    from trezorio import WireInterface
    from typing import Generator, NoReturn

    from trezor.messages import ThpPairingCredential
    from typing_extensions import Self


EMPTY_BUFFER = bytearray()


class ThpContext:
    """
    This class handles THP receiving from multiple wire interfaces.
    It also handles and responds to low-level single packet THP messages, creating new channels if needed.
    """

    def __init__(self, *ifaces: WireInterface) -> None:
        self._iface_ctxs = [InterfaceContext(iface, self) for iface in ifaces]
        self.channel_ready_box: loop.mailbox[Channel] = loop.mailbox()

    # entry point, then handle_received_message is called
    # returns channel if message is ready and valid
    async def get_next_message(self) -> Channel:
        """
        Reassemble a valid THP payload from any THP interface, and return its channel.

        Also handle THP channel allocation.
        """

        for iface_ctx in self._iface_ctxs:
            channel_id = trezorthp.message_out_ready(iface_ctx._iface.iface_num())
            if channel_id is not None:
                log.error(
                    __name__,
                    f"(cid: {hex(channel_id)}) message ready from previous loop but buffer is lost, waiting for retransmission",
                )

        channel = await self.channel_ready_box
        return channel


class InterfaceContext:
    """
    This class handles multi-packet THP payloads from a single interface.
    It also handles and responds to low-level single packet THP messages, creating new channels if needed.
    """

    def __init__(self, iface: WireInterface, thp_ctx: ThpContext) -> None:
        self._iface = iface
        self._read = wait(iface.iface_num() | io.POLL_READ)
        self._write = wait(iface.iface_num() | io.POLL_WRITE)
        self._channels: dict[int, Channel] = {}
        self.thp_ctx = thp_ctx

        self._write_box: loop.mailbox[None] = loop.mailbox()
        self._retrans_box: loop.mailbox[None] = loop.mailbox()

        self._read_loop: loop.spawn = loop.spawn(self.read_loop())
        self._write_loop: loop.spawn = loop.spawn(self.write_loop())
        self._retrans_loop: loop.spawn = loop.spawn(self.retransmission_loop())
        self._handshake_key_task: loop.spawn | None = None

        self._packet_buf = bytearray(iface.RX_PACKET_LEN)
        self._packet_view = memoryview(self._packet_buf)

        # stored by credential verification callback for use by credential request handler
        # note that this relies on no session restart between credential verification and credential request
        self._credentials: dict[int, ThpPairingCredential] = {}

        trezorthp.init(
            iface.iface_num(),
            get_encoded_device_properties(iface),
            self.verify_credential,
        )

    def get_channel(self, channel_id: int) -> Channel:
        if channel_id not in self._channels:
            from .. import THP_BUFFERS_PROVIDER

            if (buffers := THP_BUFFERS_PROVIDER.take()) is None:
                # TODO try allocation
                # TODO handle preemption
                raise NotImplementedError
            self._channels[channel_id] = Channel(
                channel_id,
                self,
                buffers=buffers,
                credential=self._credentials.pop(channel_id, None),
            )
        channel = self._channels[channel_id]
        return channel

    async def read_loop(self) -> None:
        iface = self._iface
        iface_num = iface.iface_num()

        while True:
            packet_len = await self._read
            if utils.USE_BLE and self._iface is ble.interface:
                # prevent auto-lock while handling longer workflows on Bluetooth
                idle_timer.touch()

            assert packet_len == self._iface.RX_PACKET_LEN

            self._iface.read(self._packet_buf, 0)
            packet_buffer = self._packet_view[:packet_len]
            log.debug(
                __name__,
                f"read: {utils.hexlify_if_bytes(packet_buffer)}",
                iface=iface,
            )
            result = trezorthp.packet_in(iface_num, packet_buffer)

            if isinstance(result, int):
                channel = self.get_channel(result)
                # TODO catch exceptions and remove channel
                channel.read_packet(packet_buffer)
                self.thp_ctx.channel_ready_box.put(channel, replace=True)
                continue

            log.debug(__name__, f"packet_in: {result}", iface=iface)
            if result in (trezorthp.KEY_REQUIRED, trezorthp.KEY_REQUIRED_UNLOCK):
                if self._handshake_key_task is None:
                    self._handshake_key_task = loop.spawn(
                        self.handshake_unlock(result == trezorthp.KEY_REQUIRED_UNLOCK)
                    )

            # maybe we got ACK, recompute next retransmission timeout
            # TODO request_write calls it too, maybe remove from here?
            self.recompute_timeouts()
            # wake up write loop in case broadcast/handshake channels have outgoing data
            self.request_write()

    async def write_loop(self) -> None:
        iface = self._iface
        packet_len = iface.TX_PACKET_LEN
        packet = bytearray(packet_len)

        # TODO remove: send out packets from previous loop
        self._write_box.put(None, replace=True)

        while True:
            await self._write_box
            log.debug(__name__, "write requested", iface=iface)
            await self.write_all_packets(self, packet)
            for channel in self._channels.values():
                await self.write_all_packets(channel, packet)
            self.recompute_timeouts()
            log.debug(__name__, "write done", iface=iface)

    async def write_all_packets(
        self, channel: Channel | Self, packet: AnyBuffer
    ) -> None:
        while channel.write_packet(packet):
            log.debug(
                __name__,
                f"write: {utils.hexlify_if_bytes(packet)}",
                iface=self._iface,
            )
            n_written = 0
            while n_written == 0:
                await self._write
                n_written = self._iface.write(packet)

            assert n_written == self._iface.TX_PACKET_LEN

    def write_packet(self, packet: AnyBuffer) -> bool:
        return trezorthp.packet_out(self._iface.iface_num(), None, EMPTY_BUFFER, packet)

    async def retransmission_loop(self) -> None:
        channel_id = None
        timeout_ms = None
        iface_num = self._iface.iface_num()

        while True:
            if timeout_ms is None:
                await self._retrans_box
            else:
                assert channel_id is not None
                try:
                    await race(self._retrans_box, _timeout_after(timeout_ms))
                except Timeout:
                    ok = trezorthp.message_retransmit(iface_num, channel_id)
                    if ok:
                        log.warning(
                            __name__,
                            f"({hex(channel_id)}) retransmitting message after {timeout_ms} ms",
                            iface=self._iface,
                        )
                        self.request_write()
                    elif channel_id in self._channels:
                        self._channels[channel_id].ack_box.put(
                            Timeout("THP retransmission timeout")
                        )
                    else:
                        log.error(
                            __name__,
                            f"({hex(channel_id)}) retransmission timeout, channel closed",
                            iface=self._iface,
                        )

            res = trezorthp.next_timeout(iface_num)
            channel_id, timeout_ms = res or (None, None)

    def recompute_timeouts(self) -> None:
        self._retrans_box.put(None, replace=True)

    def request_write(self) -> None:
        self._write_box.put(None, replace=True)

    async def handshake_unlock(self, try_to_unlock: bool) -> None:
        try:
            if not config.is_unlocked() and try_to_unlock:
                from trezor import workflow

                from apps.common.lock_manager import unlock_device

                log.debug(
                    __name__,
                    "Static key needed but device is locked, spawning unlock dialog",
                    iface=self._iface,
                )
                # Register the unlock prompt with the workflow management system
                # (in order to avoid immediately respawning the lockscreen task)
                await workflow.spawn(unlock_device())
            trezor_static_privkey, _trezor_static_pubkey = _derive_static_key_pair()
        except Exception as e:
            log.exception(__name__, e)
            trezorthp.handshake_key(self._iface.iface_num(), None)
        else:
            trezorthp.handshake_key(self._iface.iface_num(), trezor_static_privkey)
        finally:
            self.request_write()
            self._handshake_key_task = None

    def verify_credential(
        self, channel_id: int, host_static_public_key: bytes, payload: bytes
    ) -> int:
        from apps.thp.credential_manager import (
            decode_credential,
            unwrap_credential,
            validate_credential,
        )

        try:
            encoded_credential = unwrap_credential(payload)
            if not encoded_credential:
                return TREZOR_STATE_UNPAIRED
            credential = decode_credential(encoded_credential)
            paired = validate_credential(
                credential,
                host_static_public_key,
            )
            if paired:
                from trezor.wire.thp.paired_cache import cache_host_info

                cache_host_info(
                    mac_addr=self.connected_addr(),
                    host_name=credential.cred_metadata.host_name,
                    app_name=credential.cred_metadata.app_name,
                )
                self._credentials[channel_id] = credential
                return TREZOR_STATE_PAIRED
            else:
                return TREZOR_STATE_UNPAIRED
        except Exception as e:
            log.exception(__name__, e, iface=self._iface)
        return TREZOR_STATE_UNPAIRED

    def connected_addr(self) -> AnyBytes | None:
        """
        Return peer MAC address (if connected).

        Currently supported by BLE (used for caching THP host names).
        """
        if utils.USE_BLE:
            if self._iface is ble.interface:
                return ble.connected_addr()

        return None


# Uses `yield` instead of `await` to avoid allocations.
def _timeout_after(ms: int) -> Generator[sleep, int, NoReturn]:
    yield sleep(ms)
    raise Timeout


def _derive_static_key_pair() -> tuple[bytes, bytes]:
    from trezorcrypto import bip32

    from storage import device

    HARDENED = const(0x8000_0000)

    node_int = HARDENED | int.from_bytes(b"\x00THP", "big")
    node = bip32.from_seed(device.get_device_secret(), "curve25519")
    node.derive(node_int)

    trezor_static_private_key = node.private_key()
    trezor_static_public_key = node.public_key()[1:33]
    # Note: the first byte (\x01) of the public key is removed, as it
    # only indicates the type of the elliptic curve used

    return trezor_static_private_key, trezor_static_public_key
