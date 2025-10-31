from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from buffer_types import AnyBytes

    from trezor.utils import BufferReader


def parse_cert_chain(r: BufferReader) -> list[AnyBytes]:
    from trezor import wire
    from trezor.crypto.der import read_length

    certificates = []
    while r.remaining_count() > 0:
        cert_begin = r.offset
        if r.get() != 0x30:
            raise wire.FirmwareError("Device certificate is corrupted.")
        n = read_length(r)
        cert_len = r.offset - cert_begin + n
        r.seek(cert_begin)
        certificates.append(r.read_memoryview(cert_len))

    return certificates
