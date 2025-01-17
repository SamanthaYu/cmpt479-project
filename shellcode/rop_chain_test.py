from rop_chain import ROPChain
import unittest

class ROPChainTest(unittest.TestCase):
    def test_xchg_gadget(self):
        rop_chain = ROPChain("rop_file")
        start_offset = 0x1000
        gadget_bytes = "c3/9545/000f/0000"
        gadget_suffix = "xchg eax, ebp ; ret ;" # Corresponds to "c3/9545"

        actual_addr = rop_chain.get_gadget_addr(start_offset, gadget_bytes, gadget_suffix)
        expected_addr = 0x1004
        self.assertEqual(hex(actual_addr), hex(expected_addr))

    def test_pop_gadget(self):
        rop_chain = ROPChain("rop_file")
        start_offset = 0x2bc66
        gadget_bytes = "c3/5a/59/08e864ffffff"
        gadget_suffix = "pop ecx ; pop edx ; ret ;"

        actual_addr = rop_chain.get_gadget_addr(start_offset, gadget_bytes, gadget_suffix)
        expected_addr = 0x2BC6C
        self.assertEqual(hex(actual_addr), hex(expected_addr))

if __name__ == '__main__':
    unittest.main()