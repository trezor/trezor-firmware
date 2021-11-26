from dataclasses import dataclass
from typing import Collection, Optional, Tuple

from . import mapping

UsbId = Tuple[int, int]

VENDORS = ("bitcointrezor.com", "trezor.io")


@dataclass(eq=True, frozen=True)
class TrezorModel:
    name: str
    minimum_version: Tuple[int, int, int]
    vendors: Collection[str]
    usb_ids: Collection[UsbId]
    default_mapping: mapping.ProtobufMapping


TREZOR_ONE = TrezorModel(
    name="1",
    minimum_version=(1, 8, 0),
    vendors=VENDORS,
    usb_ids=((0x534C, 0x0001),),
    default_mapping=mapping.DEFAULT_MAPPING,
)

TREZOR_T = TrezorModel(
    name="T",
    minimum_version=(2, 1, 0),
    vendors=VENDORS,
    usb_ids=((0x1209, 0x53C1), (0x1209, 0x53C0)),
    default_mapping=mapping.DEFAULT_MAPPING,
)

TREZORS = {TREZOR_ONE, TREZOR_T}


def by_name(name: str) -> Optional[TrezorModel]:
    for model in TREZORS:
        if model.name == name:
            return model
    return None
