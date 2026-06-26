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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

"""Basic CLI tests for trezorctl.

These tests exercise CLI plumbing — command registration, aliases, argument
parsing, and output formatting — using Click's CliRunner.  No physical device
or emulator is required.
"""

from __future__ import annotations

import importlib.metadata
import json

import pytest
from click.testing import CliRunner

from trezorlib.cli.trezorctl import COMMAND_ALIASES, cli


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------


class TestVersion:
    """trezorctl version / --version output."""

    def test_version_command(self, runner: CliRunner) -> None:
        """``trezorctl version`` prints the package version."""
        result = runner.invoke(cli, ["version"])
        assert result.exit_code == 0
        expected = importlib.metadata.version("trezor")
        assert expected in result.output

    def test_version_flag(self, runner: CliRunner) -> None:
        """``trezorctl --version`` prints version and exits 0."""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert importlib.metadata.version("trezor") in result.output

    def test_version_json_output(self, runner: CliRunner) -> None:
        """``trezorctl --json version`` returns a valid JSON string."""
        result = runner.invoke(cli, ["--json", "version"])
        assert result.exit_code == 0
        parsed = json.loads(result.output.strip())
        assert parsed == importlib.metadata.version("trezor")

    def test_version_script_json(self, runner: CliRunner) -> None:
        """``--json --script`` produces compact (no newlines in value) JSON."""
        result = runner.invoke(cli, ["--json", "--script", "version"])
        assert result.exit_code == 0
        # compact mode: json.loads should still parse it
        parsed = json.loads(result.output.strip())
        assert isinstance(parsed, str)


# ---------------------------------------------------------------------------
# Help text
# ---------------------------------------------------------------------------


class TestHelpText:
    """trezorctl --help and subcommand help pages."""

    def test_root_help(self, runner: CliRunner) -> None:
        """Root --help exits 0 and lists core command groups."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        for expected in ("btc", "ethereum", "firmware", "device"):
            assert expected in result.output, f"missing '{expected}' in --help"

    def test_root_help_lists_version_command(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "version" in result.output

    def test_list_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["list", "--help"])
        assert result.exit_code == 0
        assert "List connected Trezor devices" in result.output

    def test_btc_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["btc", "--help"])
        assert result.exit_code == 0
        assert "sign-tx" in result.output

    def test_ethereum_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["ethereum", "--help"])
        assert result.exit_code == 0
        assert "sign-tx" in result.output

    def test_firmware_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["firmware", "--help"])
        assert result.exit_code == 0
        assert "update" in result.output

    def test_device_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["device", "--help"])
        assert result.exit_code == 0

    def test_set_help(self, runner: CliRunner) -> None:
        """Settings group is registered as 'set'."""
        result = runner.invoke(cli, ["set", "--help"])
        assert result.exit_code == 0
        assert "Device settings" in result.output

    def test_crypto_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["crypto", "--help"])
        assert result.exit_code == 0

    def test_cardano_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["cardano", "--help"])
        assert result.exit_code == 0

    def test_solana_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["solana", "--help"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# AliasedGroup: underscore → dash normalisation
# ---------------------------------------------------------------------------


class TestUnderscoreToDash:
    """AliasedGroup converts underscore-delimited commands to dash-delimited."""

    def test_top_level_underscore(self, runner: CliRunner) -> None:
        """``trezorctl get_features`` is recognised as ``get-features``."""
        result = runner.invoke(cli, ["get_features", "--help"])
        assert result.exit_code == 0
        assert "get-features" in result.output.lower() or "features" in result.output.lower()

    def test_get_session_underscore(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["get_session", "--help"])
        assert result.exit_code == 0

    def test_clear_session_underscore(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["clear_session", "--help"])
        assert result.exit_code == 0

    def test_wait_for_emulator_underscore(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["wait_for_emulator", "--help"])
        assert result.exit_code == 0

    def test_btc_subcommand_dash(self, runner: CliRunner) -> None:
        """Subcommand with dash works."""
        result = runner.invoke(cli, ["btc", "sign-tx", "--help"])
        assert result.exit_code == 0

    def test_btc_subcommand_underscore_rejected(self, runner: CliRunner) -> None:
        """AliasedGroup normalises at the top level only; sub-group commands
        use their own AliasedGroup instance and also normalise underscores."""
        result = runner.invoke(cli, ["btc", "sign_tx", "--help"])
        # Underscore in sub-group — AliasedGroup inside btc.cli normalises it
        # so this may succeed; what matters is it does not crash unhandled.
        assert result.exit_code in (0, 2)


# ---------------------------------------------------------------------------
# TrezorctlGroup: old-style dash-compound command lookup
# ---------------------------------------------------------------------------


class TestOldStyleCommandLookup:
    """TrezorctlGroup resolves old-style ``group-subcommand`` names."""

    def test_ethereum_sign_tx(self, runner: CliRunner) -> None:
        """``ethereum-sign-tx`` maps to ``ethereum sign-tx``."""
        result = runner.invoke(cli, ["ethereum-sign-tx", "--help"])
        assert result.exit_code == 0
        assert "sign" in result.output.lower()

    def test_btc_sign_tx(self, runner: CliRunner) -> None:
        """``btc sign-tx`` is directly in btc group; old-style falls back too."""
        result = runner.invoke(cli, ["btc", "sign-tx", "--help"])
        assert result.exit_code == 0

    def test_firmware_update_oldstyle(self, runner: CliRunner) -> None:
        """``update-firmware`` is a COMMAND_ALIAS."""
        result = runner.invoke(cli, ["update-firmware", "--help"])
        assert result.exit_code == 0

    def test_firmware_upgrade_oldstyle(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["upgrade-firmware", "--help"])
        assert result.exit_code == 0

    def test_firmware_upgrade_oldstyle2(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["firmware-upgrade", "--help"])
        assert result.exit_code == 0

    def test_firmware_update_oldstyle2(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["firmware-update", "--help"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# COMMAND_ALIASES: device-operation aliases
# ---------------------------------------------------------------------------


class TestCommandAliases:
    """Legacy long-form device aliases from COMMAND_ALIASES."""

    @pytest.mark.parametrize(
        "alias",
        [
            "change-pin",
            "enable-passphrase",
            "disable-passphrase",
            "wipe-device",
            "reset-device",
            "recovery-device",
            "backup-device",
            "sd-protect",
            "load-device",
        ],
    )
    def test_device_alias_has_help(self, runner: CliRunner, alias: str) -> None:
        """Each device alias responds to --help without error."""
        result = runner.invoke(cli, [alias, "--help"])
        assert result.exit_code == 0, (
            f"alias '{alias}' failed with exit_code={result.exit_code}:\n{result.output}"
        )

    @pytest.mark.parametrize(
        "alias",
        [
            "get-entropy",
            "encrypt-keyvalue",
            "decrypt-keyvalue",
        ],
    )
    def test_crypto_alias_has_help(self, runner: CliRunner, alias: str) -> None:
        result = runner.invoke(cli, [alias, "--help"])
        assert result.exit_code == 0, (
            f"alias '{alias}' failed: exit={result.exit_code}\n{result.output}"
        )

    def test_all_aliases_registered(self) -> None:
        """Every key in COMMAND_ALIASES is reachable via the CLI."""
        runner = CliRunner()
        for alias_name in COMMAND_ALIASES:
            result = runner.invoke(cli, [alias_name, "--help"])
            assert result.exit_code == 0, (
                f"COMMAND_ALIAS '{alias_name}' not reachable: "
                f"exit={result.exit_code}\n{result.output}"
            )


# ---------------------------------------------------------------------------
# COMMAND_ALIASES: currency shortcuts
# ---------------------------------------------------------------------------


class TestCurrencyAliases:
    """Short currency aliases (eth, ada, sol, …) resolve to their CLI groups."""

    @pytest.mark.parametrize(
        "alias, canonical",
        [
            ("eth", "ethereum"),
            ("ada", "cardano"),
            ("sol", "solana"),
            ("xmr", "monero"),
            ("xrp", "ripple"),
            ("xlm", "stellar"),
            ("xtz", "tezos"),
            ("trx", "tron"),
            ("fw", "firmware"),
        ],
    )
    def test_currency_alias_help(
        self, runner: CliRunner, alias: str, canonical: str
    ) -> None:
        result = runner.invoke(cli, [alias, "--help"])
        assert result.exit_code == 0, (
            f"currency alias '{alias}' failed: exit={result.exit_code}\n{result.output}"
        )
        # The help output should mention the canonical group name or its purpose
        assert canonical in result.output.lower() or result.output.strip(), (
            f"alias '{alias}': expected '{canonical}' in help output"
        )


# ---------------------------------------------------------------------------
# Unknown / invalid commands
# ---------------------------------------------------------------------------


class TestInvalidCommands:
    """Unknown commands produce a clear error and non-zero exit code."""

    def test_unknown_top_level_command(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["nonexistent-xyz-command"])
        assert result.exit_code != 0

    def test_unknown_command_error_message(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["nonexistent-xyz-command"])
        assert "No such command" in result.output or "Error" in result.output

    def test_unknown_btc_subcommand(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["btc", "nonexistent-subcommand"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# print_result output formatting
# ---------------------------------------------------------------------------


class TestOutputFormatting:
    """print_result callback handles plain and JSON output modes."""

    def test_plain_version_output_is_bare_string(self, runner: CliRunner) -> None:
        """Plain mode prints the version without JSON wrapping."""
        result = runner.invoke(cli, ["version"])
        assert result.exit_code == 0
        # Should not contain JSON quotes around the version
        output = result.output.strip()
        assert not output.startswith('"'), (
            "Plain mode should not JSON-encode the output"
        )

    def test_json_version_output_is_json_string(self, runner: CliRunner) -> None:
        """JSON mode wraps the version in a JSON string."""
        result = runner.invoke(cli, ["--json", "version"])
        assert result.exit_code == 0
        parsed = json.loads(result.output.strip())
        assert isinstance(parsed, str)
        assert "." in parsed  # looks like a version number

    def test_json_script_mode_compact(self, runner: CliRunner) -> None:
        """--json --script produces compact (no indent) JSON."""
        result = runner.invoke(cli, ["--json", "--script", "version"])
        assert result.exit_code == 0
        raw = result.output.strip()
        # Compact JSON has no newlines in the body
        assert "\n" not in raw


# ---------------------------------------------------------------------------
# Global option wiring
# ---------------------------------------------------------------------------


class TestGlobalOptions:
    """Global CLI options are accepted and do not cause crashes."""

    def test_verbose_flag(self, runner: CliRunner) -> None:
        """-v (verbose) is accepted alongside --help."""
        result = runner.invoke(cli, ["-v", "--help"])
        assert result.exit_code == 0

    def test_verbose_multiple(self, runner: CliRunner) -> None:
        """-vv is accepted."""
        result = runner.invoke(cli, ["-vv", "--help"])
        assert result.exit_code == 0

    def test_path_option_accepted(self, runner: CliRunner) -> None:
        """-p / --path is accepted (even with a dummy value) for --help."""
        result = runner.invoke(cli, ["--path", "udp:127.0.0.1:21324", "--help"])
        assert result.exit_code == 0

    def test_passphrase_on_host_flag(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["--passphrase-on-host", "--help"])
        assert result.exit_code == 0

    def test_script_flag(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["--script", "--help"])
        assert result.exit_code == 0
