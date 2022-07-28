# Helpers to increase the font size from existing font data.
# Thanks to it we can save space by not having to include
# the larger font definitions.
# `core/embed/rust/src/ui/font_multiplier.rs` is a Rust implementation
# that is doing it on the actual Trezor.

from __future__ import annotations

from typing_extensions import Literal
from typing import Tuple


Bit = Literal[0, 1]
Point = Tuple[int, int]


def magnify_glyph_by_two(width: int, height: int, bytes_data: list[int]) -> list[int]:
    """Magnifying the font size by two.

    Input and output are bytes (that is the standard in font files),
    but internally works with bits.
    """
    bits_data = _bytes_to_bits(bytes_data, height * width)
    double_size_data = _double_the_bits(width, bits_data)
    return _bits_to_bytes(double_size_data)


def _bytes_to_bits(bytes_data: list[int], bits_to_take: int) -> list[Bit]:
    """Transform bytes into bits."""
    bits_data = [f"{i:08b}" for i in bytes_data[:-1]]

    # Last element needs to be handled carefully,
    # to respect the number of bits to take.
    missing_bits = bits_to_take - len(bits_data) * 8
    last_byte = bytes_data[-1]
    last_binary = f"{last_byte:08b}"
    # Taking either the right or left part of the last byte
    if last_byte < 2**missing_bits:
        bits_data.append(last_binary[-missing_bits:])
    else:
        bits_data.append(last_binary[:missing_bits])

    return [1 if int(x) else 0 for x in "".join(bits_data)]


def _bits_to_bytes(bits_data: list[Bit]) -> list[int]:
    """Transform bits into bytes."""
    bits_str = "".join([str(bit) for bit in bits_data])
    bytes_str_list = [bits_str[i : i + 8] for i in range(0, len(bits_str), 8)]
    # Last element needs to be right-padded to 8 bits
    while len(bytes_str_list[-1]) != 8:
        bytes_str_list[-1] += "0"
    return [int(byte, 2) for byte in bytes_str_list]


def _double_the_bits(width: int, bits_data: list[Bit]) -> list[Bit]:
    """Double the dimension of a given glyph."""
    # Allocate space for the new data - 2*2 bigger than the original
    # Then fill all the new indexes with appropriate bits
    double_size_data: list[Bit] = [0 for _ in range(4 * len(bits_data))]
    for original_index, bit in enumerate(bits_data):
        for new_index in _corresponding_indexes(original_index, width):
            double_size_data[new_index] = bit
    return double_size_data


def _corresponding_indexes(index: int, width: int) -> list[int]:
    """Find the indexes of the four pixels that correspond to the given one."""
    point = _index_to_point(index, width)
    points = _scale_by_two(point)
    new_width = 2 * width
    return [_point_to_index(new_point, new_width) for new_point in points]


def _scale_by_two(point: Point) -> tuple[Point, Point, Point, Point]:
    """Translate one pixel into four adjacent pixels to visually scale it by two."""
    x, y = point
    return (
        (x * 2, y * 2),
        (x * 2 + 1, y * 2),
        (x * 2, y * 2 + 1),
        (x * 2 + 1, y * 2 + 1),
    )


def _point_to_index(point: Point, width: int) -> int:
    """Translate point to index according to the glyph width."""
    x, y = point
    assert 0 <= x < width
    return y * width + x


def _index_to_point(index: int, width: int) -> Point:
    """Translate index to point according to the glyph width."""
    x = index % width
    y = index // width
    return x, y


def print_from_bits(width: int, height: int, bit_data: list[Bit]):
    """Print the glyph into terminal from bit data."""
    for line_id in range(height):
        line = bit_data[line_id * width : (line_id + 1) * width]
        str_line = "".join([str(x) for x in line])
        print(str_line.replace("0", " "))
    print()


def print_from_bytes(width: int, height: int, bytes_data: list[int]):
    """Print the glyph into terminal from byte data."""
    bits_data = _bytes_to_bits(bytes_data, height * width)
    print_from_bits(width, height, bits_data)


################################
# TEST SECTION for pytest
################################

# fmt: off
HEIGHT = 7
K_WIDTH = 5
K_GLYPH = [140, 169, 138, 74, 32]
K_BITS = [1, 0, 0, 0, 1, 1, 0, 0, 1, 0, 1, 0, 1, 0, 0, 1, 1, 0, 0, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 0, 1]
K_MAGNIFIED = [192, 240, 60, 51, 12, 204, 51, 15, 3, 192, 204, 51, 12, 51, 12, 192, 240, 48]
M_GLYPH = [131, 7, 29, 89, 48, 96, 128]
M_WIDTH = 7
# fmt: on


def test_bits_to_bytes_and_back():
    vectors = (  # height, width, bytes_data
        (HEIGHT, K_WIDTH, K_GLYPH),
        (HEIGHT, M_WIDTH, M_GLYPH),
    )

    for height, width, bytes_data in vectors:
        bits_data = _bytes_to_bits(bytes_data, height * width)
        assert _bits_to_bytes(bits_data) == bytes_data


def test_bit_to_bytes():
    assert _bytes_to_bits(K_GLYPH, HEIGHT * K_WIDTH) == K_BITS


def test_overall_magnify():
    assert magnify_glyph_by_two(K_WIDTH, HEIGHT, K_GLYPH) == K_MAGNIFIED


if __name__ == "__main__":
    # Print letter K, magnify it and print it also
    print("K_GLYPH", K_GLYPH)
    print_from_bytes(K_WIDTH, HEIGHT, K_GLYPH)
    magnified_data = magnify_glyph_by_two(K_WIDTH, HEIGHT, K_GLYPH)
    print("magnified_data", magnified_data)
    print_from_bytes(2 * K_WIDTH, 2 * HEIGHT, magnified_data)
