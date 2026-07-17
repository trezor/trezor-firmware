# Ethereum app: clear-signing calldata parsing

Clear signing ([ERC-7730](https://eips.ethereum.org/EIPS/eip-7730)) decodes a
transaction's calldata according to a *display format descriptor* (built-in in
`clear_signing_definitions.py`, or provided by the host as a signed blob) and
shows the decoded values to the user instead of a raw hex dump. This document
describes how `clear_signing.py` parses ABI-encoded calldata, and how the test
suite covers each encoding shape.

Reference: the
[Solidity ABI specification](https://docs.soliditylang.org/en/latest/abi-spec.html#formal-specification-of-the-encoding).

## The one rule: static vs dynamic

ABI encoding is aligned to the 256-bit EVM word (`_EVM_WORD_SIZE = 32` bytes):
every atomic value, offset, length prefix and head slot occupies exactly one
word. Every ABI type is either **static** or **dynamic**:

* `bytes`, `string`, any `T[]`, and any tuple with at least one dynamic field
  are dynamic; everything else (integers, `address`, `bool`, `bytesN`,
  leaf-only tuples of those) is static.
* A **static** value is encoded **in place**, occupying its full size.
* A **dynamic** value's head is a **single word** holding the offset of its
  body, relative to the start of the enclosing block (the top-level parameter
  block, an array's element area, or a tuple's body).

`ABIValue.parse()` implements this head rule once, for all types. Each
subclass only describes what its *body* looks like, in `parse_body()`:

| class         | ABI types            | `is_dynamic` | body layout                                            |
| ------------- | -------------------- | ------------ | ------------------------------------------------------ |
| `Atomic`      | `uintN`, `address`, `bool`, `bytes32`, ... | never | the one-word value itself             |
| `DynamicLeaf` | `bytes`, `string`    | always       | one-word **byte length**, then that many bytes         |
| `Array`       | `T[]`                | always       | one-word **element count**, then the elements' heads   |
| `Tuple`       | structs (leaf fields only) | iff any field is dynamic | the fields' heads, back to back  |

Note the two length prefixes mean different things: a `DynamicLeaf` counts
*bytes*, an `Array` counts *elements*.

### Consequences worth spelling out

* A **static tuple** has no length word and no offsets anywhere - it is just
  its field values concatenated (`32 × len(fields)` bytes).
* An array of a **static** element type (`uint256[]`, or
  `(address,address,uint256)[]`) encodes its elements **in place** after the
  count, at a stride of the element size. An array of a **dynamic** element
  type (`bytes[]`, `uint256[][]`, or an array of structs containing `bytes`)
  encodes one offset word per element, each relative to the start of the
  element area (right after the count).
* A dynamic struct inside an array is reached by dereferencing its element
  offset; the body found there is then laid out exactly like an in-place
  static struct, with its own dynamic-field offsets relative to the body
  start. ("Parse the body in place" is universal; only the head dereference
  depends on the type's dynamism.)
* Whether a leaf-only tuple is dynamic is fully derivable from its fields.
  For tuples nested inside arrays, `ABIValue.from_proto` therefore *derives*
  the flag and ignores the wire descriptor's `is_dynamic` (which was
  historically ignored in that position anyway).

## Worked example

`TEST_PATHS_CALLDATA` (see `tests/device_tests/ethereum/test_definitions_request.py`)
calls the debug-only "paths" test descriptor `7e577e04` with parameters
`(uint256 amount, bytes packedPath, (address,address,uint256)[] swapData)`:

```text
selector 7e577e04
w0  0x00  ...001e8480   amount = 2000000            (static, in place)
w1  0x20  ...0060       offset of packedPath body   (dynamic -> offset head)
w2  0x40  ...00c0       offset of swapData body     (dynamic -> offset head)
          -- packedPath body (at 0x60, relative to block start 0x00) --
w3  0x60  ...0028       byte length = 40
w4  0x80  4444..5555    40 bytes of data...
w5  0xa0  5555..0000    ...zero-padded to a word boundary
          -- swapData body (at 0xc0) --
w6  0xc0  ...0002       element count = 2
w7  0xe0  ...6666       [0].sendingAssetId   ┐ element 0, in place
w8  0x100 ...7777       [0].receivingAssetId │ (static struct, no offset
w9  0x120 ...5b8d80     [0].fromAmount       ┘  heads, stride 96)
w10 0x140 ...8888       [1].sendingAssetId   ┐
w11 0x160 ...0000       [1].receivingAssetId │ element 1
w12 0x180 ...0de0b6...  [1].fromAmount       ┘
```

Had the struct contained a dynamic field (like LiFi's `swapData` structs with
`bytes callData`), words w7/w8 would instead be offsets relative to 0xe0, with
the two struct bodies following after the heads.

## Failure behavior

All parsing errors derive from `ClearSigningFailed`. `sign_tx` catches it and
falls back to **blind signing** - the transaction can still be signed, just
without the decoded display. Two implications:

* a descriptor/calldata mismatch degrades UX but does not brick signing;
* the signature-only fixtures (below) cannot distinguish the clear and blind
  paths, because the signature covers the raw transaction either way.

Calldata larger than the initial chunk (`MAX_DATA_STORED`) is never
clear-signed, for the same fallback-preserving reason. Zero-field tuples are
rejected at construction: they don't exist in Solidity, and a static tuple
with `head_size == 0` inside an array would defeat the heads bounds pre-check
(`array_length * 0`), letting an attacker-controlled length word drive an
unbounded parse loop. Rejecting them guarantees `head_size >= 32` for every
constructible type.
