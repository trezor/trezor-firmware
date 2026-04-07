class Refund:
    def __init__(
        self,
        address: str,
        account: str | None,
        account_path: str | None,
    ) -> None:
        self.address = address
        self.account = account
        self.account_path = account_path


class Trade:
    def __init__(
        self,
        sell_amount: str | None,
        buy_amount: str,
        address: str,
        account: str | None,
        account_path: str | None,
    ) -> None:
        if sell_amount is not None:
            assert sell_amount.startswith("-")
        assert buy_amount.startswith("+")

        self.sell_amount = sell_amount
        self.buy_amount = buy_amount
        self.address = address
        self.account = account
        self.account_path = account_path


def is_swap(trades: list[Trade]) -> bool:
    assert sum(t.sell_amount is None for t in trades) in (0, len(trades))

    return any(t.sell_amount is not None for t in trades)
