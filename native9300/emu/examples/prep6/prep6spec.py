# asmcmp.py's spec: random triangles (small, medium, huge; ties in y come often with the small ones) for
# prep6 (C) and r3_prep6 (ARM assembly); the 64-byte record and the result compared.
import struct
FUNCS = ("emu_prep6_c", "emu_prep6_asm")
S, RECIP, REC = 0x2000000, 0x2010000, 0x2000400

def case(rnd, emu):
    if not getattr(emu, "_recip", False):
        emu.write(RECIP, b"".join(struct.pack("<i", (1 << 30) // i if i else 1 << 30) for i in range(8192)))
        emu._recip = True
    s = [0] * 40
    W, H = rnd.choice((320, 400, 640)), 200
    cx, cy = rnd.randrange(W + 40) - 20, rnd.randrange(H + 30) - 15
    sz = rnd.choice((3 + rnd.randrange(12), 10 + rnd.randrange(32), 3 + rnd.randrange(3000)))
    for i in range(3):
        s[i] = cx + rnd.randrange(sz) - sz // 2; s[8 + i] = cy + rnd.randrange(sz) - sz // 2
        s[24 + i] = rnd.randrange(70000) - 20000; s[32 + i] = rnd.randrange(70000) - 20000
    emu.write(S, struct.pack("<40i", *s))
    emu.write(REC, b"\xcd" * 64)
    return (S, rnd.randrange(2) | H << 16, RECIP, REC), [(REC, 64)]

def count(r): return r == 0        # the records made (not the early outs)
def outs_if(r): return r == 0       # the record is only made then (r3_prep6 may write ymin, ymax first)
