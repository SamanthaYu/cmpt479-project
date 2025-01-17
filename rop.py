import argparse
from capstone import *
from elftools.elf.elffile import ELFFile
import pygtrie

import multiprocessing as mp
import os

DEBUG = True

# Debugging
def log(s):
    if DEBUG:
        print(s)

def accResults(result):
    log("exit worker")


class ROPHunter:
    def __init__(self, arch, mode, parallel):
        # TODO: Customize the max inst length for other architectures
        self.max_inst_len = 15
        self.max_inst_per_gadget = 3
        self.inst_trie = pygtrie.StringTrie()

        # Used to keep track of the starting addresses of the gadgets
        self.inst_addr_dict = dict()

        # initialize python class for capstone
        self.md = Cs(arch, mode)

        # Initialize prev_inst to null; used to find boring instructions
        self.prev_inst = "0"

        # Whether to run serial or parallel version
        self.parallel = parallel
        self.num_gadgets = 0

    def read_binary(self, file_path):
        with open(file_path, "rb") as f:
            bin_file = ELFFile(f)
            bin_text = bin_file.get_section_by_name('.text')
            bin_addr = bin_text["sh_addr"]
            bin_data = bin_text.data()
        return [bin_addr, bin_data]

    # Print entire gadget starting at instr_key
    def print_gadget(self, instr_key):
        self.num_gadgets += 1
        gadget_str = ""
        prefixes = self.inst_trie.prefixes(instr_key) 

        # Go back up the branch
        for prefix in prefixes:
            gadget_str = prefix.value.strip() + " ; " + gadget_str

        gadget_str = self.inst_addr_dict[instr_key] + " : " + instr_key + " | " + gadget_str
        print(gadget_str)

    def get_inst_str(self, disas_inst):
        return disas_inst[2] + " " + disas_inst[3]

    def get_inst_trie(self):
        return self.inst_trie

    def get_inst_addr_dict(self):
        return self.inst_addr_dict

    def is_inst_boring(self, disas_instr):
        if disas_instr[2] == "ret" or disas_instr[2] == "jmp":
            self.prev_inst = disas_instr[2]
            return True

        if disas_instr[2] == "leave" and self.prev_inst == "ret":
            self.prev_inst = disas_instr[2]
            return True

        if self.get_inst_str(disas_instr) == "pop rbp" and self.prev_inst == "ret":
            self.prev_inst = disas_instr[2]
            return True

        self.prev_inst = disas_instr[2]
        return False

    def is_gadget_duplicate(self, trie_key, disas_inst):
        
        if self.inst_trie.has_key(trie_key):
            if self.inst_trie[trie_key] == self.get_inst_str(disas_inst):
                return True
        return False

    def build_from(self, duplicates, output, code, pos, parent, ret_offset):
        for step in range(1, self.max_inst_len):
            inst = code[pos - step : pos - 1]
            if pos - step >= pos - 1:
                continue

            if pos - step < 0:
                continue

            num_inst = 0

            for i in self.md.disasm_lite(inst, ret_offset - step + 1):
                # disas_inst is a tuple of (address, size, mnemonic, op_str)
                disas_inst = i
                num_inst += 1
                if num_inst > 1:
                    break

            # We want to extract single instructions, so this part will only be entered if disasm finds valid instructions
            if num_inst == 1:
                trie_key = parent + "/" + inst.hex()

                # If we don't restrict the number of instructions per gadget, the number of paths to explore explodes
                if trie_key.count('/') > self.max_inst_per_gadget:
                    break

                if not self.is_inst_boring(disas_inst) and (duplicates or not self.is_gadget_duplicate(trie_key, disas_inst)):
                    self.inst_trie[trie_key] = self.get_inst_str(disas_inst)
                    self.inst_addr_dict[trie_key] = hex(disas_inst[0])

                    if(output):
                        self.print_gadget(trie_key)
                    self.build_from(duplicates, output, code, pos - step + 1, trie_key, disas_inst[0])

    def galileo(self, duplicates, output, start_offset, code):
        if self.parallel:
            return self.galileo_parallel(duplicates, output, start_offset, code)
        else:
            return self.galileo_serial(duplicates, output, start_offset, code)

    def galileo_serial(self, duplicates, output, start_offset, code):
        # place root c3 in the trie (key: c3, value: ret)
        self.inst_trie["c3"] = "ret"

        for i in range(0, len(code)):
            if code[i:i+1] == b"\xc3":
                self.prev_inst = "ret"
                self.build_from(duplicates, output, code, i + 1, "c3", start_offset + i)

        if output:
            print("Total gadgets found: " + str(self.num_gadgets) + "\n")

        return 

    def galileo_parallel(self, duplicates, output, start_offset, code):
        # determine num of cpus on machine for optimal parallelism
        N = mp.cpu_count()
        print("running on galileo in parallel on " + str(N) + " cpus:\n")
        
        # place root c3 in the trie (key: c3, value: ret)
        self.inst_trie["c3"] = "ret"

        with mp.Pool(processes=4, maxtasksperchild=1) as p:
            for i in range(0, len(code)):
                if code[i:i+1] == b"\xc3":
                    log("worker " + str(i) + "\n")
                    self.prev_inst = "ret"
                    result = p.apply_async(self.build_from, (duplicates, output, code, i + 1, "c3", start_offset + i,), callback=accResults)
                    result.get(timeout = 30)
                    log("finished function")
            p.close()
            p.join()
        return 

   
if __name__ == "__main__":
    # TODO: Add more architectures
    arch_dict = {
        "x86": CS_ARCH_X86
    }

    mode_dict = {
        "16": CS_MODE_16,
        "32": CS_MODE_32,
        "64": CS_MODE_64
    }

    arg_parser = argparse.ArgumentParser(description="Find ROP gadgets within a binary file")
    arg_parser.add_argument("--binary", help="File path of the binary executable", required=True)
    arg_parser.add_argument("--arch", help="Hardware architecture", choices=arch_dict.keys(), required=True)
    arg_parser.add_argument("--mode", help="Hardware mode", choices=mode_dict.keys(), required=True)
    arg_parser.add_argument("--parallel", help="Enable parallelism", action="store_true")
    arg_parser.add_argument("--output", help="Print gadgets to stdout", action="store_true")
    arg_parser.add_argument("--duplicates", help="Include duplicate gadgets, enabling slows down performance", action="store_true")
    args = arg_parser.parse_args()

    rop_hunter = ROPHunter(arch_dict[args.arch], mode_dict[args.mode], args.parallel)

    [start_offset, code] = rop_hunter.read_binary(args.binary)

    rop_hunter.galileo(args.duplicates, args.output, start_offset, code)
   