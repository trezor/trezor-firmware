# generated from tokens.py.mako
# do not edit manually!
# flake8: noqa
# fmt: off

UNKNOWN_TOKEN = (None, None, None, None)


def token_by_address(token_type, address):
    if False:
        pass
    elif token_type == "TRC10":
        if False:
            pass
        elif address == "1000166":
            return (token_type, address, "1CCT", 0)  # TRC10 / CryptoChain Token TRC10
    elif token_type == "TRC20":
        if False:
            pass
        elif address == "TJkG6fRtspb1YmE15PGwWpBfRbZLrvxKdv":
            return (token_type, address, "BTCt", 6)  # TRC20 / Bitcoin-Tron
        elif address == "TBoTZcARzWVgnNuB9SyE3S5g1RwsXoQL16":
            return (token_type, address, "CCT", 6)  # TRC20 / CryptoChain Token
        elif address == "TKTcfBEKpp5ZRPwmiZ8SfLx8W7CDZ7PHCY":
            return (token_type, address, "TWX", 6)  # TRC20 / TronWallet
        elif address == "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t":
            return (token_type, address, "USDT", 6)  # TRC20 / USDT
    return UNKNOWN_TOKEN
