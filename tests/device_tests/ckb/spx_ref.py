"""Host-side SLH-DSA-SHA2-128s verifier for the CKB SPHINCS+ device tests.

Built from the same `vendor/sphincsplus/ref` sources the firmware vendors, which
is deliberate: SPHINCS+ is unmodified upstream code and is not what these tests
pin down. What is under test is the CKB message construction, re-implemented
independently in `prevtx.py`; verifying the device's signature against the
host-computed message is what makes a wrong construction fail.

pyspx would be a stronger oracle for SPHINCS+ itself but bundles a different
revision - the same seed yields a different Merkle root - so it cannot verify
these signatures at all.
"""

import ctypes
import subprocess
import tempfile
from pathlib import Path
from typing import NoReturn

_REF = Path(__file__).resolve().parents[3] / "vendor" / "sphincsplus" / "ref"
_SOURCES = (
    "sign.c address.c merkle.c wots.c wotsx1.c utils.c utilsx1.c fors.c "
    "hash_sha2.c thash_sha2_simple.c sha2.c"
).split()

# Verification never calls randombytes, but dlopen refuses the library unless
# the symbol resolves.
_STUB = "void randombytes(unsigned char *x, unsigned long long n) {(void)x;(void)n;}"

_lib: ctypes.CDLL | None = None


class BuildUnavailable(Exception):
    """The reference verifier could not be built in this environment."""


def skip_or_fail(exc: BuildUnavailable) -> NoReturn:
    """Skip the calling test locally, but FAIL it on CI.

    The signature-covers-the-message tests are the strongest cryptographic
    checks in the suite; on a developer box without a C toolchain skipping is a
    convenience, but on CI a silent skip would drop that whole layer without
    anyone noticing.
    """
    import os

    import pytest

    # GitHub Actions sets CI=true; some runners set CI=false, still a truthy str.
    if os.environ.get("CI", "").lower() not in ("", "0", "false"):
        pytest.fail(f"reference verifier must build on CI: {exc}")
    pytest.skip(f"reference verifier unavailable: {exc}")


def _load() -> ctypes.CDLL:
    global _lib
    if _lib is not None:
        return _lib
    if not _REF.is_dir():
        raise BuildUnavailable(f"{_REF} is missing (submodule not checked out?)")

    out = Path(tempfile.mkdtemp(prefix="spx_ref_"))
    (out / "stub.c").write_text(_STUB)
    lib_path = out / "libspx.so"
    try:
        subprocess.run(
            ["cc", "-O2", "-shared", "-fPIC", "-o", str(lib_path)]
            + ["-DPARAMS=sphincs-sha2-128s", f"-I{_REF}"]
            + [str(_REF / src) for src in _SOURCES]
            + [str(out / "stub.c")],
            check=True,
            capture_output=True,
            timeout=300,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise BuildUnavailable(f"cannot build reference verifier: {exc}") from exc

    _lib = ctypes.CDLL(str(lib_path))
    _lib.crypto_sign_verify.restype = ctypes.c_int
    _lib.crypto_sign_verify.argtypes = [
        ctypes.c_char_p,
        ctypes.c_size_t,
        ctypes.c_char_p,
        ctypes.c_size_t,
        ctypes.c_char_p,
    ]
    return _lib


def verify_sha2_128s(message: bytes, signature: bytes, public_key: bytes) -> bool:
    lib = _load()
    return (
        lib.crypto_sign_verify(
            signature, len(signature), message, len(message), public_key
        )
        == 0
    )
