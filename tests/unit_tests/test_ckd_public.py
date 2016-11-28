import common
import unittest

from trezorlib import ckd_public


class TestCkdPublic(unittest.TestCase):

    def test_ckd(self):
        xpub1 = 'xpub661MyMwAqRbcEnKbXcCqD2GT1di5zQxVqoHPAgHNe8dv5JP8gWmDproS6kFHJnLZd23tWevhdn4urGJ6b264DfTGKr8zjmYDjyDTi9U7iyT'
        node1 = ckd_public.deserialize(xpub1)
        node2 = ckd_public.public_ckd(node1, [0])
        node3 = ckd_public.public_ckd(node1, [0, 0])
        xpub2 = ckd_public.serialize(node2)
        xpub3 = ckd_public.serialize(node3)
        self.assertEqual(xpub2, 'xpub67ymn1YTdE2iSGXitxUEZeUdHF2FsejJATroeAxVMtzTAK9o3vjmFLrE7TqE1X76iobkVc3p8h3gNzNRTwPeQGYW3CCmYCG8n5ThVkXaQzs')
        self.assertEqual(xpub3, 'xpub6BD2MwdEg5PJPqiGetL9DJs7oDo6zP3XwAABX2vAQb5eLpY3QhHGUEm25V4nkQhnFMsqEVfTwtax2gKz8EFrt1PnBN6xQjE9jGmWDR6modu')


if __name__ == '__main__':
    unittest.main()
