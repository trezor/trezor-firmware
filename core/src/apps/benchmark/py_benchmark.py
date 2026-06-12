from trezor.messages import BenchmarkResult

from .common import format_float


def func_noop() -> None:
    pass


def func_strcat() -> None:
    result = ""
    for i in range(10):
        result += "trezor"


def func_listappend() -> None:
    result = []
    for i in range(100):
        result.append(i)


def func_smallnum() -> None:
    result = 1
    for i in range(200):
        result += i


def func_bignum() -> None:
    result = 1
    for i in range(20):
        result *= i + 1

def func_bigalloc() -> None:
    for i in range(10):
        a = bytearray(1000)
        a[500] = 255


def func_import() -> None:
    for i in range(10):
        import apps.webauthn.fido2
        del apps.webauthn.fido2

def func_fromimport() -> None:
    for i in range(10):
        from apps.webauthn.fido2 import Msg
        del Msg

class PyBenchmark:
    def __init__(self, variant: str) -> None:
        self.func = {
            "noop": func_noop,
            "strcat": func_strcat,
            "listappend": func_listappend,
            "smallnum": func_smallnum,
            "bignum": func_bignum,
            "bigalloc": func_bigalloc,
            "import": func_import,
            "fromimport": func_fromimport,
        }[variant]

    def prepare(self) -> None:
        self.iterations_count = 1000

    def run(self) -> None:
        do_func = self.func
        for i in range(self.iterations_count):
            do_func()

    def get_result(self, duration_us: int, repetitions: int) -> BenchmarkResult:
        return BenchmarkResult(
            value=format_float(duration_us / (repetitions * self.iterations_count)),
            unit="us",
        )
