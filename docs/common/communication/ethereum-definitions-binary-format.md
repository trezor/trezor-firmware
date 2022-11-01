# Ethereum definition binary format

Definitions are binary encoded and have a special format:
1. prefix:
   1. format version of the definition (ASCII string `trzdX`, where `X` is version number, 5 bytes)
   2. type of data (unsigned integer, 1 byte)
   3. data version of the definition (unsigned integer, 4 bytes)
   4. length of the encoded protobuf message - payload length in bytes (unsigned integer, 2 bytes)
2. payload: serialized form of protobuf message EthereumNetworkInfo or EthereumTokenInfo (N bytes)
3. suffix:
   1. length of the Merkle tree proof - number of hashes in the proof (unsigned integer, 1 byte)
   2. proof - individual hashes used to compute Merkle tree root hash (plain bits, N*32 bytes)
   3. signed Merkle tree root hash (plain bits, 64 bytes)

This complete format must be used when definition is send to the device, but we generate definitions
without parts 3.1 (Merkle tree proof length) and 3.2 (proof itself). For more information look
at the [External definitions documentation](../ethereum-definitions.md#external-definitions)
