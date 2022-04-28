# generated from nem_mosaics.py.mako
# (by running `make templates` in `core`)
# do not edit manually!

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
        name="NEM",
        ticker=" XEM",
        namespace="nem",
        mosaic="xem",
        divisibility=6,
    )
    yield Mosaic(
        name="DIMCOIN",
        ticker=" DIM",
        namespace="dim",
        mosaic="coin",
        divisibility=6,
        levy=MosaicLevy(
            type=NEMMosaicLevy.MosaicLevy_Percentile,
            fee=10,
            namespace="dim",
            mosaic="coin",
        ),
        networks=(104,),
    )
    yield Mosaic(
        name="DIM TOKEN",
        ticker=" DIMTOK",
        namespace="dim",
        mosaic="token",
        divisibility=6,
        networks=(104,),
    )
    yield Mosaic(
        name="Breeze Token",
        ticker=" BREEZE",
        namespace="breeze",
        mosaic="breeze-token",
        divisibility=0,
        networks=(104,),
    )
    yield Mosaic(
        name="PacNEM Game Credits",
        ticker=" PAC:HRT",
        namespace="pacnem",
        mosaic="heart",
        divisibility=0,
        networks=(104,),
    )
    yield Mosaic(
        name="PacNEM Score Tokens",
        ticker=" PAC:CHS",
        namespace="pacnem",
        mosaic="cheese",
        divisibility=6,
        levy=MosaicLevy(
            type=NEMMosaicLevy.MosaicLevy_Percentile,
            fee=100,
            namespace="nem",
            mosaic="xem",
        ),
        networks=(104,),
    )
