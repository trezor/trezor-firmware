# Ethereum definition binary format

Definitions are binary encoded and have a special format:
1. prefix:
   1. format version of the definition (UTF-8 string `trzd` + version number, padded with zeroes if shorter, 8 bytes)
   2. type of data (unsigned integer, 1 byte)
   3. data version of the definition (unsigned integer, 4 bytes)
   4. length of the encoded protobuf message - payload length in bytes (unsigned integer, 2 bytes)
2. payload: serialized form of protobuf message EthereumNetworkInfo or EthereumTokenInfo (N bytes)
3. suffix:
   1. length of the Merkle tree proof - number of hashes in the proof (unsigned integer, 1 byte)
   2. proof - individual hashes used to compute Merkle tree root hash (plain bits, N*32 bytes)
   3. signed Merkle tree root hash (plain bits, 64 bytes)
