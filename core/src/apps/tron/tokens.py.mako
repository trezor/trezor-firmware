# generated from tokens.py.mako
# do not edit manually!
# flake8: noqa
# fmt: off
<%
from collections import defaultdict

def group_tokens(tokens):
    r = defaultdict(list)
    for t in sorted(tokens, key=lambda t: t.type):
        r[t.type].append(t)
    return r
%>\

UNKNOWN_TOKEN = (None, None, None, None)


def token_by_address(token_type, address):
    if False:
        pass
% for t_type, tokens in group_tokens(supported_on("trezor2", tron)).items():
    elif token_type == "${t_type}":
        if False:
            pass
        % for t in tokens:
        elif address == ${black_repr(t.address)}:
            return (token_type, address, ${black_repr(t.ticker)}, ${t.decimals})  # ${t_type} / ${t.name.strip()}
        % endfor
% endfor
    return UNKNOWN_TOKEN
