"""Production WM trust provisioning is reproducible and never exports its seed."""

import json
import subprocess
import sys
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from tools.ward_provision import ROOT, render


def test_provision_from_manager_seed_and_check_generated_key(tmp_path: Path) -> None:
    seed = bytes.fromhex("12" * 32)
    seed_file, config, output = (
        tmp_path / name for name in ("seed", "config.json", "wm_config.py")
    )
    seed_file.write_text(seed.hex() + "\n")
    args = [
        sys.executable,
        str(ROOT / "tools/ward_provision.py"),
        "--config",
        str(config),
        "--output",
        str(output),
    ]
    result = subprocess.run(
        [*args, "--seed-file", str(seed_file)], capture_output=True, check=True
    )
    public_key = (
        Ed25519PrivateKey.from_private_bytes(seed).public_key().public_bytes_raw().hex()
    )
    assert json.loads(config.read_text()) == {"public_key": public_key}
    assert output.read_text() == render(public_key)
    assert seed.hex() not in output.read_text()
    assert result.stdout == result.stderr == b""
    subprocess.run([*args, "--check"], check=True)
    output.write_text("stale")
    assert subprocess.run([*args, "--check"]).returncode == 1
