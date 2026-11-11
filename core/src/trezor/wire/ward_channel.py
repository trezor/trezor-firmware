"""Independent, device-initiated WARD backend. One private 64-byte report.

The listener owns all physical I/O; workflows communicate with it through a
mailbox. Neither wallet THP buffers nor wallet codec buffers are used here.
"""

from micropython import const
from typing import TYPE_CHECKING

from trezor import loop, protobuf
from trezor.enums import MessageType as MT
from trezor.wire import DataError, context

if TYPE_CHECKING:
    from collections.abc import Container
    from typing import Any

    from trezor.messages import WARDServiceOpen
    from trezor.wire import WireInterface

TIMEOUT_MS = const(30000)
_endpoint: "Endpoint | None" = None


class Endpoint:
    def __init__(self, iface: WireInterface) -> None:
        from .codec.streaming import StreamCodec

        self.codec = StreamCodec(iface)
        self.requests = loop.mailbox()
        from storage.cache import get_sessionless_cache
        from storage.cache_common import APP_WARD_SERVICE_BINDING

        saved = get_sessionless_cache().get(APP_WARD_SERVICE_BINDING)
        self.bound = bool(saved and saved[0])
        self.generation = int.from_bytes(saved[1:], "big") if saved else 0

    def remember(self) -> None:
        from storage.cache import get_sessionless_cache
        from storage.cache_common import APP_WARD_SERVICE_BINDING

        get_sessionless_cache().set(
            APP_WARD_SERVICE_BINDING,
            bytes([self.bound]) + self.generation.to_bytes(4, "big"),
        )

    async def bootstrap(self) -> WARDServiceOpen:
        from trezor.messages import WARDServiceOpen

        kind = await self.codec.header()
        # A bootstrap always fits in the first report, so cancellation while
        # idle cannot abandon a partly read application message.
        if kind != MT.WARDServiceOpen or self.codec.length > 16:
            raise DataError("WARD service must announce itself")
        msg = await self.codec.message(WARDServiceOpen, self.codec.length)
        if msg.protocol_version != 1:
            raise DataError("unsupported WARD service protocol")
        return msg

    async def exchange(
        self, request: protobuf.MessageType, expected: Container[int]
    ) -> protobuf.MessageType:
        await self.codec.write(request)
        return await self.codec.read(expected)

    async def run(self) -> None:
        while True:
            try:
                item = await loop.race(self.bootstrap(), self.requests)
            except Exception:
                self.bound = False
                self.remember()
                continue
            if not isinstance(item, tuple):
                from trezor.messages import WARDServiceOpenAck

                # A pending workflow cannot cancel the acknowledgement of a fully
                # received Open. Only the idle read participates in the race above.
                try:
                    # Persist before acknowledging: a wallet loop restart after
                    # the host receives the ACK must retain the announced state.
                    self.generation = (self.generation + 1) & 0xFFFFFFFF
                    self.bound = not item.close
                    self.remember()
                    result = await loop.race(
                        self.codec.write(
                            WARDServiceOpenAck(protocol_version=1, buffer_size=64)
                        ),
                        loop.sleep(TIMEOUT_MS),
                    )
                    if isinstance(result, int):
                        raise DataError("WARD announcement timed out")
                except Exception:
                    self.bound = False
                    self.remember()
                continue
            generation, request, expected, reply = item
            if not self.bound or generation != self.generation:
                # Refusing an old operation must not revoke a newer binding.
                reply.put(DataError("WARD service disconnected or rebound"))
                continue
            try:
                answer = await loop.race(
                    self.exchange(request, expected), loop.sleep(TIMEOUT_MS)
                )
                if isinstance(answer, int):
                    raise DataError("WARD service timed out")
                reply.put(answer)
            except Exception:
                self.bound = False
                self.remember()
                reply.put(DataError("WARD service exchange failed"))


async def serve(iface: WireInterface) -> None:
    global _endpoint
    _endpoint = Endpoint(iface)
    await _endpoint.run()


def selected() -> "tuple[Endpoint, int] | None":
    ctx = context.get_context()
    if not ctx.ward_selected:
        ctx.ward_selected = True
        if _endpoint is not None and _endpoint.bound:
            ctx.ward_route = (_endpoint, _endpoint.generation)
    return ctx.ward_route


async def call(
    request: protobuf.MessageType, expected: Container[int]
) -> protobuf.MessageType:
    route = selected()
    if route is None:
        raise DataError("no WARD service is bound")
    endpoint, generation = route
    reply = loop.mailbox()
    endpoint.requests.put((generation, request, expected, reply))
    answer = await reply
    if isinstance(answer, Exception):
        raise answer
    if answer.MESSAGE_WIRE_TYPE == MT.Failure:
        raise DataError("WARD backend refused the operation")
    return answer


async def ensure_ready() -> None:
    ctx = context.get_context()
    if ctx.ward_ready:
        return
    from trezor.messages import (
        WARDIngestAttestation,
        WARDReconcile,
        WARDServiceDone,
        WARDSync,
        WARDVerifyChain,
    )

    from apps.ward.ingest import ingest
    from apps.ward.reconcile import reconcile
    from apps.ward.sync import sync
    from apps.ward.verify_chain import verify_chain

    start = await sync(WARDSync())
    start.service_bound = False  # this is the backend's sync, not wallet discovery
    request = start
    phase = 0
    while True:
        expected = (
            (MT.WARDIngestAttestation, MT.Failure)
            if phase == 0
            else (MT.WARDReconcile, MT.WARDVerifyChain, MT.Failure)
            if phase == 1
            else (MT.WARDServiceDone, MT.Failure)
        )
        response = await call(request, expected)
        if phase == 0:
            assert WARDIngestAttestation.is_type_of(response)
            request = await ingest(response)
        elif phase == 1:
            if WARDVerifyChain.is_type_of(response):
                request = await verify_chain(response)
            else:
                assert WARDReconcile.is_type_of(response)
                request = await reconcile(response)
        else:
            assert WARDServiceDone.is_type_of(response)
            if response.error:
                raise DataError("WARD backend could not synchronize")
            ctx.ward_ready = True
            return
        phase += 1


async def publish(candidate: Any) -> Any:
    from trezor.messages import (
        WARDConfirmBatchByWM,
        WARDConfirmRevertByWM,
        WARDServiceDone,
    )

    from apps.ward.confirm_batch import confirm_batch
    from apps.ward.confirm_revert import confirm_revert

    revert = candidate.MESSAGE_WIRE_TYPE == MT.WARDPerformRevertAck
    expected = MT.WARDConfirmRevertByWM if revert else MT.WARDConfirmBatchByWM
    reply = await call(candidate, (expected, MT.Failure))
    if revert:
        assert WARDConfirmRevertByWM.is_type_of(reply)
        installed = await confirm_revert(reply)
    else:
        assert WARDConfirmBatchByWM.is_type_of(reply)
        installed = await confirm_batch(reply)
    done = await call(installed, (MT.WARDServiceDone, MT.Failure))
    assert WARDServiceDone.is_type_of(done)
    if done.error:
        raise DataError("WARD backend publication failed")
    candidate.service_applied = True
    if not revert:
        candidate.leaves = []
    return candidate
