# Native Symbian C++ on the Nokia 9300: GCC 2.9 pitfalls and ARM speed-ups

These notes come from building Maps 9300 (`maps9300/`, versions 0.11–1.19) as a native Series 80 v2
app (Symbian 7.0s, EKA1) with the SDK's GCC 2.9 (`arm-epoc-pe-gcc`, target `armi`, `-O2`). They
apply to any native app or DLL for the 9300/9500. Each item gives what you see, why it happens,
and what to do. The code mentioned is in `maps9300/src` and `maps9300/test`.

The phone: TI OMAP1510, an ARM925T core at 150 MHz (ARMv4T: no `CLZ`, `SMULxy`, `QADD`, ...),
no FPU, 16 KB instruction / 8 KB data cache (16-byte lines), slow RAM. The compiler's `armi` target
is ARMv4, and it is a 1999 compiler: it crashes on some valid code and makes slow code from much more.

## 0. What's in this folder (`symbian-s80-build-tools/native9300/`)

The build tools and what Maps 9300 found, for other native 9300 apps. The code in `lib/` and
`emu/examples/` are snapshots (1.19); the live copies are in `maps9300/`. What is Mapy.com's (its
API and formats, the 3D tiles, places) stays in `maps9300/` (`docs/mapy-api.md`, `docs/3d-view.md`).

| Where | What |
|---|---|
| `../toolchain/setup_eka1_toolchain.sh`, `setup_s80_sdk.sh` | The EKA1 GCC 2.9 toolchain and the Series 80 SDK on a Linux PC |
| `../toolchain/setup_vm_noroot.sh`, `symenv.sh.example` | The same in a shell with no root and ~45 s a command (staged; section 8) |
| `../toolchain/build_s80.sh` | Build any S80 app: `SYM=~/sym build_s80.sh <project> <name>` (group/ with bld.inf, sis/<name>.pkg.in) |
| `emu/armemu.py`, `build_emu.sh`, `drv_template.cpp`, `example.py` | Run phone code (GCC 2.9 armi -O2) in the Unicorn ARM emulator: instruction counts per call and function, hot blocks, the 8 KB data-cache model, faults with their function (section 5) |
| Other emulator tests | `mp4player9300/tools/armemu/` (the video decoders: `run.py decode|profile|colour|h264`), `webbrowser9300/browser9300/test/armtest.sh` (the browser's `igarm.c`), `lib/fastmem/test/` |
| `emu/examples/` | Maps 9300's drivers and scripts: renderer scenes asm vs C (`drv.cpp`, `emu75.py`), whole 3D frames from scene dumps (`drvvts.cpp`, `emuvts.py`), the JPEG decoder (`drvdec.cpp`, `emudec.py`, `emujpg.py`), profiles (`prof*.py`); PC tests (`chunkcmp.cpp`, `panocull.cpp`, `panoseam.cpp`, `jpegtest.cpp`, `mapypoitest.cpp`) |
| `lib/fastmem/` | memcpy / memset / strlen / 16- and 32-bit fills in ARM assembly (32 bytes a step), the C reference, its own README and emulator test (`test/armtest.sh`); the other `lib/` files include `fastmem.h` (add `-I.../lib/fastmem`). Copies: `webbrowser9300/fastmem/` (the browser builds from it) |
| `lib/jpegdec.*`, `jpegasm.*` | Baseline JPEG to RGB565, full or half size; IDCTs, colour, the usual block's Huffman in assembly (`symbian-s80v2-dev-tips-and-tricks/performance.md`) |
| `lib/pngdec.*` | PNG (zlib) to RGB565 |
| `lib/r3d.*`, `r3dgeo.*`, `r3dspan.*` | The 3D renderer: fixed point, bucket-sorted, affine / perspective textures, meshes with shared corners, chunk culling; the hot loops in assembly (section 4; the cache and the speed-ups: `symbian-s80v2-dev-tips-and-tricks/performance.md`) |
| `lib/rotate.*` | 16-bit pixel quarter turns (portrait screens, a turned map) |
| `lib/json.*` | A small JSON reader (no C library) |
| `lib/wait.h` | Blocking waits for worker threads with a nested active scheduler (from Net Helper 9300) |

---

## 1. Compiler crashes ("Internal compiler error") and how to get around them

GCC 2.9 crashes with `Internal compiler error` (often "insn does not satisfy its constraints")
on valid code. The crash is reported at a line inside the function that triggered it, but the
trigger is often a function that was *inlined* into it, or simply the size of the function.
Changing unrelated code in the same file can make an old crash come back (it happened twice in
Maps 9300: 0.78 and 0.91).

| Trigger | Fix |
|---|---|
| A `union` used to reinterpret bytes, e.g. `union { double d; unsigned w[2]; }` | Write and read through a pointer instead (`volatile unsigned* w = (volatile unsigned*) &d;`) and keep it in a small function of its own. See `MakeF64` in `vts3d.cpp`. |
| A small helper inlined many times into one function (`Rd::F64` inlined 7 times) | Define it out of line (in the .cpp, not in the class body). |
| One very large function | Split it into several functions. |

When it crashes, check the generated code afterwards (`arm-epoc-pe-objdump -d` on the `.o` under
`epoc32/build/.../armi/urel/`): the workaround must still do what you meant.

## 2. Things that compile but break on the phone

- **No writable static data.** An EKA1 `.app` or `.dll` can't have global or `static` variables
  that are written (petran refuses it, or it fails at load). Put state in your app or document
  class (`CBase` objects are zero-filled when created), or in `Dll::Tls()`. `static const` tables
  are fine. Remember that `static` locals in functions count too.
- **No `&_L("...")` temporaries kept by pointer.** `_L()` makes a temporary `TPtrC`. Its address
  is garbage after the statement. Use `_LIT` constants, or copy into a `TBuf`.
- **Pointers to locals that outlive the function.** Maps 9300's KERN-EXEC 3 crashes in 0.43–0.58
  were all one bug: the renderer kept a pointer to a texture description that was a local
  variable of the function that submitted the polygon; it was read later, after the stack had
  been reused. Anything a callee keeps must live in a member or on the heap (or be copied, as
  `R3D::Poly` now copies the `R3Tex`).
- **Descriptor overflow panics (USER 23 and friends).** `TBuf8<60>::Format` with a longer result
  panics the app. Size every `TBuf` for the worst case of its `Format` string (numbers: 11 chars
  each, `%S`: the source's maximum length, or `.Left(n)` it first). Before each delivery, check
  every `TBuf<N>` used with `Format`/`Append` against its format string.
- **Small stack (8 KB by default).** A few KB of local arrays plus a deep call chain overflow it
  silently (corruption, then KERN-EXEC 3 somewhere else). Big buffers go on the heap, allocated
  once (Maps 9300 moved a ~5 KB list to the heap in 0.46).
- **`new` doesn't leave, `new (ELeave)` does.** In plain C++ code shared with the PC (`r3d.cpp`,
  `vts3d.cpp`), use plain `new` and check for `NULL`.
- **Heap memory freed isn't free memory.** `HAL` free RAM doesn't go up when you `delete` things.
  The freed space stays in your heap. Count both: the phone's free RAM plus
  `User::Available()`, and call `User::CompressAllHeaps()` when really low. Otherwise an
  "evict until there's free RAM" loop never ends (see `Free3KB` in `mapy.cpp`).
- **No C library.** No `memset`, `memcpy`, `sin`, `sqrt` from libc. Use `Mem::Copy`,
  `Mem::FillZ`, `Math::Sin` (with `TReal`), or the fast versions in `lib/fastmem/`. Keep portable
  modules buildable on the PC with small wrappers (`#ifdef __SYMBIAN32__` → `Math::`, else
  `<math.h>`; see the top of `vts3d.cpp`).
- **`double` has the FPA word order**: the high 32-bit word comes first in memory, unlike a PC.
  Code that builds a `double` from file bytes must detect it (compare the words of `1.0`, as
  `MakeF64` does).
- **No 64-bit conversions between `double` and `long long`** worth using. Keep doubles within
  ±2^31 and convert to `int` (`VFloor` in `vts3d.cpp`).
- **GCC 2.9 skips the first test of a loop on a 64-bit mask in the high word.** `while (!(x & M))`,
  `while ((x & M) == 0)` or `for (; !(x & M); )` with `x` a `long long` and `M` a constant whose low
  32 bits are zero (e.g. `0x0020000000000000`) is compiled with the first round's test as `0 == 0`:
  the body always runs once. A value that already passes is changed anyway (a shift loses its top
  bit), or the loop never ends. Masks in the low word or in both words, `x < CONST`, `while (x)` and
  32-bit loops are fine (checked in the emulator). Test the high word as 32 bits instead:
  `while (!((unsigned int)(x >> 32) & (M >> 32)))`. Found in MuJS's number to text
  (`normalize_boundary` in `jsdtoa.c`: 1.5 printed as "0.5"; Browser 9300's `jsbench/mujs-gcc29.patch`).
  Look for such loops in any 64-bit code ported to this compiler (number formatting, bignums, hashes).
- **Keys while the virtual cursor is on** (`TEikVirtualCursor`, used to read the joystick as a
  mouse for looking around): **Space alone** never arrives as a key. Each press becomes ONE pointer
  event, the cursor's button down and up in turn (a toggle), so a held Space can't be seen. Use
  Space only for one action a press (read `EButton1Down` and `EButton1Up` alike, in
  `HandleWsEventL`), and other keys (E / C...) for anything held. Chr+Space does come as a key going
  down and up.
- **Shift is sticky on the 9300.** Press and let go of Shift, and the next key still has
  `EModifierShift`. For "while Shift is held", watch the Shift keys' own down / up events
  (`EStdKeyLeftShift` / `EStdKeyRightShift`) in `HandleWsEventL`.
- **Chr is `EModifierFunc`** (`0x2000` with its left/right bits); Chr+key comes with the key's normal
  scan code, so test the modifier, not the code.
- **Card and log writes are slow.** Writing a cache or log file on every event made the 3D view
  crawl. Buffer in RAM and flush every ~10 s, give the user a setting to turn the log file off,
  and prefer the memory card (E:) for caches.

## 2b. Build and packaging gotchas (from GnuBox for S80)

- **`rcomp` and long paths:** "Failed to open ...aif.rsc" / "RCOMP failed" when the toolchain's path
  plus the project's is very long. Keep both short (`~/sym`, `~/myapp`).
- **CRLF:** `rcomp` stops with "Unknown character 0xd" on files with Windows line ends (the SDK's
  examples have them): `sed -i 's/\r$//' file`.
- **`AppendNum(TUint32)` is ambiguous** in GCC 2.9: `AppendNum((TUint) x, EDecimal)`.
- **`TRAP(...)` right before `else`** breaks the parsing: put the TRAP in braces.
- **Renamed a source file:** `abld reallyclean` (stale objects get linked).
- **Check an app:** `petran -v <name>.app` must say `Data Size 0` (no writable static data).
- **Harmless noise:** perl "uninitialized value" warnings from `abld`, `Platform "" not supported`
  from `bldmake`.
- **The `.pkg`'s Series 80 platform line:** `(0x101F8ED2), 0, 0, 0, {"Series80ProductID"}`.
- **Case:** `#include`s, `LIBRARY x.lib` and the mmp / bld.inf names must match the lower-cased SDK.
- **Measured network speeds:** USB RNDIS IP passthrough at most ~107 kB/s; Bluetooth through GnuBox
  ~20-30 kB/s, held back by the 8 KB default TCP receive window per connection (more connections, or a
  bigger window: Maps 9300's TCP window setting).
- **A ready-made toolchain** (no setup run): `prebuilt/` in the private SDK repo `s80_DP_2_0_SDK`
  (Ubuntu 24.04 or newer); there too: the S80 API reference as HTML, the SDK's guides and examples.

## 3. Code GCC 2.9 makes slow, and what to write instead

Measured with the emulator (section 5), in instructions.

| You write | GCC 2.9 makes | Write instead |
|---|---|---|
| A 16-bit load or store (`unsigned short`, `TUint16`) in a hot loop | Two byte loads/stores plus shifts | Keep tables as 32-bit (`unsigned int pal[256]`), write 2 pixels per 32-bit store (`jpegdec.cpp`, `pngdec.cpp`). In assembly, `LDRH`/`STRH` are fine. |
| `x / y`, `x % y` with variable `y` | A call to `__divsi3` (~40–100 instructions): the ARM9 has no divide | A reciprocal table (`iRecip[n] = 2^30 / n` in `r3d.cpp`) and a multiply; shifts for powers of 2; `/ 3` as `* 0xAAAAAAAB >> 33`. |
| `long long a * long long b` | `__muldi3` or long inline code with spills | `(long long) intA * intB` (one `SMULL`), keep one side 32-bit. |
| `T x[3] = { a, b, c };` or `S s = { ... };` | A `memset` call (a byte loop), then the stores | Assign the fields one by one (`VtsDraw`). |
| Loops with many live variables | Every pointer and counter kept on the stack: ~90 instructions per vertex transform | Fewer live variables, or assembly for the hot loop. |
| A byte-by-byte `memcpy`/`memset`/fill | ~5 cycles a byte | `fm_memcpy`, `fm_fill16` (`lib/fastmem/`): 8 registers per `LDM`/`STM`. |
| `double` arithmetic (`a * b`, `(double) i`, `sqrt`) | A call into EUSER's floating-point emulation for every operation (`__muldf3`, `__floatsidf`, ...; tens to hundreds of cycles each) | Integers and fixed point. Maps 9300 1.13: the mesh decoder made ~110,000 such calls per 3D tile, now ~170 (a fixed-point transform built once per submesh, an integer square root for the shading). Find them: `arm-epoc-pe-objdump -dr x.o \| grep df3`. |
| One function with a fast path and a big slow path | The whole function's prologue (all registers saved, all pointers loaded) runs even when the fast path returns at once: ~100 instructions a call | Put the fast path in a small function of its own that calls the big one only when needed (`Block`/`BlockC` in `jpegdec.cpp`). |

## 4. Writing ARM assembly for it

Maps 9300's assembly lives in `.c` files as one top-level `__asm__("...")` block, guarded by
`#ifdef FM_ASM` (set for the phone build in `fastmem.h`), with a C version of every function
beside it. The PC build and the phone's self-test use the C versions; the emulator test checks
that both give the same results bit for bit (`r3dgeo.c`, `r3dspan.c`, `fastmem.c`).

Rules that matter on this target:

- **Calling convention:** arguments in r0–r3, the 5th and later on the stack (`[sp]` at entry,
  `[sp, #36]` after pushing 9 registers). Save r4–r11 and lr if used, return with `bx lr` (Thumb
  callers work). More than 4 arguments? Pass a pointer to a struct (`R3TriPrm`, `R3Rows`) and
  document the offsets next to it.
- **ARMv4 instruction rules** (the assembler enforces some, not all):
  - `MUL Rd, Rm, Rs`: Rd must differ from Rm. `MLA` likewise.
  - `SMULL/UMULL RdLo, RdHi, Rm, Rs`: RdLo, RdHi and Rm must all differ.
  - Immediates are an 8-bit value rotated by an even amount (`#16000` is fine, `#16001` isn't:
    load it from memory or build it with two instructions).
  - `LDRH Rd, [Rn], #2` (post-indexed halfword) is fine.
- **Get the exact C semantics.** A 64-bit product `(long long) n * inv` taken `>> 22` into 32
  bits is `UMULL lo, hi, nlo, inv`, then `MLA hi, nhi, inv, hi`, then subtract `nlo` from `hi`
  if `inv` is negative, then `(lo >> 22) | (hi << 10)` (`r3_texgrad` in `r3dgeo.c`). Signed vs
  unsigned compares (`BHI` vs `BGT`) and `asr` vs `lsr` are where results usually differ.
- **Range checks in one compare:** `(unsigned)(x + 30000) > 60000u` is "outside ±30000"
  (`ADD`, `CMP`, `BHI`).
- **Unroll the pixel loop by 4 and write 2 pixels per 32-bit store**, keep every value in
  registers, and move the per-row bookkeeping into the same function (`r3_rows_tex4`): the call
  and the struct per row cost more than the pixels of a small triangle.

- **Halfwords:** `LDRSH`/`LDRH`/`STRH` with a post-increment (`ldrsh r4, [r0], #2`) read 16-bit data
  at no extra cost in assembly. 16-bit vertex data (from the tile's middle) halved Maps 9300's cache
  misses there (1.13), but C code reading it gets slower (GCC 2.9's byte loads): keep such data for the
  assembly loops.

## 5. Measuring: the ARM emulator test

You can't profile on the phone, and the PC's compiler tells you nothing about GCC 2.9's code. So
Maps 9300 runs the phone's own machine code in the Unicorn ARM emulator (`pip install unicorn`):

1. Compile the modules with the phone's compiler and flags:
   `arm-epoc-pe-gcc -O2 -fno-exceptions -fno-rtti -D__MARM__ -D__MARM_ARMI__`.
2. Add a small driver (`test/arm/drv.cpp`, `drvvts.cpp`) with `extern "C"` entry points and the
   few things the missing OS would provide: a bump allocator for `operator new`/`delete`,
   `memset`/`memcpy`, `__pure_virtual`.
3. Link with `arm-epoc-pe-ld -e emu_init --image-base 0x10000 ... libgcc.a`, list the symbols
   with `arm-epoc-pe-nm`.
4. In Python, map the PE's sections into Unicorn, write the test data (a scene, a texture) into
   memory, call the entry points with r0–r3, and count instructions with a basic-block hook,
   per function (by the symbol table) and per block (the hot spots, then `objdump` them).
5. Hash the output (a frame) of the old and new code: they must match to the bit.

Ready-made: `maps9300/test/arm/build.sh` (renderer, panorama, random asm-vs-C tests) and
`buildvts.sh` + `emuvts.py` (the 3D view's city tiles from a scene dumped by `test/vtstest.cpp`
with `DUMP=`). `lib/fastmem/test/armtest.sh` does the same for fastmem. Also check that the
emulator ran **the same code** as the phone build: compare `objdump -d` of the app's objects and
the test's (Maps 9300's `emuhash.py`), since different flags give different code.

More in Maps 9300's `test/arm` (1.13):
- **A data-cache model** (`emuvts.py -c`): a memory-read hook simulating 8 KB, 2-way, 16-byte lines,
  read-allocate; misses per function. This is what found the layout changes in 4b.
- **Count the soft-float calls**: count how often the emulator enters `__muldf3`, `__adddf3`,
  `__floatsidf`, ... (their first block). `emudec.py` does this for the mesh decoder: ~110,000 calls
  a tile showed where its time went, which the instruction counts (libgcc's slow float code)
  and the PC (a real FPU) both hid.
- **Feed it what the OS would**: `drvdec.cpp` compiles the decoder without `__SYMBIAN32__`
  (`-U__SYMBIAN32__`, stub `math.h`/`string.h`) and gets the data already inflated, so zlib
  isn't needed in the emulator.

Instruction counts aren't time: cache misses and the 9300's slow memory add a lot. Use them to
compare versions, then confirm on the phone (Maps 9300 logs per-frame milliseconds).

## 7. Working method that saved phone installs

- Test everything you can on the PC first (the renderer, decoders and parsers are portable C++
  with PC tests in `maps9300/test/`), then in the emulator, and only then install.
- Keep a C reference for every piece of assembly and compare them on random inputs, including
  edge cases (out of range, behind the camera, empty, huge).
- When the compiler crashes or the phone crashes, write the cause and the fix next to the code
  and in the changelog. Several bugs came back months later in a new form.
- Every optimisation was checked against the old code: frame hashes of 3 scenes in the emulator,
  the PC renderer's 16 views, the JPEG decoder's output hashes for 49 files (plus files with
  restart markers, noise and truncation), and `objdump` of the app's objects against the
  emulator's (the same machine code ran in the test).

## 8. Building in a Cowork VM shell (no root, ~45 s a command)

The shell Claude gets on the user's laptop (Cowork) is a Linux VM without root, where each
command runs ~45 s at most and nothing survives in the background. The whole toolchain still
builds there in stages: `symbian-s80-build-tools/toolchain/setup_vm_noroot.sh debs | clone | gccsrc |
configure | make (repeat until rc=0) | install | tools | s60 | s80`:
- missing packages (flex, bison, 7z, cabextract, unshield) with `apt-get download` + `dpkg -x` into
  `~/loc`, put on `PATH`/`LD_LIBRARY_PATH`; 7z's wrapper script rewritten to its new place;
- texinfo's `ginfo` wants termcap: link it with the system's `libtinfo.so.6` (a symlink named
  `libtinfo.so` in a directory of your own, added to that Makefile's `LIBS`);
- `make` is restartable: run it again until it finishes.
Then the app builds in ~10 s, to the same machine code as elsewhere.

## Moved: findings and development tips

The findings that aren't about building moved to their own repo,
[symbian-s80v2-dev-tips-and-tricks](https://github.com/janseris/symbian-s80v2-dev-tips-and-tricks):
the data cache, what made the 3D view faster, JPEG decoding (`performance.md`), the other apps' tips
(`from-the-apps.md`), the Wikibooks tips (`wikibooks-tips.md`), networking and big uploads over GnuBox
(`networking.md`), and the DSP (`dsp/`).
