
# extmod/modtrezorutils/modtrezorutils.c
def memcpy(dst: bytearray, dst_ofs: int,
           src: bytearray, src_ofs: int,
           n: int) -> int:
    '''
    Copies at most `n` bytes from `src` at offset `src_ofs` to
    `dst` at offset `dst_ofs`.  Returns the number of actually
    copied bytes.
    '''

# extmod/modtrezorutils/modtrezorutils.c
def halt(msg: str = None) -> None:
    '''
    Halts execution.
    '''
