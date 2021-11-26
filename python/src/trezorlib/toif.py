# This file is part of the Trezor project.
#
# Copyright (C) 2012-2022 SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

import struct
import zlib
from dataclasses import dataclass
from typing import Sequence, Tuple

from typing_extensions import Literal

from . import firmware

try:
    # Explanation of having to use "Image.Image" in typing:
    # https://stackoverflow.com/questions/58236138/pil-and-python-static-typing/58236618#58236618
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


RGBPixel = Tuple[int, int, int]


def _compress(data: bytes) -> bytes:
    z = zlib.compressobj(level=9, wbits=-10)
    return z.compress(data) + z.flush()


def _decompress(data: bytes) -> bytes:
    return zlib.decompress(data, wbits=-10)


def _from_pil_rgb(pixels: Sequence[RGBPixel]) -> bytes:
    data = bytearray()
    for r, g, b in pixels:
        c = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | ((b & 0xF8) >> 3)
        data += struct.pack(">H", c)
    return bytes(data)


def _to_rgb(data: bytes) -> bytes:
    res = bytearray()
    for i in range(0, len(data), 2):
        (c,) = struct.unpack(">H", data[i : i + 2])
        r = (c & 0xF800) >> 8
        g = (c & 0x07C0) >> 3
        b = (c & 0x001F) << 3
        res += bytes((r, g, b))
    return bytes(res)


def _from_pil_grayscale(pixels: Sequence[int]) -> bytes:
    data = bytearray()
    for i in range(0, len(pixels), 2):
        left, right = pixels[i], pixels[i + 1]
        c = (left & 0xF0) | ((right & 0xF0) >> 4)
        data += struct.pack(">B", c)
    return bytes(data)


def _to_grayscale(data: bytes) -> bytes:
    res = bytearray()
    for pixel in data:
        left = pixel & 0xF0
        right = (pixel & 0x0F) << 4
        res += bytes((left, right))
    return bytes(res)


@dataclass
class Toif:
    mode: firmware.ToifMode
    size: Tuple[int, int]
    data: bytes

    def __post_init__(self) -> None:
        # checking the data size
        width, height = self.size
        if self.mode is firmware.ToifMode.grayscale:
            expected_size = width * height // 2
        else:
            expected_size = width * height * 2
        uncompressed = _decompress(self.data)
        if len(uncompressed) != expected_size:
            raise ValueError(
                f"Uncompressed data is {len(uncompressed)} bytes, expected {expected_size}"
            )

    def to_image(self) -> "Image.Image":
        if not PIL_AVAILABLE:
            raise RuntimeError(
                "PIL is not available. Please install via 'pip install Pillow'"
            )

        uncompressed = _decompress(self.data)

        pil_mode: Literal["L", "RGB"]
        if self.mode is firmware.ToifMode.grayscale:
            pil_mode = "L"
            raw_data = _to_grayscale(uncompressed)
        else:
            pil_mode = "RGB"
            raw_data = _to_rgb(uncompressed)

        return Image.frombuffer(pil_mode, self.size, raw_data, "raw", pil_mode, 0, 1)

    def to_bytes(self) -> bytes:
        width, height = self.size
        return firmware.Toif.build(
            dict(format=self.mode, width=width, height=height, data=self.data)
        )

    def save(self, filename: str) -> None:
        with open(filename, "wb") as out:
            out.write(self.to_bytes())


def from_bytes(data: bytes) -> Toif:
    parsed = firmware.Toif.parse(data)
    return Toif(parsed.format, (parsed.width, parsed.height), parsed.data)


def load(filename: str) -> Toif:
    with open(filename, "rb") as f:
        return from_bytes(f.read())


def from_image(
    image: "Image.Image", background: Tuple[int, int, int, int] = (0, 0, 0, 255)
) -> Toif:
    if not PIL_AVAILABLE:
        raise RuntimeError(
            "PIL is not available. Please install via 'pip install Pillow'"
        )

    if image.mode == "RGBA":
        img_background = Image.new("RGBA", image.size, background)
        blend = Image.alpha_composite(img_background, image)
        image = blend.convert("RGB")

    if image.mode == "L":
        toif_mode = firmware.ToifMode.grayscale
        toif_data = _from_pil_grayscale(image.getdata())
    elif image.mode == "RGB":
        toif_mode = firmware.ToifMode.full_color
        toif_data = _from_pil_rgb(image.getdata())
    else:
        raise ValueError(f"Unsupported image mode: {image.mode}")

    data = _compress(toif_data)
    return Toif(toif_mode, image.size, data)
