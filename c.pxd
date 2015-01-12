from libc.stdint cimport uint32_t, uint8_t

cdef extern from "bip32.h":

	ctypedef struct HDNode:
		uint8_t public_key[33]

	int hdnode_from_seed(const uint8_t *seed, int seed_len, HDNode *out)

	int hdnode_private_ckd(HDNode *inout, uint32_t i)

	int hdnode_public_ckd(HDNode *inout, uint32_t i)

	void hdnode_serialize_public(const HDNode *node, char *str, int strsize)

	void hdnode_serialize_private(const HDNode *node, char *str, int strsize)

	int hdnode_deserialize(const char *str, HDNode *node)

cdef extern from "ecdsa.h":

	void ecdsa_get_address(const uint8_t *pub_key, uint8_t version, char *addr, int addrsize)
