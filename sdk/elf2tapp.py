#!/usr/bin/env python3
import struct

import click

import construct as c
from construct_classes import Struct

from elftools.elf.elffile import ELFFile
from elftools.elf.relocation import RelocationSection


class AppHeader(Struct):
    code_va: int
    code_offset: int
    code_size: int
    data_va: int
    data_size: int
    idata_offset: int
    idata_size: int
    reloc_offset: int
    reloc_size: int
    stack_size: int
    entrypoint: int

    HEADER_SIZE = 1024

    # fmt: off
    SUBCON = c.Struct(
        "magic" / c.Const(b"TAPP"),
        "image_size" / c.Rebuild(c.Int32ul, lambda ctx: AppHeader.HEADER_SIZE + ctx.code_size + ctx.idata_size + ctx.reloc_size),
        "code_va" / c.Int32ul,
        "code_offset" / c.Rebuild(c.Int32ul, lambda ctx: AppHeader.HEADER_SIZE),
        "code_size" / c.Rebuild(c.Int32ul, lambda ctx: len(ctx._.code)),
        "data_va" / c.Int32ul,
        "data_size" / c.Int32ul,
        "idata_offset" / c.Rebuild(c.Int32ul, lambda ctx: ctx.code_offset + ctx.code_size),
        "idata_size" / c.Rebuild(c.Int32ul, lambda ctx: len(ctx._.idata)),
        "reloc_offset" / c.Rebuild(c.Int32ul, lambda ctx: ctx.idata_offset + ctx.idata_size),
        "reloc_size" / c.Rebuild(c.Int32ul, lambda ctx: len(ctx._.reloc)),
        "stack_size" / c.Int32ul,
        "entrypoint" / c.Int32ul,
        "_padding" / c.Padding(HEADER_SIZE - 13 * 4),
    )

class AppImage(Struct):
    header: AppHeader
    code: bytes
    idata: bytes
    reloc: bytes

    # fmt: off
    SUBCON = c.Struct(
        "header" / AppHeader.SUBCON,
        "code" / c.Bytes(c.this.header.code_size),
        "idata" / c.Bytes(c.this.header.idata_size),
        "reloc" / c.Bytes(c.this.header.reloc_size),
    )


# ARM relocation type constants
R_ARM_ABS32 = 2
R_ARM_RELATIVE = 23


def pad_to_alignment(data: bytes, alignment: int) -> bytes:
    padding = (alignment - (len(data) % alignment)) % alignment
    return data + b'\x00' * padding


def fmt_size(size_bytes: int) -> str:
    """Format size as B for <1024 and KB with one decimal otherwise."""
    return f"{size_bytes} B" if size_bytes < 1024 else f"{size_bytes / 1024:.1f} KB"


@click.command()
@click.option('-i', '--input-file', 'input_file', type=click.File("rb"), required=True, help='Input ELF file')
@click.option('-o', '--output-file', 'output_file', type=click.File("wb"), required=True, help='Output TAPP file')
@click.option('-s', '--stack-size', 'stack_size', type=int, required=True, help='Stack size in bytes (must be > 0)')
@click.option('-v', '--verbose', 'verbose', is_flag=True, help='Enable verbose output')
def cli(input_file, output_file, stack_size, verbose):
    """Convert an ELF binary to a TAPP image.

    The resulting image layout:
      [AppHeader (1024 bytes)] [RX data] [RW init data] [relocation table]
    """
    click.echo("")
    click.echo(f"\nReading file {input_file.name}")

    if stack_size <= 0:
        raise click.ClickException('Stack size must be a positive integer')
    elf = ELFFile(input_file)

    # Get LOAD segments
    load_segments = [seg for seg in elf.iter_segments() if seg['p_type'] == 'PT_LOAD']

    if len(load_segments) != 2:
        raise click.ClickException(f'Expected exactly 2 LOAD segments, found {len(load_segments)}')

    # Identify RX (R+X) and RW (R+W) segments based on flags
    # p_flags: PF_X = 0x1, PF_W = 0x2, PF_R = 0x4
    code_segment = None
    idata_segment = None

    for segment in load_segments:
        flags = segment['p_flags']
        is_readable = flags & 0x4  # PF_R
        is_writable = flags & 0x2  # PF_W
        is_executable = flags & 0x1  # PF_X

        if is_readable and is_executable and not is_writable:
            code_segment = segment
        elif is_readable and is_writable and not is_executable:
            idata_segment = segment

    if code_segment is None or idata_segment is None:
        raise click.ClickException('Could not identify RO (R+X) and RW (R+W) segments')

    # Extract code and readonly data segment bytes
    code_bytes = pad_to_alignment(code_segment.data(), 32)

    # Extract initialized data segment bytes
    idata_bytes = pad_to_alignment(idata_segment.data(), 32)

    # Get size of data segment in RAM (includes .bss)
    data_size = idata_segment['p_memsz']

    # Relocations: collect 32-bit absolute relocations
    reloc_section = elf.get_section_by_name('.rel.data')
    reloc_offsets = []
    if reloc_section and isinstance(reloc_section, RelocationSection):
        for reloc in reloc_section.iter_relocations():
            rtype = reloc['r_info_type']
            if rtype in (R_ARM_ABS32, R_ARM_RELATIVE):
                reloc_offsets.append(reloc['r_offset'])
            else:
                raise click.ClickException(f'Unexpected relocation type: {rtype}')

    reloc_offsets = sorted(reloc_offsets)

    # Build relocation table: sequence of little-endian 32-bit offsets
    reloc_bytes = b''.join(struct.pack('<I', off) for off in reloc_offsets)

    app_image_dict = {
        "header": {
            "code_va": code_segment['p_vaddr'],
            "data_va": idata_segment['p_vaddr'],
            "data_size": data_size,
            "stack_size": stack_size,
            "entrypoint": 0,
        },
        "code": code_bytes,
        "idata": idata_bytes,
        "reloc": reloc_bytes,
    }

    output_data = AppImage.SUBCON.build(app_image_dict)
    output_file.write(output_data)

    # Detailed image summary in KiB (no extra variables)
    click.echo(f"\nApplication Image:")
    click.echo(f" header        {fmt_size(AppHeader.HEADER_SIZE)}")
    click.echo(f" code, rodata  {fmt_size(len(code_bytes))}")
    click.echo(f" idata         {fmt_size(len(idata_bytes))}")
    click.echo(f" relocations   {fmt_size(len(reloc_bytes))}")
    click.echo(f"\nRAM Usage:")
    click.echo(f" stack         {fmt_size(stack_size)}")
    click.echo(f" bss, data     {fmt_size(data_size)}")
    click.echo(f'\nApplication image written to {output_file.name}')

if __name__ == "__main__":
    cli()
