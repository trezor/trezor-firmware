from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Sequence

    pass


async def confirm_total_ethereum(
    text, total_amount: str, gas_price: str, fee_max: str
) -> None:
    raise NotImplementedError


async def confirm_total_ripple(
    address: str,
    amount: str,
) -> None:
    raise NotImplementedError


async def confirm_transfer_binance(
    inputs_outputs: Sequence[tuple[str, str, str]]
) -> None:
    raise NotImplementedError


async def confirm_decred_sstx_submission(
    address: str,
    amount: str,
) -> None:
    raise NotImplementedError
