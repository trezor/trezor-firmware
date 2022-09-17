# generated from nem_mosaics.py.mako
# (by running `make templates` in `core`)
# do not edit manually!

# NOTE: not supplying the kwargs saves 120 bytes of code size
# `networks` needs kwarg as `levy` above is optional

from typing import Iterator

from trezor.enums import NEMMosaicLevy


class MosaicLevy:
    def __init__(
        self,
        type: NEMMosaicLevy,
        fee: int,
        namespace: str,
        mosaic: str,
    ) -> None:
        self.type = type
        self.fee = fee
        self.namespace = namespace
        self.mosaic = mosaic


class Mosaic:
    def __init__(
        self,
        name: str,
        ticker: str,
        namespace: str,
        mosaic: str,
        divisibility: int,
        levy: MosaicLevy | None = None,
        networks: tuple[int, ...] | None = None,
    ) -> None:
        self.name = name
        self.ticker = ticker
        self.namespace = namespace
        self.mosaic = mosaic
        self.divisibility = divisibility
        self.levy = levy
        self.networks = networks


def mosaics_iterator() -> Iterator[Mosaic]:
    yield Mosaic(
        "NEM",  # name
        " XEM",  # ticker
        "nem",  # namespace
        "xem",  # mosaic
        6,  # divisibility
        None,  # levy
    )
    yield Mosaic(
        "DIMCOIN",  # name
        " DIM",  # ticker
        "dim",  # namespace
        "coin",  # mosaic
        6,  # divisibility
        MosaicLevy(  # levy
            NEMMosaicLevy.MosaicLevy_Percentile,  # type
            10,  # fee
            "dim",  # namespace
            "coin",  # mosaic
        ),
        (104,),  # networks
    )
    yield Mosaic(
        "DIM TOKEN",  # name
        " DIMTOK",  # ticker
        "dim",  # namespace
        "token",  # mosaic
        6,  # divisibility
        None,  # levy
        (104,),  # networks
    )
    yield Mosaic(
        "Breeze Token",  # name
        " BREEZE",  # ticker
        "breeze",  # namespace
        "breeze-token",  # mosaic
        0,  # divisibility
        None,  # levy
        (104,),  # networks
    )
    yield Mosaic(
        "PacNEM Game Credits",  # name
        " PAC:HRT",  # ticker
        "pacnem",  # namespace
        "heart",  # mosaic
        0,  # divisibility
        None,  # levy
        (104,),  # networks
    )
    yield Mosaic(
        "PacNEM Score Tokens",  # name
        " PAC:CHS",  # ticker
        "pacnem",  # namespace
        "cheese",  # mosaic
        6,  # divisibility
        MosaicLevy(  # levy
            NEMMosaicLevy.MosaicLevy_Percentile,  # type
            100,  # fee
            "nem",  # namespace
            "xem",  # mosaic
        ),
        (104,),  # networks
    )
