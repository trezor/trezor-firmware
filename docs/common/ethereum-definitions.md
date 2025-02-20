# Ethereum definitions

For support of the huge number of EVM chains (networks) and ERC-20 tokens, Trezor needs
to know parameters of those networks and tokens, namely:

* currency symbol and number of decimal places, to correctly display amounts,
* SLIP44 identifier to unlock the appropriate BIP-32 subtrees.

A subset of Ethereum definitions is built into the firmware image. The rest is generated
externally and must be sent to Trezor as a signed blob.

## Built-in definitions

The set of built-in definitions is declared in the following files:
* networks - [`networks.json`](https://github.com/trezor/trezor-firmware/blob/master/common/defs/ethereum/networks.json)
* tokens - [`tokens.json`](https://github.com/trezor/trezor-firmware/blob/master/common/defs/ethereum/tokens.json)

These definitions need to be modified manually.

## External definitions

A full list of Ethereum definitions is compiled from multiple sources and is available
[in a separate repository](https://github.com/trezor/definitions).

From this list, a collection of binary blobs is generated, signed, and made available
online.

A given Trezor firmware will only accept signed definitions newer than a certain date,
typically one month before firmware release. This means that a client application should
either always fetch fresh definitions from the official URLs, or refresh its local copy
frequently.

### Retrieving the definitions

The base URL for the definitions is `https://data.trezor.io/firmware/eth-definitions/`.

#### Known chain ID

To look up a network definition by its chain ID, use the following URL:

`https://data.trezor.io/firmware/eth-definitions/chain-id/<CHAIN_ID>/network.dat`

`<CHAIN_ID>` is a decimal number, e.g., `1` for Ethereum mainnet.

To look up a token definition for a given chain ID and token address, use the following URL:

`https://data.trezor.io/firmware/eth-definitions/chain-id/<CHAIN_ID>/token-<TOKEN_ADDRESS>.dat`

`<CHAIN_ID>` is again a decimal number.<br>
`<TOKEN_ADDRESS>` is all lowercase (no checksum) token address hex without the `0x` prefix.

E.g., this is the URL for Görli TST token:
[https://data.trezor.io/firmware/eth-definitions/chain-id/5/token-7af963cf6d228e564e2a0aa0ddbf06210b38615d.dat]


#### Unknown chain ID

Certain Ethereum calls, such as `EthereumGetAddress` and `EthereumSignMessage`, do not
require the caller to know the chain ID, because their results do not depend on it.

For this situation, it is possible to look up a network definition by a SLIP-44
identifier on the following URL:

`https://data.trezor.io/firmware/eth-definitions/slip44/<SLIP44_ID>/network.dat`

`<SLIP44_ID>` is a decimal number, e.g., `60` for Ethereum mainnet.

In some cases, multiple network definitions can be registered for the same SLIP-44
number. The retrieved definition is valid for an unspecified one of those colliding
networks. This does not matter for purposes of `EthereumGetAddress` and the like,
because the information in the network definition is only used to prove validity of the
derivation path.

When using Ethereum's SLIP-44 number 60 in the derivation path, the caller does not need
to provide the network definition, because Ethereum network is always built-in.

### Full set of definitions

It is possible to download the full set of signed definitions in a single tar archive
from the following URL:

[`https://data.trezor.io/firmware/eth-definitions/definitions.tar.xz`](https://data.trezor.io/firmware/eth-definitions/definitions.tar.xz).

## Definition format

Each definition is encoded as a protobuf message `EthereumNetworkInfo` or
`EthereumTokenInfo` and packaged in the following binary format.

All numbers are unsigned little endian.

1. magic string `trzd1` (5 bytes)
2. definition type according to `DefinitionType` enum (1 byte)
3. data version of the definition (4 bytes)
4. protobuf payload length (2 bytes)
5. protobuf payload (N bytes)

A Merkle tree is constructed from all binary definitions (see below) and its root is
signed by the CoSi algorithm.

The full format of the definition is as follows:

1. Data payload (see above)
2. Number of Merkle proof entries (1 byte)
3. Sequence of 32-byte proof entries (N * 32 bytes)
4. CoSi sigmask (1 byte)
5. CoSi signature (64 bytes)

### Merkle tree algorithm

The input for the Merkle tree calculation is a collection of binary values.

1. For each entry, calculate a _leaf hash_: `SHA256(0x00 || entry)`, with `||` denoting
   string concatenation.
2. Sort the leaf hashes lexicographically in ascending order. This is the base level of
   a binary tree.
3. For each level of the tree, build the next level by taking a pair of entries from the
   left and calculating an _internal hash_:
   a. Set `min` to the smaller of the two entries, and `max` to the larger one.
   b. The internal hash is `SHA256(0x01 || min || max)`.
4. If there is a left-over odd entry, append it to the end of the next level.
5. Continue until there is only one entry left. This is the root hash.

For each leaf, its proof is a sequence of neighbor hashes going up the tree. One way to
keep track of the proof is, whenever constructing an internal node, add the right hash
to the left child's proof list and vice versa.

A [reference implementation](https://github.com/trezor/trezor-firmware/blob/master/python/src/trezorlib/merkle_tree.py) is provided.

## Data sources

External Ethereum definitions are generated based on data from external APIs and repositories:

* [CoinGecko](https://www.coingecko.com/) for most of the info about networks and tokens
* [defillama](https://defillama.com/) to pair as much networks as we can to CoinGecko ID
* [Ethereum Lists - chains](https://github.com/ethereum-lists/chains) as the only source of EVM-based networks
* [Ethereum Lists - tokens](https://github.com/ethereum-lists/tokens) as another source of tokens
