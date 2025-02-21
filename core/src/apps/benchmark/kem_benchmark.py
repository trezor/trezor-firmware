from typing import TYPE_CHECKING

from trezor.messages import BenchmarkResult
from trezor.utils import estimate_unused_stack, zero_unused_stack

from .common import format_float

if TYPE_CHECKING:
    from typing import Protocol

    class KEM(Protocol):
        def generate_keypair(self) -> tuple[bytes, bytes]: ...

        def encapsulate(self, encapsulation_key: bytes) -> tuple[bytes, bytes]: ...

        def decapsulate(self, decapsulation_key: bytes, ciphertext: bytes) -> bytes: ...


class GenerateKeypairTimeBenchmark:
    def __init__(self, kem: KEM) -> None:
        self.kem = kem

    def prepare(self) -> None:
        self.iterations_count = 100

    def run(self) -> None:
        for _ in range(self.iterations_count):
            self.private_key, self.public_key = self.kem.generate_keypair()

    def get_result(self, duration_us: int, repetitions: int) -> BenchmarkResult:
        value = duration_us / (repetitions * self.iterations_count * 1000)

        return BenchmarkResult(value=format_float(value), unit="ms")


class EncapsulateTimeBenchmark:
    def __init__(self, kem: KEM) -> None:
        self.kem = kem

    def prepare(self) -> None:
        self.iterations_count = 100
        self.private_key, self.public_key = self.kem.generate_keypair()

    def run(self) -> None:
        for _ in range(self.iterations_count):
            self.kem.encapsulate(self.public_key)

    def get_result(self, duration_us: int, repetitions: int) -> BenchmarkResult:
        value = duration_us / (repetitions * self.iterations_count * 1000)

        return BenchmarkResult(value=format_float(value), unit="ms")


class DecapsulateTimeBenchmark:
    def __init__(self, kem: KEM) -> None:
        self.kem = kem

    def prepare(self) -> None:
        self.iterations_count = 100
        self.private_key, self.public_key = self.kem.generate_keypair()
        self.ciphertext, self.shared_secret = self.kem.encapsulate(self.public_key)

    def run(self) -> None:
        for _ in range(self.iterations_count):
            self.kem.decapsulate(self.private_key, self.ciphertext)

    def get_result(self, duration_us: int, repetitions: int) -> BenchmarkResult:
        value = duration_us / (repetitions * self.iterations_count * 1000)

        return BenchmarkResult(value=format_float(value), unit="ms")


class GenerateKeypairMemoryBenchmark:
    def __init__(self, key: KEM) -> None:
        self.key = key

    def prepare(self) -> None:
        pass

    def run(self) -> None:
        zero_unused_stack()
        unused_stack_before = estimate_unused_stack()
        self.key.generate_keypair()
        unused_stack_after = estimate_unused_stack()
        self.usage = unused_stack_before - unused_stack_after

    def get_result(self, duration_us: int, repetitions: int) -> BenchmarkResult:
        return BenchmarkResult(value=str(self.usage), unit="B")


class EncapsulateMemoryBenchmark:
    def __init__(self, key: KEM) -> None:
        self.key = key

    def prepare(self) -> None:
        self.private_key, self.public_key = self.key.generate_keypair()

    def run(self) -> None:
        zero_unused_stack()
        unused_stack_before = estimate_unused_stack()
        self.key.encapsulate(self.public_key)
        unused_stack_after = estimate_unused_stack()
        self.usage = unused_stack_before - unused_stack_after

    def get_result(self, duration_us: int, repetitions: int) -> BenchmarkResult:
        return BenchmarkResult(value=str(self.usage), unit="B")


class DecapsulateMemoryBenchmark:
    def __init__(self, key: KEM) -> None:
        self.key = key

    def prepare(self) -> None:
        self.private_key, self.public_key = self.key.generate_keypair()
        self.ciphertext, self.shared_secret = self.key.encapsulate(self.public_key)

    def run(self) -> None:
        zero_unused_stack()
        unused_stack_before = estimate_unused_stack()
        self.key.decapsulate(self.private_key, self.ciphertext)
        unused_stack_after = estimate_unused_stack()
        self.usage = unused_stack_before - unused_stack_after

    def get_result(self, duration_us: int, repetitions: int) -> BenchmarkResult:
        return BenchmarkResult(value=str(self.usage), unit="B")
