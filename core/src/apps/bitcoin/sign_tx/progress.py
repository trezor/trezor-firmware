from typing import TYPE_CHECKING

from trezor import ui

if TYPE_CHECKING:
    from trezor.messages import SignTx
    from apps.common.coininfo import CoinInfo
    from .tx_info import OriginalTxInfo

# Checking previous transactions typically requires the following pieces of
# information to be fetched for each input:
# the input, prevtx metadata, prevtx input, prevtx output, prevtx change-output
_PREV_TX_MULTIPLIER = 5

_progress = 0
_steps = 0
_signing = False
_prev_tx_step = 0


def init(tx: SignTx) -> None:
    global _progress, _steps, _signing
    _progress = 0
    _signing = False

    # Step 1 and 2 - load inputs and outputs
    _steps = tx.inputs_count + tx.outputs_count

    report_init()
    report()


def init_signing(
    external: int,
    segwit: int,
    taproot_only: bool,
    has_presigned: bool,
    serialize: bool,
    coin: CoinInfo,
    tx: SignTx,
    orig_txs: list[OriginalTxInfo],
) -> None:
    if __debug__:
        assert_finished()

    global _progress, _steps, _signing
    _progress = 0
    _steps = 0
    _signing = True

    # Step 3 - verify inputs
    if taproot_only or (coin.overwintered and tx.version == 5):
        if has_presigned:
            _steps += external
    else:
        _steps = tx.inputs_count * _PREV_TX_MULTIPLIER

    for orig in orig_txs:
        _steps += orig.tx.inputs_count

    # Steps 3 and 4 - get_legacy_tx_digest() for each legacy input.
    if not (coin.force_bip143 or coin.overwintered or coin.decred):
        _steps += (tx.inputs_count - segwit) * (tx.inputs_count + tx.outputs_count)

        if segwit != tx.inputs_count:
            # The transaction has a legacy input.

            # Simplification: We assume that all original transaction inputs
            # are legacy, since mixed script types are not supported in Suite.
            for orig in orig_txs:
                _steps += orig.tx.inputs_count * (
                    orig.tx.inputs_count + orig.tx.outputs_count
                )

    # Steps 4 and 6 - serialize and sign inputs
    if serialize:
        _steps += tx.inputs_count + segwit
    else:
        _steps += tx.inputs_count - external

    # Step 5 - serialize outputs
    if serialize and not coin.decred:
        _steps += tx.outputs_count

    report_init()
    report()


def init_prev_tx(inputs: int, outputs: int) -> None:
    global _prev_tx_step
    _prev_tx_step = _PREV_TX_MULTIPLIER / (inputs + outputs)


def advance() -> None:
    global _progress
    _progress += 1
    report()


def advance_prev_tx() -> None:
    global _progress
    _progress += _prev_tx_step
    report()


def report_init() -> None:
    from trezor import workflow

    workflow.close_others()
    ui.display.clear()
    if _signing:
        ui.header("Signing transaction")
    else:
        ui.header("Loading transaction")


def report() -> None:
    from trezor import utils

    if utils.DISABLE_ANIMATION:
        return
    p = int(1000 * _progress / _steps)
    ui.display.loader(p, False, 18, ui.WHITE, ui.BG)


if __debug__:

    def assert_finished() -> None:
        if abs(_progress - _steps) > 0.5:
            operation = "signing" if _signing else "loading"
            from trezor import wire
            raise wire.FirmwareError(
                f"Transaction {operation} progress finished at {_progress}/{_steps}."
            )
