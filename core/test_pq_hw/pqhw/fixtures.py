"""Access to the binary fixture set built by build_fixtures.py."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from trezorlib.firmware.pq_secure import PqSecureBundle

MODEL = "T3W1"
DEFAULT_ROOT = Path(__file__).resolve().parents[1] / "fixtures"

VARIANTS = ("universal", "btc-only")


class FixtureError(Exception):
    pass


class Fixtures:
    def __init__(self, root: Path = DEFAULT_ROOT) -> None:
        self.root = root
        manifest = root / "manifest.json"
        if not manifest.exists():
            raise FixtureError(
                f"no fixture set at {root}; run core/test_pq_hw/build_fixtures.py"
            )
        self.manifest = json.loads(manifest.read_text())
        self.files: dict[str, dict] = self.manifest["files"]

    def verify(self) -> None:
        """Every file the manifest lists is present and unchanged."""
        bad = []
        for rel, meta in sorted(self.files.items()):
            path = self.root / rel
            if not path.exists():
                bad.append(f"{rel}: missing")
            elif hashlib.sha256(path.read_bytes()).hexdigest() != meta["sha256"]:
                bad.append(f"{rel}: sha256 differs from the manifest")
        if bad:
            raise FixtureError("fixture set is inconsistent:\n  " + "\n  ".join(bad))

    def path(self, rel: str) -> Path:
        if rel not in self.files:
            raise FixtureError(f"{rel} is not in the fixture manifest")
        return self.root / rel

    def info(self, rel: str) -> dict:
        return self.files[rel]

    # --- named fixtures ---------------------------------------------------

    def legacy(self, part: str) -> Path:
        """`boardloader`, `bootloader`, or a firmware variant."""
        if part in VARIANTS:
            return self.path(f"legacy/firmware-{part}.bin")
        return self.path(f"legacy/{part}.bin")

    def intermediary(self, variant: str) -> Path:
        return self.path(f"intermediary/firmware-{variant}.bin")

    def release_zip(self, release: str) -> Path:
        return self.path(f"{release}/{MODEL}.zip")

    def release_file(self, release: str, name: str) -> Path:
        return self.path(f"{release}/{MODEL}/{name}")

    def release_bootloader(self, release: str) -> Path:
        return self.release_file(release, "bootloader.bin")

    def bundle(self, release: str, variant: str) -> PqSecureBundle:
        return PqSecureBundle.load(self.release_zip(release), variant)

    def release_meta(self, release: str) -> dict:
        return json.loads(self.release_file(release, "bundle.json").read_text())
