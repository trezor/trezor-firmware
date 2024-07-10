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

import hashlib
import typing as t
from dataclasses import dataclass
from enum import Enum

from .util import FirmwareHashParameters

if t.TYPE_CHECKING:
    from typing_extensions import Self

    from ..models import TrezorModel


class Model(Enum):
    T1B1 = b"T1B1"
    T2T1 = b"T2T1"
    T3T1 = b"T3T1"
    T3B1 = b"T3B1"
    T2B1 = b"T2B1"
    D001 = b"D001"
    D002 = b"D002"

    # legacy aliases
    ONE = b"T1B1"
    T = b"T2T1"
    R = b"T2B1"
    DISC1 = b"D001"
    DISC2 = b"D002"

    @classmethod
    def from_hw_model(cls, hw_model: t.Union["Self", bytes]) -> "Model":
        if isinstance(hw_model, cls):
            return hw_model
        if hw_model == b"\x00\x00\x00\x00":
            return cls.T2T1
        raise ValueError(f"Unknown hardware model: {hw_model}")

    @classmethod
    def from_trezor_model(cls, trezor_model: "TrezorModel") -> "Self":
        return cls(trezor_model.internal_name.encode("ascii"))

    def model_keys(self, dev_keys: bool = False) -> "ModelKeys":
        if dev_keys:
            model_map = MODEL_MAP_DEV
        else:
            model_map = MODEL_MAP
        return model_map[self]

    def hash_params(self) -> "FirmwareHashParameters":
        return MODEL_HASH_PARAMS_MAP[self]

    def code_alignment(self) -> int:
        return MODEL_CODE_ALIGNMENT_MAP[self]


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


LEGACY_V1V2 = ModelKeys(
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

LEGACY_V1V2_DEV = ModelKeys(
    production=False,
    boardloader_keys=(),
    boardloader_sigs_needed=-1,
    bootloader_keys=(),
    bootloader_sigs_needed=-1,
    firmware_keys=[
        bytes.fromhex(key)
        for key in (
            "042c0b7cf95324a07d05398b240174dc0c2be444d96b159aa6c7f7b1e668680991ae31a9c671a36543f46cea8fce6984608aa316aa0472a7eed08847440218cb2f",
            "04edabbd16b41c8371b92ef2f04c1185b4f03b6dcd52ba9b78d9d7c89c8f2211452c88a66eb8ac3c19a1cc3a3fc6d72506f6fce2025f738d8b55f29f22125eb0a4",
            "04665f660a5052be7a95546a02179058d93d3e08a779734914594346075bb0afd45113948d72cf3dc8f2b70ee02dc1695d051bb0c6da2a914a69045e3277682d3b",
            "0466635d999417b65566866c65630d977a7ae723fe5f6c4cd17fa00f088ba184c103f86b11525fc876237f804b1496bbb98916dcdda18e1e3670522cb5106f410d",
            "04f36c7d0fb615ada43d7188580f15ebda22d6f6b9b1a92bff16c6937799dcbc667e3bd719d5c84068a94b75e43724467398892eab80a0f8283f9bad6657f146c9",
        )
    ],
    firmware_sigs_needed=3,
)

LEGACY_V3 = ModelKeys(
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

LEGACY_V3_DEV = ModelKeys(
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

T2T1 = ModelKeys(
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

TREZOR_CORE_DEV = ModelKeys(
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

T2B1 = ModelKeys(
    production=True,
    boardloader_keys=[
        bytes.fromhex(key)
        for key in (
            "549a45557008d5518a9a151dc6a3568cf73830a7fe419f2626d9f30d024b2bec",
            "c16c7027f8a3962607bf24cdec2e3cd2344e1f6071e8260b3dda52b1a5107cb7",
            "87180f933178b2832bee2d7046c7f4b98300ca7d7fb2e4567169c8730a1c4020",
        )
    ],
    boardloader_sigs_needed=2,
    bootloader_keys=[
        bytes.fromhex(key)
        for key in (
            "bf4e6f004fcb32cec683f22c88c1a86c1518c6de8ac97002d84a63bea3e375dd",
            "d2def691c1e9d809d8190cf7af935c10688f68983479b4ee9abac19104878ec1",
            "07c85134946bf89fa19bdc2c5e5ff9ce01296508ee0863d0ff6d63331d1a2516",
        )
    ],
    bootloader_sigs_needed=2,
    firmware_keys=(),
    firmware_sigs_needed=-1,
)

T3T1 = ModelKeys(
    production=True,
    boardloader_keys=[
        bytes.fromhex(key)
        for key in (
            "76af426e61406bad7c077b409c66fde39fb817919313ae1e4c02535c80beed96",
            "619751dc8d2d09d7e5dfb99e41f606debdf419f85a8143e8e5399ea67a3988c7",
            "abf94b6615a7dde2a871f7d62c38efc7d9d8f6010d8846bee636e4f3e658a38c",
        )
    ],
    boardloader_sigs_needed=2,
    bootloader_keys=[
        bytes.fromhex(key)
        for key in (
            "338b949b7e3b26470d4fe3696fd6fff28757265d14cca48ebf2db97b4f5bc039",
            "28682027730b783201b05a8c9d11685447c17297db71b8a60dc693a44610751d",
            "9fbf31b4e351a4cc81c75995b2257f0a7169268da5a44e94b6a5590d434e32da",
        )
    ],
    bootloader_sigs_needed=2,
    firmware_keys=(),
    firmware_sigs_needed=-1,
)

T3B1 = ModelKeys(
    production=True,
    boardloader_keys=[
        bytes.fromhex(key)
        for key in (
            "bbc21adbc1b44d6bfe10c5223de33c28429e52680707d3249007ed42dcc5be13",
            "22e42a301f3b6ff4f2e6926bce4359e83fc83f0f4a84a7338959c1fd0e29dc13",
            "7f478f5fb78d8c054b720d8104bf2f6487e452402458979b5525c290dc344d32",
        )
    ],
    boardloader_sigs_needed=2,
    bootloader_keys=[
        bytes.fromhex(key)
        for key in (
            "41d9884801377cff04b0b459fc9b56af1b51f47343a3a6e4fdc1eacabcad7756",
            "23ec4ec4674d68ac5431e8ba84d7ac24cb5a66702ec565014d164a72182a66c7",
            "8a7dac53e1be46607231920b0c71056a27be16b67a2fc0d8644d5f8708a28dd1",
        )
    ],
    bootloader_sigs_needed=2,
    firmware_keys=(),
    firmware_sigs_needed=-1,
)

LEGACY_HASH_PARAMS = FirmwareHashParameters(
    hash_function=hashlib.sha256,
    chunk_size=1024 * 64,
    padding_byte=b"\xff",
)

T2T1_HASH_PARAMS = FirmwareHashParameters(
    hash_function=hashlib.blake2s,
    chunk_size=1024 * 128,
    padding_byte=None,
)

T3T1_HASH_PARAMS = FirmwareHashParameters(
    hash_function=hashlib.sha256,
    chunk_size=1024 * 128,
    padding_byte=None,
)

T3B1_HASH_PARAMS = FirmwareHashParameters(
    hash_function=hashlib.sha256,
    chunk_size=1024 * 128,
    padding_byte=None,
)

D002_HASH_PARAMS = FirmwareHashParameters(
    hash_function=hashlib.sha256,
    chunk_size=1024 * 256,
    padding_byte=None,
)

MODEL_MAP = {
    Model.T1B1: LEGACY_V3,
    Model.T2T1: T2T1,
    Model.T2B1: T2B1,
    Model.T3T1: T3T1,
    Model.T3B1: T3B1,
    Model.D001: TREZOR_CORE_DEV,
    Model.D002: TREZOR_CORE_DEV,
}

MODEL_MAP_DEV = {
    Model.T1B1: LEGACY_V3_DEV,
    Model.T2T1: TREZOR_CORE_DEV,
    Model.T2B1: TREZOR_CORE_DEV,
    Model.T3T1: TREZOR_CORE_DEV,
    Model.T3B1: TREZOR_CORE_DEV,
    Model.D001: TREZOR_CORE_DEV,
    Model.D002: TREZOR_CORE_DEV,
}

MODEL_HASH_PARAMS_MAP = {
    Model.T1B1: LEGACY_HASH_PARAMS,
    Model.T2T1: T2T1_HASH_PARAMS,
    Model.T2B1: T2T1_HASH_PARAMS,
    Model.T3T1: T3T1_HASH_PARAMS,
    Model.T3B1: T3B1_HASH_PARAMS,
    Model.D001: T2T1_HASH_PARAMS,
    Model.D002: D002_HASH_PARAMS,
}


MODEL_CODE_ALIGNMENT_MAP = {
    Model.T1B1: 0x200,
    Model.T2T1: 0x200,
    Model.T2B1: 0x200,
    Model.T3T1: 0x200,
    Model.T3B1: 0x200,
    Model.D001: 0x200,
    Model.D002: 0x400,
}

# aliases

TREZOR_ONE_V1V2 = LEGACY_V1V2
TREZOR_ONE_V1V2_DEV = LEGACY_V1V2_DEV
TREZOR_ONE_V3 = LEGACY_V3
TREZOR_ONE_V3_DEV = LEGACY_V3_DEV

TREZOR_T = T2T1
TREZOR_R = T2B1
TREZOR_T3T1 = T3T1
TREZOR_T3B1 = T3B1
TREZOR_T_DEV = TREZOR_CORE_DEV
TREZOR_R_DEV = TREZOR_CORE_DEV

DISC1 = TREZOR_CORE_DEV
DISC1_DEV = TREZOR_CORE_DEV
D001 = TREZOR_CORE_DEV
D001_DEV = TREZOR_CORE_DEV
D002 = TREZOR_CORE_DEV
D002_DEV = TREZOR_CORE_DEV
