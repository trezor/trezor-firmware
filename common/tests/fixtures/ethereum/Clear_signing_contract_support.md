# Ethereum Clear-Signing Test Fixtures — Contract Call Reference

Reference for the 14 unique smart contract function calls tested in
`sign_tx_clear_signing.json`. Organised by protocol.

---

## Clear-Signing Display System

Each `DisplayFormat` in `clear_signing_definitions.py` declares a list of
`FieldDefinition` entries. Each entry has three parts:

```
FieldDefinition(path, label, formatter)
```

These are the fields that will actually be presented to the signer on the
device — everything else in the calldata is ignored for display purposes.

### Path indexing

The `path` is a tuple of integers that navigates the parsed parameter tree:

| Path style | Meaning | Example |
|---|---|---|
| `(N,)` | Top-level parameter at index N | `(2,)` → 3rd parameter |
| `(N, M)` | Field M inside the struct at parameter N | `(1, 4)` → struct param 1, field index 4 |
| `(N, I, M)` | Field M inside element I of the array at parameter N | `(5, 0, 4)` → array param 5, first element, field index 4 |
| Negative index | From the end of an array | `(5, -1, 3)` → last element of array param 5, field index 3 |
| Nested tuple `(0, 20)` | Byte-slice `[0:20]` of a `bytes` field | Extracts the first 20 bytes (an address) |
| Nested tuple `(-20,)` | Last 20 bytes of a `bytes` field | Extracts the last address from a packed path |
| `ContainerPath.From` | `msg.sender` — not from calldata, from the transaction envelope | Used when the beneficiary is always the tx sender |
| `ContainerPath.Value` | `msg.value` — ETH attached to the transaction | Used for native-ETH-input functions where no amount field exists in calldata |

### `token_path` inside `TokenAmountFormatter`

`TokenAmountFormatter(token_path=(...))` takes a path (same indexing rules as
above) that locates the **ERC20 contract address** to use for decimal and
symbol lookup. This is how the device knows whether an amount is in USDC (6
decimals) or WETH (18 decimals).

When `TokenAmountFormatter` is used **without** a `token_path`, no token
address can be resolved — the formatter must fall back to displaying a raw
integer or a generic "unknown token" value. This happens when the output token
is not present in the calldata (e.g. native ETH output, or output implied by
opaque pool routing).

---

## 1. 1inch AggregationRouter V6

**Contract:** `0x111111125421cA6dc452d289314280a0f8842A65`

---

### `swap`

**Selector:** `0x07ed2379`

```solidity
function swap(
    IAggregationExecutor executor,
    SwapDescription calldata desc,
    bytes calldata data
) external payable returns (uint256 returnAmount, uint256 spentAmount)
```

**`SwapDescription` struct:**

| Field | Type | Description |
|---|---|---|
| `srcToken` | `IERC20` | Token being sold |
| `dstToken` | `IERC20` | Token being bought |
| `srcReceiver` | `address payable` | Address that receives the source token from the caller (usually the executor) |
| `dstReceiver` | `address payable` | Address that receives the output token |
| `amount` | `uint256` | Exact amount of `srcToken` to swap |
| `minReturnAmount` | `uint256` | Minimum acceptable output; reverts if not met |
| `flags` | `uint256` | Bitmask controlling routing behaviour (e.g. partial fill, ETH wrapping) |

**Top-level parameters:**

| Parameter | Type | Description |
|---|---|---|
| `executor` | `IAggregationExecutor` | Contract that executes the actual swap steps |
| `desc` | `SwapDescription` | Swap parameters (see struct above) |
| `data` | `bytes` | Calldata passed to the executor for routing |

**Purpose:** General-purpose aggregated swap. Routes through any combination of
DEX pools via an external executor contract, enabling complex multi-hop paths.

**Clear-signing display fields:**

| Label | Path | Resolves to | Formatter | `token_path` | Notes |
|---|---|---|---|---|---|
| "Amount to Send" | `(1, 4)` | `desc.amount` | `TokenAmountFormatter` | `(1, 0)` → `desc.srcToken` | |
| "Minimum to Receive" | `(1, 5)` | `desc.minReturnAmount` | `TokenAmountFormatter` | `(1, 1)` → `desc.dstToken` | |
| "Beneficiary" | `(1, 3)` | `desc.dstReceiver` | `AddressNameFormatter` | — | |

---

### `unoswap`

**Selector:** `0x83800a8e`

```solidity
function unoswap(
    address token,
    uint256 amount,
    uint256 minReturn,
    uint256[] calldata pools
) external payable returns (uint256 returnAmount)
```

| Parameter | Type | Description |
|---|---|---|
| `token` | `address` | Source token address |
| `amount` | `uint256` | Amount of source token to swap |
| `minReturn` | `uint256` | Minimum acceptable output amount; reverts if not met |
| `pools` | `uint256[]` | Bit-packed pool descriptors — see below |

**Purpose:** Optimised single- or multi-hop swap through Uniswap-compatible pools.
Cheaper gas than `swap` when no complex routing logic is required. Output is sent
to `msg.sender`.

**The `pools` parameter — bit-packed `uint256[]`:**

Although the ABI declares `pools` as `uint256[]`, each element is **not** a plain
number. 1inch uses bit-packing to store the pool address, swap direction, and DEX
type flags all inside a single 256-bit word, bypassing the need for separate
`address[]` and `bool[]` parameters. The internal assembly uses `calldataload`
directly rather than standard Solidity array reads, which saves gas by avoiding
memory allocation.

The bit layout of each `uint256` element is:

| Bits | Width | Meaning |
|---|---|---|
| 0 – 159 | 160 bits | Pool contract address (lower 20 bytes) |
| 160 – 254 | 95 bits | Reserved / DEX-type flags (Uniswap V2, V3, PancakeSwap, etc.) |
| 255 | 1 bit | **Direction flag** (`REVERSE_MASK`): `0` = Token0→Token1, `1` = Token1→Token0 |

Extraction in pseudocode:

```solidity
uint256 pool = pools[i];
address poolAddress = address(uint160(pool));          // lower 160 bits
bool reverse = (pool & 0x8000000000000000000000000000000000000000000000000000000000000000) != 0;
```

Because the direction flag sits in bit 255, a pool that is traversed in reverse
will have a `uint256` value that looks enormous — far larger than any real
address — which is why the raw hex looks "weird" in the clear-signing registry.
The ERC-7730 spec has no built-in formatter for this composite type; the
`UnitFormatter` assigned to "Last pool" in the display definitions is therefore
a placeholder that cannot meaningfully decode the packed value.

**Clear-signing display fields:**

| Label | Path | Resolves to | Formatter | `token_path` | Notes |
|---|---|---|---|---|---|
| "Amount to Send" | `(1,)` | `amount` | `TokenAmountFormatter` | `(0,)` → `token` (srcToken) | |
| "Minimum to Receive" | `(2,)` | `minReturn` | `TokenAmountFormatter` | — (none) | ⚠️ **No token_path**: output token is not present in calldata — it is implied by the final pool. Formatter cannot resolve decimals/symbol. |
| "Beneficiary" | `ContainerPath.From` | `msg.sender` | `AddressNameFormatter` | — | Output always goes to the transaction sender; this is not a calldata field. |
| "Last pool" | `(3, -1)` | `pools[-1]` (last element) | `UnitFormatter` | — | ⚠️ **Type/formatter mismatch**: the field is a packed `uint256` pool descriptor (encodes an address + direction flags as a bitfield). `UnitFormatter` appends a unit string but the raw value is not human-readable as a plain number. |

---

### `unoswapTo`

**Selector:** `0xe2c95c82`

```solidity
function unoswapTo(
    address payable to,
    address token,
    uint256 amount,
    uint256 minReturn,
    uint256[] calldata pools
) external payable returns (uint256 returnAmount)
```

| Parameter | Type | Description |
|---|---|---|
| `to` | `address payable` | Recipient of the output token |
| `token` | `address` | Source token address |
| `amount` | `uint256` | Amount of source token to swap |
| `minReturn` | `uint256` | Minimum acceptable output amount |
| `pools` | `uint256[]` | Bit-packed pool descriptors — same encoding as `unoswap` (see above) |

**Purpose:** Identical to `unoswap` but allows specifying a different recipient
for the output tokens instead of defaulting to `msg.sender`.

**Clear-signing display fields:**

| Label | Path | Resolves to | Formatter | `token_path` | Notes |
|---|---|---|---|---|---|
| "Amount to Send" | `(2,)` | `amount` | `TokenAmountFormatter` | `(1,)` → `token` (srcToken) | |
| "Minimum to Receive" | `(3,)` | `minReturn` | `TokenAmountFormatter` | — (none) | ⚠️ **No token_path**: same situation as `unoswap` — output token is not in calldata. |
| "Beneficiary" | `(0,)` | `to` | `AddressNameFormatter` | — | |
| "Last pool" | `(4, -1)` | `pools[-1]` (last element) | `UnitFormatter` | — | ⚠️ **Type/formatter mismatch**: same packed `uint256` pool descriptor issue as `unoswap`. |

---

## 2. LiFi Diamond

**Contract:** `0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE`

All LiFi swap functions share the same top-level parameter structure. The
`LibSwap.SwapData` struct describes a single swap step within a larger route.

**`LibSwap.SwapData` struct:**

| Field | Index | Type | Description |
|---|---|---|---|
| `callTo` | 0 | `address` | DEX/contract to call for this step |
| `approveTo` | 1 | `address` | Contract to approve token spending for (often same as `callTo`) |
| `sendingAssetId` | 2 | `address` | Token sent into this step (`0xEEEE...` for native ETH) |
| `receivingAssetId` | 3 | `address` | Token received from this step |
| `fromAmount` | 4 | `uint256` | Amount of `sendingAssetId` to use in this step |
| `callData` | 5 | `bytes` | Encoded call to execute on `callTo` |
| `requiresDeposit` | 6 | `bool` | Whether the contract must deposit `sendingAssetId` before calling |

> **Note on array paths:** For the `Multiple` variants the `_swapData`
> parameter is an array. A path like `(5, 0, 4)` means: top-level param 5
> (`_swapData`), element at index 0 (first swap step), struct field at index 4
> (`fromAmount`). The path `(5, -1, 3)` uses -1 to reach the **last** element
> of the array, then field 3 (`receivingAssetId`). This lets the display
> always show the initial spend and the final receive regardless of how many
> intermediate hops exist.

---

### `swapTokensMultipleV3ERC20ToERC20`

**Selector:** `0x5fd9ae2e`

```solidity
function swapTokensMultipleV3ERC20ToERC20(
    bytes32 _transactionId,
    string calldata _integrator,
    string calldata _referrer,
    address payable _receiver,
    uint256 _minAmountOut,
    LibSwap.SwapData[] calldata _swapData
) external
```

| Parameter | Index | Type | Description |
|---|---|---|---|
| `_transactionId` | 0 | `bytes32` | Unique identifier for this LiFi transaction |
| `_integrator` | 1 | `string` | Name of the integrating application (e.g. `"kucoin"`) |
| `_referrer` | 2 | `string` | Referrer address string (usually zero address) |
| `_receiver` | 3 | `address payable` | Final recipient of the output ERC20 tokens |
| `_minAmountOut` | 4 | `uint256` | Minimum acceptable output amount across all steps |
| `_swapData` | 5 | `LibSwap.SwapData[]` | Ordered array of swap steps to execute |

**Purpose:** Execute a multi-step swap path where both input and output are ERC20
tokens. Transfers input tokens from caller before executing steps.

**Clear-signing display fields:**

| Label | Path | Resolves to | Formatter | `token_path` | Notes |
|---|---|---|---|---|---|
| "Amount to Send" | `(5, 0, 4)` | `_swapData[0].fromAmount` | `TokenAmountFormatter` | `(5, 0, 2)` → `_swapData[0].sendingAssetId` | First step, first token |
| "Minimum to Receive" | `(4,)` | `_minAmountOut` | `TokenAmountFormatter` | `(5, -1, 3)` → `_swapData[-1].receivingAssetId` | Last step's output token |
| "Recipient" | `(3,)` | `_receiver` | `AddressNameFormatter` | — | |

---

### `swapTokensMultipleV3ERC20ToNative`

**Selector:** `0x2c57e884`

```solidity
function swapTokensMultipleV3ERC20ToNative(
    bytes32 _transactionId,
    string calldata _integrator,
    string calldata _referrer,
    address payable _receiver,
    uint256 _minAmountOut,
    LibSwap.SwapData[] calldata _swapData
) external
```

| Parameter | Index | Type | Description |
|---|---|---|---|
| `_transactionId` | 0 | `bytes32` | Unique identifier for this LiFi transaction |
| `_integrator` | 1 | `string` | Name of the integrating application |
| `_referrer` | 2 | `string` | Referrer address string |
| `_receiver` | 3 | `address payable` | Final recipient of the native ETH output |
| `_minAmountOut` | 4 | `uint256` | Minimum acceptable native ETH output |
| `_swapData` | 5 | `LibSwap.SwapData[]` | Ordered array of swap steps; final step produces native ETH |

**Purpose:** Multi-step swap where input is ERC20 and output is native ETH.
Unwraps WETH at the final step and sends ETH to `_receiver`.

**Clear-signing display fields:**

| Label | Path | Resolves to | Formatter | `token_path` | Notes |
|---|---|---|---|---|---|
| "Amount to Send" | `(5, 0, 4)` | `_swapData[0].fromAmount` | `TokenAmountFormatter` | `(5, 0, 2)` → `_swapData[0].sendingAssetId` | |
| "Minimum Amount to receive" | `(4,)` | `_minAmountOut` | `TokenAmountFormatter` | — (none) | ⚠️ **No token_path**: output is native ETH — there is no ERC20 address to resolve. Formatter cannot display symbol/decimals. The value should be formatted as ETH (18 decimals) but `TokenAmountFormatter` without a token_path has no way to know that. |
| "Recipient" | `(3,)` | `_receiver` | `AddressNameFormatter` | — | |

---

### `swapTokensMultipleV3NativeToERC20`

**Selector:** `0x736eac0b`

```solidity
function swapTokensMultipleV3NativeToERC20(
    bytes32 _transactionId,
    string calldata _integrator,
    string calldata _referrer,
    address payable _receiver,
    uint256 _minAmountOut,
    LibSwap.SwapData[] calldata _swapData
) external payable
```

| Parameter | Index | Type | Description |
|---|---|---|---|
| `_transactionId` | 0 | `bytes32` | Unique identifier for this LiFi transaction |
| `_integrator` | 1 | `string` | Name of the integrating application |
| `_referrer` | 2 | `string` | Referrer address string |
| `_receiver` | 3 | `address payable` | Final recipient of the ERC20 output tokens |
| `_minAmountOut` | 4 | `uint256` | Minimum acceptable ERC20 output |
| `_swapData` | 5 | `LibSwap.SwapData[]` | Ordered array of swap steps; first step consumes `msg.value` |

**Purpose:** Multi-step swap where input is native ETH (sent as `msg.value`) and
output is an ERC20 token. Wraps ETH to WETH in the first step.

**Clear-signing display fields:**

| Label | Path | Resolves to | Formatter | `token_path` | Notes |
|---|---|---|---|---|---|
| "Amount to Send" | `ContainerPath.Value` | `msg.value` (tx ETH value) | `AmountFormatter` | — | ⚠️ **Source is transaction envelope, not calldata**: the ETH amount is not in the calldata at all. `AmountFormatter` displays it as a native ETH amount in wei. |
| "Minimum to Receive" | `(4,)` | `_minAmountOut` | `TokenAmountFormatter` | `(5, -1, 3)` → `_swapData[-1].receivingAssetId` | Last step's output ERC20 |
| "Recipient" | `(3,)` | `_receiver` | `AddressNameFormatter` | — | |

> **Note:** This function appears **twice** in the test fixture (entries at
> indices 5 and 6) with identical calldata and transaction hash — this is a
> duplicate test case.

---

### `swapTokensSingleV3ERC20ToERC20`

**Selector:** `0x4666fc80`

```solidity
function swapTokensSingleV3ERC20ToERC20(
    bytes32 _transactionId,
    string calldata _integrator,
    string calldata _referrer,
    address payable _receiver,
    uint256 _minAmountOut,
    LibSwap.SwapData calldata _swapData
) external
```

| Parameter | Index | Type | Description |
|---|---|---|---|
| `_transactionId` | 0 | `bytes32` | Unique identifier for this LiFi transaction |
| `_integrator` | 1 | `string` | Name of the integrating application |
| `_referrer` | 2 | `string` | Referrer address string |
| `_receiver` | 3 | `address payable` | Recipient of the output ERC20 token |
| `_minAmountOut` | 4 | `uint256` | Minimum acceptable output amount |
| `_swapData` | 5 | `LibSwap.SwapData` | Single swap step descriptor (not an array) |

**Purpose:** Single-step ERC20-to-ERC20 swap. More gas-efficient than the
`Multiple` variant when only one DEX hop is needed.

**Clear-signing display fields:**

| Label | Path | Resolves to | Formatter | `token_path` | Notes |
|---|---|---|---|---|---|
| "Amount to Send" | `(5, 4)` | `_swapData.fromAmount` | `TokenAmountFormatter` | `(5, 2)` → `_swapData.sendingAssetId` | Single struct (no array index) |
| "Minimum to receive" | `(4,)` | `_minAmountOut` | `TokenAmountFormatter` | `(5, 3)` → `_swapData.receivingAssetId` | |
| "Recipient" | `(3,)` | `_receiver` | `AddressNameFormatter` | — | |

---

### `swapTokensSingleV3ERC20ToNative`

**Selector:** `0x733214a3`

```solidity
function swapTokensSingleV3ERC20ToNative(
    bytes32 _transactionId,
    string calldata _integrator,
    string calldata _referrer,
    address payable _receiver,
    uint256 _minAmountOut,
    LibSwap.SwapData calldata _swapData
) external
```

| Parameter | Index | Type | Description |
|---|---|---|---|
| `_transactionId` | 0 | `bytes32` | Unique identifier for this LiFi transaction |
| `_integrator` | 1 | `string` | Name of the integrating application |
| `_referrer` | 2 | `string` | Referrer address string |
| `_receiver` | 3 | `address payable` | Recipient of the native ETH output |
| `_minAmountOut` | 4 | `uint256` | Minimum acceptable native ETH output |
| `_swapData` | 5 | `LibSwap.SwapData` | Single swap step; must produce native ETH (unwrap WETH) |

**Purpose:** Single-step swap from ERC20 to native ETH.

**Clear-signing display fields:**

| Label | Path | Resolves to | Formatter | `token_path` | Notes |
|---|---|---|---|---|---|
| "Amount to Send" | `(5, 4)` | `_swapData.fromAmount` | `TokenAmountFormatter` | `(5, 2)` → `_swapData.sendingAssetId` | |
| "Minimum Amount to receive" | `(4,)` | `_minAmountOut` | `TokenAmountFormatter` | — (none) | ⚠️ **No token_path**: output is native ETH, same issue as `swapTokensMultipleV3ERC20ToNative`. |
| "Recipient" | `(3,)` | `_receiver` | `AddressNameFormatter` | — | |

---

### `swapTokensSingleV3NativeToERC20`

**Selector:** `0xaf7060fd`

```solidity
function swapTokensSingleV3NativeToERC20(
    bytes32 _transactionId,
    string calldata _integrator,
    string calldata _referrer,
    address payable _receiver,
    uint256 _minAmountOut,
    LibSwap.SwapData calldata _swapData
) external payable
```

| Parameter | Index | Type | Description |
|---|---|---|---|
| `_transactionId` | 0 | `bytes32` | Unique identifier for this LiFi transaction |
| `_integrator` | 1 | `string` | Name of the integrating application |
| `_referrer` | 2 | `string` | Referrer address string |
| `_receiver` | 3 | `address payable` | Recipient of the output ERC20 token |
| `_minAmountOut` | 4 | `uint256` | Minimum acceptable ERC20 output |
| `_swapData` | 5 | `LibSwap.SwapData` | Single swap step; consumes `msg.value` as native ETH input |

**Purpose:** Single-step swap from native ETH to an ERC20 token.

**Clear-signing display fields:**

| Label | Path | Resolves to | Formatter | `token_path` | Notes |
|---|---|---|---|---|---|
| "Amount to send" | `ContainerPath.Value` | `msg.value` (tx ETH value) | `AmountFormatter` | — | ⚠️ **Source is transaction envelope, not calldata**: same pattern as `swapTokensMultipleV3NativeToERC20`. |
| "Minimum to Receive" | `(4,)` | `_minAmountOut` | `TokenAmountFormatter` | `(5, 3)` → `_swapData.receivingAssetId` | |
| "Recipient" | `(3,)` | `_receiver` | `AddressNameFormatter` | — | |

---

### `swapTokensGeneric`

**Selector:** `0x4630a0d8`

```solidity
function swapTokensGeneric(
    bytes32 _transactionId,
    string calldata _integrator,
    string calldata _referrer,
    address payable _receiver,
    uint256 _minAmountOut,
    LibSwap.SwapData[] calldata _swapData
) external payable
```

| Parameter | Index | Type | Description |
|---|---|---|---|
| `_transactionId` | 0 | `bytes32` | Unique identifier for this LiFi transaction |
| `_integrator` | 1 | `string` | Name of the integrating application |
| `_referrer` | 2 | `string` | Referrer address string |
| `_receiver` | 3 | `address payable` | Recipient of the final output tokens or ETH |
| `_minAmountOut` | 4 | `uint256` | Minimum acceptable output across all steps |
| `_swapData` | 5 | `LibSwap.SwapData[]` | Ordered array of swap steps (any token combination) |

**Purpose:** Protocol-agnostic multi-step swap. Accepts any combination of input
and output tokens (ERC20 or native ETH). Used when a more specific variant is
not available or when routing across heterogeneous DEX protocols.

**Clear-signing display fields:**

| Label | Path | Resolves to | Formatter | `token_path` | Notes |
|---|---|---|---|---|---|
| "Amount info" | `(5, 0, 4)` | `_swapData[0].fromAmount` | `TokenAmountFormatter` | `(5, 0, 2)` → `_swapData[0].sendingAssetId` | Note: label is "Amount info" rather than "Amount to Send" as in the other LiFi variants — likely an inconsistency. |
| "Minimum Amount to receive" | `(4,)` | `_minAmountOut` | `TokenAmountFormatter` | `(5, -1, 3)` → `_swapData[-1].receivingAssetId` | |
| "Recipient" | `(3,)` | `_receiver` | `AddressNameFormatter` | — | |

---

## 3. Uniswap V3 — SwapRouter02

**Contract:** `0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45`

All four functions accept a single calldata struct. The `fee` field specifies
the pool fee tier (e.g. `500` = 0.05%, `3000` = 0.3%, `10000` = 1%).

> **Note on `path` byte-slice indexing:** For `exactInput` and `exactOutput`,
> the swap route is encoded as a packed `bytes` value alternating 20-byte
> addresses and 3-byte fee tiers: `[tokenA (20 bytes)][fee (3 bytes)][tokenB (20 bytes)]...`.
> The path is navigated using byte-slice syntax inside the token_path:
>
> - `(0, 0, (0, 20))` → param 0 (the struct), field 0 (`path` bytes), then
>   slice `[0:20]` = the first address in the path.
> - `(0, 0, (-20,))` → same struct and field, then the last 20 bytes = the
>   final address in the path.
>
> In `exactInput` the path runs **source → destination**, so `[0:20]` = tokenIn
> and `[-20:]` = tokenOut.
>
> In `exactOutput` the path runs **destination → source** (reverse order per
> Uniswap spec), so `[0:20]` = tokenOut and `[-20:]` = tokenIn.

---

### `exactInputSingle`

**Selector:** `0x04e45aaf`

```solidity
function exactInputSingle(
    ExactInputSingleParams calldata params
) external payable returns (uint256 amountOut)
```

**`ExactInputSingleParams` struct:**

| Field | Index | Type | Description |
|---|---|---|---|
| `tokenIn` | 0 | `address` | Token being sold |
| `tokenOut` | 1 | `address` | Token being bought |
| `fee` | 2 | `uint24` | Fee tier of the pool to use |
| `recipient` | 3 | `address` | Address that receives `tokenOut` |
| `amountIn` | 4 | `uint256` | Exact amount of `tokenIn` to spend |
| `amountOutMinimum` | 5 | `uint256` | Minimum acceptable output; reverts if not met |
| `sqrtPriceLimitX96` | 6 | `uint160` | Optional price limit (0 = no limit) |

**Purpose:** Swap an exact input amount for as much output as possible through a
**single** pool. Simplest Uniswap V3 swap.

**Clear-signing display fields:**

| Label | Path | Resolves to | Formatter | `token_path` | Notes |
|---|---|---|---|---|---|
| "Send" | `(0, 4)` | `params.amountIn` | `TokenAmountFormatter` | `(0, 0)` → `params.tokenIn` | |
| "Minimum to Receive" | `(0, 5)` | `params.amountOutMinimum` | `TokenAmountFormatter` | `(0, 1)` → `params.tokenOut` | |
| "Uniswap fee" | `(0, 2)` | `params.fee` | `UnitFormatter(decimals=4, base="%", prefix=False)` | — | ⚠️ **Type/formatter mismatch**: the ABI type is `uint24` (a raw integer like `3000`), but the formatter applies 4 decimal places and a `%` suffix, rendering it as `0.3%`. The raw value must be divided by 10,000 to produce the display value — the formatter handles this scaling, not the type parser. |
| "Beneficiary" | `(0, 3)` | `params.recipient` | `AddressNameFormatter` | — | |

---

### `exactInput`

**Selector:** `0xb858183f`

```solidity
function exactInput(
    ExactInputParams calldata params
) external payable returns (uint256 amountOut)
```

**`ExactInputParams` struct:**

| Field | Index | Type | Description |
|---|---|---|---|
| `path` | 0 | `bytes` | ABI-encoded sequence of `(tokenAddress, fee, tokenAddress, fee, …)` defining the multi-hop route |
| `recipient` | 1 | `address` | Address that receives the final output token |
| `amountIn` | 2 | `uint256` | Exact amount of the first token to spend |
| `amountOutMinimum` | 3 | `uint256` | Minimum acceptable final output; reverts if not met |

**Purpose:** Swap an exact input amount through a **multi-hop** path (two or more
pools in sequence). The `path` bytes encode consecutive pool hops.

**Clear-signing display fields:**

| Label | Path | Resolves to | Formatter | `token_path` | Notes |
|---|---|---|---|---|---|
| "Amount to Send" | `(0, 2)` | `params.amountIn` | `TokenAmountFormatter` | `(0, 0, (0, 20))` → `params.path[0:20]` (tokenIn) | Byte-slice extracts the first address from the packed path |
| "Minimum to Receive" | `(0, 3)` | `params.amountOutMinimum` | `TokenAmountFormatter` | `(0, 0, (-20,))` → `params.path[-20:]` (tokenOut) | Byte-slice extracts the last address from the packed path |
| "Beneficiary" | `(0, 1)` | `params.recipient` | `AddressNameFormatter` | — | |

---

### `exactOutputSingle`

**Selector:** `0x5023b4df`

```solidity
function exactOutputSingle(
    ExactOutputSingleParams calldata params
) external payable returns (uint256 amountIn)
```

**`ExactOutputSingleParams` struct:**

| Field | Index | Type | Description |
|---|---|---|---|
| `tokenIn` | 0 | `address` | Token being sold |
| `tokenOut` | 1 | `address` | Token being bought |
| `fee` | 2 | `uint24` | Fee tier of the pool to use |
| `recipient` | 3 | `address` | Address that receives `tokenOut` |
| `amountOut` | 4 | `uint256` | Exact amount of `tokenOut` to receive |
| `amountInMaximum` | 5 | `uint256` | Maximum amount of `tokenIn` allowed to spend |
| `sqrtPriceLimitX96` | 6 | `uint160` | Optional price limit (0 = no limit) |

**Purpose:** Spend as little input as possible to receive an **exact output**
amount through a **single** pool. Useful when the output quantity must be
precise (e.g. buying exactly N tokens).

**Clear-signing display fields:**

| Label | Path | Resolves to | Formatter | `token_path` | Notes |
|---|---|---|---|---|---|
| "Maximum Amount In" | `(0, 5)` | `params.amountInMaximum` | `TokenAmountFormatter` | `(0, 0)` → `params.tokenIn` | |
| "Amount to Receive" | `(0, 4)` | `params.amountOut` | `TokenAmountFormatter` | `(0, 1)` → `params.tokenOut` | |
| "Uniswap fee" | `(0, 2)` | `params.fee` | `UnitFormatter(decimals=4, base="%", prefix=False)` | — | ⚠️ **Type/formatter mismatch**: same as `exactInputSingle` — `uint24` raw value scaled to percentage by the formatter. |
| "Beneficiary" | `(0, 3)` | `params.recipient` | `AddressNameFormatter` | — | |

---

### `exactOutput`

**Selector:** `0x09b81346`

```solidity
function exactOutput(
    ExactOutputParams calldata params
) external payable returns (uint256 amountIn)
```

**`ExactOutputParams` struct:**

| Field | Index | Type | Description |
|---|---|---|---|
| `path` | 0 | `bytes` | ABI-encoded route, specified in **reverse** order (output token first) |
| `recipient` | 1 | `address` | Address that receives the final output token |
| `amountOut` | 2 | `uint256` | Exact amount of the output token to receive |
| `amountInMaximum` | 3 | `uint256` | Maximum amount of input token allowed to spend |

**Purpose:** Spend as little input as possible to receive an **exact output**
amount through a **multi-hop** path. Note: `path` is encoded in reverse
(destination → source) compared to `exactInput`.

**Clear-signing display fields:**

| Label | Path | Resolves to | Formatter | `token_path` | Notes |
|---|---|---|---|---|---|
| "Maximum Amount In" | `(0, 3)` | `params.amountInMaximum` | `TokenAmountFormatter` | `(0, 0, (-20,))` → `params.path[-20:]` (tokenIn) | Because path is **reversed**, the last 20 bytes are the input token |
| "Amount to Receive" | `(0, 2)` | `params.amountOut` | `TokenAmountFormatter` | `(0, 0, (0, 20))` → `params.path[0:20]` (tokenOut) | Because path is **reversed**, the first 20 bytes are the output token |
| "Beneficiary" | `(0, 1)` | `params.recipient` | `AddressNameFormatter` | — | |

---

## Summary Table

| # | Test Name | Protocol | Function | Selector | Contract |
|---|---|---|---|---|---|
| 1 | `clear_sign_1inch_swap` | 1inch V6 | `swap` | `0x07ed2379` | `0x1111...a65` |
| 2 | `clear_sign_1inch_unoswap` | 1inch V6 | `unoswap` | `0x83800a8e` | `0x1111...a65` |
| 3 | `clear_sign_1inch_unoswapTo` | 1inch V6 | `unoswapTo` | `0xe2c95c82` | `0x1111...a65` |
| 4 | `clear_sign_lifi_swapTokensMultipleV3ERC20ToERC20` | LiFi | `swapTokensMultipleV3ERC20ToERC20` | `0x5fd9ae2e` | `0x1231...aE` |
| 5 | `clear_sign_lifi_swapTokensMultipleV3ERC20ToNative` | LiFi | `swapTokensMultipleV3ERC20ToNative` | `0x2c57e884` | `0x1231...aE` |
| 6 | `clear_sign_lifi_swapTokensMultipleV3NativeToERC20` *(×2)* | LiFi | `swapTokensMultipleV3NativeToERC20` | `0x736eac0b` | `0x1231...aE` |
| 7 | `clear_sign_lifi_swapTokensSingleV3ERC20ToERC20` | LiFi | `swapTokensSingleV3ERC20ToERC20` | `0x4666fc80` | `0x1231...aE` |
| 8 | `clear_sign_lifi_swapTokensSingleV3ERC20ToNative` | LiFi | `swapTokensSingleV3ERC20ToNative` | `0x733214a3` | `0x1231...aE` |
| 9 | `clear_sign_lifi_swapTokensSingleV3NativeToERC20` | LiFi | `swapTokensSingleV3NativeToERC20` | `0xaf7060fd` | `0x1231...aE` |
| 10 | `clear_sign_lifi_swapTokensGeneric` | LiFi | `swapTokensGeneric` | `0x4630a0d8` | `0x1231...aE` |
| 11 | `clear_sign_uniswap_exactInput` | Uniswap V3 | `exactInput` | `0xb858183f` | `0x68b3...c45` |
| 12 | `clear_sign_uniswap_exactInputSingle` | Uniswap V3 | `exactInputSingle` | `0x04e45aaf` | `0x68b3...c45` |
| 13 | `clear_sign_uniswap_exactOutput` | Uniswap V3 | `exactOutput` | `0x09b81346` | `0x68b3...c45` |
| 14 | `clear_sign_uniswap_exactOutputSingle` | Uniswap V3 | `exactOutputSingle` | `0x5023b4df` | `0x68b3...c45` |
