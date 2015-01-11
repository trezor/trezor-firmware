cimport c
cimport cython

cdef class HDNode:

	cdef c.HDNode node

	def __init__(self, str serialized = None, HDNode copyfrom = None):
		if copyfrom is not None:
			self.node = copyfrom.node
		elif serialized is not None:
			if c.hdnode_deserialize(serialized, cython.address(self.node)) != 0:
				raise Exception('Invalid xpub/xprv provided')
		else:
			raise Exception('Need to provide serialized or node parameter')

	def xpub(self):
		cdef char[120] string
		c.hdnode_serialize_public(cython.address(self.node), string, 120)
		return str(string)

	def xprv(self):
		cdef char[120] string
		c.hdnode_serialize_private(cython.address(self.node), string, 120)
		return str(string)

	def address(self):
		cdef char[40] string
		c.ecdsa_get_address(self.node.public_key, 0, string, 40)
		return str(string)

	def public_ckd(self, int i):
		x = HDNode(copyfrom=self)
		c.hdnode_public_ckd(cython.address(x.node), i)
		return x

	def private_ckd(self, int i):
		x = HDNode(copyfrom=self)
		c.hdnode_private_ckd(cython.address(x.node), i)
		return x
