import pytest
from click import ClickException

from trezorlib import messages
from trezorlib.cli.cosmos import _require_single_fee_amount, _validate_tx_json


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
        match="Invalid transaction format: missing 'auth_info.fee' field",
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
