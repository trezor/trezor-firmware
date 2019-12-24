# generated from tokens.py.mako
# do not edit manually!
# flake8: noqa
# fmt: off
#TODO: ADD .MAKO
UNKNOWN_TOKEN = (None, None, None, None)


def token_by_address(token_type, address):
    print("AAA", token_type, address)
    if False:
        pass
    elif token_type == "TRC20":
        if False:
            pass
        elif address == "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t":
            return (token_type, address, "$USDT", 6)
        elif address == "TBoTZcARzWVgnNuB9SyE3S5g1RwsXoQL16":
            return (token_type, address, "$CCT", 6)
    elif chain_id == "TRC10":
        if False:
            pass
        elif address == "1000166":
            return (token_type, address, "$CCT", 0) 
    return UNKNOWN_TOKEN
