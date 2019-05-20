# generated from tokens.py.mako
# do not edit manually!

<%
from collections import defaultdict

def group_tokens(tokens):
    r = defaultdict(list)
    for t in tokens:
        r[t.chain_id].append(t)
    return r
%>

UNKNOWN_TOKEN = (None, None, None, None)


def token_by_chain_address(chain_id, address):
    if False:
        pass
    # fmt: off
% for token_chain_id, tokens in group_tokens(supported_on("trezor2", erc20)).items():
    elif chain_id == ${token_chain_id}:
        if False:
            pass
        % for t in tokens:
        elif address == ${black_repr(t.address_bytes)}:
            return (${t.chain_id}, ${black_repr(t.address_bytes)}, ${black_repr(t.symbol)}, ${t.decimals})  # ${t.chain} / ${t.name.strip()}
        % endfor
% endfor
    # fmt: on
    return UNKNOWN_TOKEN
