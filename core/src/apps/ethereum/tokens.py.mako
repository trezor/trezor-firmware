# generated from tokens.py.mako
# (by running `make templates` in `core`)
# do not edit manually!
# fmt: off

# NOTE: returning a tuple instead of `TokenInfo` from the "data" function
# saves 5600 bytes of flash size. Implementing the `_token_iterator`
# instead of if-tree approach saves another 5600 bytes.

# NOTE: interestingly, it did not save much flash size to use smaller
# parts of the address, for example address length of 10 bytes saves
# 1 byte per entry, so 1887 bytes overall (and further decrease does not help).
# (The idea was not having to store the whole address, even a smaller part
# of it has enough collision-resistance.)
# (In the if-tree approach the address length did not have any effect whatsoever.)

from typing import Iterator

<%
from collections import defaultdict

def group_tokens(tokens):
    r = defaultdict(list)
    for t in sorted(tokens, key=lambda t: t.chain_id):
        r[t.chain_id].append(t)
    return r
%>\

class TokenInfo:
    def __init__(self, symbol: str, decimals: int) -> None:
        self.symbol = symbol
        self.decimals = decimals


UNKNOWN_TOKEN = TokenInfo("Wei UNKN", 0)


def token_by_chain_address(chain_id: int, address: bytes) -> TokenInfo:
    for addr, symbol, decimal in _token_iterator(chain_id):
        if address == addr:
            return TokenInfo(symbol, decimal)
    return UNKNOWN_TOKEN


def _token_iterator(chain_id: int) -> Iterator[tuple[bytes, str, int]]:
% for token_chain_id, tokens in group_tokens(supported_on("trezor2", erc20)).items():
    if chain_id == ${token_chain_id}:
        % for t in tokens:
        yield (  # address, symbol, decimals
            ${black_repr(t.address_bytes)},
            ${black_repr(t.symbol)},
            ${t.decimals},
        )
        % endfor
% endfor
