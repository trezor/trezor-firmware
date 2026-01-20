# flake8: noqa: F403,F405
from common import *  # isort:skip

if not utils.BITCOIN_ONLY:
    from trezor.enums import (
        StellarHostFunctionType,
        StellarSCValType,
        StellarSorobanAuthorizedFunctionType,
        StellarSorobanCredentialsType,
    )
    from trezor.messages import (
        StellarHostFunction,
        StellarInt128Parts,
        StellarInt256Parts,
        StellarInvokeContractArgs,
        StellarSCVal,
        StellarSCValMapEntry,
        StellarSorobanAuthorizationEntry,
        StellarSorobanAuthorizedFunction,
        StellarSorobanAuthorizedInvocation,
        StellarSorobanCredentials,
        StellarUInt128Parts,
        StellarUInt256Parts,
    )

    from apps.stellar.operations.layout import (
        _format_i128,
        _format_i256,
        _format_sc_val,
        _format_u128,
        _format_u256,
        _is_root_auth_entry,
    )

    def _u32(value):
        return StellarSCVal(type=StellarSCValType.SCV_U32, u32=value)

    def _u64(value):
        return StellarSCVal(type=StellarSCValType.SCV_U64, u64=value)

    def _bytes(value):
        return StellarSCVal(type=StellarSCValType.SCV_BYTES, bytes=value)

    def _string(value):
        return StellarSCVal(type=StellarSCValType.SCV_STRING, string=value)

    def _symbol(value):
        return StellarSCVal(type=StellarSCValType.SCV_SYMBOL, symbol=value)

    def _vec(items):
        return StellarSCVal(type=StellarSCValType.SCV_VEC, vec=items)

    def _map(entries):
        return StellarSCVal(type=StellarSCValType.SCV_MAP, map=entries)

    def _entry(key, value):
        return StellarSCValMapEntry(key=key, value=value)


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestStellarFormatIntegers(unittest.TestCase):
    def test_format_u128(self):
        TESTS = [
            ((0, 0), "0"),
            ((0, 1), "1"),
            ((1, 0), str(2**64)),
            ((0xFFFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFF), str(2**128 - 1)),
        ]
        for (hi, lo), expected in TESTS:
            self.assertEqual(_format_u128(StellarUInt128Parts(hi=hi, lo=lo)), expected)

    def test_format_i128(self):
        TESTS = [
            ((0, 0), "0"),
            ((0, 1), "1"),
            ((-1, 0xFFFFFFFFFFFFFFFF), "-1"),
            ((1, 0), str(2**64)),
            ((-1, 0), str(-(2**64))),
            ((0x7FFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFF), str(2**127 - 1)),
            ((-0x8000000000000000, 0), str(-(2**127))),
        ]
        for (hi, lo), expected in TESTS:
            self.assertEqual(_format_i128(StellarInt128Parts(hi=hi, lo=lo)), expected)

    def test_format_u256(self):
        TESTS = [
            ((0, 0, 0, 0), "0"),
            ((0, 0, 0, 1), "1"),
            ((0, 0, 1, 0), str(2**64)),
            ((0, 1, 0, 0), str(2**128)),
            ((1, 0, 0, 0), str(2**192)),
            (
                (
                    0xFFFFFFFFFFFFFFFF,
                    0xFFFFFFFFFFFFFFFF,
                    0xFFFFFFFFFFFFFFFF,
                    0xFFFFFFFFFFFFFFFF,
                ),
                str(2**256 - 1),
            ),
        ]
        for (hi_hi, hi_lo, lo_hi, lo_lo), expected in TESTS:
            parts = StellarUInt256Parts(
                hi_hi=hi_hi, hi_lo=hi_lo, lo_hi=lo_hi, lo_lo=lo_lo
            )
            self.assertEqual(_format_u256(parts), expected)

    def test_format_i256(self):
        TESTS = [
            ((0, 0, 0, 0), "0"),
            ((0, 0, 0, 1), "1"),
            (
                (
                    -1,
                    0xFFFFFFFFFFFFFFFF,
                    0xFFFFFFFFFFFFFFFF,
                    0xFFFFFFFFFFFFFFFF,
                ),
                "-1",
            ),
            ((0, 0, 1, 0), str(2**64)),
            ((-1, 0xFFFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFF, 0), str(-(2**64))),
            ((0, 1, 0, 0), str(2**128)),
            ((-1, 0xFFFFFFFFFFFFFFFF, 0, 0), str(-(2**128))),
            ((1, 0, 0, 0), str(2**192)),
            ((-1, 0, 0, 0), str(-(2**192))),
            (
                (
                    0x7FFFFFFFFFFFFFFF,
                    0xFFFFFFFFFFFFFFFF,
                    0xFFFFFFFFFFFFFFFF,
                    0xFFFFFFFFFFFFFFFF,
                ),
                str(2**255 - 1),
            ),
            ((-0x8000000000000000, 0, 0, 0), str(-(2**255))),
        ]
        for (hi_hi, hi_lo, lo_hi, lo_lo), expected in TESTS:
            parts = StellarInt256Parts(
                hi_hi=hi_hi, hi_lo=hi_lo, lo_hi=lo_hi, lo_lo=lo_lo
            )
            self.assertEqual(_format_i256(parts), expected)


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestStellarFormatScVal(unittest.TestCase):
    def test_format_bytes(self):
        TESTS = [
            (b"", "0x"),
            (b"\xde\xad\xbe\xef", "0xdeadbeef"),
        ]
        for value, expected in TESTS:
            self.assertEqual(_format_sc_val(_bytes(value)), expected)

    def test_format_string(self):
        TESTS = [
            (b"hello", '"hello"'),
            # embedded quotes and backslashes are escaped so a string cannot forge
            # the surrounding quotes (and thus the vec/map separators)
            (b'a"b', r'"a\"b"'),
            (b"a\\b", r'"a\\b"'),
            (b'a\\"b', r'"a\\\"b"'),
            # control characters are passed through unescaped
            (b"a\nb", '"a\nb"'),
            # non-UTF-8 bytes fall back to hex, like SCV_BYTES
            (b"\xff\xfe", "0xfffe"),
        ]
        for value, expected in TESTS:
            self.assertEqual(_format_sc_val(_string(value)), expected)

    def test_format_symbol(self):
        TESTS = [
            ("transfer", '"transfer"'),
            ('a"b', r'"a\"b"'),
        ]
        for value, expected in TESTS:
            self.assertEqual(_format_sc_val(_symbol(value)), expected)

    def test_format_vec(self):
        TESTS = [
            ([], "[]"),
            ([_u32(1), _symbol("a")], '[1, "a"]'),
            ([_vec([_u32(1)])], "[[1]]"),
            # a string element cannot forge additional vec items
            ([_string(b'", "x')], r'["\", \"x"]'),
        ]
        for items, expected in TESTS:
            self.assertEqual(_format_sc_val(_vec(items)), expected)

    def test_format_map(self):
        TESTS = [
            ([], "{}"),
            ([_entry(_symbol("amount"), _u32(5))], '{"amount": 5}'),
            (
                [
                    _entry(_symbol("amount"), _u32(5)),
                    # a string value cannot forge map structure
                    _entry(_symbol("k"), _string(b'", "x')),
                ],
                r'{"amount": 5, "k": "\", \"x"}',
            ),
        ]
        for entries, expected in TESTS:
            self.assertEqual(_format_sc_val(_map(entries)), expected)


# valid contract (C...) strkeys, see test_apps.stellar.address.py for the format
_CONTRACT_A = "CAAACAQDAQCQMBYIBEFAWDANBYHRAEISCMKBKFQXDAMRUGY4DUPB6N4O"
_CONTRACT_B = "CBSGKZTHNBUWU23MNVXG64DROJZXI5LWO54HS6T3PR6X474AQGBIHDKP"


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestStellarIsRootAuthEntry(unittest.TestCase):
    def test_is_root_auth_entry(self):
        invoked = StellarHostFunction(
            type=StellarHostFunctionType.HOST_FUNCTION_TYPE_INVOKE_CONTRACT,
            invoke_contract=StellarInvokeContractArgs(
                contract_address=_CONTRACT_A, function_name="submit", args=[_u32(1)]
            ),
        )

        TESTS = [
            ((_CONTRACT_A, "submit", [_u32(1)]), True),  # identical
            ((_CONTRACT_A, "submit", [_u32(2)]), False),  # different arg value
            ((_CONTRACT_A, "submit", [_u64(1)]), False),  # different arg type
            ((_CONTRACT_A, "submit", [_u32(1), _u32(1)]), False),  # extra arg
            ((_CONTRACT_A, "submit", []), False),  # missing arg
            ((_CONTRACT_A, "swap", [_u32(1)]), False),  # different function
            ((_CONTRACT_B, "submit", [_u32(1)]), False),  # different contract
        ]
        for (contract, function, args), is_root in TESTS:
            auth_entry = StellarSorobanAuthorizationEntry(
                credentials=StellarSorobanCredentials(
                    type=StellarSorobanCredentialsType.SOROBAN_CREDENTIALS_SOURCE_ACCOUNT
                ),
                root_invocation=StellarSorobanAuthorizedInvocation(
                    function=StellarSorobanAuthorizedFunction(
                        type=StellarSorobanAuthorizedFunctionType.SOROBAN_AUTHORIZED_FUNCTION_TYPE_CONTRACT_FN,
                        contract_fn=StellarInvokeContractArgs(
                            contract_address=contract,
                            function_name=function,
                            args=args,
                        ),
                    ),
                    sub_invocations=[],
                ),
            )
            self.assertEqual(_is_root_auth_entry(auth_entry, invoked), is_root)


if __name__ == "__main__":
    unittest.main()
