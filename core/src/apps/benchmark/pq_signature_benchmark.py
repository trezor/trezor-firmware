from typing import TYPE_CHECKING

from trezor.messages import BenchmarkResult

from .common import format_float, random_bytes

if TYPE_CHECKING:
    from typing import Protocol, Tuple

    class PqSignature(Protocol):
        public_key_size: int
        secret_key_size: int
        signature_size: int

        def sign(self, secret_key: bytes, message: bytes) -> bytes: ...

        def verify(
            self, public_key: bytes, signature: bytes, message: bytes
        ) -> bool: ...

        def generate_keypair(self) -> Tuple[bytes, bytes]: ...


class SignTimeBenchmark:
    def __init__(self, pq_signature: PqSignature) -> None:
        self.pq_signature = pq_signature

    def prepare(self) -> None:
        self.iterations_count = 1
        self.secret_key, self.public_key = self.pq_signature.generate_keypair()
        self.digest = random_bytes(32)

    def run(self) -> None:
        for _ in range(self.iterations_count):
            self.pq_signature.sign(self.secret_key, self.digest)

    def get_result(self, duration_us: int, repetitions: int) -> BenchmarkResult:
        value = duration_us / (repetitions * self.iterations_count * 1000)

        return BenchmarkResult(value=format_float(value), unit="ms")


class VerifyTimeBenchmark:
    def __init__(self, pq_signature: PqSignature) -> None:
        self.pq_signature = pq_signature

    def prepare(self) -> None:
        self.iterations_count = 10
        self.secret_key, self.public_key = self.pq_signature.generate_keypair()
        self.digest = random_bytes(32)
        self.signature = self.pq_signature.sign(self.secret_key, self.digest)

    def run(self) -> None:
        for _ in range(self.iterations_count):
            self.pq_signature.verify(self.public_key, self.signature, self.digest)

    def get_result(self, duration_us: int, repetitions: int) -> BenchmarkResult:
        value = duration_us / (repetitions * self.iterations_count * 1000)

        return BenchmarkResult(value=format_float(value), unit="ms")


class GenerateKeypairTimeBenchmark:
    def __init__(self, pq_signature: PqSignature) -> None:
        self.pq_signature = pq_signature

    def prepare(self) -> None:
        self.iterations_count = 1

    def run(self) -> None:
        for _ in range(self.iterations_count):
            _, _ = self.pq_signature.generate_keypair()

    def get_result(self, duration_us: int, repetitions: int) -> BenchmarkResult:
        value = duration_us / (repetitions * self.iterations_count * 1000)

        return BenchmarkResult(value=format_float(value), unit="ms")


class GenerateKeypairMemoryBenchmark:
    def __init__(self, pq_signature: PqSignature) -> None:
        self.pq_signature = pq_signature

    def prepare(self) -> None:
        pass

    def run(self) -> None:
        from trezor.utils import estimate_unused_stack, zero_unused_stack

        zero_unused_stack()
        unused_stack_before = estimate_unused_stack()
        self.pq_signature.generate_keypair()
        unused_stack_after = estimate_unused_stack()
        self.usage = unused_stack_before - unused_stack_after

    def get_result(self, duration_us: int, repetitions: int) -> BenchmarkResult:
        return BenchmarkResult(value=str(self.usage), unit="B")


class SignMemoryBenchmark:
    def __init__(self, pq_signature: PqSignature) -> None:
        self.pq_signature = pq_signature

    def prepare(self) -> None:
        self.secret_key, self.public_key = self.pq_signature.generate_keypair()
        self.digest = random_bytes(32)

    def run(self) -> None:
        from trezor.utils import estimate_unused_stack, zero_unused_stack

        zero_unused_stack()
        unused_stack_before = estimate_unused_stack()
        self.pq_signature.sign(self.secret_key, self.digest)
        unused_stack_after = estimate_unused_stack()
        self.usage = unused_stack_before - unused_stack_after

    def get_result(self, duration_us: int, repetitions: int) -> BenchmarkResult:
        return BenchmarkResult(value=str(self.usage), unit="B")


class VerifyMemoryBenchmark:
    def __init__(self, pq_signature: PqSignature) -> None:
        self.pq_signature = pq_signature

    def prepare(self) -> None:
        self.secret_key, self.public_key = self.pq_signature.generate_keypair()
        self.digest = random_bytes(32)
        self.signature = self.pq_signature.sign(self.secret_key, self.digest)

    def run(self) -> None:
        from trezor.utils import estimate_unused_stack, zero_unused_stack

        zero_unused_stack()
        unused_stack_before = estimate_unused_stack()
        assert (
            self.pq_signature.verify(self.public_key, self.signature, self.digest)
            is True
        )
        unused_stack_after = estimate_unused_stack()
        self.usage = unused_stack_before - unused_stack_after

    def get_result(self, duration_us: int, repetitions: int) -> BenchmarkResult:
        return BenchmarkResult(value=str(self.usage), unit="B")
