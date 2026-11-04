#!/usr/bin/env python3
"""Two functions of one emulator image (usually assembly and its C reference) on the same random
inputs: the results and the memory they write must match to the bit; instructions per call of each.
Build the image with build_emu.sh (a driver giving both as extern "C" entry points), then

    python3 asmcmp.py emu.exe emu.sym spec.py [cases] [seed]

spec.py (see examples/prep6/prep6spec.py) gives
    FUNCS = ("ref_entry", "asm_entry")        # called with the same arguments
    def case(rnd, emu): ...                   # writes one case's inputs into memory (from 0x2000000),
                                              # returns (args, outs): up to 4 int arguments, and the
                                              # [(address, bytes)] to compare after each call
    def count(r): ...                         # optional: count this call's instructions? (default: all)
    def outs_if(r): ...                       # optional: compare the memory only for this result
                                              # (default: always; the results are always compared)
Each case is written afresh before each call (same seed), so a function can't pass on the other's
output. Stops at the first 5 differences, printing the case number and seed to replay it."""
import sys, random, importlib.util, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from armemu import Emu

def main():
    exe, sym, specf = sys.argv[1:4]
    n = int(sys.argv[4]) if len(sys.argv) > 4 else 2000
    seed = int(sys.argv[5]) if len(sys.argv) > 5 else 1
    sp = importlib.util.spec_from_file_location("spec", specf)
    spec = importlib.util.module_from_spec(sp); sp.loader.exec_module(spec)
    count = getattr(spec, "count", lambda r: True)
    outs_if = getattr(spec, "outs_if", lambda r: True)
    e = Emu(exe, sym)
    e.call("emu_init")
    tot = {f: [0, 0] for f in spec.FUNCS}
    bad = 0
    for k in range(n):
        got = []
        for f in spec.FUNCS:
            rnd = random.Random(seed * 1000003 + k)
            args, outs = spec.case(rnd, e)
            r, ins = e.call(f, *args)
            got.append((r, [e.read(a, l) for a, l in outs] if outs_if(r) else None))
            if count(r): tot[f][0] += ins; tot[f][1] += 1
        if any(g != got[0] for g in got[1:]):
            bad += 1
            print("case %d (seed %d): %s" % (k, seed, " / ".join("%s r0 %d" % (f, g[0]) for f, g in zip(spec.FUNCS, got))))
            if bad >= 5: break
    for f in spec.FUNCS:
        c, m = tot[f]
        print("%-20s %8.1f instructions a call (%d calls counted)" % (f, c / max(m, 1), m))
    print("%d cases, %d differences" % (k + 1, bad))
    sys.exit(1 if bad else 0)

main()
