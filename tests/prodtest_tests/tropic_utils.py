# This file is part of the Trezor project.
#
# Copyright (C) SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

"""Helpers for inspecting the Tropic model state after a prodtest run.

The `model_server` (Tropic model) dumps its final state to a YAML file when it
shuts down (see `trezorlib._internal.emulator.TropicModel.stop`, which sends
SIGINT so the model's `atexit` save handler runs). This module wraps that YAML
in a small read-only view so tests can assert on pairing keys, config words,
memory slots and ECC keys without re-parsing the raw structure everywhere.
"""

from __future__ import annotations

import typing as t
from pathlib import Path

import yaml

from trezorlib._internal.emulator import TropicModel
from trezorlib.prodtest.prodtest_client import ProdtestClient


# TODO: remove once ts-tvl ships the plain-int-key dump from
# https://github.com/tropicsquare/ts-tvl/pull/14 — then `from_file` can go back
# to a plain `yaml.safe_load` (and this loader + `_construct_apply` can go).
class _TropicYamlLoader(yaml.SafeLoader):
    """SafeLoader that tolerates the model's Python-tagged enum keys.

    Some commands (e.g. `tropic-lock`) make the model serialize slot indices
    as `!!python/object/apply:tvl.api.l3_api.SlotEnum [N]` instead of a plain
    integer. The stock `SafeLoader` refuses those tags. We map any such
    `apply` node back to its single argument (the integer), so pairing-key
    slots keyed by `SlotEnum(N)` read back identically to the `N` used
    elsewhere. Subclassing keeps this off the global `SafeLoader`.
    """


def _construct_apply(
    loader: yaml.SafeLoader, _tag_suffix: str, node: yaml.Node
) -> t.Any:
    # The SlotEnum form is `apply:...SlotEnum [N]` — a one-element arg sequence.
    if isinstance(node, yaml.SequenceNode):
        args = loader.construct_sequence(node, deep=True)
    elif isinstance(node, yaml.MappingNode):
        # General apply mapping form (`{args: [...], ...}`).
        args = loader.construct_mapping(node, deep=True).get("args", [])
    else:
        args = []
    return args[0] if len(args) == 1 else tuple(args)


_TropicYamlLoader.add_multi_constructor(
    "tag:yaml.org,2002:python/object/apply:", _construct_apply
)


class TropicModelState:
    """Read-only view over a Tropic model config-output YAML file.

    The structure mirrors `tests/tropic_model/config.yml`:

      - `i_config` / `r_config`: dicts of `cfg_*` config words (ints)
      - `i_pairing_keys`: slot index -> {`state`, `value`}
      - `r_user_data`: slot index -> {`value`, `free`}
      - `r_ecc_keys`: slot index -> {`a`, `s`, `prefix`, `origin`}
    """

    def __init__(self, raw: dict[str, t.Any]) -> None:
        self.raw = raw

    @classmethod
    def from_file(cls, path: Path | str) -> "TropicModelState":
        path = Path(path)
        assert path.exists(), (
            f"Tropic model output file was not generated: {path}. "
            "Did the Tropic model receive SIGINT on shutdown?"
        )
        return cls(yaml.load(path.read_text(), Loader=_TropicYamlLoader) or {})

    @property
    def i_config(self) -> dict[str, int]:
        return self.raw.get("i_config", {})

    @property
    def r_config(self) -> dict[str, int]:
        return self.raw.get("r_config", {})

    @property
    def chip_id(self) -> bytes | None:
        return self.raw.get("chip_id")

    def pairing_key(self, slot: int) -> dict[str, t.Any] | None:
        return (self.raw.get("i_pairing_keys") or {}).get(slot)

    def pairing_key_state(self, slot: int) -> str | None:
        key = self.pairing_key(slot)
        return key.get("state") if key else None

    def pairing_key_value(self, slot: int) -> bytes | None:
        key = self.pairing_key(slot)
        return key.get("value") if key else None

    def slot(self, slot: int) -> dict[str, t.Any] | None:
        return (self.raw.get("r_user_data") or {}).get(slot)

    def slot_value(self, slot: int) -> bytes | None:
        entry = self.slot(slot)
        return entry.get("value") if entry else None

    def slot_is_erased(self, slot: int) -> bool:
        """True if the slot is absent, explicitly free, empty or all-0xFF."""
        entry = self.slot(slot)
        if not entry:
            return True
        if entry.get("free") is True:
            return True
        value = entry.get("value")
        if value in (None, b""):
            return True
        return all(byte == 0xFF for byte in value)

    def ecc_key(self, slot: int) -> dict[str, t.Any] | None:
        return (self.raw.get("r_ecc_keys") or {}).get(slot)

    def ecc_key_is_present(self, slot: int) -> bool:
        return self.ecc_key(slot) is not None

    @property
    def mcounters(self) -> dict[int, dict[str, t.Any]]:
        return self.raw.get("r_mcounters") or {}

    def mcounter(self, slot: int) -> dict[str, t.Any] | None:
        return self.mcounters.get(slot)


class TropicSession:
    """A prodtest client together with the Tropic model backing its emulator.

    Exposes the prodtest `client` for issuing `tropic-*` commands and,
    once the surrounding context manager has closed (so the Tropic model has
    flushed its state), `state` for inspecting the resulting model config.
    """

    def __init__(self, client: ProdtestClient, tropic_model: TropicModel) -> None:
        self.client = client
        self.tropic_model = tropic_model

    def state(self) -> TropicModelState:
        """Parse the Tropic model output YAML.

        Only meaningful after the `tropic_prodtest` context manager has exited,
        because the model writes the file on shutdown.
        """
        return TropicModelState.from_file(self.tropic_model.configfile_output)


class TropicProdtest(t.Protocol):
    """Type of the `tropic_prodtest` fixture: a factory of `TropicSession`.

    Annotate the fixture parameter with this so `with tropic_prodtest() as
    session` infers `session: TropicSession`::

        def test_x(tropic_prodtest: TropicProdtest) -> None:
            with tropic_prodtest() as session:
                ...
    """

    def __call__(
        self, *, tropic_model_configfile: str | Path | None = None
    ) -> t.ContextManager[TropicSession]: ...
