from typing import TYPE_CHECKING, Callable

from trezor.messages import BenchmarkResult

from .common import format_float, maximum_used_memory_in_bytes, random_bytes

if TYPE_CHECKING:
    from typing import Protocol

    class CipherCtx(Protocol):
        def encrypt(self, data: bytes) -> bytes: ...

        def decrypt(self, data: bytes) -> bytes: ...


class EncryptBenchmark:
    def __init__(
        self, cipher_ctx_constructor: Callable[[], CipherCtx], block_size: int
    ) -> None:
        self.cipher_ctx_constructor = cipher_ctx_constructor
        self.block_size = block_size

    def prepare(self) -> None:
        self.cipher_ctx = self.cipher_ctx_constructor()
        self.blocks_count = maximum_used_memory_in_bytes // self.block_size
        self.iterations_count = 100
        self.data = random_bytes(self.blocks_count * self.block_size)

    def run(self) -> None:
        for _ in range(self.iterations_count):
            self.cipher_ctx.encrypt(self.data)

    def get_result(self, duration_us: int, repetitions: int) -> BenchmarkResult:
        value = (repetitions * self.iterations_count * len(self.data) * 1000 * 1000) / (
            duration_us * 1024 * 1024
        )

        return BenchmarkResult(
            value=format_float(value),
            unit="MB/s",
        )


class DecryptBenchmark:
    def __init__(
        self, cipher_ctx_constructor: Callable[[], CipherCtx], block_size: int
    ) -> None:
        self.cipher_ctx_constructor = cipher_ctx_constructor
        self.block_size = block_size

    def prepare(self) -> None:
        self.cipher_ctx = self.cipher_ctx_constructor()
        self.blocks_count = maximum_used_memory_in_bytes // self.block_size
        self.iterations_count = 100
        self.data = random_bytes(self.blocks_count * self.block_size)

    def run(self) -> None:
        for _ in range(self.iterations_count):
            self.cipher_ctx.decrypt(self.data)

    def get_result(self, duration_us: int, repetitions: int) -> BenchmarkResult:
        value = (repetitions * self.iterations_count * len(self.data) * 1000 * 1000) / (
            duration_us * 1024 * 1024
        )

        return BenchmarkResult(
            value=format_float(value),
            unit="MB/s",
        )
