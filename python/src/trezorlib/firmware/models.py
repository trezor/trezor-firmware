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

import typing as t
from dataclasses import dataclass
from enum import Enum


class Model(Enum):
    ONE = b"T1B1"
    T = b"T2T1"
    R = b"T2B1"


@dataclass
class ModelKeys:
    """Model-specific keys."""

    production: bool
    boardloader_keys: t.Sequence[bytes]
    boardloader_sigs_needed: int
    bootloader_keys: t.Sequence[bytes]
    bootloader_sigs_needed: int
    firmware_keys: t.Sequence[bytes]
    firmware_sigs_needed: int


TREZOR_ONE_V1V2 = ModelKeys(
    production=True,
    boardloader_keys=(),
    boardloader_sigs_needed=-1,
    bootloader_keys=(),
    bootloader_sigs_needed=-1,
    firmware_keys=[
        bytes.fromhex(key)
        for key in (
            "04d571b7f148c5e4232c3814f777d8faeaf1a84216c78d569b71041ffc768a5b2d810fc3bb134dd026b57e65005275aedef43e155f48fc11a32ec790a93312bd58",
            "0463279c0c0866e50c05c799d32bd6bab0188b6de06536d1109d2ed9ce76cb335c490e55aee10cc901215132e853097d5432eda06b792073bd7740c94ce4516cb1",
            "0443aedbb6f7e71c563f8ed2ef64ec9981482519e7ef4f4aa98b27854e8c49126d4956d300ab45fdc34cd26bc8710de0a31dbdf6de7435fd0b492be70ac75fde58",
            "04877c39fd7c62237e038235e9c075dab261630f78eeb8edb92487159fffedfdf6046c6f8b881fa407c4a4ce6c28de0b19c1f4e29f1fcbc5a58ffd1432a3e0938a",
            "047384c51ae81add0a523adbb186c91b906ffb64c2c765802bf26dbd13bdf12c319e80c2213a136c8ee03d7874fd22b70d68e7dee469decfbbb510ee9a460cda45",
        )
    ],
    firmware_sigs_needed=3,
)

TREZOR_ONE_V1V2_DEV = ModelKeys(
    production=False,
    boardloader_keys=(),
    boardloader_sigs_needed=-1,
    bootloader_keys=(),
    bootloader_sigs_needed=-1,
    firmware_keys=[
        bytes.fromhex(key)
        for key in (
            "032c0b7cf95324a07d05398b240174dc0c2be444d96b159aa6c7f7b1e668680991",
            "02edabbd16b41c8371b92ef2f04c1185b4f03b6dcd52ba9b78d9d7c89c8f221145",
            "03665f660a5052be7a95546a02179058d93d3e08a779734914594346075bb0afd4",
            "0366635d999417b65566866c65630d977a7ae723fe5f6c4cd17fa00f088ba184c1",
            "03f36c7d0fb615ada43d7188580f15ebda22d6f6b9b1a92bff16c6937799dcbc66",
        )
    ],
    firmware_sigs_needed=3,
)

TREZOR_ONE_V3 = ModelKeys(
    production=True,
    boardloader_keys=(),
    boardloader_sigs_needed=-1,
    bootloader_keys=(),
    bootloader_sigs_needed=-1,
    firmware_keys=[
        bytes.fromhex(key)
        for key in (
            "032300c1bb4539fcbfca2590bda3dd2093826f4ae437bddecc1a2e72520764ff7a",
            "0233baeaebc94a2a3e8b11f39a7133dbf427be292fcbceb887d71ef51e85395a19",
            "0357091fa254b55233d0bb4c48e106c91b92fd0788ebed9d3a916719f44c76c015",
        )
    ],
    firmware_sigs_needed=2,
)

TREZOR_ONE_V3_DEV = ModelKeys(
    production=False,
    boardloader_keys=(),
    boardloader_sigs_needed=-1,
    bootloader_keys=(),
    bootloader_sigs_needed=-1,
    firmware_keys=[
        bytes.fromhex(key)
        for key in (
            "037308e14077161c365dea0f5c80aa6c5dba34719e825bd23ae5f7e7d2988adb0f",
            "039c1b2460e343712e982e0732e7ed17f60de4c933065b7170d99c6e7fe7cc7f4b",
            "03152b37fdf126111274c894c348dcc975b57c115ee24ceb19b5190ac7f7b65173",
        )
    ],
    firmware_sigs_needed=2,
)

TREZOR_T = ModelKeys(
    production=True,
    boardloader_keys=[
        bytes.fromhex(key)
        for key in (
            "0eb9856be9ba7e972c7f34eac1ed9b6fd0efd172ec00faf0c589759da4ddfba0",
            "ac8ab40b32c98655798fd5da5e192be27a22306ea05c6d277cdff4a3f4125cd8",
            "ce0fcd12543ef5936cf2804982136707863d17295faced72af171d6e6513ff06",
        )
    ],
    boardloader_sigs_needed=2,
    bootloader_keys=[
        bytes.fromhex(key)
        for key in (
            "c2c87a49c5a3460977fbb2ec9dfe60f06bd694db8244bd4981fe3b7a26307f3f",
            "80d036b08739b846f4cb77593078deb25dc9487aedcf52e30b4fb7cd7024178a",
            "b8307a71f552c60a4cbb317ff48b82cdbf6b6bb5f04c920fec7badf017883751",
        )
    ],
    bootloader_sigs_needed=2,
    firmware_keys=(),
    firmware_sigs_needed=-1,
)

TREZOR_T_DEV = ModelKeys(
    production=False,
    boardloader_keys=[
        bytes.fromhex(key)
        for key in (
            "db995fe25169d141cab9bbba92baa01f9f2e1ece7df4cb2ac05190f37fcc1f9d",
            "2152f8d19b791d24453242e15f2eab6cb7cffa7b6a5ed30097960e069881db12",
            "22fc297792f0b6ffc0bfcfdb7edb0c0aa14e025a365ec0e342e86e3829cb74b6",
        )
    ],
    boardloader_sigs_needed=2,
    bootloader_keys=[
        bytes.fromhex(key)
        for key in (
            "d759793bbc13a2819a827c76adb6fba8a49aee007f49f2d0992d99b825ad2c48",
            "6355691c178a8ff91007a7478afb955ef7352c63e7b25703984cf78b26e21a56",
            "ee93a4f66f8d16b819bb9beb9ffccdfcdc1412e87fee6a324c2a99a1e0e67148",
        )
    ],
    bootloader_sigs_needed=2,
    firmware_keys=(),
    firmware_sigs_needed=-1,
)


MODEL_MAP = {
    Model.ONE: TREZOR_ONE_V3,
    Model.T: TREZOR_T,
}

MODEL_MAP_DEV = {
    Model.ONE: TREZOR_ONE_V3_DEV,
    Model.T: TREZOR_T_DEV,
}
