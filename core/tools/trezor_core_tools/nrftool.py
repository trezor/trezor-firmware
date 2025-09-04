from __future__ import annotations

import typing as t
from pathlib import Path

import click
import intelhex
import munch
import yaml

from trezorlib import _ed25519 as ed25519
from trezorlib._internal import firmware_headers as fw_headers
from trezorlib.firmware import InvalidSignatureError, nrf
from trezorlib.firmware.models import Model

HERE = Path(__file__).parent.resolve()
ROOT = HERE.parent.parent.parent

TREZOR_BLE_DIR = ROOT / "nordic" / "trezor" / "trezor-ble"
VERSION_FILE = TREZOR_BLE_DIR / "VERSION"
PARTITION_FILE = TREZOR_BLE_DIR / "pm_static.yml"

DEV_KEYS = fw_headers._make_dev_keys(b"\x44", b"\x45")


def _format_tlv(tlv: nrf.TlvTable) -> str:
    type_name = tlv.magic.name
    output = [
        f"TLV {type_name} ({tlv.length} bytes)",
    ]
    for entry in tlv.entries:
        if isinstance(entry.id, nrf.TlvType):
            name = entry.id.name
        else:
            name = f"unrecognized {entry.id}"
        if len(entry.data) > 64:
            data = entry.data[:64].hex() + "..."
        elif entry.id is nrf.TlvType.MODEL:
            data = f"{entry.data.decode()} ({entry.data.hex()})"
        else:
            data = entry.data.hex()
        output.append(f"  {name}: {len(entry.data)} bytes {data}")

    return "\n".join(output)


class NrfImage(nrf.NrfImage):
    NAME: t.ClassVar[str] = "nrf"

    def signature_present(self) -> bool:
        return (
            nrf.TlvType.SIGNATURE1 in self.unprotected_tlv
            and nrf.TlvType.SIGNATURE2 in self.unprotected_tlv
        )

    def format(self, verbose: bool = False) -> str:
        header_str = "NrfHeader " + fw_headers._format_container(self.header)
        image_str = f"Image data: {len(self.img_data)} bytes"
        protected_tlv_str = _format_tlv(self.protected_tlv)
        unprotected_tlv_str = _format_tlv(self.unprotected_tlv)
        fingerprint_str = (
            f"Calculated fingerprint: {click.style(self.digest().hex(), bold=True)}"
        )
        sig_result = fw_headers._check_signature_any(self)
        sig_ok = fw_headers.SYM_OK if sig_result.is_ok() else fw_headers.SYM_FAIL
        sig_str = f"{sig_ok} Signature is {sig_result.value}"

        return "\n".join(
            [
                header_str,
                image_str,
                protected_tlv_str,
                unprotected_tlv_str,
                fingerprint_str,
                sig_str,
            ]
        )


class FileSource:
    def __init__(self, path: Path) -> None:
        self.path = path

    def read(self) -> bytes:
        raise NotImplementedError

    def write(self, data: bytes, offset: int | None = None) -> None:
        raise NotImplementedError

    @classmethod
    def from_path(cls, path: Path) -> FileSource:
        if path.suffix == ".hex":
            return HexFileSource(path)
        elif path.suffix == ".bin":
            return BinFileSource(path)
        else:
            raise click.ClickException(f"Unsupported file type: {path.suffix}")


class BinFileSource(FileSource):
    def read(self) -> bytes:
        return self.path.read_bytes()

    def write(self, data: bytes, offset: int | None = None) -> None:
        self.path.write_bytes(data)


class HexFileSource(FileSource):
    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.base_addr = 0

    def read(self) -> bytes:
        ih = intelhex.IntelHex(str(self.path))
        minaddr = ih.minaddr()
        assert minaddr is not None
        self.base_addr = minaddr
        return bytes(ih.tobinarray())

    def write(self, data: bytes, offset: int | None = None) -> None:
        ih = intelhex.IntelHex()
        if offset is None:
            offset = self.base_addr
        ih.frombytes(data, offset)
        ih.write_hex_file(str(self.path))


def get_version() -> tuple[int, int, int, int]:
    version_text = VERSION_FILE.read_text()
    version_kv = {}
    for line in version_text.splitlines():
        if not line or line.startswith("#"):
            continue
        key, value = line.split("=")
        version_kv[key.strip()] = value.strip()

    return (
        int(version_kv["VERSION_MAJOR"]),
        int(version_kv["VERSION_MINOR"]),
        int(version_kv["PATCHLEVEL"]),
        int(version_kv["VERSION_TWEAK"]),
    )


@click.group()
def cli():
    pass


@cli.command()
@click.argument(
    "binary_file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path),
)
@click.option(
    "-o",
    "--output-file",
    type=click.Path(exists=False, file_okay=True, dir_okay=False, path_type=Path),
    required=True,
)
@click.option(
    "-b",
    "--board",
    type=str,
    required=True,
)
def wrap(binary_file: Path, output_file: Path, board: str) -> None:
    """Wrap a binary file in a mcuboot header.

    Version and partition scheme are taken from files in the repository:

    \b
    - /nordic/trezor/trezor-ble/VERSION
    - /nordic/trezor/trezor-ble/pm_static.yml
    """
    try:
        model = Model.from_bytes(board[:4].upper().encode())
    except ValueError:
        raise click.ClickException(f"Could not guess model from board name: {board}")

    infile = FileSource.from_path(binary_file)
    try:
        NrfImage.parse(infile.read())
    except Exception:
        pass
    else:
        raise click.ClickException("This file already has a valid mcuboot header")

    version = get_version()
    pm: t.Any = munch.munchify(yaml.safe_load(PARTITION_FILE.read_text()))

    img_data = infile.read()

    if pm.app.size < len(img_data):
        raise click.ClickException(f"Image too large: {len(img_data)} > {pm.app.size}")

    assert pm.mcuboot_pad.address + pm.mcuboot_pad.size == pm.app.address

    image = NrfImage.create(
        version=version,
        img_data=img_data,
        header_size=pm.mcuboot_pad.size,
        model=model,
    )

    FileSource.from_path(output_file).write(image.build(), pm.mcuboot_pad.address)


@cli.command()
@click.argument(
    "binary_file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path),
)
def dump(binary_file: Path) -> None:
    """Dump image information to the console."""
    image = NrfImage.parse(FileSource.from_path(binary_file).read())
    click.echo(image.format())


@cli.command()
@click.argument(
    "binary_file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path),
)
@click.option("-s", "--sigmask", type=int)
def digest(binary_file: Path, sigmask: int | None) -> None:
    """Print a digest of the image.

    If -s is specified, a digest with a modified sigmask is printed instead.
    """
    image = NrfImage.parse(FileSource.from_path(binary_file).read())
    if sigmask is not None:
        image.sigmask = sigmask
    print(image.digest().hex())


@cli.command()
@click.argument(
    "binary_file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path),
)
@click.argument("sigmask", type=int)
@click.argument("signature1_hex", type=str)
@click.argument("signature2_hex", type=str)
@click.option("-f", "--force", is_flag=True, help="Insert an invalid signature.")
def sign(
    binary_file: Path,
    sigmask: int,
    signature1_hex: str,
    signature2_hex: str,
    force: bool,
) -> None:
    """Insert signatures into the image.

    To insert development signatures, use `nrftool sign-dev` instead.
    """
    binary_source = FileSource.from_path(binary_file)
    image = NrfImage.parse(binary_source.read())
    image.sigmask = sigmask
    sig1 = bytes.fromhex(signature1_hex)
    sig2 = bytes.fromhex(signature2_hex)
    image.set_signatures((sig1, sig2))
    try:
        image.verify()
    except InvalidSignatureError:
        if not force:
            raise click.ClickException("Invalid signature")

    binary_source.write(image.build())


@cli.command()
@click.argument(
    "binary_file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path),
)
def sign_dev(binary_file: Path) -> None:
    """Insert development signatures into the image."""
    binary_source = FileSource.from_path(binary_file)
    image = NrfImage.parse(binary_source.read())
    image.sigmask = 0x03
    digest = image.digest()
    sig1 = ed25519.signature_unsafe(
        digest, DEV_KEYS[0], ed25519.publickey_unsafe(DEV_KEYS[0])
    )
    sig2 = ed25519.signature_unsafe(
        digest, DEV_KEYS[1], ed25519.publickey_unsafe(DEV_KEYS[1])
    )
    image.set_signatures((sig1, sig2))
    image.verify(dev_keys=True)
    binary_source.write(image.build())
