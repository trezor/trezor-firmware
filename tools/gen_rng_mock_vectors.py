#!/usr/bin/env python3
"""Generate expected strong-RNG output for the emulator's mock entropy streams."""

from __future__ import annotations

import hashlib

import click

MODEL_SE_TAGS = {
    "T2T1": (),
    "T2B1": ("Optiga",),
    "T3B1": ("Optiga",),
    "T3T1": ("Optiga",),
    "T3W1": ("Optiga", "Tropic"),
}

SE_BLOCK_SIZE = 32


def mcu_stream(length: int, seed: int = 0, offset_u32: int = 0) -> bytes:
    """The emulator MCU stream (crypto/rand_insecure.c LCG), skipping
    `offset_u32` words of prior consumption."""
    out = bytearray()
    state = seed
    for _ in range(offset_u32 + (length + 3) // 4):
        state = (1664525 * state + 1013904223) % 2**32
        out += state.to_bytes(4, "little")
    return bytes(out[offset_u32 * 4 :][:length])


def se_stream(tag: str, length: int, seed: int = 0) -> bytes:
    """An emulated secure element's stream (core/embed/sec/rng/unix/rng_mock.c)."""
    out = b""
    counter = 0
    while len(out) < length:
        msg = tag.encode() + seed.to_bytes(4, "little") + counter.to_bytes(4, "little")
        digest = hashlib.sha256(msg).digest()
        out += digest[: min(SE_BLOCK_SIZE, length - len(out))]
        counter += 1
    return out


def strong(model: str, length: int, seed: int = 0, offset_u32: int = 0) -> bytes:
    """Expected rng_fill_buffer_strong() output of `length` bytes."""
    out = bytearray(mcu_stream(length, seed, offset_u32))
    for tag in MODEL_SE_TAGS[model]:
        stream = se_stream(tag, length, seed)
        for i in range(length):
            out[i] ^= stream[i]
    return bytes(out)


def plain(length: int, seed: int = 0, offset_u32: int = 0) -> bytes:
    """Expected random.bytes() output -- MCU stream only, no secure elements."""
    return mcu_stream(length, seed, offset_u32)


@click.command()
@click.option(
    "-m",
    "--model",
    type=click.Choice(sorted(MODEL_SE_TAGS)),
    help="Internal model name, omit for --plain.",
)
@click.option("-l", "--length", type=int, default=32, help="Bytes to draw.")
@click.option("-s", "--seed", type=int, default=0, help="random.reseed() value.")
@click.option(
    "-o",
    "--mcu-offset",
    type=int,
    default=0,
    metavar="N",
    help="Skip N 32-bit words of MCU stream, for draws that follow other "
    "plain-RNG consumption after the reseed.",
)
@click.option(
    "-p",
    "--plain",
    "plain_only",
    is_flag=True,
    help="random.bytes() instead of random.bytes(n, True): MCU stream only.",
)
def main(
    model: str | None, length: int, seed: int, mcu_offset: int, plain_only: bool
) -> None:
    if plain_only:
        click.echo(plain(length, seed, mcu_offset).hex())
    elif model:
        click.echo(strong(model, length, seed, mcu_offset).hex())
    else:
        raise click.UsageError("need --model or --plain")


if __name__ == "__main__":
    main()
