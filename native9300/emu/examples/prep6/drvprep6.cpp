// The emulator driver for asmcmp.py: Maps 9300's prep6 (dsp/prep6.inc, C) against r3_prep6 (dsp/prep6asm.inc,
// ARM assembly), the ARM's half of the 3D view split with the DSP (dspprobe 12-14). r3_texgrad comes from
// Maps' src/r3dgeo.c (build_prep6.sh compiles it with the driver).
#include "r3dgeo.h"
static char* gHeap = (char*) 0x400000;
void* operator new(unsigned int n) { void* p = gHeap; gHeap += (n + 7) & ~7; return p; }
void operator delete(void*) {}
extern "C" void __pure_virtual() {}
extern "C" void* memset(void* d, int c, unsigned int n) { char* p = (char*) d; while (n--) *p++ = (char) c; return d; }
extern "C" void* memcpy(void* d, const void* s, unsigned int n) { char* p = (char*) d; const char* q = (const char*) s; while (n--) *p++ = *q++; return d; }
extern "C" {
#include "prep6.inc"
#include "prep6asm.inc"
int r3_prep6(const int* aS, const int* aRecip, unsigned short* aRec, int aDownH);
int emu_init() { return 0; }
// the same arguments for both: the polygon, down | H << 16, the reciprocals, the record
int emu_prep6_c(const int* s, int downH, const int* recip, unsigned short* rec) { return prep6(s, downH & 1, downH >> 16, recip, rec); }
int emu_prep6_asm(const int* s, int downH, const int* recip, unsigned short* rec) { return r3_prep6(s, recip, rec, downH); }
}
