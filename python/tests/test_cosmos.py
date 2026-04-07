import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import pytest
from click import ClickException
from click.testing import CliRunner

from trezorlib import messages
from trezorlib.cli.cosmos import (
    _require_single_fee_amount,
    _validate_supported_auth_info,
    _validate_supported_signer_info,
    _validate_tx_json,
    sign_transaction,
)


@dataclass(frozen=True)
class _FakeFieldDescriptor:
    name: str


@dataclass
class _FakeFee:
    payer: str = ""
    granter: str = ""


@dataclass
class _FakeModeInfoSingle:
    mode: Optional[int] = None


@dataclass
class _FakeModeInfo:
    single: Optional[_FakeModeInfoSingle] = None


@dataclass
class _FakePublicKey:
    type_url: str = ""
    value: bytes = b""


@dataclass
class _FakeSignerInfo:
    public_key: Optional[_FakePublicKey] = None
    mode_info: Optional[_FakeModeInfo] = None
    sequence: int = 0


@dataclass
class _FakeAuthInfo:
    signer_infos: list[object]
    fee: _FakeFee
    extra_fields: list[str] = field(default_factory=list)

    def ListFields(self) -> list[tuple[_FakeFieldDescriptor, Any]]:
        fields: list[tuple[_FakeFieldDescriptor, Any]] = [
            (_FakeFieldDescriptor("fee"), self.fee),
        ]
        if self.signer_infos:
            fields.insert(0, (_FakeFieldDescriptor("signer_infos"), self.signer_infos))
        for name in self.extra_fields:
            fields.append((_FakeFieldDescriptor(name), object()))
        return fields


class _FakeCosmosPubKey:
    def __init__(self) -> None:
        self.key = b""

    def ParseFromString(self, payload: bytes) -> None:
        self.key = payload


def test_validate_tx_json_requires_body() -> None:
    with pytest.raises(
        ClickException, match="Invalid transaction format: missing 'body' field"
    ):
        _validate_tx_json({"auth_info": {"fee": {}}})


def test_validate_tx_json_requires_auth_info() -> None:
    with pytest.raises(
        ClickException, match="Invalid transaction format: missing 'auth_info' field"
    ):
        _validate_tx_json({"body": {}})


def test_validate_tx_json_requires_fee() -> None:
    with pytest.raises(
        ClickException,
        match=r"Invalid transaction format: missing 'auth_info\.fee' field",
    ):
        _validate_tx_json({"body": {}, "auth_info": {}})


def test_require_single_fee_amount_rejects_missing_amounts() -> None:
    with pytest.raises(
        ClickException, match="Transaction must specify exactly one fee amount"
    ):
        _require_single_fee_amount(messages.CosmosFee(gas_limit=1))


def test_require_single_fee_amount_rejects_multiple_amounts() -> None:
    with pytest.raises(ClickException, match="Multiple fee amounts are not supported"):
        _require_single_fee_amount(
            messages.CosmosFee(
                gas_limit=1,
                amount=[
                    messages.CosmosCoin(amount="1", denom="uatom"),
                    messages.CosmosCoin(amount="2", denom="uosmo"),
                ],
            )
        )


def test_require_single_fee_amount_returns_only_amount() -> None:
    fee_amount = _require_single_fee_amount(
        messages.CosmosFee(
            gas_limit=1,
            amount=[messages.CosmosCoin(amount="42", denom="uatom")],
        )
    )

    assert fee_amount.amount == "42"
    assert fee_amount.denom == "uatom"


def test_validate_supported_auth_info_rejects_missing_signer() -> None:
    with pytest.raises(
        ClickException, match="Transaction must specify exactly one signer"
    ):
        _validate_supported_auth_info(_FakeAuthInfo(signer_infos=[], fee=_FakeFee()))


def test_validate_supported_auth_info_rejects_multiple_signers() -> None:
    with pytest.raises(
        ClickException, match="Transaction must specify exactly one signer"
    ):
        _validate_supported_auth_info(
            _FakeAuthInfo(signer_infos=[object(), object()], fee=_FakeFee())
        )


def test_validate_supported_auth_info_rejects_fee_payer() -> None:
    with pytest.raises(ClickException, match="Fee payer is not supported"):
        _validate_supported_auth_info(
            _FakeAuthInfo(signer_infos=[object()], fee=_FakeFee(payer="cosmos1payer"))
        )


def test_validate_supported_auth_info_rejects_fee_granter() -> None:
    with pytest.raises(ClickException, match="Fee granter is not supported"):
        _validate_supported_auth_info(
            _FakeAuthInfo(
                signer_infos=[object()],
                fee=_FakeFee(granter="cosmos1granter"),
            )
        )


def test_validate_supported_auth_info_rejects_tip() -> None:
    with pytest.raises(ClickException, match="Unsupported auth_info fields: tip"):
        _validate_supported_auth_info(
            _FakeAuthInfo(
                signer_infos=[object()],
                fee=_FakeFee(),
                extra_fields=["tip"],
            )
        )


def test_validate_supported_signer_info_rejects_missing_mode_info() -> None:
    with pytest.raises(ClickException, match="Signer mode_info is required"):
        _validate_supported_signer_info(
            _FakeSignerInfo(
                public_key=_FakePublicKey(
                    type_url="/cosmos.crypto.secp256k1.PubKey",
                    value=b"pubkey",
                ),
                mode_info=None,
                sequence=7,
            ),
            expected_sequence=7,
            expected_public_key=b"pubkey",
            pubkey_cls=_FakeCosmosPubKey,
        )


def test_validate_supported_signer_info_rejects_non_direct_mode() -> None:
    with pytest.raises(
        ClickException, match="Signer mode_info must use SIGN_MODE_DIRECT"
    ):
        _validate_supported_signer_info(
            _FakeSignerInfo(
                public_key=_FakePublicKey(
                    type_url="/cosmos.crypto.secp256k1.PubKey",
                    value=b"pubkey",
                ),
                mode_info=_FakeModeInfo(single=_FakeModeInfoSingle(mode=2)),
                sequence=7,
            ),
            expected_sequence=7,
            expected_public_key=b"pubkey",
            pubkey_cls=_FakeCosmosPubKey,
        )


def test_validate_supported_signer_info_rejects_missing_public_key() -> None:
    with pytest.raises(ClickException, match="Signer public_key is required"):
        _validate_supported_signer_info(
            _FakeSignerInfo(
                public_key=None,
                mode_info=_FakeModeInfo(single=_FakeModeInfoSingle(mode=1)),
                sequence=7,
            ),
            expected_sequence=7,
            expected_public_key=b"pubkey",
            pubkey_cls=_FakeCosmosPubKey,
        )


def test_validate_supported_signer_info_rejects_public_key_mismatch() -> None:
    with pytest.raises(
        ClickException, match="Signer public_key does not match the requested address"
    ):
        _validate_supported_signer_info(
            _FakeSignerInfo(
                public_key=_FakePublicKey(
                    type_url="/cosmos.crypto.secp256k1.PubKey",
                    value=b"other-pubkey",
                ),
                mode_info=_FakeModeInfo(single=_FakeModeInfoSingle(mode=1)),
                sequence=7,
            ),
            expected_sequence=7,
            expected_public_key=b"pubkey",
            pubkey_cls=_FakeCosmosPubKey,
        )


def test_validate_supported_signer_info_rejects_sequence_mismatch() -> None:
    with pytest.raises(ClickException, match="Signer sequence does not match --sequence"):
        _validate_supported_signer_info(
            _FakeSignerInfo(
                public_key=_FakePublicKey(
                    type_url="/cosmos.crypto.secp256k1.PubKey",
                    value=b"pubkey",
                ),
                mode_info=_FakeModeInfo(single=_FakeModeInfoSingle(mode=1)),
                sequence=9,
            ),
            expected_sequence=7,
            expected_public_key=b"pubkey",
            pubkey_cls=_FakeCosmosPubKey,
        )


def test_sign_transaction_rejects_negative_account_number(tmp_path: Path) -> None:
    tx_file = tmp_path / "tx.json"
    tx_file.write_text(json.dumps({"body": {}, "auth_info": {"fee": {}}}))

    result = CliRunner().invoke(
        sign_transaction,
        [
            str(tx_file),
            "--address",
            "m/44h/118h/0h/0/0",
            "--chain-id",
            "cosmoshub-4",
            "--account-number",
            "-1",
            "--sequence",
            "0",
        ],
    )

    assert result.exit_code != 0
    assert "-1 is not in the range x>=0" in result.output


def test_sign_transaction_rejects_negative_sequence(tmp_path: Path) -> None:
    tx_file = tmp_path / "tx.json"
    tx_file.write_text(json.dumps({"body": {}, "auth_info": {"fee": {}}}))

    result = CliRunner().invoke(
        sign_transaction,
        [
            str(tx_file),
            "--address",
            "m/44h/118h/0h/0/0",
            "--chain-id",
            "cosmoshub-4",
            "--account-number",
            "0",
            "--sequence",
            "-1",
        ],
    )

    assert result.exit_code != 0
    assert "-1 is not in the range x>=0" in result.output
