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
% for m in supported_on("trezor2", nem):
    yield Mosaic(
        name="${m.name}",
        ticker=" ${m.ticker}",
        namespace="${m.namespace}",
        mosaic="${m.mosaic}",
        divisibility=${m.divisibility},
% if "levy" in m:
        levy=MosaicLevy(
            type=NEMMosaicLevy.${m.levy},
            fee=${m.fee},
            namespace="${m.levy_namespace}",
            mosaic="${m.levy_mosaic}",
        ),
% endif
% if "networks" in m:
        networks=${tuple(m.networks)},
% endif
    )
% endfor
