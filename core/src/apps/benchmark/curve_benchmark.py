from typing import TYPE_CHECKING

from trezor.messages import BenchmarkResult

from .common import format_float, random_bytes

if TYPE_CHECKING:
    from typing import Protocol

    class Curve(Protocol):
        def generate_secret(self) -> bytes: ...

        def publickey(self, secret_key: bytes) -> bytes: ...

    class SignCurve(Curve, Protocol):
        def sign(self, secret_key: bytes, digest: bytes) -> bytes: ...

        def verify(
            self, public_key: bytes, signature: bytes, digest: bytes
        ) -> bool: ...

        def generate_secret(self) -> bytes: ...

        def publickey(self, secret_key: bytes) -> bytes: ...

    class MultiplyCurve(Curve, Protocol):
        def generate_secret(self) -> bytes: ...

        def publickey(self, secret_key: bytes) -> bytes: ...

        def multiply(self, secret_key: bytes, public_key: bytes) -> bytes: ...


class SignBenchmark:
    def __init__(self, curve: SignCurve) -> None:
        self.curve = curve

    def prepare(self) -> None:
        self.iterations_count = 10
        self.secret_key = self.curve.generate_secret()
        self.digest = random_bytes(32)

    def run(self) -> None:
        for _ in range(self.iterations_count):
            self.curve.sign(self.secret_key, self.digest)

    def get_result(self, duration_us: int, repetitions: int) -> BenchmarkResult:
        value = duration_us / (repetitions * self.iterations_count * 1000)

        return BenchmarkResult(value=format_float(value), unit="ms")


class VerifyBenchmark:
    def __init__(self, curve: SignCurve) -> None:
        self.curve = curve

    def prepare(self) -> None:
        self.iterations_count = 10
        self.secret_key = self.curve.generate_secret()
        self.public_key = self.curve.publickey(self.secret_key)
        self.digest = random_bytes(32)
        self.signature = self.curve.sign(self.secret_key, self.digest)

    def run(self) -> None:
        for _ in range(self.iterations_count):
            self.curve.verify(self.public_key, self.signature, self.digest)

    def get_result(self, duration_us: int, repetitions: int) -> BenchmarkResult:
        value = duration_us / (repetitions * self.iterations_count * 1000)

        return BenchmarkResult(value=format_float(value), unit="ms")


class MultiplyBenchmark:
    def __init__(self, curve: MultiplyCurve) -> None:
        self.curve = curve

    def prepare(self) -> None:
        self.secret_key = self.curve.generate_secret()
        self.public_key = self.curve.publickey(self.curve.generate_secret())
        self.iterations_count = 10

    def run(self) -> None:
        for _ in range(self.iterations_count):
            self.curve.multiply(self.secret_key, self.public_key)

    def get_result(self, duration_us: int, repetitions: int) -> BenchmarkResult:
        value = duration_us / (repetitions * self.iterations_count * 1000)

        return BenchmarkResult(value=format_float(value), unit="ms")


class PublickeyBenchmark:
    def __init__(self, curve: Curve) -> None:
        self.curve = curve

    def prepare(self) -> None:
        self.iterations_count = 10
        self.secret_key = self.curve.generate_secret()

    def run(self) -> None:
        for _ in range(self.iterations_count):
            self.curve.publickey(self.secret_key)

    def get_result(self, duration_us: int, repetitions: int) -> BenchmarkResult:
        value = duration_us / (repetitions * self.iterations_count * 1000)

        return BenchmarkResult(value=format_float(value), unit="ms")
