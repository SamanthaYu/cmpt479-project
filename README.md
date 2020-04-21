# CMPT 479 Project - ROPHunter

## Setup
- We'll disable ASLR:
```
sudo sysctl -w kernel.randomize_va_space=0
```

- We'll be running the following instructions within a Python virtualenv:
```
python3 -m venv venv
source venv/bin/activate
```

- Install all necessary requirements:
```
pip install -r requirements.txt
```

## Find Base Address of libc
- In this attack, we'll assume that libc is not statically linked to the executable
- We can run `ldd examples/vuln` to find this base address:
```
	linux-gate.so.1 =>  (0xb7fd9000)
	libc.so.6 => /lib/i386-linux-gnu/libc.so.6 (0xb7e09000)
	/lib/ld-linux.so.2 (0xb7fdb000)
```
In this example, libc's base address is `0xb7e09000`

## How to Find Gadgets
```
python3 rop.py <binary> <architecture> <mode>
```
For example:
```
python3 rop.py /lib/i386-linux-gnu/libc-2.23.so x86 32
```

## How to Create an ROP Chain
- We create an ROP chain to launch a shell and insert that ROP chain into a buffer overflow in `examples/vuln.c`
```
python3 examples/gen_shellcode.py <rophunter_path> <libc_offset>
```
For example:
```
python3 examples/gen_shellcode.py gadgets/x86_32/libc_rophunter.txt 0xb7e09000
```

## How to Run ROPgadget
```
ROPgadget --binary <libc_path> --rawArch x86 --rawMode 32
```

## How to Evaluate Gadgets Found by ROPgadget vs. ROPHunter
```
python3 evaluate_rop.py <ropgadget_path> <rophunter_path>
```

For example:
```
python3 evaluate_rop.py gadgets/x86_32/libc_ropgadget.txt gadgets/x86_32/libc_rophunter.txt
```

- `evaluation/matches.txt` and `evaluation/mismatches.txt` correspond to gadgets that both ROPgadget and ROPHunter found at the same address.
- `evaluation/false_positives.txt` refers to gadgets that only ROPHunter found
- `evaluation/false_negatives.txt` refers to gadgets that only ROPgadget found
