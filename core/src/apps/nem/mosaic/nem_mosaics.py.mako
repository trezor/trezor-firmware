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
% for m in supported_on("T2T1", nem):
    yield Mosaic(
        "${m.name}",  # name
        " ${m.ticker}",  # ticker
        "${m.namespace}",  # namespace
        "${m.mosaic}",  # mosaic
        ${m.divisibility},  # divisibility
% if "levy" in m:
        MosaicLevy(  # levy
            NEMMosaicLevy.${m.levy},  # type
            ${m.fee},  # fee
            "${m.levy_namespace}",  # namespace
            "${m.levy_mosaic}",  # mosaic
        ),
% else:
        None,  # levy
% endif
% if "networks" in m:
        ${tuple(m.networks)},  # networks
% endif
    )
% endfor
