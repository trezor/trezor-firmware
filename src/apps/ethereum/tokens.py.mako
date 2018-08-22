# generated from tokens.py.mako
# do not edit manually!


def token_by_chain_address(chain_id, address):
    for token in tokens:
        if chain_id == token[0] and address == token[1]:
            return token
    return UNKNOWN_TOKEN


UNKNOWN_TOKEN = (None, None, None, None)


# fmt: off
tokens = [
% for t in supported_on("trezor2", erc20):
    (${t.chain_id}, ${black_repr(t.address_bytes)}, ${black_repr(t.symbol)}, ${t.decimals}),  # ${t.chain} / ${t.name.strip()}
% endfor
]
# fmt: on
