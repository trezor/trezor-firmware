import logging
import tarfile
import typing as t
from pathlib import Path

import construct as c
import requests
from construct_classes import Struct, subcon

from . import cosi, merkle_tree
from .messages import DefinitionType
from .tools import EnumAdapter

LOG = logging.getLogger(__name__)

FORMAT_MAGIC = b"trzd1"
DEFS_BASE_URL = "https://data.trezor.io/firmware/eth-definitions/"

DEFINITIONS_DEV_SIGS_REQUIRED = 1
DEFINITIONS_DEV_PUBLIC_KEYS = [
    bytes.fromhex(key)
    for key in ("db995fe25169d141cab9bbba92baa01f9f2e1ece7df4cb2ac05190f37fcc1f9d",)
]

DEFINITIONS_SIGS_REQUIRED = 2
DEFINITIONS_PUBLIC_KEYS = [
    bytes.fromhex(key)
    for key in (
        "4334996343623e462f0fc93311fef1484ca23d2ff1eec6df1fa8eb7e3573b3db",
        "a9a22cc265a0cb1d6cb329bc0e60bc45df76b9ab28fb87b61136feaf8d8fdc96",
        "b8d2b21de27124f0511f903ae7e60e07961810a0b8f28ea755fa50367a8a2b8b",
    )
]


ProofFormat = c.PrefixedArray(c.Int8ul, c.Bytes(32))


class DefinitionPayload(Struct):
    magic: bytes
    data_type: DefinitionType
    timestamp: int
    data: bytes

    SUBCON = c.Struct(
        "magic" / c.Const(FORMAT_MAGIC),
        "data_type" / EnumAdapter(c.Int8ul, DefinitionType),
        "timestamp" / c.Int32ul,
        "data" / c.Prefixed(c.Int16ul, c.GreedyBytes),
    )


class Definition(Struct):
    payload: DefinitionPayload = subcon(DefinitionPayload)
    proof: t.List[bytes]
    sigmask: int
    signature: bytes

    SUBCON = c.Struct(
        "payload" / DefinitionPayload.SUBCON,
        "proof" / ProofFormat,
        "sigmask" / c.Int8ul,
        "signature" / c.Bytes(64),
    )

    def verify(self, dev: bool = False) -> None:
        payload = self.payload.build()
        root = merkle_tree.evaluate_proof(payload, self.proof)
        cosi.verify(
            self.signature,
            root,
            DEFINITIONS_DEV_SIGS_REQUIRED,
            DEFINITIONS_DEV_PUBLIC_KEYS,
            self.sigmask,
        )


class Source:
    def fetch_path(self, *components: str) -> t.Optional[bytes]:
        raise NotImplementedError

    def get_network_by_slip44(self, slip44: int) -> t.Optional[bytes]:
        return self.fetch_path("slip44", str(slip44), "network.dat")

    def get_network(self, chain_id: int) -> t.Optional[bytes]:
        return self.fetch_path("chain-id", str(chain_id), "network.dat")

    def get_token(self, chain_id: int, address: t.AnyStr) -> t.Optional[bytes]:
        if isinstance(address, bytes):
            address_str = address.hex()
        elif address.startswith("0x"):
            address_str = address[2:]
        else:
            address_str = address

        address_str = address_str.lower()

        return self.fetch_path("chain-id", f"{chain_id}", f"token-{address_str}.dat")


class NullSource(Source):
    def fetch_path(self, *components: str) -> t.Optional[bytes]:
        return None


class FilesystemSource(Source):
    def __init__(self, root: Path) -> None:
        self.root = root

    def fetch_path(self, *components: str) -> t.Optional[bytes]:
        path = self.root.joinpath(*components)
        if not path.exists():
            LOG.info("Requested definition at %s was not found", path)
            return None
        LOG.info("Reading definition from %s", path)
        return path.read_bytes()


class UrlSource(Source):
    def __init__(self, base_url: str = DEFS_BASE_URL) -> None:
        self.base_url = base_url

    def fetch_path(self, *components: str) -> t.Optional[bytes]:
        url = self.base_url + "/".join(components)
        LOG.info("Downloading definition from %s", url)
        r = requests.get(url)
        if r.status_code == 404:
            LOG.info("Requested definition at %s was not found", url)
            return None
        r.raise_for_status()
        return r.content


class TarSource(Source):
    def __init__(self, path: Path) -> None:
        self.archive = tarfile.open(path)

    def fetch_path(self, *components: str) -> t.Optional[bytes]:
        inner_name = "/".join(components)
        LOG.info("Extracting definition from %s:%s", self.archive.name, inner_name)
        try:
            return self.archive.extractfile(inner_name).read()  # type: ignore [not a known attribute]
        except Exception:
            LOG.info("Requested definition at %s was not found", inner_name)
            return None
