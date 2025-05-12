from typing import TYPE_CHECKING, Callable

from trezor.messages import BenchmarkResult

from .common import format_float, maximum_used_memory_in_bytes, random_bytes

if TYPE_CHECKING:
    from typing import Protocol

    class HashCtx(Protocol):
        block_size: int

        def update(self, __buf: bytes) -> None: ...

        def digest(self) -> bytes: ...


class HashBenchmark:
    def __init__(self, hash_ctx_constructor: Callable[[], HashCtx]) -> None:
        self.hash_ctx_constructor = hash_ctx_constructor

    def prepare(self) -> None:
        self.hash_ctx = self.hash_ctx_constructor()
        self.blocks_count = maximum_used_memory_in_bytes // self.hash_ctx.block_size
        self.iterations_count = 100
        self.data = random_bytes(self.blocks_count * self.hash_ctx.block_size)

        self.hash_ctx.update(self.data)

    def run(self) -> None:
        for _ in range(self.iterations_count):
            self.hash_ctx.digest()

    def get_result(self, duration_us: int, repetitions: int) -> BenchmarkResult:
        value = (repetitions * self.iterations_count * len(self.data) * 1000 * 1000) / (
            duration_us * 1024 * 1024
        )

        return BenchmarkResult(
            value=format_float(value),
            unit="MB/s",
        )


class RateHashBenchmark:
    def __init__(self, hash_ctx_constructor: Callable[[], HashCtx]) -> None:
        self.hash_ctx_constructor = hash_ctx_constructor

    def prepare(self) -> None:
        self.hash_ctx = self.hash_ctx_constructor()
        self.iterations_count = 10000
        self.data = bytes(self.hash_ctx.block_size)

    def run(self) -> None:
        for _ in range(self.iterations_count):
            self.hash_ctx.update(self.data)

    def get_result(self, duration_us: int, repetitions: int) -> BenchmarkResult:
        value = (repetitions * self.iterations_count * 1000 * 1000) / (duration_us)

        return BenchmarkResult(
            value=format_float(value),
            unit="#/s",
        )


class TimeHashBenchmark:
    def __init__(self, hash_ctx_constructor: Callable[[], HashCtx]) -> None:
        self.hash_ctx_constructor = hash_ctx_constructor

    def prepare(self) -> None:
        from ubinascii import hexlify

        self.hash_ctx = self.hash_ctx_constructor()
        self.hash_ctx.update(bytes(1000 * [0x00]))
        d1 = self.hash_ctx.digest()

        self.hash_ctx = self.hash_ctx_constructor()
        self.hash_ctx.update(bytes(1000 * [0xff]))
        d2 = self.hash_ctx.digest()

        print(hexlify(d1))
        print(hexlify(d2))

        self.iterations_count = 10000
        self.data = bytes(self.hash_ctx.block_size)

    def run(self) -> None:
        for _ in range(self.iterations_count):
            self.hash_ctx.update(self.data)

    def get_result(self, duration_us: int, repetitions: int) -> BenchmarkResult:
        value = (duration_us) / (repetitions * self.iterations_count * 1000)

        return BenchmarkResult(
            value=format_float(value),
            unit="ms",
        )
