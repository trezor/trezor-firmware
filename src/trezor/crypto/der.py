def convert_length(l: int):
    if l < 0x80:
       return bytes([l])
    elif l <= 0xFF:
       return bytes([0x81, l])
    elif l <= 0xFFFF:
       return bytes([0x82, l & 0xFF, l >> 8])
    else:
       raise ValueError

def convert_int(i: bytes):
    i = i.lstrip(b'\x00')
    if i[0] >= 0x80:
        i = b'\x00' + i
    return b'\x02' + convert_length(len(i)) + i

def convert_seq(seq: tuple):
    res = b''
    for i in seq:
        res += convert_int(i)
    return b'\x30' + convert_length(len(res)) + res
