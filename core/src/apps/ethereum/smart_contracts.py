# generated from smart_contracts.py.mako
# (by running `make templates` in `core`)
# do not edit manually!
# fmt: off

# NOTE: the concept of iteration is similar to token.py.mako to save space

from typing import TYPE_CHECKING

from trezor import utils
from trezor.messages import EthereumSmartContractDefinition, EthereumSmartContractArg
if TYPE_CHECKING:
    from typing import Iterator

    # fmt: off
    ERC20FuncDef = tuple[
        bytes,  # function signature
        str,  # name
        tuple[tuple[str, str, str], ...],  # inputs[name, type, internal_type]
        bool,  # is_transfer
    ]
    # fmt: on


def erc20_func_by_sig(func_sig: bytes) -> EthereumSmartContractDefinition | None:
    def convert_helper(args):
        return [EthereumSmartContractArg(name=arg[0], type=arg[1], internal_type=arg[2]) for arg in args]

    for sig, name, inputs, is_transfer in _erc20_func_iterator():
        if sig == func_sig:
            return EthereumSmartContractDefinition(
                sig=sig,
                name=name,
                inputs=convert_helper(list(inputs)),
                is_transfer=is_transfer
            )
    return None


def _erc20_func_iterator() -> Iterator[ERC20FuncDef]:
    if utils.MODEL_IS_T2B1:
        yield (  # sig, name, inputs, is_transfer
            b"\x09\x5e\xa7\xb3",
            "approve",
            (("Address", "address", "address"), ("Amount", "uint256", "int")),
            False,
        )
        yield (
            b"\x70\xa0\x82\x31",
            "balanceOf",
            (("Owner", "address", "address"),),
            False,
        )
    else:
        yield (  # sig, name, inputs, is_transfer
            b"\x09\x5e\xa7\xb3",
            "approve",
            (("Address", "address", "address"), ("Amount", "uint256", "int")),
            False,
        )
        yield (
            b"\x70\xa0\x82\x31",
            "balanceOf",
            (("Owner", "address", "address"),),
            False,
        )
