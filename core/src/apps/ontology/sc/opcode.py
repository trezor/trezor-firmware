# OpCode constants
# An empty array of bytes is pushed onto the stack.
PUSH0 = 0x00
PUSHBYTES75 = 0x4B
# The next byte contains the number of bytes to be pushed onto the stack.
PUSHDATA1 = 0x4C
# The next two bytes contain the number of bytes to be pushed onto the stack.
PUSHDATA2 = 0x4D
# The next four bytes contain the number of bytes to be pushed onto the stack.
PUSHDATA4 = 0x4E
# The number -1 is pushed onto the stack.
PUSHM1 = 0x4F
# The number 1 is pushed onto the stack.
PUSH1 = 0x51

# Flow control
SYSCALL = 0x68
DUPFROMALTSTACK = 0x6A

# Stack
# Puts the input onto the top of the alt stack. Removes it from the main stack.
TOALTSTACK = 0x6B
# Puts the input onto the top of the main stack. Removes it from the alt stack.
FROMALTSTACK = 0x6C
# The top two items on the stack are swapped.
SWAP = 0x7C

# Array
PACK = 0xC1
NEWSTRUCT = 0xC6
APPEND = 0xC8
