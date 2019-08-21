# generated from tokens.py.mako
# do not edit manually!
# flake8: noqa
# fmt: off
<%
from collections import defaultdict

def group_tokens(tokens):
    r = defaultdict(list)
    for t in sorted(tokens, key=lambda t: t.chain_id):
        r[t.chain_id].append(t)
    return r
%>\

UNKNOWN_TOKEN = (None, None, None, None)


def token_by_chain_address(chain_id, address):
    if False:
        pass
% for token_chain_id, tokens in group_tokens(supported_on("trezor2", erc20)).items():
    elif chain_id == ${token_chain_id}:
        if False:
            pass
        % for t in tokens:
        elif address == ${black_repr(t.address_bytes)}:
            return (chain_id, address, ${black_repr(t.symbol)}, ${t.decimals})  # ${t.chain} / ${t.name.strip()}
        % endfor
% endfor
    return UNKNOWN_TOKEN
