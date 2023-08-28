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

from trezor import utils
from trezor.messages import EthereumTokenInfo
<%
from collections import defaultdict

def group_tokens(tokens):
    r = defaultdict(list)
    for t in sorted(tokens, key=lambda t: t.chain_id):
        r[t.chain_id].append(t)
    return r
%>\

UNKNOWN_TOKEN = EthereumTokenInfo(
    symbol="Wei UNKN",
    decimals=0,
    address=b"",
    chain_id=0,
    name="Unknown token",
)


def token_by_chain_address(chain_id: int, address: bytes) -> EthereumTokenInfo | None:
    for addr, symbol, decimal, name in _token_iterator(chain_id):
        if address == addr:
            return EthereumTokenInfo(
                symbol=symbol,
                decimals=decimal,
                address=address,
                chain_id=chain_id,
                name=name,
            )
    return None


def _token_iterator(chain_id: int) -> Iterator[tuple[bytes, str, int, str]]:
    if utils.MODEL_IS_T2B1:
% for token_chain_id, tokens in group_tokens(supported_on("T2B1", erc20)).items():
        if chain_id == ${token_chain_id}:  # ${tokens[0].chain}
            % for t in tokens:
            yield (  # address, symbol, decimals, name
                ${black_repr(t.address_bytes)},
                ${black_repr(t.symbol)},
                ${t.decimals},
                ${black_repr(t.name.strip())},
            )
            % endfor
% endfor
    else:
% for token_chain_id, tokens in group_tokens(supported_on("T2T1", erc20)).items():
        if chain_id == ${token_chain_id}:  # ${tokens[0].chain}
            % for t in tokens:
            yield (  # address, symbol, decimals, name
                ${black_repr(t.address_bytes)},
                ${black_repr(t.symbol)},
                ${t.decimals},
                ${black_repr(t.name.strip())},
            )
            % endfor
% endfor
