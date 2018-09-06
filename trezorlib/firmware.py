import binascii

import construct as c
import pyblake2

from . import cosi, messages as proto, tools


def bytes_not(data):
    return bytes(~b & 0xff for b in data)


# fmt: off
Toif = c.Struct(
    "magic" / c.Const(b"TOI"),
    "format" / c.Enum(c.Byte, full_color=b"f", grayscale=b"g"),
    "width" / c.Int16ul,
    "height" / c.Int16ul,
    "data" / c.Prefixed(c.Int32ul, c.GreedyBytes),
)


VendorTrust = c.Transformed(c.BitStruct(
    "reserved" / c.Padding(9),
    "show_vendor_string" / c.Flag,
    "require_user_click" / c.Flag,
    "red_background" / c.Flag,
    "delay" / c.BitsInteger(4),
), bytes_not, 2, bytes_not, 2)


VendorHeader = c.Struct(
    "_start_offset" / c.Tell,
    "magic" / c.Const(b"TRZV"),
    "_header_len" / c.Padding(4),
    "expiry" / c.Int32ul,
    "version" / c.Struct(
        "major" / c.Int8ul,
        "minor" / c.Int8ul,
    ),
    "vendor_sigs_required" / c.Int8ul,
    "vendor_sigs_n" / c.Rebuild(c.Int8ul, c.len_(c.this.pubkeys)),
    "vendor_trust" / VendorTrust,
    "reserved" / c.Padding(14),
    "pubkeys" / c.Bytes(32)[c.this.vendor_sigs_n],
    "vendor_string" / c.Aligned(4, c.PascalString(c.Int8ul, "utf-8")),
    "vendor_image" / Toif,
    "_data_end_offset" / c.Tell,

    c.Padding(-(c.this._data_end_offset + 65) % 512),
    "sigmask" / c.Byte,
    "signature" / c.Bytes(64),

    "_end_offset" / c.Tell,
    "header_len" / c.Pointer(
        c.this._start_offset + 4,
        c.Rebuild(c.Int32ul, c.this._end_offset - c.this._start_offset)
    ),
)


VersionLong = c.Struct(
    "major" / c.Int8ul,
    "minor" / c.Int8ul,
    "patch" / c.Int8ul,
    "build" / c.Int8ul,
)


FirmwareHeader = c.Struct(
    "_start_offset" / c.Tell,
    "magic" / c.Const(b"TRZF"),
    "_header_len" / c.Padding(4),
    "expiry" / c.Int32ul,
    "code_length" / c.Rebuild(
        c.Int32ul,
        lambda this:
            len(this._.code) if "code" in this._
            else (this.code_length or 0)),
    "version" / VersionLong,
    "fix_version" / VersionLong,
    "reserved" / c.Padding(8),
    "hashes" / c.Bytes(32)[16],

    "reserved" / c.Padding(415),
    "sigmask" / c.Byte,
    "signature" / c.Bytes(64),

    "_end_offset" / c.Tell,
    "header_len" / c.Pointer(
        c.this._start_offset + 4,
        c.Rebuild(c.Int32ul, c.this._end_offset - c.this._start_offset)
    ),
)


Firmware = c.Struct(
    "vendor_header" / VendorHeader,
    "firmware_header" / FirmwareHeader,
    "code" / c.Bytes(c.this.firmware_header.code_length),
    c.Terminated,
)
# fmt: on


def validate_firmware(filename):
    with open(filename, "rb") as f:
        data = f.read()
    if data[:6] == b"54525a":
        data = binascii.unhexlify(data)

    try:
        fw = Firmware.parse(data)
    except Exception as e:
        raise ValueError("Invalid firmware image format") from e

    vendor = fw.vendor_header
    header = fw.firmware_header

    print(
        "Vendor header from {}, version {}.{}".format(
            vendor.vendor_string, vendor.version.major, vendor.version.minor
        )
    )
    print(
        "Firmware version {v.major}.{v.minor}.{v.patch} build {v.build}".format(
            v=header.version
        )
    )

    # rebuild header without signatures
    stripped_header = header.copy()
    stripped_header.sigmask = 0
    stripped_header.signature = b"\0" * 64
    header_bytes = FirmwareHeader.build(stripped_header)
    digest = pyblake2.blake2s(header_bytes).digest()

    print("Fingerprint: {}".format(binascii.hexlify(digest).decode()))

    global_pk = cosi.combine_keys(
        vendor.pubkeys[i] for i in range(8) if header.sigmask & (1 << i)
    )

    try:
        cosi.verify(header.signature, digest, global_pk)
        print("Signature OK")
    except Exception:
        print("Signature FAILED")
        raise


# ====== Client functions ====== #


@tools.session
def update(client, fp):
    if client.features.bootloader_mode is False:
        raise RuntimeError("Device must be in bootloader mode")

    data = fp.read()

    resp = client.call(proto.FirmwareErase(length=len(data)))
    if isinstance(resp, proto.Failure) and resp.code == proto.FailureType.FirmwareError:
        return False

    # TREZORv1 method
    if isinstance(resp, proto.Success):
        # fingerprint = hashlib.sha256(data[256:]).hexdigest()
        # LOG.debug("Firmware fingerprint: " + fingerprint)
        resp = client.call(proto.FirmwareUpload(payload=data))
        if isinstance(resp, proto.Success):
            return True
        elif (
            isinstance(resp, proto.Failure)
            and resp.code == proto.FailureType.FirmwareError
        ):
            return False
        raise RuntimeError("Unexpected result %s" % resp)

    # TREZORv2 method
    if isinstance(resp, proto.FirmwareRequest):
        import pyblake2

        while True:
            payload = data[resp.offset : resp.offset + resp.length]
            digest = pyblake2.blake2s(payload).digest()
            resp = client.call(proto.FirmwareUpload(payload=payload, hash=digest))
            if isinstance(resp, proto.FirmwareRequest):
                continue
            elif isinstance(resp, proto.Success):
                return True
            elif (
                isinstance(resp, proto.Failure)
                and resp.code == proto.FailureType.FirmwareError
            ):
                return False
            raise RuntimeError("Unexpected result %s" % resp)

    raise RuntimeError("Unexpected message %s" % resp)
